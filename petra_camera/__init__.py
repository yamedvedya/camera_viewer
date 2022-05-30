import sys
import os
import logging
import traceback
import time

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from pathlib import Path
from PyQt5 import QtWidgets
from optparse import OptionParser
from logging.handlers import RotatingFileHandler

from petra_camera.main_window import PETRACamera, APP_NAME
from .version import __version__


# --------------------------------------------------------------------
def excepthook(exc_type, exc_value, traceback_obj):
    """
    Global function to catch unhandled exceptions. This function will result in an error dialog which displays the
    error information.

    :param exc_type: exception type
    :param exc_value: exception value
    :param traceback_obj: traceback object
    :return:
    """
    separator = '-' * 80
    log_path = f"{os.path.expanduser('~')}/.petra_camera/error.log"
    time_string = time.strftime("%Y-%m-%d, %H:%M:%S")
    tb_info_file = StringIO()
    traceback.print_tb(traceback_obj, None, tb_info_file)
    tb_info_file.seek(0)
    tb_info = tb_info_file.read()
    errmsg = '%s: \n%s' % (str(exc_type), str(exc_value))
    sections = [separator, time_string, separator, errmsg, separator, tb_info]
    msg = '\n'.join(sections)
    try:
        f = open(log_path, "a")
        f.write(msg)
        f.close()
    except IOError:
        pass

    msg_box = QtWidgets.QMessageBox()
    msg_box.setModal(False)
    msg_box.setIcon(QtWidgets.QMessageBox.Critical)
    msg_box.setText(msg)
    msg_box.setInformativeText(msg)
    msg_box.setWindowTitle("Error")
    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg_box.show()


# --------------------------------------------------------------------
def setup_logger(args):
    if not os.path.exists(f"{str(Path.home())}/.petra_camera"):
        os.mkdir(f"{str(Path.home())}/.petra_camera")

    filename = f"{str(Path.home())}/.petra_camera/camera.log"
    print(f"Logs to file: {filename}")

    log_level = logging.DEBUG

    log_formatter = logging.Formatter("%(asctime)s %(filename)s:%(lineno)d %(levelname)-8s %(message)s")

    my_handler = RotatingFileHandler(filename, mode='a', maxBytes=5 * 1024 * 1024,
                                     backupCount=2, encoding=None, delay=0)
    my_handler.setFormatter(log_formatter)
    my_handler.setLevel(log_level)

    app_log = logging.getLogger(APP_NAME)
    app_log.setLevel(log_level)

    app_log.addHandler(my_handler)

    if args.log:
        console = logging.StreamHandler()
        console.setLevel(log_level)
        console.setFormatter(log_formatter)
        app_log.addHandler(console)


# --------------------------------------------------------------------
def main():

    parser = OptionParser()

    parser.add_option("-p", "--profile", dest='profile', default='default', help="profile selection")
    parser.add_option("--log", action='store_true', dest='log', help="print logs to console")

    (options, _) = parser.parse_args()

    setup_logger(options)

    app = QtWidgets.QApplication([])
    sys.excepthook = excepthook

    mainWindow = PETRACamera(options)
    mainWindow.show()

    app.exec_()
    del app


# --------------------------------------------------------------------
# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    main()
