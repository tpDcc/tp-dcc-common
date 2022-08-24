#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that implements float ports
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.nodegraph.core import port


class FloatPort(port.Port, object):

    COLOR = (96, 169, 23, 255)
    IS_VALUE_PORT = True
    INTERNAL_DATA_STRUCTURE = float
    SUPPORTED_DATA_TYPES = ('FloatPort', 'IntPort')
    PORT_DATA_TYPE_HINT = 'FloatPort', 0.0

    def __init__(self, *args, **kwargs):
        kwargs['default_value'] = kwargs.get('default_value', 0.0)
        super(FloatPort, self).__init__(*args, **kwargs)
