import subprocess


# this is the file, where RPi stores the temperature measurements
TEMP_FILE = '/sys/class/thermal/thermal_zone0/temp'


def get_temp():
    """Get current clock temp"""
    with open(TEMP_FILE, 'r') as f:
        f_content = f.read()
        return round(int(f_content) / 1000, 1)


def get_throttle_status():
    """Get throttle status and error codes"""
    """https://www.raspberrypi.org/documentation/raspbian/applications/vcgencmd.md#:~:text=vcgencmd%20is%20a%20command%20line,that%20will%20be%20described%20here."""
    # exec shell command
    sb = subprocess.Popen(['vcgencmd', 'get_throttled'], stdout=subprocess.PIPE)
    cmd_out = sb.communicate()
    # grab string after '='
    hex_string = cmd_out[0].decode().split('=')[1].strip()
    # convert to binary, and then to list, and strip the leading '0b' identifier
    bin_list = list(bin(int(hex_string, 16)))[2:]
    # reverse list to align with error codes
    bin_list.reverse()
    # use mapping provided on https://www.raspberrypi.org/
    bit_mapping = {
        0: 'Under-voltage detected',
        1: 'Arm frequency capped',
        2: 'Currently throttled',
        3: 'Soft temperature limit active',
        16: 'Under-voltage has occurred previously',
        17: 'Arm frequency capping has occurred',
        18: 'Throttling has occurred previously',
        19: 'Soft temperature limit has occurred'
    }
    err_codes = [bit_mapping[idx] for idx, val in enumerate(bin_list) if int(val) == 1]
    return hex_string, err_codes


if __name__ == '__main__':
    temp = get_temp()
    print(f"Temp = {temp}'C")
    throttle_hex_string, throttle_err_codes = get_throttle_status()
    print(f"Throttle = {throttle_hex_string} ({'; '.join(throttle_err_codes)})")
