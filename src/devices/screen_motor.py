# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Camera motor class
"""

import socket
import errno, time
import json
import PyTango
import threading

from io import StringIO
from queue import Queue, Empty

REFRESH_PERIOD = 1

# ----------------------------------------------------------------------
class MotorExecutor(object):

    SOCKET_TIMEOUT = 3
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
            self._motor_name = str(settings.getAttribute("motor_name"))

            self._fsbt_server = None
            self._fsbt_host = str(settings.getAttribute("motor_host"))
            self._fsbt_port = int(settings.getAttribute("motor_port"))

            self._fsbt_worker = threading.Thread(target=self.server_connection)
            self._fsbt_worker_status = 'running'
            self._run_server = True
            self._motor_position = None
            self._move_queue = Queue()

            self._fsbt_worker.start()

        else:
            raise RuntimeError('Unknown type of motor')

    def server_connection(self):
        if not self.get_connection_to_fsbt():
            self._fsbt_worker_status = 'stopped'
            return

        while self._run_server:
            try:
                status = self.send_command_to_fsbt('status ' + self._motor_name)
                self._motor_position = status[1][self._motor_name] == 'in'
            except Exception as err:
                self._log.error("Error during motor status {}...".format(err))
                return None

            try:
                result = self.send_command_to_fsbt(self._move_queue.get(block=False))
                if not result:
                    self._log.error("Cannot move motor")

            except Empty:
                pass

            except Exception as err:
                pass

            time.sleep(REFRESH_PERIOD)

        self._fsbt_worker_status = 'stopped'

    # ----------------------------------------------------------------------
    def motor_position(self):
        if self._motor_type == 'Acromag':
            _currentPos = list('{0:04b}'.format(int(self._valve_device_proxy.read_attribute("Register0").value)))
            return _currentPos[3 - self._valve_channel] == "1"

        elif self._motor_type == 'FSBT':
            return self._motor_position

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
            if self._motor_position != new_state:
                if new_state:
                    self._move_queue.put('in {:s}'.format(self._motor_name))
                else:
                    self._move_queue.put('out {:s}'.format(self._motor_name))
        else:
            raise RuntimeError('Unknown type of motor')

    # ----------------------------------------------------------------------
    def get_connection_to_fsbt(self):

        self._fsbt_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._fsbt_server.settimeout(self.SOCKET_TIMEOUT)

        start_timeout = time.time()
        time_out = False
        is_connected = False
        while not time_out and not is_connected:
            err = self._fsbt_server.connect_ex((self._fsbt_host, self._fsbt_port))
            if err == 0 or err == errno.EISCONN:
                is_connected = True
            if time.time() - start_timeout > self.SOCKET_TIMEOUT:
                time_out = True

        return is_connected

    # ----------------------------------------------------------------------
    def send_command_to_fsbt(self, command):

        try:
            self._fsbt_server.sendall(str(command).encode())
        except Exception as err:
            return

        start_timeout = time.time()
        time_out = False
        got_answer = False
        ans = ''
        while not time_out and not got_answer:
            try:
                ans = str(self._fsbt_server.recv(self.DATA_BUFFER_SIZE).decode())
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