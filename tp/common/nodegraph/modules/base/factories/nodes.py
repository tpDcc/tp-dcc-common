#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains factory used to create node views
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.nodegraph.core import factory

from tpDcc.libs.nodegraph.core import consts
from tpDcc.libs.nodegraph.core.views import node as node_view
from tpDcc.libs.nodegraph.modules.base.nodes import group, timer


class NodeViewFactory(factory.NodeFactory, object):

    @staticmethod
    def create(node_model, *args, **kwargs):

        if isinstance(node_model, group.NodesGroup):
            new_node = group.NodesGroupView(model=node_model)
        elif isinstance(node_model, timer.Timer):
            new_node = node_view.NodeView(model=node_model, header_color=consts.FLOW_CONTROL_COLOR)
        else:
            new_node = node_view.NodeView(model=node_model)

        return new_node
