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
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import QObject, QThread, pyqtSignal

warnings.filterwarnings("ignore") # Filter out all warnings
config = configparser.ConfigParser()  # Creating a configuration object
config.read('config.ini')   # Reading the configuration file

# Getting values from a file
hostname = config['Connection']['hostname']
location = config['Connection']['location']
ssh_port = int(config['Connection']['port'])  # Converting a port to an integer
username = config['Connection']['username']
password = config['Connection']['password']
debug = int(config['Connection']['debug'])  # Convert debug to an integer
count = 0

class Worker(QObject):
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()

    def __init__(self, gif_path, gif_label):
        super().__init__()
        self.gif_path = gif_path
        self.gif_label = gif_label
        self.movie = QMovie(self.gif_path)
        self.gif_label.setMovie(self.movie)
        self.start_signal.connect(self.movie.start)
        self.stop_signal.connect(self.movie.stop)

    def start_animation(self):
        self.start_signal.emit()

    def stop_animation(self):
        self.stop_signal.emit()


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 1024, 500)
        self.setWindowTitle('Поиск устройства')

        main_layout = QVBoxLayout(self)

        self.gif_label = QLabel(self)
        self.gif_label.setGeometry(1024, 1, 100, 100)

        self.worker_thread_search = QThread()
        self.worker_search = Worker(self.find_gif_in_subfolders('.'), self.gif_label)
        self.worker_search.moveToThread(self.worker_thread_search)
        self.worker_thread_search.start()

        self.info_line = QLabel('', self)
        self.info_line.setText('')
        self.info_line.setMaximumHeight(20)
        main_layout.addWidget(self.info_line)

        self.label = QLabel('', self)
        main_layout.addWidget(self.label)

        # Изменить цвет текста self.label на светло-серый
        self.label.setStyleSheet("background-color: lightgrey;")

        input_layout = QHBoxLayout()
        main_layout.addLayout(input_layout)

        self.heading = QLabel('Введите IP или MAC-адрес искомого устройства:', self)
        input_layout.addWidget(self.heading)

        self.line_edit = QLineEdit(self)
        input_layout.addWidget(self.line_edit)
        self.line_edit.setFocus()

        btn_layout = QHBoxLayout()
        main_layout.addLayout(btn_layout)

        self.search_btn = QPushButton('Поиск', self)
        self.search_btn.setToolTip('Запуск поиска')
        self.search_btn.clicked.connect(self.on_button_click)
        btn_layout.addWidget(self.search_btn)

        exit_btn = QPushButton('Выход', self)
        exit_btn.setToolTip('Завершить приложение')
        exit_btn.clicked.connect(self.exit_button_click)
        btn_layout.addWidget(exit_btn)

        self.setLayout(main_layout)
        
        self.line_edit.returnPressed.connect(self.on_enter_pressed)

        self.show()

    def append_text(self, text):
        current_text = self.label.text()
        new_text = f"{current_text}<br>{text}"
        self.label.setText(new_text)
    
    def display_info(self, text):
        new_text = f"<b>{text}</b>"
        self.info_line.setText(new_text)

    def set_label_text(self, text):
        self.label.setText(text)

    def on_button_click(self):
        self.worker_search.start_animation()
        self.label.clear()
        self.display_info("Поиск начат")
        input_text = self.line_edit.text()
        # Сделать кнопку неактивной
        self.search_btn.setEnabled(False)
        input_parametr(input_text)  
        self.worker_search.start_animation()
        # Сделать кнопку активной
        self.search_btn.setEnabled(True)

    def on_enter_pressed(self):
        self.on_button_click()

    def exit_button_click(self):
        sys.exit()

    def find_gif_in_subfolders(self, folder):
        for dirpath, _, filenames in os.walk(folder):
            for filename in filenames:
                if filename.endswith('loading_animation.gif'):
                    return os.path.join(dirpath, filename)
        return None

def input_parametr(in_string):
    input_parametr = in_string.lower()
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
               window.append_text(f"<span style='font-size: 16px;'>Некоректный MAC или IP -адрес</span>") 
 
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
    result = getpass.getpass(f"Введите код доступа к ядру сети: ")
    clear_screen()  # Call the function to clear the screen
    return result

""" def reconnect(self, hostname_loc):
     window.append_text(f"Узел {hostname_loc} недоступен")
    in_ansver = input(f"{WHITE_ON_BLACK}Повторить попытку подключения?: Y/N (N) ")
    if in_ansver.lower() == "y" or in_ansver.lower() == "yes":
        if ping_host(hostname_loc,'4'):
            return True
        else:
            reconnect(self, hostname_loc)
    else:
        sys.exit() """
    
def ping_host(host,packet):
    process = subprocess.Popen(['ping', '-c', packet, host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if debug:
         window.append_text(output)
    return True if not error else False

def establish_ssh_connection(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc): # Function to establish an SSH connection
    client = paramiko.SSHClient() # Create an SSH client object
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #if hostname_loc == core_loc and not ping_host(hostname_loc,'1'): # Check if the hostname is the core and if it is not reachable
        #reconnect(self, hostname_loc)       # Reconnect to the host if it is the core and not reachable  
    #try: # Try to establish an SSH connection using the specified parameters
    client.connect(hostname_loc, ssh_port_loc, username_loc, password_loc)
    #except Exception as e:   
    #if debug:
    window.display_info("Соединение установлено")
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
         window.append_text(output)
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
         window.append_text(f"MAC   {mac_loc}")
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
         window.append_text(f"Порт    {port_loc}")
         window.append_text(f"Vlan    {vlan_loc}")
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
         window.append_text(f"IPv4    {ip_loc}")
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
             window.append_text(f"LAG    {result}")
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
                 window.append_text(f"str Порты в LAG    {str_lag_ports_loc}")
            break
    if str_lag_ports_loc:
        result = str_lag_ports_loc.split(",")
        if debug:
             window.append_text(f"array Порты в LAG    {result}")
    return result if result else None

def find_unmanaged_switch(port_loc,channel_loc):
    output_loc = run_ssh_command(channel_loc, f"show mac add int {port_loc}")
    if debug:
         window.append_text(output_loc)
   
    mac_count = 0
    mac_loc = None
    mac_loc = re.findall(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',output_loc)
    
    if mac_loc is not None:
        mac_count = len(mac_loc)
    if debug:
         window.append_text(mac_count)
    if mac_count > 1:
        return True
    else:
        return False

def output_info(ip_address_loc,mac_loc):
    window.append_text(f"<span style='font-size: 16px;'>Информация об устройстве с физическим адресом <b>{mac_loc}</b>:</span>")
    window.append_text('\n')
    response_vendor(mac_loc)
    if ip_address_loc is not None:
        window.append_text(f"        <b>IPv4</b>           {ip_address_loc}")
        hostname_by_ip = None
        try:
            hostname_by_ip = socket.gethostbyaddr(ip_address_loc)[0] # Get the hostname corresponding to the IP address
            socket.gethostbyname
            hostname_by_ip_crop = hostname_by_ip.split('.')[0]
        except socket.herror as e:
            hostname_by_ip_crop = None
        if hostname_by_ip_crop is not None:             
            window.append_text(f"        <b>hostname</b>       {hostname_by_ip_crop}")
    window.append_text('\n')
            
def response_vendor(mac_loc):   
    window.display_info("Запрос информации о вендоре")
    response = requests.get(f"https://api.maclookup.app/v2/macs/{mac_loc}", verify=False)    # Make a GET request to the API URL with SSL verification disabled
    if response.status_code == 200: # Check if the request was successful
        data = response.json()  # Convert the response content to JSON format
    properties = ["company", "country", "updated"] # Display specific properties in a formatted list
    for prop in properties:
        window.append_text(f"        <b>{prop}</b>        {data.get(prop, 'N/A')}")
    else:
        return False
    
                
def execute_script(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc, mac_loc,count_loc,ip_loc):
    channel, password_loc = open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
    ccname = ''  
    output = ''
    next_hostname = None
    port_loc = None
    vlan = None
    lag = None
    lag_ports = None
    if ip_loc is not None:
        window.display_info("Поиск MAC по IP")
        #windows.worker_search.start_animation()
        if ping_host(ip_loc,'1'):
            output = run_ssh_command(channel, f"show arp | inc {ip_loc}")
            mac_loc = find_mac_by_ip(output, ip_loc)
       # windows.worker_search.stop_animation()
    

    window.display_info(f"Поиск MAC на {hostname_loc}")
    output = run_ssh_command(channel, f"show mac add | inc {mac_loc}")
    ccname = find_cctname(output)
    port_loc, vlan = find_mac_address(output, mac_loc)
    ###
    #erase_line()
    str_lag_ports = ''
    if port_loc is not None:
        if count_loc == 0:
            window.display_info("Запрос IP")
            output = run_ssh_command(channel, f"show arp | inc {mac_loc}")
            ip_address = find_ip_address(output, port_loc)
            ###
            #erase_line()
            output_info(ip_address, mac_loc)
            window.append_text(f"<span style='font-size: 16px;'>MAC-адрес <b>{mac_loc}</b> обнаружен:</span>")
            if port_loc == 'self':
                window.append_text(f"                     и это коммутатор <b>{hostname_loc}</b>  в <b>{location}<b>")
            else:
                lag = find_lag(port_loc)
                if lag is not None:
                    lag_ports = find_lag_ports(lag,channel)
                    if debug:
                        window.append_text(f"Порты в LAG    <b>{lag_ports}</b>")
                    if lag_ports is not None:
                        str_lag_ports = ",".join(lag_ports)
                    window.append_text(f"                     в группе портов <b>{lag}</b> на портах <b>{str_lag_ports}</b> коммутатора <b>{hostname_loc}</b>  в <b>{location}</b>")
                else:  
                    window.append_text(f"                     на порту <b>{port_loc}</b> коммутатора <b>{hostname_loc}</b>  в <b>{location}</b>")
        else:
            if port_loc == 'self':
                window.append_text(f"                     это коммутатор <b>{hostname_loc}</b>  в КШ <b>{ccname}</b>")
            else:
                window.append_text(f"                     на порту <b>{port_loc}</b> коммутатора <b>{hostname_loc}</b>  в КШ <b>{ccname}</b> в <b>{vlan}</b> VLAN")
        output=''
        if lag_ports is not None:
            for lag_port in lag_ports:
                window.display_info("Поиск следующего коммутатора")
                output = run_ssh_command(channel, f"show lldp neighbors | inc {lag_port}")
                next_hostname = find_next_hostname(output,lag_port)
                if next_hostname is not None:
                    break
        else:
            window.display_info("Поиск следующего коммутатора")
            output = run_ssh_command(channel, f"show lldp neighbors | inc {port_loc}")
            next_hostname = find_next_hostname(output,port_loc)         
    else:
        window.append_text(f"<span style='font-size: 16px;'>MAC-адрес <b>{mac_loc}</b> не обнаружен в сети</span>")
            
   
    if next_hostname is not None and next_hostname!=hostname_loc:
        count_loc+=1
        if ping_host(next_hostname,'1'):
            window.display_info(f"Узел {next_hostname} доступен")
            channel.close()
            channel, password_loc = open_channel(core_loc, hostname_loc, ssh_port_loc, username_loc, password_loc)
            execute_script(core_loc,next_hostname, ssh_port_loc, username_loc, password_loc, mac_loc, count_loc, None)
        else:
            window.append_text("")
            window.append_text(f"                     где-то за <b>{next_hostname}</b>, но этот узел недоступен для анализа")            
            channel.close()
            window.display_info("Поиск завершен")
    else:
        channel, password_loc = open_channel(core_loc,hostname_loc, ssh_port_loc, username_loc, password_loc)
        if find_unmanaged_switch(port_loc,channel):
            window.append_text("где-то за неуправляемым свичем" )
        else:
            window.append_text("")      
        channel.close()
        window.display_info("Поиск завершен")

# Check for passed command arguments when calling the script
#if len(sys.argv) < 2:
#     window.append_text('Использование: python findMac.py "MAC"')
#else:
#    mac = sys.argv[1]
#password = enter_pass()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = App()
    window.gif_label.raise_()  # Размещение self.gif_label поверх всех элементов
    sys.exit(app.exec_())

""" while True:    
     window.append_text(f"{GREY}--- Для выхода введите quit или q ---")
    in_string = input(f"{WHITE_ON_BLACK}Введите IP или MAC-адрес искомого устройства: ")
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
               window.append_text(f"{WHITE_ON_BLACK}Некоректный MAC или IP -адрес")
              # window.append_text(f"{WHITE_ON_BLACK}Ожидается ввод типа AA:BB:CC:DD:EE:FF ")
 """