import smbus2, time

bus = smbus2.SMBus(1)
ADDR = 0x08

def send_command(cmd):
    data = [ord(c) for c in cmd]
    bus.write_i2c_block_data(ADDR, 0, data)

# Example
send_command("UP")
time.sleep(2)
send_command("STOP")