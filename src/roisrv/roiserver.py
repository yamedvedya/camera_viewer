#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@mail.desy.de
# Last modified: 2017, December 5
# ----------------------------------------------------------------------

"""TCP/IP server exposing some summary statistics about the data frame.

General format:
    <init_token>;command

Example session:
    p22roisrv;getroi
    p22roisrv;ok;42
"""

from __future__ import print_function

import logging
import socket

from src.utils.propagatingThread import ExcThread
from Queue import Empty as emptyQueue
from Queue import Queue

import json

import select
import traceback
import time

from PyQt4 import QtCore

# ----------------------------------------------------------------------
class RoiServer(QtCore.QObject):
    """
    """
    INIT_TOKEN = "p22roisrv"
    SEPARATOR = ";"
    SOCKET_TIMEOUT = .5                            # [s]
    MAX_REQUEST_LEN = 256
    MAX_CLIENT_NUMBER = 32
    CMD_MAP = {"getSum": {'location': 'settingWidget', 'function': 'getValue', 'property': 'sum'},
               "getCoM": {'location': 'settingWidget', 'function': 'getValue', 'property': 'roiCoM'},
               "getFWHM": {'location': 'settingWidget', 'function': 'getValue', 'property': 'roiFWHM'},
               "getSettings": {'type': 'property', 'location': 'settingWidget', 'function': 'getValue', 'property': 'roi2ectrl'},
               "getMarkerSettings": {'location': 'settingWidget', 'function': 'marker2ectrl'},
               "getCameraSettings": {'location': 'settingWidget', 'function': 'getCameraSettings'},
               "setCameraSettings": {'location': 'settingWidget', 'function': 'setCameraSettings'},
               "getListOfCommands": {'location': 'server', 'function': 'listOfCommands'}}

    # ----------------------------------------------------------------------
    def __init__(self, host, port):

        super(RoiServer, self).__init__()

        self.settingWidget = []

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
    def start(self):
        """
        """
        self._serverWorker.start()

    # ----------------------------------------------------------------------
    def run(self):
        """
        """
        self._state = "run"
        print("V2D server on port {}".format(self.port))

        self._socket.listen(self.MAX_CLIENT_NUMBER)

        read_list = [self._socket]
        while not self._serverWorker.stopped():
            readable, writable, errored = select.select(read_list, [], [], 0.1)
            for s in readable:
                if s is self._socket:
                    connection, address = self._socket.accept()
                    connection.setblocking(False)
                    self._connectionMap.append([connection, address])
                    print('New client added: {:s}'.format(address))

            for connection, address in self._connectionMap:
                try:
                    request = connection.recv(self.MAX_REQUEST_LEN)
                    if request:
                        connection.sendall(self._processRequest(request))
                    else:
                        print('Client closed: {:s}'.format(address))
                        connection.close()
                        self._connectionMap.remove([connection, address])

                except socket.error as err:
                    if err.args[0] == 10035:
                        if self._serverWorker.stopped():
                            break
                    elif err.errno == 11:
                        time.sleep(0.1)
                    elif err.errno == 10054:
                        print('Client closed: {:s}'.format(address))
                        connection.close()
                        self._connectionMap.remove([connection, address])
                    else:
                        pass

                except KillConnection as _:
                    print(traceback.format_exc())
                    print('Client closed: {:s}'.format(address))
                    connection.close()
                    self._connectionMap.remove([connection, address])

                except Exception as _:
                    print(traceback.format_exc())
                    self.stopServerBucket.put('1')
                    break

        self._socket.close()
        self._state = 'aborted'
        
        print(__file__, "closed!")

    # ----------------------------------------------------------------------
    def stop(self):
        """
        """
        self._serverWorker.stop()
        while self._state != 'aborted':
            time.sleep(0.1)

    # ----------------------------------------------------------------------
    def _processRequest(self, request):
        """
        Returns:
            (str) response, e.g.: "ok;manipulator;x;12.0"
        """
        response = ''
        print(__file__, "processing request '{}'".format(request))

        tokens = request.split(self.SEPARATOR)
        if tokens[0] != self.INIT_TOKEN:
            response = self._makeResponse("err", "invalid_special_token")
        else:
            try:
                if self.CMD_MAP[tokens[1]]['location'] == 'settingWidget':
                    source = self.settingWidget
                else:
                    source = self

                if len(tokens) > 2:
                    response = self._makeResponse("OK", getattr(source, self.CMD_MAP[tokens[1]]['function'])(tokens[2:]))
                else:
                    if 'property' in self.CMD_MAP[tokens[1]]:
                        response = self._makeResponse("OK", getattr(source, self.CMD_MAP[tokens[1]]['function'])(self.CMD_MAP[tokens[1]]['property']))
                    else:
                        response = self._makeResponse("OK", getattr(source, self.CMD_MAP[tokens[1]]['function'])())

            except Exception as err:
                response = self._makeResponse("err", 'request unknown') # this works  'request unknown'

        return response

    # ----------------------------------------------------------------------
    def listOfCommands(self):

        commands = self.CMD_MAP.keys()
        return commands

    # ----------------------------------------------------------------------
    def _makeResponse(self, flag, message):
        """
        """
        return "{};{};{}".format(self.INIT_TOKEN, flag, json.dumps(message))

# ----------------------------------------------------------------------
class KillConnection(Exception):
    pass

