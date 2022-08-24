#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains port connected undo command implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtWidgets import QUndoCommand

from tpDcc.libs.qt.core import contexts as qt_contexts

from tpDcc.libs.nodegraph.core import consts, connector
from tpDcc.libs.nodegraph.core.views import connector as connector_view


class PortConnectedUndoCommand(QUndoCommand, object):
    def __init__(self, graph_view, source_port_model, target_port_model):
        super(PortConnectedUndoCommand, self).__init__()

        self._graph_view = graph_view
        self._source_port_model = source_port_model
        self._target_port_model = target_port_model

        self.setText('Ports Connected: {} >> {}'.format(self._source_port_model.name, self._target_port_model.name))

    def undo(self):

        with qt_contexts.block_signals(self._source_port_model):
            self._source_port_model.disconnect_from(self._target_port_model)

        source_uuid = self._source_port_model.uuid
        source_node = self._source_port_model.node
        source_node_view = self._graph_view.get_node_by_uuid(source_node.uuid)
        if not source_node_view:
            return
        source_view = source_node_view.get_port_by_uuid(source_uuid)
        if not source_view:
            return

        source_connectors = source_view.get_connectors()
        ports_uuids = [self._source_port_model.uuid, self._target_port_model.uuid]
        for connector_found in source_connectors:
            if connector_found.source.get_uuid() in ports_uuids and connector_found.target.get_uuid() in ports_uuids:
                connector_found.delete()

    def redo(self):

        self.update_model()

        current_scene = self._graph_view.scene()
        if not current_scene:
            return

        new_connector = connector.Connector()

        if self._target_port_model.direction == consts.PortDirection.Input:
            new_connector.source = self._source_port_model
            new_connector.target = self._target_port_model
        else:
            new_connector.source = self._target_port_model
            new_connector.target = self._source_port_model

        new_connector_view = connector_view.ConnectorView(model=new_connector)
        new_connector_view.pre_create()
        current_scene.addItem(new_connector_view)
        new_connector_view.post_create()

    def update_model(self):

        if self._target_port_model not in self._source_port_model.sources:
            self._source_port_model.sources.add(self._target_port_model)
        if self._source_port_model not in self._target_port_model.sources:
            self._target_port_model.sources.add(self._source_port_model)

        if self._source_port_model.direction == consts.PortDirection.Input:
            self._source_port_model.value = self._target_port_model.value
        else:
            self._target_port_model.value = self._source_port_model.value


# class PortConnectedUndoCommand(QUndoCommand, object):
#     def __init__(self, output_port_model, input_port_model):
#         super(PortConnectedUndoCommand, self).__init__()
#
#         self._output_port_model = output_port_model
#         self._input_port_model = input_port_model
#
#     def undo(self):
#         self._input_port_model.disconnect_from(self._output_port_model)
#
#     def redo(self):
#         self._input_port_model.connect_to(self._output_port_model)
