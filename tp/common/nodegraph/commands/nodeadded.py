#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains node added undo command implementation
"""

from __future__ import print_function, division, absolute_import

import logging

from Qt.QtWidgets import QUndoCommand

from tpDcc.libs.nodegraph.core import common
from tpDcc.libs.nodegraph.managers import nodes

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


class NodeAddedUndoCommand(QUndoCommand, object):
    def __init__(self, graph_view, node_object):
        super(NodeAddedUndoCommand, self).__init__()

        self._graph_view = graph_view
        self._node_object = node_object
        self._pos = None

        self.setText('Added Node')

    def undo(self):
        node_uuid = self._node_object.uuid
        node_view_to_delete = self._graph_view.get_node_by_uuid(node_uuid)
        if not node_view_to_delete:
            LOGGER.warning('Impossible to undo Add Node command. Node view with UUID "{}" not found!'.format(node_uuid))
            return

        self._pos = node_view_to_delete.pos()

        # When deleting an item through the model, a signal is emitted that forces the view to delete a node through
        # the usage of an undo command, to avoid that we disable signals, so model is up to date but we do the view
        # removal manually by calling delete in the node view instance
        with common.block_graph_signals(self._graph_view):
            self._node_object.delete()
            node_view_to_delete.delete()

    def redo(self):

        self.update_model()

        current_scene = self._graph_view.scene()
        if not current_scene:
            return

        node_view = nodes.create_node_view_from_model(self._node_object)
        if not node_view:
            return

        node_view.pre_create()
        if current_scene:
            self._graph_view.scene().addItem(node_view)
        self._graph_view._node_views[node_view.get_uuid()] = node_view
        node_view.post_create()

        if self._pos:
            node_view.setPos(self._pos)

    def update_model(self):
        node_uuid = self._node_object.uuid

        # If the node object is not in graph model, we add it
        if not self._graph_view.model.get_node_by_uuid(node_uuid):
            with common.block_graph_signals(self._graph_view):
                self._graph_view.model.add_node(self._node_object)
