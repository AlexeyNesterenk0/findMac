# findPort
Скрипт поиска порта подключения оконечного устройства в сети коммутаторов ELTEX по Имени пользователя, логину пользователя, 
мени АРМ пользователя, ip или MAC-адресу используя данные о соединении, полученные посредством LLDP

                    параметры подключения к коммутаторам, AD и базам прописываются в файле config.ini

                    Поиск по имени АРМ работает при предварительной web-публикации JSON структур, 
                    полученных при выполнении LOGON-скрипта run.cmd
                    и регулярном выполнеии powerShell скрипта  FindUserLogons_SRV.ps1
                    из репозитория https://github.com/AlexeyNesterenk0/FindUserLogons
                    [findPort](https://github.com/user-attachments/assets/d0089be9-d393-4dcf-9ae2-6979877cdf4a)
                    ![findPort](https://github.com/user-attachments/assets/d0089be9-d393-4dcf-9ae2-6979877cdf4a)
                    lldp должно быть настроено на аплинках предварительно.
