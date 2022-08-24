#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains node deleted undo command implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtWidgets import QUndoCommand

from tpDcc.libs.qt.core import contexts as qt_contexts

from tpDcc.libs.nodegraph.core import node
from tpDcc.libs.nodegraph.managers import nodes


class NodeDeletedUndoCommand(QUndoCommand, object):
    def __init__(self, graph_view, node_data):
        super(NodeDeletedUndoCommand, self).__init__()

        self._graph_view = graph_view
        self._node_data = node_data
        self._pos = None

    def undo(self):
        current_scene = self._graph_view.scene()
        if not current_scene:
            return

        node_uuid = self._node_data['uuid']
        node_model = node.Node.from_data(graph=self._graph_view.model, data=self._node_data)
        node_view = nodes.create_node_view_from_model(node_model)
        with qt_contexts.block_signals(self._graph_view.model):
            if not self._graph_view.model.get_node_by_uuid(node_uuid):
                self._graph_view.model.add_node(node_model)

            node_view.pre_create()
            if current_scene:
                self._graph_view.scene().addItem(node_view)
            self._graph_view.node_views[node_view.get_uuid()] = node_view
            node_view.post_create()

            if self._pos:
                node_view.setPos(self._pos)

    def redo(self):

        self.update_model()

        node_uuid = self._node_data['uuid']
        node_to_remove = self._graph_view.get_node_by_uuid(node_uuid)
        if not node_to_remove:
            return

        self._pos = node_to_remove.pos()

        # Update model and remove connector views
        for input_port_view in node_to_remove.get_connected_inputs():
            with qt_contexts.block_signals(input_port_view.model):
                input_port_view.model.disconnect_from()
                input_connectors = input_port_view.get_connectors()
                for connector_found in input_connectors:
                    connector_found.delete()

        for output_port_view in node_to_remove.get_connected_outputs():
            with qt_contexts.block_signals(output_port_view.model):
                output_port_view.model.disconnect_from()
                input_connectors = output_port_view.get_connectors()
                for connector_found in input_connectors:
                    connector_found.delete()

        node_to_remove.delete()

    def update_model(self):

        node_uuid = self._node_data['uuid']

        if self._graph_view.model.get_node_by_uuid(node_uuid):
            with qt_contexts.block_signals(self._graph_view.model):
                self._graph_view.model.delete_node(node_uuid)
