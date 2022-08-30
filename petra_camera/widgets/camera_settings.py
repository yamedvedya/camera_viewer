# Created by matveyev at 22.02.2022

from distutils.util import strtobool
import PyTango
try:
    from HasyUtils import getDeviceNamesByClass
except:
    from petra_camera.utils.tango_utils import getDeviceNamesByClass

from PyQt5 import QtWidgets, QtCore

from petra_camera.devices.petrastatus import DEFAULT_TANGO_SERVER

from petra_camera.utils.functions import refresh_combo_box
from petra_camera.gui.CameraSettings_ui import Ui_CameraSettings


class CameraSettings(QtWidgets.QWidget):

    delete_me = QtCore.pyqtSignal(int)
    new_name = QtCore.pyqtSignal(int, str)

    def __init__(self, parent, my_id, settings_node=None):

        super(CameraSettings, self).__init__()
        self._ui = Ui_CameraSettings()
        self._ui.setupUi(self)

        self.my_id = my_id

        self._ui.cmd_default_status_source.clicked.connect(lambda: self._ui.le_status_server.setText(DEFAULT_TANGO_SERVER))

        self._ui.cmb_camera_type.currentTextChanged.connect(self._switch_camera_type)
        self._ui.cmb_motor_type.currentTextChanged.connect(self._switch_motor_type)

        self._ui.cmb_camera_type.addItems(['PetraStatus', 'LMScreen', 'TangoVimba', 'AXISCamera'])
        self._ui.cmb_motor_type.addItems(['None', 'FSBT', 'Acromag'])

        self._ui.le_tango_host.setText(PyTango.Database().get_db_host().split('.')[0])
        self._rescan_database()

        self._ui.cmd_delete.clicked.connect(lambda status, x=my_id: self.delete_me.emit(x))
        self._ui.le_name.editingFinished.connect(self._new_name)

        self._ui.cmd_rescan_database.clicked.connect(self._rescan_database)

        self._ui.chk_manual_tango_device.stateChanged.connect(self._manual_tango_device)
        self._ui.chk_manual_roi_device.stateChanged.connect(self._manual_roi_device)

        self._ui.chk_roi_server.stateChanged.connect(self._enable_roi_device)

        if settings_node is not None:
            self._ui.le_name.setText(settings_node.get('name'))

            if 'enabled' in settings_node.keys():
                self._ui.chk_enabled.setChecked(strtobool(settings_node.get('enabled')))
            else:
                self._ui.chk_enabled.setChecked(True)

            camera_type = settings_node.get('proxy')
            refresh_combo_box(self._ui.cmb_camera_type, camera_type)
            self._switch_camera_type(camera_type)

            if 'tango_server' in settings_node.keys():
                server = settings_node.get('tango_server')
                try:
                    self._ui.le_tango_host.setText(PyTango.DeviceProxy(server).get_db_host().split('.')[0])
                    self._rescan_database()
                    set_manual = not refresh_combo_box(self._ui.cmb_tango_device, PyTango.DeviceProxy(server).dev_name())
                except:
                    set_manual = True

                if set_manual:
                    self._ui.chk_manual_tango_device.setChecked(True)
                    self._ui.le_tango_server.setText(server)

            if 'roi_server' in settings_node.keys():
                server = settings_node.get('roi_server')
                self._ui.chk_roi_server.setChecked(True)

                if not refresh_combo_box(self._ui.cmb_roi_device, PyTango.DeviceProxy(server).dev_name()):
                    self._ui.chk_manual_roi_device.setChecked(True)
                    self._ui.le_roi_server.setText(server)

            if 'status_source' in settings_node.keys():
                if settings_node.get('status_source') == 'tango':
                    self._ui.but_status_source_tango.setChecked(True)
                    if 'server' in settings_node.keys():
                        self._ui.le_status_server.setText(settings_node.get('server'))
                    else:
                        self._ui.le_status_server.setText(DEFAULT_TANGO_SERVER)
                else:
                    self._ui.but_status_source_infoscreen.setChecked(True)

            motor_type = settings_node.get('motor_type')
            if motor_type == 'FSBT':
                refresh_combo_box(self._ui.cmb_motor_type, 'FSBT')
                self._ui.le_fsbt_motor_name.setText(settings_node.get('motor_name'))
                self._ui.le_fsbt_host.setText(settings_node.get('motor_host'))
                self._ui.le_fsbt_port.setText(settings_node.get('motor_port'))
                self._ui.fr_fsbt.setVisible(True)

            elif motor_type == 'Acromag':
                refresh_combo_box(self._ui.cmb_motor_type, 'Acromag')
                self._ui.le_acromag_server.setText(settings_node.get('valve_tango_server'))
                self._ui.le_acromag_valve.setText(settings_node.get('valve_channel'))
                self._ui.fr_acromag.setVisible(True)

            else:
                refresh_combo_box(self._ui.cmb_motor_type, 'None')

            if 'flip_vertical' in settings_node.keys():
                self._ui.chk_flip_v.setChecked(strtobool(settings_node.get('flip_vertical')))
            if 'flip_horizontal' in settings_node.keys():
                self._ui.chk_flip_h.setChecked(strtobool(settings_node.get('flip_horizontal')))
            if 'rotate' in settings_node.keys():
                self._ui.sp_rotate.setValue(int(settings_node.get('rotate')))
            if 'high_depth' in settings_node.keys():
                self._ui.chk_high_depth.setChecked(strtobool(settings_node.get('high_depth')))
            if 'color' in settings_node.keys():
                self._ui.chk_color.setChecked(strtobool(settings_node.get('color')))

            pass

    # ----------------------------------------------------------------------
    def _switch_camera_type(self, mode):
        self._ui.fr_tango.setVisible(mode in ('LMScreen', 'TangoVimba', 'AXISCamera'))
        self._ui.chk_color.setVisible(mode in ('TangoVimba', 'AXISCamera'))
        self._ui.chk_high_depth.setVisible(mode in ('TangoVimba',))
        self._ui.chk_roi_server.setChecked(False)
        self._ui.gb_status_source.setVisible(mode in ('PetraStatus',))

    # ----------------------------------------------------------------------
    def _rescan_database(self):
        for dev_type, cmb_box in ((self._ui.cmb_camera_type.currentText(),  self._ui.cmb_tango_device),
                                  ('FrameAnalysis',                         self._ui.cmb_roi_device)):
            current_selection = cmb_box.currentText()
            cmb_box.clear()
            cmb_box.addItems(getDeviceNamesByClass(dev_type, self._ui.le_tango_host.text()))
            refresh_combo_box(cmb_box, current_selection)

    # ----------------------------------------------------------------------
    def _enable_roi_device(self, state):
        self._ui.le_roi_server.setVisible(state == 2)
        self._ui.cmb_roi_device.setVisible(state == 2)
        self._ui.chk_manual_roi_device.setVisible(state == 2)

    # ----------------------------------------------------------------------
    def _manual_tango_device(self, state):
        self._ui.le_tango_host.setEnabled(state != 2)
        self._ui.cmb_tango_device.setEnabled(state != 2)
        self._ui.cmd_rescan_database.setEnabled(state != 2)
        self._ui.le_tango_server.setEnabled(state == 2)

    # ----------------------------------------------------------------------
    def _manual_roi_device(self, state):
        self._ui.cmb_roi_device.setEnabled(state != 2)
        self._ui.le_roi_server.setEnabled(state == 2)

    # ----------------------------------------------------------------------
    def _switch_motor_type(self, mode):
        self._ui.fr_acromag.setVisible(False)
        self._ui.fr_fsbt.setVisible(False)

        if mode == 'FSBT':
            self._ui.fr_fsbt.setVisible(True)
        elif mode == 'Acromag':
            self._ui.fr_acromag.setVisible(True)

    # ----------------------------------------------------------------------
    def get_data(self):
        camera_type = self._ui.cmb_camera_type.currentText()

        data_to_save = [('name', self._ui.le_name.text()),
                        ('enabled', str(self._ui.chk_enabled.isChecked())),
                        ('proxy', camera_type)]

        if self._ui.cmb_motor_type.currentText() == 'FSBT':
            data_to_save.append(('motor_type', 'FSBT'))
            data_to_save.append(('motor_name', self._ui.le_fsbt_motor_name.text()))
            data_to_save.append(('motor_host', self._ui.le_fsbt_host.text()))
            data_to_save.append(('motor_port', self._ui.le_fsbt_port.text()))

        elif self._ui.cmb_motor_type.currentText() == 'Acromag':
            data_to_save.append(('motor_type', 'Acromag'))
            data_to_save.append(('valve_tango_server', self._ui.le_acromag_server.text()))
            data_to_save.append(('valve_channel', self._ui.le_acromag_valve.text()))
        else:
            data_to_save.append((('motor_type', 'none')),)

        if camera_type in ['LMScreen', 'TangoVimba', 'AXISCamera']:
            if self._ui.chk_manual_tango_device.isChecked():
                address = self._ui.le_tango_server.text()
            else:
                address = self._ui.le_tango_host.text() + ':10000/' + self._ui.cmb_tango_device.currentText()

            data_to_save.append(('tango_server', address))

        if camera_type == 'PetraStatus':
            if self._ui.but_status_source_tango.isChecked():
                data_to_save.append(('status_source', 'tango'))
                data_to_save.append(('server', self._ui.le_status_server.text()))
            else:
                data_to_save.append(('status_source', 'infoscreen'))

        if self._ui.chk_roi_server.isChecked():
            if self._ui.chk_manual_roi_device.isChecked():
                address = self._ui.le_roi_server.text()
            else:
                address = self._ui.le_tango_host.text() + ':10000/' + self._ui.cmb_roi_device.currentText()

            data_to_save.append(('roi_server', address))

        data_to_save.append(('flip_vertical', str(self._ui.chk_flip_v.isChecked())))
        data_to_save.append(('flip_horizontal', str(self._ui.chk_flip_h.isChecked())))
        data_to_save.append(('rotate', str(self._ui.sp_rotate.value())))

        if camera_type == 'TangoVimba':
            data_to_save.append(('high_depth', str(self._ui.chk_high_depth.isChecked())))
            data_to_save.append(('color', str(self._ui.chk_color.isChecked())))

        if camera_type == 'AXISCamera':
            data_to_save.append(('color', str(self._ui.chk_color.isChecked())))

        return data_to_save

    # ----------------------------------------------------------------------
    def _new_name(self):
        self.new_name.emit(self.my_id, self._ui.le_name.text())