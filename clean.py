#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from sys import platform

src_dir = "src"
uis_dir = "src/ui_vimbacam"

print("Removing pyc files...")


for root, dirs, files in os.walk(src_dir):
    for f in [f for f in files if f.endswith(".pyc")]:
        if platform == "linux" or platform == "linux2":
            os.system("rm {}".format(os.path.join(root, f)))
        elif platform == "win32":
            os.remove(os.path.join(root, f))

print("Removing uis and rcs...")
for root, dirs, files in os.walk(uis_dir):
    for f in [f for f in files if (f.endswith(".pyc") or f.endswith(".py"))
              and f != "__init__.py"]:
        if platform == "linux" or platform == "linux2":
            os.system("rm {}".format(os.path.join(root, f)))
        elif platform == "win32":
            os.remove(os.path.join(root, f))

print("All OK!")

