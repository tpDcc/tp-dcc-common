#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base class to create tpNodeGraph function libraries
"""

from __future__ import print_function, division, absolute_import

import inspect
try:
    from inspect import getfullargspec as getargspec
except ImportError:
    from inspect import getargspec

from tpDcc.libs.nodegraph.core import consts


class FunctionLibrary(object):
    def __init__(self, module_name):
        super(FunctionLibrary, self).__init__()

        self._functions = dict()
        for name, fn in inspect.getmembers(self, inspect.isfunction):
            fn.__annotations__['module_name'] = module_name
            fn.__annotations__['lib'] = self.__class__.__name__
            self._functions[name] = fn

    @property
    def functions(self):
        return self._functions


def IMPLEMENT_NODE(fn=None, returns=consts.EMPTY_FUNCTION_RETURN, meta={
    consts.NodeLibraryMeta.CATEGORY: consts.DEFAULT_NODE_CATEGORY,
    consts.NodeLibraryMeta.KEYWORDS: consts.DEFAULT_NODE_KEYWORDS}, node_type=consts.NodeTypes.Pure):
    def wrapper(fn):
        fn.__annotations__ = getattr(fn, '__annotations__', {})
        fn.__annotations__['node_type'] = node_type
        if not meta == consts.EMPTY_FUNCTION_RETURN:
            fn.__annotations__['meta'] = meta
        if not returns == consts.EMPTY_FUNCTION_RETURN:
            fn.__annotations__['return'] = returns
        defaults = fn.__defaults__
        if defaults:
            spec = getargspec(fn)
            for i, name in enumerate(spec.args[-len(defaults):]):
                if len(defaults[i]) < 1 or defaults[i][0] is consts.EMPTY_FUNCTION_RETURN:
                    continue
                fn.__annotations__[name] = defaults[i]
        return fn

    if returns == consts.EMPTY_FUNCTION_RETURN:
        return wrapper(fn)

    return wrapper
