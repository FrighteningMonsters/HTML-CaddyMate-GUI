import smbus2, time

bus = smbus2.SMBus(1)
ADDR = 0x08

def send_command(cmd):
    data = [ord(c) for c in cmd]
    bus.write_i2c_block_data(ADDR, 0, data)

def send_command_for_duration(cmd, duration):
    end_time = time.time() + duration
    while time.time() < end_time:
        send_command(cmd)
        time.sleep(0.1)  # Small delay between sends
    send_command("STOP")

# Main loop
while True:
    user_input = input("\nEnter command (or 'q' to exit): ").strip().upper()
    
    if user_input == 'Q':
        print("Exiting...")
        break
    
    if user_input:
        print(f"Sending '{user_input}' for 10 seconds...")
        send_command_for_duration(user_input, 10)
        print("Stopped.")