import ldap
from ldap3 import Server, Connection, SUBTREE, ALL_ATTRIBUTES

def response_login(ldap_srv, ldap_user, ldap_password, part_of_full_name):
    
    # Установка соединения с сервером Active Directory
    server = Server(f'ldap://{ldap_srv}')
    
    try:
        conn = Connection(server, ldap_user, ldap_password, auto_bind=True)

        # Задание базового DN и sAMAccountName для поиска
        parts = ldap_srv.split('.')
        base_dn = f'dc={parts[0]},dc={parts[1]}'
        
        # Формирование фильтра поиска для части displayName
        search_filter = f'(&(displayName=*{part_of_full_name}*))'

        # Выполнение поиска в Active Directory
        conn.search(search_base=base_dn, search_filter=search_filter, search_scope=SUBTREE, attributes=ALL_ATTRIBUTES)
        
        login_list = []
        displayName_list = []
        
        # Получение результатов поиска
        for entry in conn.entries:
            # Получение sAMAccountName и displayName пользователя из результатов поиска
            if 'sAMAccountName' in entry and 'displayName' in entry:
                login_list.append(entry.sAMAccountName.value)
                displayName_list.append(entry.displayName.value)
        
    except ldap.LDAPError as e:
        print(e)
        return None, None
    finally:
        # Закрытие соединения
        conn.unbind()
    
    return login_list, displayName_list if login_list else (None, None)


