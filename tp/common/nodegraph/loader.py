#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tpDcc.libs.nodegraph
"""

from tpDcc.libs.nodegraph.managers import modules


def init(*args, **kwargs):
    """
    Initializes library
    """

    modules_path = modules.get_modules_path()
    modules.load_modules(package_name='tpDcc-libs-nodegraph', module_paths=modules_path)
