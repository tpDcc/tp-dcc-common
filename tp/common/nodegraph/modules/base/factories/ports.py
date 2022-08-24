#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains factory used to create port views
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.nodegraph.core import factory

from tpDcc.libs.nodegraph.core.views import port
from tpDcc.libs.nodegraph.modules.base.ports import execport
from tpDcc.libs.nodegraph.modules.base.views import execport as view_execport


class PortViewFactory(factory.PortFactory, object):

    @staticmethod
    def create(port_model, owning_node, *args, **kwargs):

        if isinstance(port_model, execport.ExecPort):
            port_view = view_execport.ExecPortView(model=port_model, parent=owning_node)
        else:
            port_view = port.PortView(model=port_model, parent=owning_node)

        return port_view
