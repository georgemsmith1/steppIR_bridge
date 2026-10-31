import socket
import time
import re

RIG_IP = "127.0.0.1"
RIG_PORT = 4532
MOXA_IP = "192.168.1.254"
MOXA_PORT = 4002

print("Connecting to Moxa NPort (Strict Data Out Set Release)...")
try:
    moxa_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    moxa_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    moxa_sock.settimeout(2.0)
    moxa_sock.connect((MOXA_IP, MOXA_PORT))
    print("-> Connected to Moxa successfully!")
except Exception as e:
    print(f"-> Failed to connect to Moxa: {e}")
    exit(1)

print("Connecting to Hamlib rigctld...")
try:
    rig_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rig_sock.settimeout(1.0)
    rig_sock.connect((RIG_IP, RIG_PORT))
    print("-> Connected to rigctld successfully!")
except Exception as e:
    print(f"-> Failed to connect to rigctld: {e}")
    moxa_sock.close()
    exit(1)

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
                        
                        moxa_sock.sendall(packet)
                        print(f"Sent {freq_khz} kHz -> Data Out Hex: {packet.hex().upper()}")
                        last_khz = freq_khz
                        
        except (socket.timeout, socket.error) as net_err:
            print(f"Network glitch: {net_err}")
            
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nClosing bridge connections safely...")
finally:
    rig_sock.close()
    moxa_sock.close()
