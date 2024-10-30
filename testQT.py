import sys
from PyQt5.QtWidgets import QWidget, QApplication, QDialog, QLabel, QVBoxLayout
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import Qt

class LoadingAnimation(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Анимация загрузки')
        layout = QVBoxLayout()

        self.loading_label = QLabel(self)
        self.movie = QMovie('loading_animation.gif')  # Подставьте путь к вашему анимационному GIF

        self.loading_label.setMovie(self.movie)
        layout.addWidget(self.loading_label)

        self.movie.start()

        self.setLayout(layout)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)  # Устанавливаем виджет поверх других окон

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoadingAnimation()
    window.show()

    # Ваш процесс или задача
    # ...
    
    sys.exit(app.exec_())
