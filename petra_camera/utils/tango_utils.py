import PyTango

# ----------------------------------------------------------------------
class TangoDBsInfo():

    def __init__(self):
        self._known_dbs = {}
        self._devices_in_dbs = {}

    # ----------------------------------------------------------------------
    def getDeviceNamesByClass(self, class_name, tango_host):
        '''Return a list of all devices of a specified class,
            'DGG2' -> ['p09/dgg2/exp.01', 'p09/dgg2/exp.02']
        '''
        srvs = self.getServerNameByClass(class_name, tango_host)
        argout = []

        db = self._known_dbs[tango_host]

        for srv in srvs:
            argout += db.get_device_name(srv, class_name).value_string
        return argout

    # ----------------------------------------------------------------------
    def getServerNameByClass(self, argin, tango_host):
        '''Return a list of servers containing the specified class '''

        if tango_host not in self._known_dbs:
            db = findDB(tango_host)
            if not db:
                return None
            self._known_dbs[tango_host] = db
        else:
            db = self._known_dbs[tango_host]

        if tango_host not in self._devices_in_dbs:
            self._devices_in_dbs[tango_host] = dict.fromkeys(db.get_server_list("*").value_string)

        argout = []

        for srv in self._devices_in_dbs[tango_host].keys():
            if self._devices_in_dbs[tango_host][srv] is None:
                self._devices_in_dbs[tango_host][srv] = db.get_server_class_list(srv).value_string
            for clss in self._devices_in_dbs[tango_host][srv]:
                if clss == argin:
                    argout.append(srv)
                    break
        return argout

# ----------------------------------------------------------------------
def findDB(tango_host):

    #
    # unexpeccted: tango://haspe212oh.desy.de:10000/motor/dummy_mot_ctrl/1
    #
    if tango_host.find('tango://') == 0:
        print("Bad TANGO_HOST syntax %s" % tango_host)
        return None
    #
    # tangHost "haspp99:10000"
    #
    lst = tango_host.split(':')
    if len(lst) == 2:
        return PyTango.Database(lst[0], lst[1])
    #
    # tangHost "haspp99"
    #
    elif len(lst) == 1:
        return PyTango.Database(lst[0], "10000")
    else:
        print("Failed to return Database, %s" % tango_host)
        return None