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
    def node(self, node_path=None):
        """
        """
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
