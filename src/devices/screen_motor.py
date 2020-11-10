# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Camera motor class
"""

import socket
import errno, time
import json
import PyTango

from io import StringIO


class MotorExecutor(object):

    SOCKET_TIMEOUT = 5
    DATA_BUFFER_SIZE = 2 ** 22

    def __init__(self, settings, log):
        super(MotorExecutor, self).__init__()

        self._log = log
        if str(settings.getAttribute("motor_type")).lower() == 'acromag':
            self._motor_type = 'Acromag'
            self._valve_device_proxy = PyTango.DeviceProxy(str(settings.getAttribute("valve_tango_server")))
            self._valve_channel = int(settings.getAttribute("valve_channel"))

        elif str(settings.getAttribute("motor_type")).lower() == 'fsbt':
            self._motor_type = 'FSBT'
            self._fsbt_server_host = str(settings.getAttribute("motor_host"))
            self._fsbt_server_port = int(settings.getAttribute("motor_port"))
            self._motor_name = str(settings.getAttribute("motor_name"))
        else:
            raise RuntimeError('Unknown type of motor')

    # ----------------------------------------------------------------------
    def motor_position(self):
        if self._motor_type == 'Acromag':
            _currentPos = list('{0:04b}'.format(int(self._valve_device_proxy.read_attribute("Register0").value)))
            return _currentPos[3 - self._valve_channel] == "1"

        elif self._motor_type == 'FSBT':
            try:
                FSBTServer = self.get_connection_to_fsbt()
                if FSBTServer:
                    status = self.send_command_to_fsbt(FSBTServer, 'status ' + self._motor_name)
                    return status[1][self._motor_name] == 'in'
                else:
                    return None
            except Exception as err:
                self._log.error("Error during motor status {}...".format(err))
                return None

    # ----------------------------------------------------------------------
    def move_motor(self, new_state):

        if self._motor_type == 'Acromag':
            _currentPos = list('{0:04b}'.format(int(self._valve_device_proxy.read_attribute("Register0").value)))
            current_state = _currentPos[3 - self._valve_channel] == "1"

            if current_state != new_state:
                if new_state:
                    _currentPos[3 - self._valve_channel] = "1"
                else:
                    _currentPos[3 - self._valve_channel] = "0"

                self._valve_device_proxy.write_attribute("Register0", int("".join(_currentPos), 2))

        elif self._motor_type == 'FSBT':
            try:
                FSBTServer = self.get_connection_to_fsbt()
                if FSBTServer:
                    status = self.send_command_to_fsbt(FSBTServer, 'status ' + self._motor_name)[1][self._motor_name] == 'in'
                    if status != new_state:
                        if new_state:
                            result = self.send_command_to_fsbt(FSBTServer, 'in {:s}'.format(self._motor_name))
                        else:
                            result = self.send_command_to_fsbt(FSBTServer, 'out {:s}'.format(self._motor_name))
                        if not result:
                            self._log.error("Cannot move motor")
                    FSBTServer.close()
            except Exception as err:
                self._log.error("Error during motor movement {}...".format(err))
        else:
            raise RuntimeError('Unknown type of motor')

    # ----------------------------------------------------------------------
    def get_connection_to_fsbt(self):

        FSBTSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        FSBTSocket.settimeout(self.SOCKET_TIMEOUT)

        start_timeout = time.time()
        time_out = False
        is_connected = False
        while not time_out and not is_connected:
            err = FSBTSocket.connect_ex((self._fsbt_server_host, self._fsbt_server_port))
            if err == 0 or err == errno.EISCONN:
                is_connected = True
            if time.time() - start_timeout > self.SOCKET_TIMEOUT:
                time_out = True

        if is_connected:
            return FSBTSocket
        else:
            return None

    # ----------------------------------------------------------------------
    def send_command_to_fsbt(self, FSBTSocket, command):

        FSBTSocket.sendall(str(command))

        start_timeout = time.time()
        time_out = False
        got_answer = False
        ans = ''
        while not time_out and not got_answer:
            try:
                ans = FSBTSocket.recv(self.DATA_BUFFER_SIZE)
                got_answer = True
            except socket.error as err:
                if err.errno != 11:
                    time_out = True
                if time.time() - start_timeout > self.SOCKET_TIMEOUT:
                    time_out = True
        if not time_out:
            return json.load(StringIO(ans))
        else:
            raise RuntimeError("The FSBT server does not respond")

    # ----------------------------------------------------------------------
    def int_to_bin(self, val):
        b = '{0:04b}'.format(val)
        l = [0] * 4

        for i in range(4):
            l[i] = int(b[i], 2)

        return l