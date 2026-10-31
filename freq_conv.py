#!/usr/bin/env python3
import sys

def convert_freq(freq_in):
    # Clean up common characters
    clean_input = freq_in.replace(",", "").replace(" ", "").strip()
    if not clean_input:
        return
        
    try:
        # Handle standard MHz float inputs (e.g., 14.2 or 7.030)
        if "." in clean_input:
            freq_hz = int(float(clean_input) * 1_000_000)
        else:
            # Handle raw Hz integer inputs (e.g., 14200000 or 7030000)
            freq_hz = int(clean_input)
    except ValueError:
        print("❌ Invalid input format! Use examples like '14.2' or '14200000'")
        sys.stdout.flush()
        return

    # 1. Apply the protocol specification: Divide Hz by 10
    target_val = freq_hz // 10
    
    # 2. Check for 24-bit unsigned bounds (0 to 16,777,215)
    if target_val < 0 or target_val > 16777215:
        print(f"❌ Value ({target_val}) out of 24-bit bounds! Max is 16,777,215.")
        sys.stdout.flush()
        return

    # 3. Convert to 3 Big-Endian bytes safely
    hex_bytes = target_val.to_bytes(3, byteorder='big')
    fh = hex_bytes[0]
    fm = hex_bytes[1]
    fl = hex_bytes[2]
    
    # Print out the results beautifully and immediately force a terminal flush
    print("\n" + "="*45)
    print(f" Calculated Frequency:  {freq_hz:,} Hz ({freq_hz/1e6:.4f} MHz)")
    print(f" Protocol Value (Hz/10): {target_val:,}")
    print(f" Full Hex String:        {hex_bytes.hex().upper()}")
    print("-"*45)
    print(f" Fh (Byte 1 / High):     0x{fh:02X}")
    print(f" Fm (Byte 2 / Mid):      0x{fm:02X}")
    print(f" Fl (Byte 3 / Low):      0x{fl:02X}")
    print("="*45 + "\n")
    sys.stdout.flush()

def main():
    print("=============================================")
    print("  SteppIR 24-bit Frequency Conversion Tool")
    print("  Type 'exit' or press Ctrl+C to quit.")
    print("  Try entering: '14.2' or '7030000'")
    print("=============================================\n")
    sys.stdout.flush()
    
    while True:
        try:
            # Print prompt and flush to guarantee visibility
            sys.stdout.write("Enter Frequency > ")
            sys.stdout.flush()
            
            user_in = sys.stdin.readline()
            if not user_in:  # Handle EOF / Ctrl+D
                break
                
            user_in = user_in.strip()
            if user_in.lower() in ['exit', 'quit']:
                break
                
            convert_freq(user_in)
        except KeyboardInterrupt:
            print("\nExiting tool.")
            sys.stdout.flush()
            break

if __name__ == "__main__":
    main()
