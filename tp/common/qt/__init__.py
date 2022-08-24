#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tpDcc-libs-qt
"""

from __future__ import print_function, division, absolute_import

import sys

from Qt.QtWidgets import QApplication


app = QApplication.instance() or QApplication(sys.argv)
