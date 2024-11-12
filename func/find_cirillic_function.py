def check_cyrillic(input_text):
    cyrillic = False
    for char in input_text:
        if 'а' <= char.lower() <= 'я' or char.lower() == 'ё':
            cyrillic = True
            break
    return cyrillic