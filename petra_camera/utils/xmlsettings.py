#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Parse settings given in xml files
"""

import os
from pathlib import Path
import shutil
from datetime import datetime
import xml.etree.cElementTree as ET


# ----------------------------------------------------------------------
class XmlSettings(object):

    # ----------------------------------------------------------------------
    def __init__(self, file_name):
        self.file_name = file_name
        self.et_tree = ET.parse(file_name)
        self.root = self.et_tree.getroot()

        self.check_cameras_ids()

    # ----------------------------------------------------------------------
    def check_cameras_ids(self):

        id_counter = 0
        used_ids = []
        need_to_be_saved = False

        for el in self.root.findall('camera'):
            if not el.get("id"):
                need_to_be_saved = True
                el.set("id", str(id_counter))
                used_ids.append(id_counter)
            else:
                id = int(el.get("id"))
                if id in used_ids:
                    need_to_be_saved = True
                    el.set("id", str(id_counter))
                    used_ids.append(id_counter)
                else:
                    used_ids.append(id)
            while id_counter in used_ids:
                id_counter += 1

        if need_to_be_saved:
            self._archive_settings()
            self.et_tree.write(self.file_name)

    # ----------------------------------------------------------------------
    def save_new_options(self, general_settings, cameras_settings):

        self._archive_settings()

        for node, values in general_settings:
            try:
                node = self.node(node, self.root)
            except:
                node = self.make_node(self.root, node)

            for attribute, value in values:
                node.set(attribute, str(value))

        for el in self.root.findall('camera'):
            self.root.remove(el)

        el = None
        for camera in cameras_settings:
            el = ET.SubElement(self.root, 'camera', dict((key, value) for (key, value) in camera))
            el.tail = '\n\n\t'

        if el is not None:
            el.tail = '\n\n'

        self.et_tree.write(self.file_name)

    # ----------------------------------------------------------------------
    def option(self, node_path, attribute):
        """Retrieve option's value from a config file.
        """

        return self.node(node_path).get(attribute)

    # ----------------------------------------------------------------------
    def get_nodes(self, node_name, node_path=None):
        """
        """

        return self.node(node_path).findall(node_name)

    # ----------------------------------------------------------------------
    def make_node(self, root, node_path):
        for node in node_path.split("/"):
            if root.find(node) is not None:
                root = root.find(node)
            else:
                root = ET.SubElement(root, node)
                root.tail = '\n\n\t'

        return root

    # ----------------------------------------------------------------------
    def node(self, node_path=None, root=None):
        """
        """
        if root is None:
            root = self.root

        if node_path is not None:
            for node in node_path.split("/"):
                if root.find(node) is not None:
                    root = root.find(node)
                else:
                    raise RuntimeError('Wrong xml path')

        return root

    # ----------------------------------------------------------------------
    def has_node(self, node_path):
        try:
            self.node(node_path)
            return True
        except:
            return False

    # ----------------------------------------------------------------------
    def _archive_settings(self):
        file_name = os.path.basename(self.file_name)
        folder = os.path.join(os.path.join(str(Path.home()), '.petra_camera'), 'archive')

        if not os.path.exists(folder):
            os.mkdir(folder)

        fname, fext = os.path.splitext(file_name)

        now = datetime.now()
        shutil.copyfile(self.file_name, os.path.join(folder, f'{fname}_{now.strftime("%d_%m_%Y_%H_%M_%S")}{fext}'))
