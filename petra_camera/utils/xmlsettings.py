#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        yury.matveev@desy.de
# ----------------------------------------------------------------------

"""Parse settings given in xml files
"""

import xml.etree.cElementTree as ET


# ----------------------------------------------------------------------
class XmlSettings(object):

    # ----------------------------------------------------------------------
    def __init__(self, file_name):
        self.file_name = file_name

    # ----------------------------------------------------------------------
    def set_options(self, general_settings, cameras_settings):

        et_tree = ET.parse(self.file_name)
        root = et_tree.getroot()
        for node, values in general_settings:
            try:
                node = self.node(node, root)
            except:
                node = self.make_node(root, node)

            for attribute, value in values:
                node.set(attribute, str(value))

        for el in root.findall('camera'):
            root.remove(el)

        el = None
        for camera in cameras_settings:
            el = ET.SubElement(root, 'camera', dict((key, value) for (key, value) in camera))
            el.tail = '\n\n\t'

        if el is not None:
            el.tail = '\n\n'

        et_tree.write(self.file_name)

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

        return root

    # ----------------------------------------------------------------------
    def node(self, node_path=None, root=None):
        """
        """
        if root is None:
            root = ET.parse(self.file_name).getroot()

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
