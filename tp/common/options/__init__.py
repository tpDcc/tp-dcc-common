#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tpDcc-libs-options
"""

from __future__ import print_function, division, absolute_import

import os
import logging.config

from tpDcc.core import library

LIB_ID = 'tpDcc-libs-options'
LIB_ENV = LIB_ID.replace('-', '_').upper()

LOGGER = logging.getLogger('tpDcc-libs-options')


class OptionsLib(library.DccLibrary, object):
    def __init__(self, *args, **kwargs):
        super(OptionsLib, self).__init__(*args, **kwargs)

    @classmethod
    def config_dict(cls, file_name=None):
        base_tool_config = library.DccLibrary.config_dict(file_name=file_name)
        tool_config = {
            'name': 'Options Library',
            'id': LIB_ID,
            'supported_dccs': {'maya': ['2017', '2018', '2019', '2020']},
            'tooltip': 'Library to easily create data driven options/attributes views.'
        }
        base_tool_config.update(tool_config)

        return base_tool_config
