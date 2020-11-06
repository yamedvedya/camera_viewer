#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Author:        sebastian.piec@desy.de
# Last modified: 2016, April 7
# ----------------------------------------------------------------------

"""Parse settings given in xml files
"""

from xml.dom.minidom import Document, parseString

# ----------------------------------------------------------------------
class XmlSettings(object):

    # ----------------------------------------------------------------------
    def __init__(self, fileName):
        self.fileName = fileName

    # ----------------------------------------------------------------------
    def option(self, nodePath, attribute):
        """Retrieve option's value from a config file.
        """
        with open(self.fileName, "r") as inFile:        # read over-and-over??? TODO
            dom = parseString(inFile.read())

            path = nodePath.split("/")

            node = dom
            for nodeName in path:
                node = node.getElementsByTagName(nodeName)[0]     # take first node always...

            return node.getAttribute(attribute)

    # ----------------------------------------------------------------------
    def getNodes(self, nodePath, nodeName):
        """
        """
        with open(self.fileName, "r") as inFile:
            dom = parseString(inFile.read())

            path = nodePath.split("/")[:-1]

            node = dom
            for nodeName in path:
                node = node.getElementsByTagName(nodeName)[0]

            return node.getElementsByTagName(nodeName)

    # ----------------------------------------------------------------------
    def node(self, nodePath):
        """
        """
        with open(self.fileName, "r") as f:
            dom = parseString(f.read())
            path = nodePath.split("/")

            node = dom
            for nodeName in path[:-1]:
                node = node.getElementsByTagName(nodeName)[0]

            return node.getElementsByTagName(path[-1])[0]           # returns first matching node always...

    # ----------------------------------------------------------------------
    def hasattr(self, nodePath):
        try:
            self.node(nodePath)
            return True
        except:
            return False
