# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------


"""TCP/IP server exposing some summary statistics about the data frame.

"""

import json

import select
import traceback
import time

import logging
import socket

from queue import Queue
from src.utils.propagatingThread import ExcThread

from PyQt5 import QtCore

# ----------------------------------------------------------------------
class RoiServer(QtCore.QObject):
    """
    """

    change_camera = QtCore.pyqtSignal(str)

    SOCKET_TIMEOUT = .5                            # [s]
    MAX_REQUEST_LEN = 256
    MAX_CLIENT_NUMBER = 32
    CMD_MAP = {"get_camera_list": {'function': '_get_camera_list', "args": ''},
               "get_sum": {'function': '_get_roi_value', 'args': 'sum'},
               "get_fwhm": {'function': '_get_roi_value', 'args': 'fwhm'},
               "set_camera": {'function': '_set_camera',"args": ''},
               "get_list_of_commands": {'function': '_get_list_of_commands', "args": ''}}

    # ----------------------------------------------------------------------
    def __init__(self, host, port):

        super(RoiServer, self).__init__()

        self._camera_device = None
        self._cameras_list = None

        self.log = logging.getLogger("cam_logger")
        
        self.host = str(host)
        self.port = int(port)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)      # TODO
        self._socket.settimeout(self.SOCKET_TIMEOUT)
        self._socket.bind((self.host, self.port))

        self._connectionMap = []

        self._state = "idle"

        self._errorQueue = Queue()
        self._serverWorker = ExcThread(self.run, 'roiServer', self._errorQueue)
        
        self.log.info("ROI server host {}, port {}".format(self.host,
                                                           self.port))

    # ----------------------------------------------------------------------
    def set_camera_device(self, camera_device, cameras_list):
        self._camera_device = camera_device
        self._cameras_list = cameras_list

    # ----------------------------------------------------------------------
    def start(self):
        """
        """
        self._serverWorker.start()

    # ----------------------------------------------------------------------
    def run(self):
        """
        """
        self._state = "run"
        self._socket.listen(self.MAX_CLIENT_NUMBER)

        read_list = [self._socket]
        while not self._serverWorker.stopped():
            readable, writable, errored = select.select(read_list, [], [], 0.1)
            for s in readable:
                if s is self._socket:
                    connection, address = self._socket.accept()
                    connection.setblocking(False)
                    self._connectionMap.append([connection, address])
                    self.log.info('New client added: {}'.format(address))

            for connection, address in self._connectionMap:
                try:
                    request = connection.recv(self.MAX_REQUEST_LEN).decode()
                    if request:
                        connection.sendall(self._processRequest(request).encode())
                    else:
                        self.log.info('Client closed: {}'.format(address))
                        connection.close()
                        self._connectionMap.remove([connection, address])

                except socket.error as err:
                    if err.args[0] == 10035:
                        if self._serverWorker.stopped():
                            break
                    elif err.errno == 11:
                        time.sleep(0.1)
                    elif err.errno == 10054:
                        self.log.info('Client closed: {}'.format(address))
                        connection.close()
                        self._connectionMap.remove([connection, address])
                    else:
                        pass

                except KillConnection as _:
                    self.log.error(traceback.format_exc())
                    self.log.info('Client closed: {}'.format(address))
                    connection.close()
                    self._connectionMap.remove([connection, address])

                except Exception as _:
                    self.log.error(traceback.format_exc())
                    break

        self._socket.close()
        self._state = 'aborted'

    # ----------------------------------------------------------------------
    def stop(self):
        """
        """
        self._serverWorker.stop()
        while self._state != 'aborted':
            time.sleep(0.1)

        self.log.debug('ROI server stopped')

    # ----------------------------------------------------------------------
    def _processRequest(self, request):
        """
        Returns:
            (str) response, e.g.: "ok;manipulator;x;12.0"
        """
        response = ''
        print(__file__, "processing request '{}'".format(request))

        tokens = request.split()

        try:
            if len(tokens)> 1:
                response = self._makeResponse("OK", getattr(self, self.CMD_MAP[tokens[0]]['function'])(
                    self.CMD_MAP[tokens[0]]['args'], tokens[1:]))
            else:
                response = self._makeResponse("OK", getattr(self, self.CMD_MAP[tokens[0]]['function'])(
                    self.CMD_MAP[tokens[0]]['args'], []))

        except Exception as err:
            response = self._makeResponse("err", 'request unknown')

        return response

    # ----------------------------------------------------------------------
    def listOfCommands(self):

        commands = self.CMD_MAP.keys()
        return commands

    # ----------------------------------------------------------------------
    def _makeResponse(self, flag, message):
        """
        """
        return "{};{}".format(flag, json.dumps(message))

    # ----------------------------------------------------------------------
    def _get_camera_list(self, args, tockens):
        return ';'.join(self._cameras_list)

    # ----------------------------------------------------------------------
    def _set_camera(self, args, tockens):
        self.change_camera.emit(str(tockens[0]))

    # ----------------------------------------------------------------------
    def _get_roi_value(self, args, tockens):
        return self._statistics[self._current_roi_index][args]

    # ----------------------------------------------------------------------
    def get_list_of_commands(self, args, tockens):
        return ';'.join(self.CMD_MAP.keys())

# ----------------------------------------------------------------------
class KillConnection(Exception):
    pass

