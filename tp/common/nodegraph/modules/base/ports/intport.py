#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that implements integer ports
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.nodegraph.core import port


class IntPort(port.Port, object):

    COLOR = (0, 168, 107, 255)
    IS_VALUE_PORT = True
    INTERNAL_DATA_STRUCTURE = int
    SUPPORTED_DATA_TYPES = ('IntPort', 'FloatPort')
    PORT_DATA_TYPE_HINT = 'IntPort', 0

    def __init__(self, *args, **kwargs):
        kwargs['default_value'] = kwargs.get('default_value', 0)
        super(IntPort, self).__init__(*args, **kwargs)
