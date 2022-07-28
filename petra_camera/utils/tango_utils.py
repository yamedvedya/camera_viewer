# copy of necessary HasyUtils functions in case there is not HasyUtils installation
import sys
import PyTango

_db = None

def getDeviceNamesByClass(className, tangoHost=None):
    '''Return a list of all devices of a specified class,
        'DGG2' -> ['p09/dgg2/exp.01', 'p09/dgg2/exp.02']
    '''
    srvs = getServerNameByClass(className, tangoHost)
    argout = []

    db = _findDB(tangoHost)
    if not db:
        return None

    for srv in srvs:
        lst = db.get_device_name(srv, className).value_string
        for i in range(0, len(lst)):
            argout.append(lst[i])
    return argout

def getServerNameByClass(argin, tangoHost = None):
    '''Return a list of servers containing the specified class '''

    db = _findDB( tangoHost)

    srvs = db.get_server_list( "*").value_string

    argout = []

    for srv in srvs:
        classList = db.get_server_class_list( srv).value_string
        for clss in classList:
            if clss == argin:
                argout.append( srv)
                break
    return argout

def _findDB(tangoHost = None):
    '''
    handle these cases:
      - tangoHost == None: use TANGO_HOST DB
      - tangoHost == "haspp99:10000" return db link
      - tangoHost == "haspp99" insert 100000 and return db link
    '''
    if tangoHost is None:
        if _db is None:
            print( "TgUtils._findDB: _db is None")
            sys.exit( 255)
        return _db

    #
    # unexpeccted: tango://haspe212oh.desy.de:10000/motor/dummy_mot_ctrl/1
    #
    if tangoHost.find( 'tango://') == 0:
        print( "TgUtils._fineDB: bad TANGO_HOST syntax %s" % tangoHost)
        return None
    #
    # tangHost "haspp99:10000"
    #
    lst = tangoHost.split( ':')
    if len(lst) == 2:
        return PyTango.Database(lst[0], lst[1])
    #
    # tangHost "haspp99"
    #
    elif len(lst) == 1:
        return PyTango.Database(lst[0], "10000")
    else:
        print("TgUtils._fineDB: failed to return Database, %s" % tangoHost)
        return None