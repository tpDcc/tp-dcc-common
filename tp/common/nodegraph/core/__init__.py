#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc-libs-curves function core implementations
"""

from __future__ import print_function, division, absolute_import

from tpDcc.core import library

LIB_ID = 'tpDcc-libs-nodegraph'


class NodeGraphLib(library.DccLibrary, object):
    def __init__(self, *args, **kwargs):
        super(NodeGraphLib, self).__init__(*args, **kwargs)

    @classmethod
    def config_dict(cls, file_name=None):
        base_tool_config = library.DccLibrary.config_dict(file_name=file_name)
        tool_config = {
            'name': 'Node Graph Library',
            'id': LIB_ID,
            'supported_dccs': {'maya': ['2017', '2018', '2019', '2020']},
            'tooltip': 'Library to create and manage graph in a DCC agnostic way'
        }
        base_tool_config.update(tool_config)

        return base_tool_config
