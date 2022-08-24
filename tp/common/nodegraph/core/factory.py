#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base class to create tpNodeGraph factories
"""

from __future__ import print_function, division, absolute_import


class Factory(object):
    """
    Base class that defines factory classes
    """

    def __init__(self):
        super(Factory, self).__init__()

    @staticmethod
    def create(model, *args, **kwargs):
        pass


class NodeFactory(Factory, object):
    """
    Base class that defines node factory class
    """

    pass


class PortFactory(object):
    """
    Base class that defines port factory class
    """

    @staticmethod
    def create(model, owning_node, *args, **kwargs):
        pass
