import re 

def find_lag(port_loc):
    output_loc = re.search(r"Po\d+|Po[\w-]+\d+", port_loc, re.I)
    if output_loc is not None:
        result = output_loc.group()
        return result if result else None
    else:
        return None