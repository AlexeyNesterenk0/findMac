import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMovie

class GifViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Просмотр GIF')
        self.setGeometry(100, 100, 400, 300)

        layout = QHBoxLayout()

        self.gif_label = QLabel(self)
        self.start_button = QPushButton('Запустить', self)
        self.start_button.clicked.connect(self.start_animation)
        self.stop_button = QPushButton('Остановить', self)
        self.stop_button.clicked.connect(self.stop_animation)

        #current_dir = os.getcwd()
        root_folder = '.'  # Начальная папка для поиска GIF файлов (текущая папка)
        gif_path = self.find_gif_in_subfolders(root_folder)

        self.movie = QMovie(gif_path)
        self.gif_label.setMovie(self.movie)
        self.movie.start()

        layout.addWidget(self.gif_label, alignment= Qt.AlignRight)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        self.setLayout(layout)

    def stop_animation(self):
        if self.movie.state() != QMovie.NotRunning:
            self.movie.stop()

    def start_animation(self):
        if self.movie.state() == QMovie.NotRunning:
            self.movie.start()


    def find_gif_in_subfolders(self, folder):
        for dirpath, _, filenames in os.walk(folder):
            for filename in filenames:
                if filename.endswith('Spinning octopus.gif'):
                    return os.path.join(dirpath, filename)
        return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = GifViewer()
    viewer.show()
    sys.exit(app.exec_())
