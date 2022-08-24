#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that implements exec ports
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.nodegraph.core import port


class ExecPort(port.Port, object):

    COLOR = (200, 200, 200, 255)
    IS_VALUE_PORT = False
    IS_EXEC = True
    INTERNAL_DATA_STRUCTURE = None

    def __init__(self, *args, **kwargs):
        super(ExecPort, self).__init__(*args, **kwargs)
