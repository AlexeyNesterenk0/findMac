import re

def check_mac_address(mac_address):
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')  # Regular expression for checking the MAC address

    if mac_pattern.match(mac_address):
        return True
    else:
        return False