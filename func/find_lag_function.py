import re 

def find_lag(port_loc):
    output_loc = re.search(r"Po\d+|Po[\w-]+\d+", port_loc, re.I)
    result = None
    if output_loc is not None:
        result = output_loc.group()
    if debug:
        print(f'LAG    {result}')
    return result if result else None

