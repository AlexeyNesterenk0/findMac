import sys
import unittest

# Добавляем путь к родительскому каталогу в список путей поиска модулей
sys.path.append("/home/AVANGARD.LOC/anesterenko/Python3/findMAC/findMAC/")  # Добавляет родительский каталог в список поиска модулей
# импортируем функцию из другого файла
from findMac  import find_lag

# объявляем класс с тестом
class find_lagTestCase(unittest.TestCase):
    # функция, которая проверит, как формируется приветствие
   def test_find_lag(self):
        # отправляем тестовую строку в функцию
        result = find_lag("Port-Channel11")
        # задаём ожидаемый результат
        self.assertEqual(result, "Port-Channel11")

# запускаем тестирование
if __name__ == '__main__':
    unittest.main() 