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
import getpass
import re
import os
import sys
import subprocess
import configparser
import socket
import requests
import warnings

warnings.filterwarnings("ignore") # Filter out all warnings
# Проверка наличия файла
if not os.path.exists('config.ini'):
    print(f"Ошибка: Файл 'config.ini'' отсутствует.")
    sys.exit()  # Закрыть приложение
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


def check_mac_address(mac_address):
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')  # Regular expression for checking the MAC address

    if mac_pattern.match(mac_address):
        return True
    else:
        return False

def check_ip_address(ip_address):
    ip_pattern = re.compile(r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?).(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?).(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?).(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')  # Regular expression for checking the IP address

    if ip_pattern.match(ip_address):
        return True
    else:
        return False

def clear_screen(): # Function to clear the screen
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear the screen based on the operating system
    
def enter_pass():    
    result = getpass.getpass(f"{WHITE_ON_BLACK}Введите код доступа к ядру сети: {RESET}")
    clear_screen()  # Call the function to clear the screen
    return result

def reconnect(hostname_loc):
    print(f"Узел {hostname_loc} недоступен")
    in_ansver = input(f"{WHITE_ON_BLACK}Повторить попытку подключения?: Y/N (N) {RESET}")
    if in_ansver.lower() == "y" or in_ansver.lower() == "yes":
        if ping_host(hostname_loc,'4'):
            return True
        else:
            reconnect(hostname_loc)
    else:
        sys.exit()
    
def ping_host(host,packet):
    process = subprocess.Popen(['ping', '-c', packet, host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if debug:
        print(output)
    return True if not error else False

def establish_ssh_connection(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc): # Function to establish an SSH connection
    client = paramiko.SSHClient() # Create an SSH client object
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if hostname_loc == core_loc and not ping_host(hostname_loc,'1'): # Check if the hostname is the core and if it is not reachable
        reconnect(hostname_loc)       # Reconnect to the host if it is the core and not reachable  
    try: # Try to establish an SSH connection using the specified parameters
        client.connect(hostname_loc, ssh_port_loc, username_loc, password_loc)
    except Exception as e:
        print(f"Авторизация не пройдена")
        in_ansver = input(f"{WHITE_ON_BLACK}Повторить попытку авторизации?: Y/N (N) {RESET}") # Prompt user to retry authorization
        if in_ansver.lower() == "y" or in_ansver.lower() == "yes":
            client.close()
            password_loc = enter_pass()
            ping_host(hostname_loc,'4')
            establish_ssh_connection(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc) # Recursive call to retry connection
        else:
            sys.exit() # Exit the program
        
    if debug:
        print("Соединение установлено")
    return client, password_loc # Return the SSH client object and password

def open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc):
    client, password_loc = establish_ssh_connection(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
    channel = client.invoke_shell()
    output = ''
    while True:
        if channel.recv_ready():
            output += channel.recv(1024).decode('utf-8')
            if output.endswith('#') or output.endswith('>'):
                break
    return channel, password_loc

def run_ssh_command(channel, command):
    channel.send(command + '\n')
    output = ''
    while True:
        if channel.recv_ready():
            output += channel.recv(1024).decode('utf-8')
            if output.endswith('#') or output.endswith('>'):
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
    if debug:
        print(f"MAC   {mac_loc}")
    return mac_loc if mac_loc else None
    

def find_mac_address(output_loc, mac_loc):
    lines = output_loc.split('\n')
    port_loc = None
    vlan_loc = None
    for line in lines:
        if "self" in line:           
            port_loc = "self"
            break 
        else:      
            if 'dyn' in line and mac_loc in line:
                parts = line.split()
                port_loc = parts[2]
                vlan_loc = parts[0]
                break
    if debug:
        print(f"Порт    {port_loc}")
        print(f"Vlan    {vlan_loc}")
    return port_loc if port_loc else None, vlan_loc if vlan_loc else None

def find_ip_address(output_loc, port_loc):
    lines = output_loc.split('\n')
    ip_loc = None
    for line in lines:
        if port_loc in line:
            parts = line.split()
            ip_loc = parts[3]
            break
    if debug:
        print(f"IPv4    {ip_loc}")
    return ip_loc if ip_loc else None

def find_cctname(output_loc):
    result = re.search(r"\w-\d-\w", output_loc)
    return result.group() if result else None

def find_next_hostname(output_loc, port_loc):
    result = None
    lines = output_loc.split('\n')
    for line in lines:
        parts = line.split()
        port_in_part0 = parts[0]
        if port_in_part0 == port_loc:
            result = re.search(r"[sS][wW]\d+", line)
            break
    return result.group() if result else None

def find_lag(port_loc):
    output_loc = re.search(r"Po\d+", port_loc)
    if output_loc is not None:
        result = output_loc.group()
        if debug:
            print(f"LAG    {result}")
        return result if result else None
    else:
        return None

def find_lag_ports(lag_loc,channel_loc):
    number_lag = re.search(r"\d+", lag_loc)
    str_number_lag = number_lag.group()
    output_loc = run_ssh_command(channel_loc, f"show interfaces channel-group {str_number_lag}")
    result = None
    str_lag_ports_loc = ''
    lines = output_loc.split('\n')
    for line in lines:
        if 'Act' in line and lag_loc in line:
            parts = line.split(':')
            str_lag_ports_loc = parts[1].strip()
            if debug:
                print(f"str Порты в LAG    {str_lag_ports_loc}")
            break
    if str_lag_ports_loc:
        result = str_lag_ports_loc.split(",")
        if debug:
            print(f"array Порты в LAG    {result}")
    return result if result else None

def find_unmanaged_switch(port_loc,channel_loc):
    output_loc = run_ssh_command(channel_loc, f"show mac add int {port_loc}")
    if debug:
        print(output_loc)
   
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

def erase_line():
    print('\033[F', end='')  # Remove the previous 
    print(' '*160)   # Replace the current line with
    print('\033[F', end='')  # Remove the previous 

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
    erase_line()
    properties = ["company", "country", "updated"] # Display specific properties in a formatted list
    for prop in properties:
        print(f"        {BLUE}{prop}{RESET}        {GREEN}{data.get(prop, 'N/A')}{RESET}")
    else:
        return False
    
                
def execute_script(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc, mac_loc,count_loc,ip_loc):
    channel, password_loc = open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
    ccname = ''  
    output = ''
    #ip_address = None
    next_hostname = None
    port_loc = None
    vlan = None
    lag = None
    lag_ports = None
    if ip_loc is not None:
        for _ in tqdm(range(10), desc=f"Поиск MAC по IP", unit="%"):
            if ping_host(ip_loc,'1'):
                output = run_ssh_command(channel, f"show arp | inc {ip_loc}")
                mac_loc = find_mac_by_ip(output, ip_loc)
        erase_line()

    for _ in tqdm(range(10), desc=f"Поиск MAC на {hostname_loc}", unit="%"):
        output = run_ssh_command(channel, f"show mac add | inc {mac_loc}")
        ccname = find_cctname(output)
        port_loc, vlan = find_mac_address(output, mac_loc)
    erase_line()
    str_lag_ports = ''
    if port_loc is not None:
        if count_loc == 0:
            for _ in tqdm(range(10), desc=f"Запрос IP", unit="%"):
                output = run_ssh_command(channel, f"show arp | inc {mac_loc}")
                ip_address = find_ip_address(output, port_loc)
            erase_line()
            output_info(ip_address,mac_loc)
            print(f"MAC-адрес {GREENL}{mac_loc}{RESET} обнаружен:")
            if port_loc == 'self':
                print(f"                     и это коммутатор {GREEN}{hostname_loc}{RESET}  в {PURPLE}{location}{RESET}")
            else:
                lag = find_lag(port_loc)
                if lag is not None:
                    lag_ports = find_lag_ports(lag,channel)
                    if debug:
                        print(f"Порты в LAG    {lag_ports}")
                    if lag_ports is not None:
                        str_lag_ports = ",".join(lag_ports)
                    print(f"                     в группе портов {YELLOW}{lag}{RESET} на портах {YELLOWL}{str_lag_ports}{RESET} коммутатора {GREEN}{hostname_loc}{RESET}  в {PURPLE}{location}{RESET}")
                else:  
                    print(f"                     на порту {YELLOWL}{port_loc}{RESET} коммутатора {GREEN}{hostname_loc}{RESET}  в {PURPLE}{location}{RESET}")
        else:
            if port_loc == 'self':
                print(f"                     это коммутатор {GREEN}{hostname_loc}{RESET}  в КШ {PURPLE}{ccname}{RESET}",end = ' ')
            else:
                print(f"                     на порту {YELLOWL}{port_loc}{RESET} коммутатора {GREEN}{hostname_loc}{RESET}  в КШ {PURPLE}{ccname}{RESET} в {YELLOW}{vlan}{RESET} VLAN",end = ' ')
        output=''
        if lag_ports is not None:
            for lag_port in lag_ports:
                #for _ in tqdm(range(10), desc=f"Поиск следующего коммутатора", unit="%"):
                output = run_ssh_command(channel, f"show lldp neighbors | inc {lag_port}")
                next_hostname = find_next_hostname(output,lag_port)
                #erase_line()
                if next_hostname is not None:
                    break
        else:
            #for _ in tqdm(range(10), desc=f"Поиск следующего коммутатора", unit="%"):
            output = run_ssh_command(channel, f"show lldp neighbors | inc {port_loc}")
            next_hostname = find_next_hostname(output,port_loc)
            #erase_line()
    else:
        print(f"MAC-адрес {GREENL}{mac_loc}{RESET} не обнаружен в сети")
            
   
    if next_hostname is not None and next_hostname!=hostname_loc:
        count_loc+=1
        if ping_host(next_hostname,'1'):
            if debug:
                print(f"Узел {PURPLE}{next_hostname}{RESET} доступен")
            channel.close()
            channel, password_loc = open_channel(core_loc, hostname_loc, ssh_port_loc, username_loc, password_loc)
            execute_script(core_loc,next_hostname, ssh_port_loc, username_loc, password_loc, mac_loc, count_loc, None)
        else:
            print("", end='\n')
            print(f"                     где-то за {PURPLE}{next_hostname}{RESET}, {RED}но этот узел недоступен для анализа{RESET}")            
            channel.close()
            print("Поиск завершен")
    else:
        channel, password_loc = open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
        if find_unmanaged_switch(port_loc,channel):
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
    in_string = input(f"{WHITE_ON_BLACK}Введите IP или MAC-адрес искомого устройства: {RESET}")
    input_parametr = in_string.lower()
    if input_parametr == "quit" or input_parametr == "q":
        break
    if check_mac_address(input_parametr.strip()):     
        clear_screen()
        execute_script(hostname, hostname, ssh_port, username, password, input_parametr, count, None)
    else:
        if check_ip_address(input_parametr.strip()):  
            clear_screen()
            execute_script(hostname, hostname, ssh_port, username, password, None, count, input_parametr)
        else:
            if ping_host(input_parametr,'1'):
                clear_screen()
                ip_by_hostname = socket.gethostbyname(input_parametr)[0] # Get the hostname corresponding to the IP address
                execute_script(hostname, hostname, ssh_port, username, password, None, count, ip_by_hostname)                
            else:
              print(f"{WHITE_ON_BLACK}Некоректный MAC или IP -адрес{RESET}")
              #print(f"{WHITE_ON_BLACK}Ожидается ввод типа AA:BB:CC:DD:EE:FF {RESET}")
