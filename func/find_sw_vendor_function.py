import re

def find_sw_vendor(output_loc, debug):
    sw_vendor_loc = re.search(r"QSW-", output_loc) 
    if sw_vendor_loc is not None:
        print('Производитель QTECH')
        return 'Vector' # Упрощено - команды и мак адреса имеют тот же синтаксис и формат, что и у Vector
    else:
        sw_vendor_loc = re.search(r"Vector", output_loc) 
        if sw_vendor_loc is not None:
            if debug:
                print('Производитель Vector')
            return 'Vector'
        else:
            if debug:
                print('Производитель Eltex')
            return 'Eltex'