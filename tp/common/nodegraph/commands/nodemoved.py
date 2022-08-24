#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains node moved  undo command implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtWidgets import QUndoCommand


class NodeMovedUndoCommand(QUndoCommand, object):
    def __init__(self, graph_view, node_uuid, pos=None, prev_pos=None):
        super(NodeMovedUndoCommand, self).__init__()

        self._graph_view = graph_view
        self._node_uuid = node_uuid
        self._pos = pos
        self._prev_pos = prev_pos

    def undo(self):
        node_view_to_move = self._graph_view._node_views.get(self._node_uuid, None)
        if not node_view_to_move:
            return
        node_view_to_move.set_position(self._prev_pos)

    def redo(self):
        if self._pos == self._prev_pos:
            return
        node_view_to_move = self._graph_view.get_node_by_uuid(self._node_uuid)
        if not node_view_to_move:
            return
        node_view_to_move.set_position(self._pos)
