import os
import sys
from PyQt5 import QtGui, QtCore, QtWidgets

folder = './ui'


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    image = QtGui.QPixmap()
    for file in os.listdir(folder):
        if file.endswith('.png'):
            file_name = os.path.join(folder, file)
            image.load(file_name)
            f = QtCore.QFile(file_name)
            f.open(QtCore.QIODevice.WriteOnly)
            image.save(f, 'png')
    sys.exit(app.exec_())