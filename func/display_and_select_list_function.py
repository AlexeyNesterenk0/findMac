from clear_screen_function import clear_screen
from color_constants import VALUE, INPUTLINE, RESET

   

def display_and_select_list(items):
    while True:
        # Вывод списка в терминале
        print('Найдено несколько пользователей:')

        for index, item in enumerate(items):
            print(f"{index + 1}. {VALUE}{item}{RESET}")
        
        # Предложение пользователю выбора
        choice = input(f"{INPUTLINE}Выберите искомого, введя соответствующий индекс: {RESET}")
        
        try:
            choice_index = int(choice) - 1  # Получаем индекс выбранного пункта
            if 0 <= choice_index < len(items):
                #print(f"Выбран пункт с индексом {choice_index}: {items[choice_index]}")
                break
            else:
                print("{ERROR}Неверный индекс выбранного пункта.{RESET}")
                clear_screen()
        except ValueError:
            print("{ERROR}Пожалуйста, введите корректный индекс.{RESET}")
            clear_screen()
    clear_screen()
    return choice_index

