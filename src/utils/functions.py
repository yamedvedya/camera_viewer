#!/usr/bin/env python

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de & yury.matveev@desy.de
# Last modified: 2017, December 12
# ----------------------------------------------------------------------

"""Auxiliary functions used in many different contexts.
"""

import datetime
import logging
import math
import os

# ----------------------------------------------------------------------
def roi_text(value, compact=False):
    """
    Args:
        value (float), number of counts
        compact (bool), 
    Returns:
        (str)
    """
    if not compact:
        return "{:.1f}".format(int(value))

    value = int(value)
    value_bak = value

    post = ["", "k", "M", "G"]      #, "T", "P"]

    cnt = -1
    while value > 0:
        cnt += 1
        if cnt >= len(post) - 1: break
        value /= 1000

    value = value_bak / (math.pow(1000, cnt)) if cnt > 0 else value_bak
    return "{:.1f}{}".format(value, post[cnt])

# ----------------------------------------------------------------------  
def make_log_name(logfile_base, logdir):
    """Create date dependent log directory and generate unique logfile
    name within the dir.

    Args:

    Returns:
        (str, str), logfile and directory names
    """
    now = datetime.datetime.now()
    date_str, time_str = now.strftime("%Y_%m_%d"), now.strftime("%H_%M_%S")
    
    target_dir = os.path.join(logdir, date_str)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    file_name = os.path.join(target_dir, logfile_base + "_" + time_str + ".txt")
    #file_name = uniqueFileName(file_name, os.listdir(target_dir))
    file_name = unique_name(file_name, os.listdir(target_dir))

    return file_name, target_dir

# ---------------------------------------------------------------------- 
def parse_log_level(level):
    """
    Args:
        (str) stringified logging level
    Returns:
        corresponding logging module's level (enum?)
    """
    return {"debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
           }[level.lower()]

# ----------------------------------------------------------------------
def unique_name(base_name, used_names, max_trials=10e+6):
    """
    """
    new_name = base_name
    is_unique = False

    cnt = 1
    while new_name in used_names and cnt < max_trials:
        new_name = base_name + "_%02d" % cnt
        cnt += 1 

    if cnt >= max_trials:
        raise RuntimeError("Cannot generate unique name (trials {})".format(max_trials))

    return new_name

# ----------------------------------------------------------------------
def refresh_combo_box(comboBox, text):
    """Auxiliary function refreshing combo box with a given text.
    """
    idx = comboBox.findText(text)
    comboBox.blockSignals(True)
    if idx != -1:
        comboBox.setCurrentIndex(idx)
        comboBox.blockSignals(False)
        return True
    else:
        comboBox.setCurrentIndex(0)
        comboBox.blockSignals(False)
        return False


# ----------------------------------------------------------------------
def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy

# ----------------------------------------------------------------------
# A little bit of unit testing...
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import random
    random.seed(42)

    for i in range(15):
        value = (random.randint(1, 9) * math.pow(10, i) +
                 random.randint(10, 1000))
        print("Value: {}, rep: {}".format(value, roi_text(value, compact=True)))

