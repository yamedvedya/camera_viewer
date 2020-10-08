#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2017, July 5
# ----------------------------------------------------------------------

"""Compiles ui and rcc files (works on Linux/Windows, with PyQt/PySide).

Usage:
     ./build.py [qtlib] [os]

e.g.:
     ./build.py pyqt linux
     ./build.py pyside windows
"""

from __future__ import print_function

import os
import sys

# ----------------------------------------------------------------------
in_dirs = ["ui"]
out_dirs = ["src/ui_vimbacam"]

ui_compilers = {"linux": {
                    "pyqt": "pyuic4",
                    "pyside": "pyside-uic"
                },
                "win32": {
                    "pyqt": "C:\\Python27\\lib\\site-packages\\PyQt4\\pyuic4.bat",
                    "pyside": ""
                }
               }

rc_compilers = {"linux": {
                    "pyqt": "pyrcc4",
                    "pyside": "pyside-rcc"
                },
                "win32": {
                    "pyqt": "C:\\Python27\\lib\\site-packages\\PyQt4\\pyrcc4.exe",
                    "pyside": ""
                }
               }


# ----------------------------------------------------------------------
def compile_uis(ui_compiler, rc_compiler, in_dirs, out_dirs):
    """
    """ 
    for in_dir, out_dir in zip(in_dirs, out_dirs):
        for f in [f for f in os.listdir(in_dir) if os.path.isfile(os.path.join(in_dir, f))
                  and os.path.splitext(f)[-1] in [".ui", ".qrc"]]:        # simplify this loop TODO
            base, ext = os.path.splitext(f)
            post, comp = ("_ui", ui_compiler) if ext == ".ui" else ("_rc", rc_compiler)

            cmd = "{} {}/{} -o {}/{}{}.py".format(comp, in_dir, f, out_dir, base, post)
            print(cmd)
            os.system(cmd)
  
# ----------------------------------------------------------------------
if __name__ == "__main__":

    lib_name, sys_name = "pyqt", sys.platform

    print("Removing pyc files...")

    for out_dir in out_dirs:
        for root, dirs, files in os.walk(out_dir):
            for f in [f for f in files if f.endswith(".pyc")]:
                if sys.platform == "linux" or sys.platform == "linux2":
                    os.system("rm {}".format(os.path.join(root, f)))
                elif sys.platform == "win32":
                    os.remove(os.path.join(root, f))

    print("Removing uis and rcs...")
    for out_dir in out_dirs:
        for root, dirs, files in os.walk(out_dir):
            for f in [f for f in files if (f.endswith(".pyc") or f.endswith(".py"))
                                          and f != "__init__.py"]:
                if sys.platform == "linux" or sys.platform == "linux2":
                    os.system("rm {}".format(os.path.join(root, f)))
                elif sys.platform == "win32":
                    os.remove(os.path.join(root, f))

    print("All removed!")

    if len(sys.argv) > 1:
        lib_name = sys.argv[1].lower()
    
    if len(sys.argv) > 2:
        sys_name = sys.argv[2].lower()

    compile_uis(ui_compilers[sys_name][lib_name],
                rc_compilers[sys_name][lib_name], in_dirs, out_dirs)
    
    print("All OK!")

