import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import json
import re

def response_base_srv(srv_base_loc, base_loc, username_loc, password_base_loc, find_parametr_loc):
    # Отправка GET-запроса с использованием аутентификации HTTPBasicAuth
    url = f"https://{srv_base_loc}/{base_loc}.json"
    response = requests.get(url, verify = False,  auth=HTTPBasicAuth(username_loc, password_base_loc))
    max_datetime_key, max_datetime_value = None, None
    # Проверить успешность GET запроса
    if response.status_code == 200:
        try:
            # Декодируем ответ с учетом utf-16LE и удаляем BOM символ
            json_data = json.loads(response.content.decode('utf-16LE').lstrip('\ufeff'))
            key = None
            for item in json_data:
                key = item.get('Key')
                if key == find_parametr_loc:
                    value = item.get('Value')
                    value_datetime = {}
                    for k, v in value.items():
                        if re.match(r"[A-Za-z]{3} \d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}", v):
                            value_datetime[k] = datetime.strptime(v, '%a %m/%d/%Y %H:%M:%S')
                        elif re.match(r"\d{2}\.\d{2}\.\d{4} \d+:\d{2}:\d{2}", v):
                            value_datetime[k] = datetime.strptime(v, '%d.%m.%Y %H:%M:%S')
                        else:
                            value_datetime[k] = datetime.strptime(v, '%d.%m.%Y %H:%M:%S')
                    max_datetime_key = max(value_datetime, key=lambda k: value_datetime[k])
                    max_datetime_value = value_datetime[max_datetime_key]

                    #print(f"  Item: {max_datetime_key}")
                    #print(f"  LastLogOn: {max_datetime_value}")
                    break
             
        except json.JSONDecodeError as e:
            print(f"Произошла ошибка при декодировании JSON: {e}")
        except Exception as e:
            print(f"Произошла ошибка: {e}")
    else:
       print(f"Ошибка при выполнении GET запроса: {response.status_code}")
    
    return (max_datetime_key, max_datetime_value) if max_datetime_key is not None else (None, None)
