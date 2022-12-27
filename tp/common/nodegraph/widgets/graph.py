#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph widget implementation
"""

from __future__ import print_function, division,absolute_import

from Qt.QtWidgets import QTabWidget


class NodeGraphWidget(QTabWidget):
	def __init__(self, parent=None):
		super(NodeGraphWidget, self).__init__(parent=parent)

		self.setTabsClosable(True)
		self.setTabBarAutoHide(True)
