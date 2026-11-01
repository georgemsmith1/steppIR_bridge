import socket
import time
import re
import json
import os

# Configuration file path
CONFIG_FILE = "config.json"

# Default fallback values
defaults = {
    "RIG_IP": "127.0.0.1",
    "RIG_PORT": 4532,
    "SDA100_IP": "192.168.1.254",
    "SDA100_PORT": 4002
}

def load_config():
    """Load settings from config file, fallback to defaults if missing or corrupted."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Ensure all required keys exist
                for key in defaults:
                    if key not in config:
                        config[key] = defaults[key]
                return config
        except Exception:
            print("Warning: Configuration file corrupted. Using defaults.")
            return defaults.copy()
    return defaults.copy()

def save_config(config):
    """Save the updated configuration values to the JSON file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print("-> Settings saved successfully!\n")
    except Exception as e:
        print(f"-> Error saving configuration: {e}\n")

def get_user_config():
    """Display current configurations and allow interactive updates."""
    config = load_config()
    
    print("=" * 50)
    print("      SteppIR SDA100 Bridge Configuration      ")
    print("=" * 50)
    print("Press [ENTER] to keep the current value, or type a new one.")
    print("-" * 50)
    
    # Query RIG_IP
    val = input(f"Rig IP [{config['RIG_IP']}]: ").strip()
    if val:
        config['RIG_IP'] = val
        
    # Query RIG_PORT
    while True:
        val = input(f"Rig Port [{config['RIG_PORT']}]: ").strip()
        if not val:
            break
        try:
            config['RIG_PORT'] = int(val)
            break
        except ValueError:
            print("Invalid port number. Please enter digits only.")

    # Query SDA100_IP
    val = input(f"SDA100 IP [{config['SDA100_IP']}]: ").strip()
    if val:
        config['SDA100_IP'] = val

    # Query SDA100_PORT
    while True:
        val = input(f"SDA100 Port [{config['SDA100_PORT']}]: ").strip()
        if not val:
            break
        try:
            config['SDA100_PORT'] = int(val)
            break
        except ValueError:
            print("Invalid port number. Please enter digits only.")

    print("-" * 50)
    save_config(config)
    return config

# --- Main Program Execution ---

# 1. Get configurations (Loads last saved, updates if user modifies)
config = get_user_config()

RIG_IP = config["RIG_IP"]
RIG_PORT = config["RIG_PORT"]
SDA100_IP = config["SDA100_IP"]
SDA100_PORT = config["SDA100_PORT"]

print(f"Connecting to SteppIR SDA100 controller at {SDA100_IP}:{SDA100_PORT}...")
try:
    sda_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sda_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sda_sock.settimeout(2.0)
    sda_sock.connect((SDA100_IP, SDA100_PORT))
    print("-> Connected to SDA100 successfully!")
except Exception as e:
    print(f"-> Failed to connect to SDA100: {e}")
    exit(1)

print(f"Connecting to Rig at {RIG_IP}:{RIG_PORT}...")
try:
    rig_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rig_sock.settimeout(1.0)
    rig_sock.connect((RIG_IP, RIG_PORT))
    print("-> Connected to Rig successfully!")
except Exception as e:
    print(f"-> Failed to connect to Rig: {e}")
    sda_sock.close()
    exit(1)

print("\nBridge running. Press Ctrl+C to stop.")
print("-" * 50)

last_khz = 0

try:
    while True:
        try:
            # Query frequency from rigctld
            rig_sock.sendall(b"f\n")
            raw_response = rig_sock.recv(1024).decode('utf-8').strip()
            
            # Clean up the response to extract digits
            freq_digits = "".join(re.findall(r'\d+', raw_response))
            
            if freq_digits:
                freq_hz = int(freq_digits)
                if freq_hz > 0:
                    freq_khz = int(freq_hz / 1000)
                    
                    # Gated transmission: Only send when a new spot is clicked!
                    if freq_khz != last_khz:
                        # 1. Apply Data Out Specification: Frequency in Hz divided by 10
                        target_val = freq_hz // 10
                        
                        # 2. Extract 3 big-endian bytes (Fh, Fm, Fl)
                        fh = (target_val >> 16) & 0xFF
                        fm = (target_val >> 8) & 0xFF
                        fl = target_val & 0xFF
                        
                        # 3. Assemble the exact 11-byte Data Out Set Command:
                        # Pos 0-1: 0x40, 0x41 -> @A
                        # Pos 2:   0x00       -> z (Mandatory Zero byte)
                        # Pos 3-5: fh, fm, fl -> 24-bit binary frequency value (Hz/10)
                        # Pos 6:   0x00       -> ac (Active motor flags filler)
                        # Pos 7:   0x00       -> dir (Force Normal/Forward tracking direction)
                        # Pos 8-9: 0x39, 0x63 -> vh, vl (ASCII '9' and 'c' Version signature strings)
                        # Pos 10:  0x0D       -> \r Carriage Return terminator
                        packet = bytes([0x40, 0x41, 0x00, fh, fm, fl, 0x00, 0x00, 0x39, 0x63, 0x0D])
                        
                        sda_sock.sendall(packet)
                        print(f"Sent {freq_khz} kHz -> Data Out Hex: {packet.hex().upper()}")
                        last_khz = freq_khz
                        
        except (socket.timeout, socket.error) as net_err:
            print(f"Network glitch: {net_err}")
            
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nClosing bridge connections safely...")
finally:
    rig_sock.close()
    sda_sock.close()
EOF
