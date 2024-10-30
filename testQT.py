import sys, subprocess
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class PingThread(QThread):
    finished = pyqtSignal()

    def __init__(self, host, packet):
        super().__init__()
        self.host = host
        self.packet = packet

    def run(self):
        process = subprocess.Popen(['ping', '-c', self.packet, self.host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if debug:
            print(output)
        self.finished.emit()

class LoadingAnimation(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 400, 300)
        self.setWindowTitle('Анимация загрузки')
        layout = QVBoxLayout()

        self.loading_label = QLabel(self)
        #self.loading_label.move(250, 10)
        self.movie = QMovie('Spinning octopus.gif')  # Подставьте путь к вашему анимационному GIF

        self.loading_label.setMovie(self.movie)
        layout.addWidget(self.loading_label)

        self.movie.start()

        self.setLayout(layout)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)  # Устанавливаем виджет поверх других окон

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoadingAnimation()
    window.show()

    ping_thread = PingThread('192.168.10.110', '100')
    ping_thread.finished.connect(window.movie.stop)
    
    ping_thread.start()

    sys.exit(app.exec_())
