from collections import OrderedDict

APP_NAME = "2DCameraViewer"

CAMERAS_SETTINGS = OrderedDict(
   {'PetraStatus':  {'tango_server': None,          'color': False, 'high_depth': False},
    'LMScreen':     {'tango_server': 'LMScreen',    'color': False, 'high_depth': False},
    'TangoVimba':   {'tango_server': 'TangoVimba',  'color': True,  'high_depth': True},
    'AXISCamera':   {'tango_server': 'AXISCamera',  'color': True,  'high_depth': False},
    'LimaCCD':      {'tango_server': 'LimaCCDs',    'color': False, 'high_depth': False}})
