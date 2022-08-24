#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains function libraries implementation for math nodes
"""

from tpDcc.libs.nodegraph.core import consts, functionlib


class MathLib(functionlib.FunctionLibrary):

    @staticmethod
    @functionlib.IMPLEMENT_NODE(
        returns=('BoolPort', False),
        meta={consts.NodeLibraryMeta.CATEGORY: 'Math|Basic', consts.NodeLibraryMeta.KEYWORDS: ['=', 'operator']})
    def IsEqual(
            a=('AnyPort', None, {consts.PortSpecifiers.CONSTRAINT: '1'}),
            b=('AnyPort', None, {consts.PortSpecifiers.CONSTRAINT: '1'})):
        """
        Is a equal to b
        :param a:
        :param b:
        :return:
        """

        return a == b
