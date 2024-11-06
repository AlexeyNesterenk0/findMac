#- Script name: Network Operations Script with SSH
#- Python Version: Python 3
#- Description: This Python script uses the Paramiko library for SSH connections
#to network devices.
#It includes functions for establishing SSH connections, executing commands on remote switches, performing MAC address searches, and
#information about aggregated channels.
#The script interacts with network devices based on the provided configuration parameters in the config.ini file.
#===========================================================
#- Author: Alexey Nesterenko
#- Date: 10.2024
#- Configuration file: config.ini (contains connection parameters)
#- Dependencies: Paramiko library, configparser library
#===========================================================
from tqdm import tqdm
import paramiko
from paramiko.ssh_exception import SSHException
import getpass
import re
import os
import sys
import subprocess
import configparser
import socket
import requests
import warnings
#from io import StringIO

# Создание объекта для перехвата вывода
#error_output = StringIO()
#sys.stderr = error_output

warnings.filterwarnings("ignore") # Filter out all warnings

if not os.path.exists('config.ini'):    # Checking for file availability
    print(f"Ошибка: Файл 'config.ini'' отсутствует.")
    sys.exit()  # Close the application
config = configparser.ConfigParser()  # Creating a configuration object
config.read('config.ini')   # Reading the configuration file

RED = '\033[91m'  # ANSI Escape sequence for red
BLUE = '\u001b[34;1m'   # ANSI Escape sequence for blue
GREEN = '\u001b[32m'    # ANSI Escape sequence for green
GREENL = '\u001b[32;1m'    # ANSI Escape sequence for bright green color
YELLOW = '\u001b[33m'   # ANSI Escape sequence for yellow
YELLOWL = '\u001b[33;1m' # ANSI Escape sequence for bright yellow
PURPLE = '\u001b[35;1m' # ANSI Escape sequence for magenta
WHITE_ON_BLACK = '\033[7;37;40m' # ANSI escape sequence for white background and black font
RED_BACKGROUND_WHITE_TEXT = '\033[41m' # ANSI escape sequence for red background and black font
GREY = "\033[90m"     #ANSI Escape sequence for grey
RESET = '\033[0m'     # ANSI Escape sequence for color reset


# Getting values from a file
hostname = config['Connection']['hostname']
location = config['Connection']['location']
ssh_port = int(config['Connection']['port'])  # Converting a port to an integer
username = config['Connection']['username']
password = config['Connection']['password']
debug = int(config['Connection']['debug'])  # Convert debug to an integer
count = 0
count_string = 1 # default coint string erase
#debug = 1

#sys.path.append('findMAC/func')
sys.path.append('func')
from find_lag_function import find_lag
from check_mac_address_function import check_mac_address
from check_ip_address_function import check_ip_address
from find_sw_vendor_function import find_sw_vendor

def clear_screen(): # Function to clear the screen
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear the screen based on the operating system
    
def enter_pass():    
    result = getpass.getpass(f"{WHITE_ON_BLACK}Введите код доступа к ядру сети: {RESET}")
    clear_screen()  # Call the function to clear the screen
    return result

def is_valid_ip(ip_loc):
    try:
        socket.inet_aton(ip_loc)
        return True
    except socket.error:
        return False
    
def ping_host(ping_host_loc, packet, debug):
    try:
        process = subprocess.Popen(['ping', '-W', '1', '-c', packet, ping_host_loc], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if debug:
            print(output.decode())  # Декодируем вывод для отладки
        if error:  # Если есть ошибка
            return False
        lines = output.decode().splitlines()  # Разделяем вывод на строки
        for line in lines:
            if '0 received' in line or 'сбой' in line or 'failure' in line:  # Если все пакеты потеряны
                return False
        return True
    except subprocess.CalledProcessError:
        return False



def reconnect(hostname_loc):
    print(f"Узел {hostname_loc} недоступен")
    in_ansver = input(f"{WHITE_ON_BLACK}Повторить попытку подключения?: Y/N (N) {RESET}")
    if in_ansver.lower() == "y" or in_ansver.lower() == "yes":
        if ping_host(hostname_loc,'4',debug):
            return True
        else:
            reconnect(hostname_loc)
    else:
        sys.exit()

def find_next_sw(channel, vendor, port_loc):
    #for _ in tqdm(range(10), desc="Поиск следующего коммутатора", unit="%"):
    command = f"show lldp neighbors brief | inc {port_loc}" if vendor == "Vector" else f"show lldp neighbors | inc {port_loc}"
    output = run_ssh_command(channel, command)
    if debug:
        print(output)
    next_hostname_loc = find_next_hostname(output, port_loc)
    #erase_line(count_string)
    if next_hostname_loc is not None:
        return next_hostname_loc
    else:
        return None


def establish_ssh_connection(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc): # Function to establish an SSH connection
    client = paramiko.SSHClient() # Create an SSH client object
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if hostname_loc == core_loc and not ping_host(hostname_loc,'1',debug): # Check if the hostname is the core and if it is not reachable
        reconnect(core_loc)       # Reconnect to the host if it is the core and not reachable  
    try: # Try to establish an SSH connection using the specified parameters
        client.connect(hostname_loc, ssh_port_loc, username_loc, password_loc)
        if debug:
            print("Соединение установлено")
    except SSHException as e:      
        if hostname_loc == core_loc:
            print(f"Авторизация не пройдена")
            in_ansver = input(f"{WHITE_ON_BLACK}Повторить попытку авторизации?: Y/N (N) {RESET}") # Prompt user to retry authorization
            if in_ansver.lower() == "y" or in_ansver.lower() == "yes":
                password_loc = enter_pass()
                ping_host(hostname_loc,'4',debug)
                establish_ssh_connection(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc) # Recursive call to retry connection
            else:
                sys.exit() # Exit the program
        else:
            if debug:
                print(f"Авторизация не пройдена")
                print("Соединение закрыто")
            client = None
            password_loc = None       
    return client, password_loc # Return the SSH client object and password

def open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc):
    client, password_loc = establish_ssh_connection(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
    if client is not None:
        channel = client.invoke_shell()
        output = ''
        while True:
            if channel.recv_ready():
                output += channel.recv(1024).decode('utf-8')
                if output.endswith('#') or output.endswith('>'):
                    break
        return channel, password_loc
    else:
        return None, None

def run_ssh_command(channel, command):
    channel.send(command + '\n')
    output = ''
    while True:
        if channel.recv_ready():
            output += channel.recv(1024).decode('utf-8')
            if output.endswith('--More-- '):    # Check if the output contains '--More--' which indicates more scrolling is needed
                channel.send('\n')
            if output.endswith('#') or output.endswith('>'):    # Check if the output ends with prompt symbols '#' or '>'
                break
    if debug:
        print(output)
    return output

def find_mac_by_ip(output_loc, ip_loc):
    lines = output_loc.split('\n')
    mac_loc = None
    for line in lines:
        if 'vlan' in line and ip_loc in line:
            parts = line.split()
            mac_loc = parts[4]
            break
        if 'Vlan' in line and ip_loc in line:
            parts = line.split()
            mac_vector_loc = parts[1]
            mac_loc = mac_vector_loc.replace('-', ':')
            break
    if debug:
        print(f"MAC   {mac_loc}")
    return mac_loc if mac_loc else None
    

def find_mac_address(output_loc, mac_loc):
    lines = output_loc.split('\n')
    port_loc = None
    vlan_loc = None
    for line in lines:
        if "self" in line or "CPU" in line:           
            port_loc = "self"
            break 
        else:      
            if 'dyn' in line and mac_loc in line:
                parts = line.split()
                port_loc = parts[2]
                vlan_loc = parts[0]
                break
            if 'DYN' in line and mac_loc in line:
                parts = line.split()
                port_loc = parts[4]
                vlan_loc = parts[0]
                break
    if debug:
        print(f"Порт    {port_loc}")
        print(f"Vlan    {vlan_loc}")
    return port_loc if port_loc else None, vlan_loc if vlan_loc else None

def find_ip_address(output_loc, port_loc, vendor):
    lines = output_loc.split('\n')
    ip_loc = None
    for line in lines:
        if port_loc in line:
            parts = line.split()
            if vendor == 'Vector':
                ip_loc = parts[0]
            else:
                ip_loc = parts[3]
            break
    if debug:
        print(f"IPv4    {ip_loc}")
    return ip_loc if ip_loc else None

def find_cctname(output_loc):
    if debug:
         print(f"Поиск информации о размещении")
    result = re.search(r"\w-\d-\w", output_loc)
    if debug:
         print(f"Поиск информации о размещении завершен")
    return result.group() if result else None

def find_next_hostname(output_loc, port_loc):
    result = None
    lines = output_loc.split('\n')
    for line in lines:
        parts = line.split()
        if len(parts) > 0:
            port_in_part0 = parts[0]
            if port_in_part0 == port_loc:
                result = re.search(r"[sS][wW]\d+", line)
                if result is not None:
                    break
    return result.group() if result else None



def find_lag_ports(lag_loc,channel_loc, vendor):
    if debug:
         print(f"Поиск портов в LAG  {lag_loc}")
    number_lag = re.search(r"\d+", lag_loc)
    str_number_lag = number_lag.group()
    result = None
    if debug:
        print(f"{vendor} запрос информации о портах в {lag_loc} ")
    if vendor == 'Vector':
        output_loc = run_ssh_command(channel_loc, f"show interface port-channel {str_number_lag}")
    else:
        output_loc = run_ssh_command(channel_loc, f"show interface channel-group {str_number_lag}")  
    if debug:
         print(output_loc)
    if debug:
        print(f"{vendor} запрос информации о портах в {lag_loc} завершен")
    str_lag_ports_loc = ''
    lines = output_loc.split('\n')
    for line in lines:
        if vendor == 'Vector':
            if 'Ethernet' in line:
                result = result = [item for item in line.split(' ') if item.strip() != '' and item.strip() != 'n' and item.strip() != 'r']
                break
        else:
            if lag_loc in line and 'Act':
                parts = line.split(':')
                str_lag_ports_loc = parts[1].strip()
                if debug:
                    print(f"str Порты в LAG    {str_lag_ports_loc}")              
                if str_lag_ports_loc:
                    result = str_lag_ports_loc.split(",")
                break
    if debug:
        print(f"array Порты в LAG    {result}")
        print(f"Поиск портов в LAG  {lag_loc} завершен")
    return result if result else None

def find_unmanaged_switch(port_loc,channel_loc, vendor):
    if debug:
        print(f"Поиск информации о вендоре")
    if vendor == 'Vector':
       output_loc = run_ssh_command(channel_loc, f"show mac-address-table int {port_loc}")
    else:
        output_loc = run_ssh_command(channel_loc, f"show mac add int {port_loc}")
    if debug:
        print(output_loc)
        print(f"Поиск информации о вендоре завершен")

    mac_count = 0
    mac_loc = None
    mac_loc = re.findall(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',output_loc)
    
    if mac_loc is not None:
        mac_count = len(mac_loc)
    if debug:
        print(mac_count)
    if mac_count > 1:
        return True
    else:
        return False

def erase_line(count_string_loc):
    for i in range (1,count_string_loc + 1):
        print('\033[F', end='')  # Remove the previous line
        print(' '*160)   # Replace the current line with spaces
        print('\033[F', end='')  # Remove the previous line

def output_info(ip_address_loc,mac_loc):
    print(f"Информация об устройстве с физическим адресом {GREENL}{mac_loc}{RESET}:")
    print('\n')
    response_vendor(mac_loc)
    if ip_address_loc is not None:
        print(f"        {BLUE}IPv4{RESET}           {YELLOWL}{ip_address_loc}{RESET}")
        hostname_by_ip = None
        try:
            hostname_by_ip = socket.gethostbyaddr(ip_address_loc)[0] # Get the hostname corresponding to the IP address
            socket.gethostbyname
            hostname_by_ip_crop =hostname_by_ip.split('.')[0]
        except socket.herror as e:
            hostname_by_ip_crop = None
        if hostname_by_ip_crop is not None:             
            print(f"        {BLUE}hostname{RESET}       {YELLOWL}{hostname_by_ip_crop}{RESET}")
    print('\n')
            
def response_vendor(mac_loc):   
    for _ in tqdm(range(10), desc="Запрос информации о вендоре", unit="%"):
        response = requests.get(f"https://api.maclookup.app/v2/macs/{mac_loc}", verify=False)    # Make a GET request to the API URL with SSL verification disabled
        if response.status_code == 200: # Check if the request was successful
            data = response.json()  # Convert the response content to JSON format
    erase_line(count_string)
    properties = ["company", "country", "updated"] # Display specific properties in a formatted list
    for prop in properties:
        print(f"        {BLUE}{prop}{RESET}        {GREEN}{data.get(prop, 'N/A')}{RESET}")
    else:
        return False
    
                
def execute_script(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc, mac_loc,count_loc,ip_loc):
    channel, password_loc = open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
    if channel is not None:
        ccname = ''  
        output = ''
        next_hostname = None
        vlan = None
        lag = None
        lag_ports = None
        if ip_loc is not None:
            for _ in tqdm(range(10), desc=f"Поиск MAC по IP", unit="%"):
                if ping_host(ip_loc,'1', debug):
                    output = run_ssh_command(channel, f"show arp | inc {ip_loc}")
                    mac_loc = find_mac_by_ip(output, ip_loc)
            erase_line(count_string)
        mac_vector = mac_loc.replace(':', '-')
        for _ in tqdm(range(10), desc=f"Определение вендора {hostname_loc}", unit="%"):
            output = run_ssh_command(channel, f"show ver")
            vendor = find_sw_vendor(output, debug)
        erase_line(count_string)
        port_loc = None
        for _ in tqdm(range(10), desc=f"Поиск MAC на {hostname_loc}", unit="%"):
            if vendor == "Vector":            
                output = run_ssh_command(channel, f"show mac-address-table | inc {mac_vector}")
                port_loc, vlan = find_mac_address(output, mac_vector)
            else:
                output = run_ssh_command(channel, f"show mac add | inc {mac_loc}")
                port_loc, vlan = find_mac_address(output, mac_loc)
            ccname = find_cctname(output)
        erase_line(count_string)
        str_lag_ports = ''
        if port_loc is not None:  
            lag = None      
            lag_ports = None
            lag = find_lag(port_loc, debug)
            if lag is not None:
                lag_ports = find_lag_ports(lag,channel, vendor)
                if debug:
                    print(f"Порты в LAG    {lag_ports}")
            if count_loc == 0:
                if ip_loc == None:
                    for _ in tqdm(range(10), desc=f"Запрос IP", unit="%"):
                        if vendor == 'Vector':
                            output = run_ssh_command(channel, f"show arp | inc {mac_vector}")
                        else:   
                            output = run_ssh_command(channel, f"show arp | inc {mac_loc}")
                        ip_loc = find_ip_address(output, port_loc, vendor)
                    erase_line(count_string)
                output_info(ip_loc,mac_loc)
                print(f"MAC-адрес {GREENL}{mac_loc}{RESET} обнаружен:")
                if port_loc == 'self':
                    print(f"                     и это коммутатор {GREEN}{hostname_loc}{RESET}  в {PURPLE}{location}{RESET}")
                else:
                    if lag_ports is not None:
                        str_lag_ports = ",".join(lag_ports)
                        print(f"                     в группе портов {YELLOW}{lag}{RESET} на портах {YELLOWL}{str_lag_ports}{RESET} коммутатора {GREEN}{hostname_loc}{RESET}  в {PURPLE}{location}{RESET}")
                    else:  
                        print(f"                     на порту {YELLOWL}{port_loc}{RESET} коммутатора {GREEN}{hostname_loc}{RESET}  в {PURPLE}{location}{RESET}")
            else:
                if port_loc == 'self':
                    print(f"                     это коммутатор {GREEN}{hostname_loc}{RESET}  в КШ {PURPLE}{ccname}{RESET}",end = ' ')
                else:
                    if lag_ports is not None:
                        str_lag_ports = ",".join(lag_ports)
                        print(f"                     в группе портов {YELLOW}{lag}{RESET} на портах {YELLOWL}{str_lag_ports}{RESET} коммутатора {GREEN}{hostname_loc}{RESET}  в  КШ {PURPLE}{ccname}{RESET} в {YELLOW}{vlan}{RESET} VLAN",end = ' ')
                    else:  
                        print(f"                     на порту {YELLOWL}{port_loc}{RESET} коммутатора {GREEN}{hostname_loc}{RESET}  в КШ {PURPLE}{ccname}{RESET} в {YELLOW}{vlan}{RESET} VLAN",end = ' ')
            output=''
            if lag_ports is not None:
                for lag_port in lag_ports:
                    next_hostname = find_next_sw(channel, vendor, lag_port)
                    if next_hostname is not None:
                       break
            else:
                next_hostname = find_next_sw(channel, vendor, port_loc)
        else:
            print(f"MAC-адрес {GREENL}{mac_loc}{RESET} не обнаружен в сети")        
        if next_hostname is not None and next_hostname!=hostname_loc:
            count_loc+=1
            if ping_host(next_hostname,'1', debug):
                if debug:
                    print(f"Узел {PURPLE}{next_hostname}{RESET} доступен")
                channel.close()
                if debug:
                    print(f"Попытка подключения к  {PURPLE}{next_hostname}{RESET}")
                channel, password_loc = open_channel(core_loc, next_hostname, ssh_port_loc, username_loc, password_loc)
                if channel is not None:
                    execute_script(core_loc,next_hostname, ssh_port_loc, username_loc, password_loc, mac_loc, count_loc, None)
                else:
                    print(f"                     где-то за {PURPLE}{next_hostname}{RESET}, {RED}но этот узел недоступен для анализа{RESET}")   
                    print("Поиск завершен")    

            else:
                print("", end='\n')
                print(f"                     где-то за {PURPLE}{next_hostname}{RESET}, {RED}но этот узел недоступен для анализа{RESET}")            
                channel.close()
                print("Поиск завершен")
        else:
            channel, password_loc = open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
            if find_unmanaged_switch(port_loc,channel,vendor):
                print(f"{RED}где-то за неуправляемым свичем{RESET}" )
            else:
                print("", end='\n')      
            channel.close()
            print("Поиск завершен")

# Check for passed command arguments when calling the script
#if len(sys.argv) < 2:
#    print('Использование: python findMac.py "MAC"')
#else:
#    mac = sys.argv[1]
#password = enter_pass()
while True:    
    print(f"{GREY}--- Для выхода введите quit или q ---{RESET}")
    parametr = ''
    in_string = input(f"{WHITE_ON_BLACK}Введите HostName, IP или MAC-адрес искомого устройства: {RESET}")
    parametr = in_string.lower()
    clear_screen()
    if parametr == "quit" or parametr == "q":
        break
    if check_mac_address(parametr.strip()):  
        parametr = parametr.replace('-', ':') 
        execute_script(hostname, hostname, ssh_port, username, password, parametr, count, None)  
    elif check_ip_address(parametr.strip()):  
            execute_script(hostname, hostname, ssh_port, username, password, None, count, parametr)                 
    else:
            if ping_host(parametr.strip(), '1', debug):
                parametr = socket.gethostbyname(parametr.strip())  # get ip by hostname
                execute_script(hostname, hostname, ssh_port, username, password, None, count, parametr)
            else:
                print(f"{RED_BACKGROUND_WHITE_TEXT}Некорректный MAC, HostName или IP-адрес{RESET}")
                continue  
 
    
