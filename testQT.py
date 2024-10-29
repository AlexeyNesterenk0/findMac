import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox, QLabel, QLineEdit, QVBoxLayout

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 400, 300)
        self.setWindowTitle('Поиск устройства по MAC')

        btn = QPushButton('Поиск', self)
        btn.setToolTip('Запуск поиска')
        btn.resize(btn.sizeHint())
        btn.move(310, 250)
        btn.clicked.connect(self.on_button_click)

        exit_btn = QPushButton('Выход', self)
        exit_btn.setToolTip('Завершить приложение')
        exit_btn.resize(exit_btn.sizeHint())
        exit_btn.move(200, 250)
        exit_btn.clicked.connect(self.exit_button_click)

        self.label = QLabel('', self)
        self.label.setGeometry(50, 50, 100, 100)

        self.label.move(10, 10)

        self.line_edit = QLineEdit(self)
        self.line_edit.resize(self.line_edit.sizeHint())
        self.line_edit.move(10, 100)

        self.show()

    def set_label_text(self, text):
        self.label.setText(text)

    def on_button_click(self):
        input_text = self.line_edit.text()
        self.set_label_text(input_text)

    def exit_button_click(self):
        sys.exit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
