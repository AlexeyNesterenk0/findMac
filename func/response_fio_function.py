from ldap3 import Server, Connection, SUBTREE, ALL_ATTRIBUTES

def response_fio(ldap_srv, ldap_user, ldap_password, samaccountname ):

    # Установка соединения с сервером Active Directory

    server = Server(f'ldap://{ldap_srv}')
    try:
        conn = Connection(server, ldap_user, ldap_password, auto_bind=True)

        # Задание базового DN и sAMAccountName для поиска
        parts = ldap_srv.split('.')
        base_dn = f'dc={parts[0]},dc={parts[1]}'
        # Формирование фильтра поиска
        search_filter = '(sAMAccountName={})'.format(samaccountname)

        # Выполнение поиска в Active Directory
        conn.search(search_base=base_dn, search_filter=search_filter, search_scope=SUBTREE, attributes=ALL_ATTRIBUTES)
        full_name = None 
        # Получение результатов поиска
        if conn.entries:
            # Получение ФИО пользователя из результатов поиска
            # Предположим, что ФИО пользователя находится в атрибуте 'displayName', вы можете использовать другой атрибут по необходимости
            full_name = conn.entries[0].displayName.value
        

    except ldap.LDAPError as e:
        print(e)

    # Закрытие соединения
    conn.unbind()
    return full_name if full_name else None
