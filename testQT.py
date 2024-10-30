import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import QObject, QThread, pyqtSignal

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

class GifViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Управление анимацией GIF')
        self.setGeometry(100, 100, 400, 350)

        self.layout = QVBoxLayout()

        self.gif_label = QLabel(self)
        self.layout.addWidget(self.gif_label)

        self.start_button = QPushButton('Старт', self)
        self.layout.addWidget(self.start_button)

        self.stop_button = QPushButton('Стоп', self)
        self.layout.addWidget(self.stop_button)

        self.setLayout(self.layout)

        self.worker_thread = QThread()
        self.worker = Worker(self.find_gif_in_subfolders('.'), self.gif_label)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.start_button.clicked.connect(self.worker.start_animation)
        self.stop_button.clicked.connect(self.worker.stop_animation)

    def find_gif_in_subfolders(self, folder):
        for dirpath, _, filenames in os.walk(folder):
            for filename in filenames:
                if filename.endswith('.gif'):
                    return os.path.join(dirpath, filename)
        return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = GifViewer()
    viewer.show()
    sys.exit(app.exec_())
