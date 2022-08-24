#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains sliced connectors undo command implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtWidgets import QUndoCommand

from tpDcc.libs.qt.core import contexts as qt_contexts

from tpDcc.libs.nodegraph.core import common

class SlicedConnectorsUndoCommand(QUndoCommand, object):
    def __init__(self, graph_view, input_output_models):
        super(SlicedConnectorsUndoCommand, self).__init__()

        self._graph_view = graph_view
        self._input_output_models = input_output_models

    def undo(self):
        for input_output_model in self._input_output_models:

            input_port_model = input_output_model[0]
            output_port_model = input_output_model[1]

            # We cannot reuse input/output models because maybe the can be already deleted.
            input_port_uuid = input_port_model.uuid
            output_port_uuid = output_port_model.uuid
            input_node = input_port_model.node
            output_node = output_port_model.node
            input_node_view = self._graph_view.get_node_by_uuid(input_node.uuid)
            output_node_view = self._graph_view.get_node_by_uuid(output_node.uuid)
            if not input_node_view or not output_node_view:
                return
            input_view = input_node_view.get_port_by_uuid(input_port_uuid)
            output_view = output_node_view.get_port_by_uuid(output_port_uuid)

            with qt_contexts.block_signals(input_view.model):
                input_port_model.connect_to(output_view.model)

            common.create_connector(input_view.scene(), input_view.model, output_view.model)

    def redo(self):
        for input_output_model in self._input_output_models:
            input_port_model = input_output_model[0]
            output_port_model = input_output_model[1]

            with qt_contexts.block_signals(input_port_model):
                input_port_model.disconnect_from(output_port_model)

            input_port_uuid = input_port_model.uuid
            output_port_uuid = output_port_model.uuid
            input_node = input_port_model.node
            output_node = output_port_model.node
            input_node_view = self._graph_view.get_node_by_uuid(input_node.uuid)
            output_node_view = self._graph_view.get_node_by_uuid(output_node.uuid)
            if not input_node_view or not output_node_view:
                return
            input_view = input_node_view.get_port_by_uuid(input_port_uuid)
            output_view = output_node_view.get_port_by_uuid(output_port_uuid)
            if not input_view or not output_view:
                return

            input_connector = input_view.find_connector(output_view)
            if not input_connector:
                return

            input_connector.delete()
