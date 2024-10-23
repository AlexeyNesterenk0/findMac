#- Script name: Network Operations Script with SSH
#- Python Version: Python 3
#- Description: This Python script uses the Paramiko library for SSH connections
#to network devices.
#It includes functions for establishing SSH connections, executing commands on remote switches, performing MAC address searches, and
#information about aggregated channels.
#The script interacts with network devices based on the provided configuration parameters in the config.ini file.
#===========================================================
#- Author: Alexey Nesterenko
#- Date: 21.10.2024
#- Configuration file: config.ini (contains connection parameters)
#- Dependencies: Paramiko library, configparser library
#===========================================================

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


# Filter out all warnings
warnings.filterwarnings("ignore")
# Creating a configuration object
config = configparser.ConfigParser()

# Reading the configuration file
config.read('config.ini')

RED = '\033[91m'      # ANSI Escape sequence for red
BLUE = '\u001b[34;1m'   # ANSI Escape sequence for blue
GREEN = '\u001b[32m'  # ANSI Escape sequence for green
GREENL = '\u001b[32;1m'  # ANSI Escape sequence for bright green color
YELLOW = '\u001b[33m' # ANSI Escape sequence for yellow
YELLOWL = '\u001b[33;1m' # ANSI Escape sequence for bright yellow
PURPLE = '\u001b[35;1m' # ANSI Escape sequence for magenta
WHITE_ON_BLACK = '\033[7;37;40m' # ANSI escape sequence for white background and black font
GREY = "\033[90m"     #ANSI Escape sequence for grey
RESET = '\033[0m'     # ANSI Escape sequence for color reset


# Getting values from a file
hostname = config['Connection']['hostname']
location = config['Connection']['location']
port = int(config['Connection']['port'])  # Converting a port to an integer
username = config['Connection']['username']
password = config['Connection']['password']
debug = int(config['Connection']['debug'])  # Convert debug to an integer
#debug = 1
count = 0


def check_mac_address(mac_address):
    # Регулярное выражение для проверки MAC-адреса
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')

    if mac_pattern.match(mac_address):
        return True
    else:
        return False

# Function to clear the screen
def clear_screen():
    # Clear the screen based on the operating system
    os.system('cls' if os.name == 'nt' else 'clear')
    
def enter_pass():    
    result = getpass.getpass(f"{WHITE_ON_BLACK}Введите код доступа к ядру сети: {RESET}")
    return result
    # Call the function to clear the screen
    clear_screen()

def reconnect(hostname_int):
    print(f"Узел {hostname_int} недоступен")
    in_ansver = input(f"{WHITE_ON_BLACK}Повторить попытку подключения?: Y/N (N) {RESET}")
    if in_ansver.lower() == "y" or in_ansver.lower() == "yes":
        if ping_host(hostname_int,'4'):
            return True
        else:
            reconnect(hostname_int)
    else:
        sys.exit()

    
def ping_host(host,packet):
    process = subprocess.Popen(['ping', '-c', packet, host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if debug:
        print(output)
    return True if not error else False

def establish_ssh_connection(core_int,hostname_int, port_int, username_int, password_int):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if hostname_int == core_int and not ping_host(hostname_int,'1'):
        reconnect(hostname_int)        
    try:
        client.connect(hostname_int, port_int, username_int, password_int)
    except Exception as e:
        print(f"Авторизация не пройдена")
        in_ansver = input(f"{WHITE_ON_BLACK}Повторить попытку авторизации?: Y/N (N) {RESET}")
        if in_ansver.lower() == "y" or in_ansver.lower() == "yes":
            client.close()
            password_int = enter_pass()
            ping_host(hostname_int,'4')
            establish_ssh_connection(core_int,hostname_int, port_int, username_int, password_int)
        else:
            sys.exit()
        
    if debug:
        print("Соединение установлено")
    return client, password_int

def open_channel(core_int,hostname_int, port_int, username_int, password_int):
    client, password_int = establish_ssh_connection(core_int,hostname_int, port_int, username_int, password_int)
    channel = client.invoke_shell()
    output = ''
    while True:
        if channel.recv_ready():
            output += channel.recv(1024).decode('utf-8')
            if output.endswith('#') or output.endswith('>'):
                break
    return channel, password_int

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

def find_mac_address(output_int, mac_int):
    lines = output_int.split('\n')
    port_int = None
    vlan_int = None
    for line in lines:
        if 'dyn' in line and mac in line:
            parts = line.split()
            port_int = parts[2]
            vlan_int = parts[0]
            break
    if debug:
        print(f"Порт    {port_int}")
        print(f"Vlan    {vlan_int}")
    return port_int if port_int else None, vlan_int if vlan_int else None

def find_ip_address(output_int):
    lines = output_int.split('\n')
    ip_int = None
    for line in lines:
        if 'vlan' in line and 'dyn' in line:
            parts = line.split()
            ip_int = parts[3]
            break
    if debug:
        print(f"IPv4    {ip_int}")
    return ip_int if ip_int else None

def find_cctname(output_int):
    result = re.search(r"\w-\d-\w", output_int)
    return result.group() if result else None

def find_next_hostname(output_int, port_int):
    result = None
    lines = output_int.split('\n')
    for line in lines:
        parts = line.split()
        port_in_part0 = parts[0]
        if port_in_part0 == port_int:
            result = re.search(r"[sS][wW]\d+", line)
            break
    return result.group() if result else None

def find_lag(port_int):
    output_int = re.search(r"Po\d+", port_int)
    if output_int is not None:
        result = output_int.group()
        if debug:
            print(f"LAG    {result}")
        return result if result else None
    else:
        return None

def find_lag_ports(lag_int,channel_int):
    number_lag = re.search(r"\d+", lag_int)
    str_number_lag = number_lag.group()
    output_int = run_ssh_command(channel_int, f"show interfaces channel-group {str_number_lag}")
    result = None
    str_lag_ports_int = ''
    lines = output_int.split('\n')
    for line in lines:
        if 'Act' in line and lag_int in line:
            parts = line.split(':')
            str_lag_ports_int = parts[1].strip()
            if debug:
                print(f"str Порты в LAG    {str_lag_ports_int}")
            break
    if str_lag_ports_int:
        result = str_lag_ports_int.split(",")
        if debug:
            print(f"array Порты в LAG    {result}")
    return result if result else None

def find_unmanaged_switch(port_int,channel_int):
    output_int = run_ssh_command(channel_int, f"show mac add int {port_int}")
    if debug:
        print(output_int)
   
    mac_count = 0
    mac_int = None
    mac_int = re.findall(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',output_int)
    
    if mac_int is not None:
        mac_count = len(mac_int)
    if debug:
        print(mac_count)
    if mac_count > 1:
        return True
    else:
        return False

def output_info(ip_address_int,mac_int):
    print(f"Информация об устройстве с физическим адресом {GREENL}{mac_int}{RESET}:")
    print('\n')
    response_vendor(mac_int)
    if ip_address_int is not None:
        print(f"        {BLUE}IPv4{RESET}           {YELLOWL}{ip_address_int}{RESET}")
        hostname_by_ip = None
        try:
            hostname_by_ip = socket.gethostbyaddr(ip_address_int)[0] # Get the hostname corresponding to the IP address
            hostname_by_ip_crop =hostname_by_ip.split('.')[0]
        except socket.herror as e:
            hostname_by_ip_crop = None
        if hostname_by_ip_crop is not None:             
            print(f"        {BLUE}hostname{RESET}       {YELLOWL}{hostname_by_ip_crop}{RESET}")
    print('\n')
            
def response_vendor(mac_int):
    # Make a GET request to the API URL with SSL verification disabled
    response = requests.get(f"https://api.maclookup.app/v2/macs/{mac_int}", verify=False)    
    if response.status_code == 200: # Check if the request was successful
        data = response.json()  # Convert the response content to JSON format        
    properties = ["company", "country", "updated"] # Display specific properties in a formatted list
    for prop in properties:
        print(f"        {BLUE}{prop}{RESET}        {GREEN}{data.get(prop, 'N/A')}{RESET}")
    else:
        return False
    
                
def execute_script(core_int,hostname_int, port_int, username_int, password_int, mac_int,count_int):
    channel, password_int = open_channel(core_int,hostname_int, port_int, username_int, password_int)
    ccname = ''  
    output = ''
    ip_address = None
    next_hostname = None
    port = None
    vlan = None
    lag = None
    lag_ports = None
    output = run_ssh_command(channel, f"show mac add | inc {mac_int}")
    ccname = find_cctname(output)
    port, vlan = find_mac_address(output, mac_int)
    str_lag_ports = ''
    if port is not None:
        if count_int == 0:
            output = run_ssh_command(channel, f"show arp | inc {mac_int}")
            ip_address = find_ip_address(output)
            output_info(ip_address,mac)
            print(f"MAC-адрес {GREENL}{mac_int}{RESET} обнаружен:")
            lag = find_lag(port)
            if lag is not None:
                lag_ports = find_lag_ports(lag,channel)
                if debug:
                    print(f"Порты в LAG    {lag_ports}")
                if lag_ports is not None:
                    str_lag_ports = ",".join(lag_ports)
                print(f"                     в группе портов {YELLOW}{lag}{RESET} на портах {YELLOWL}{str_lag_ports}{RESET} коммутатора {GREEN}{hostname_int}{RESET}  в {PURPLE}{location}{RESET}")
            else:  
                print(f"                     на порту {YELLOWL}{port}{RESET} коммутатора {GREEN}{hostname_int}{RESET}  в {PURPLE}{location}{RESET}")
        else:

            print(f"                     на порту {YELLOWL}{port}{RESET} коммутатора {GREEN}{hostname_int}{RESET}  в КШ {PURPLE}{ccname}{RESET} в {YELLOW}{vlan}{RESET} VLAN",end = ' ')
        output=''
        if lag_ports is not None:
            for lag_port in lag_ports:
                output = run_ssh_command(channel, f"show lldp neighbors | inc {lag_port}")
                next_hostname = find_next_hostname(output,lag_port)
                if next_hostname is not None:
                    break
        else:
            output = run_ssh_command(channel, f"show lldp neighbors | inc {port}")
            next_hostname = find_next_hostname(output,port)
    else:
        print(f"MAC-адрес {GREENL}{mac}{RESET} не обнаружен в сети")
            
   
    if next_hostname is not None and next_hostname!=hostname_int:
        count_int+=1
        if ping_host(next_hostname,'1'):
            if debug:
                print(f"Узел {PURPLE}{next_hostname}{RESET} доступен")
            channel.close()
            channel, password_int = open_channel(core_int, hostname_int, port_int, username_int, password_int)
            execute_script(core_int,next_hostname, port_int, username_int, password_int, mac_int, count_int)
        else:
            print("", end='\n')
            print(f"                     где-то за {PURPLE}{next_hostname}{RESET}, {RED}но этот узел недоступен для анализа{RESET}")            
            channel.close()
            print("Поиск завершен")
    else:
        channel, password_int = open_channel(core_int,hostname_int, port_int, username_int, password_int)
        if find_unmanaged_switch(port,channel):
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
    print('\n')    
    print(f"{GREY}--- Для выхода введите quit или q ---{RESET}")
    in_mac = input(f"{WHITE_ON_BLACK}Введите MAC-адрес искомого устройства: {RESET}")
    mac = in_mac.lower()
    if mac == "quit" or mac == "q":
        break
    if check_mac_address(mac):     
        clear_screen()
        execute_script(hostname, hostname, port, username, password, mac, count)
    else:
        print(f"{WHITE_ON_BLACK}Некоректный MAC-адрес{RESET}")
        print(f"{WHITE_ON_BLACK}Ожидается ввод типа AA:BB:CC:DD:EE:FF {RESET}")
