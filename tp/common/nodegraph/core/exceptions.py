#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains multiple exceptions for tpDcc-libs-nodegraph
"""

from __future__ import print_function, division, absolute_import


class NodeRegistrationException(Exception):
    pass


class PortRegistrationException(Exception):
    pass


class NodeFunctionLibraryRegistrationException(Exception):
    pass


class NodeFactoryRegistrationException(Exception):
    pass


class PortFactoryRegistrationException(Exception):
    pass


class PortDataTypeRegistrationException(Exception):
    pass


class NodeMenuRegistrationException(Exception):
    pass


class NodePropertyError(Exception):
    pass