#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph implementation
"""

from __future__ import print_function, division, absolute_import

import gc
import logging
from uuid import uuid4

from Qt.QtCore import Qt, QObject, Signal, QPoint, QPointF, QRect, QRectF, QSize
from Qt.QtWidgets import QGraphicsView, QMenuBar, QRubberBand, QShortcut, QGraphicsColorizeEffect, QUndoStack
from Qt.QtWidgets import QGraphicsTextItem, QGraphicsItem, QGraphicsWidget, QGraphicsProxyWidget
from Qt.QtGui import QFont, QColor, QPainter, QPainterPath, QKeySequence

from tpDcc.libs.python import python, name as name_utils
from tpDcc.libs.qt.core import mixin, input, contexts as qt_contexts

from tpDcc.libs.nodegraph.core import consts
from tpDcc.libs.nodegraph.commands import nodeadded
from tpDcc.libs.nodegraph.managers import nodes

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


class Graph(object):
    def __init__(self, model=None):
        super(Graph, self).__init__()

        self._model = model or GraphModel()

    def add_node(self, node_class):
        new_node = node_class()
        new_node

        node_uuids = python.force_list(node_uuid)
        assert node_uuids, 'Failed to add nodes, None is passed'

        nodes_to_add = [uuid_node for uuid_node in node_uuids if uuid_node and uuid_node not in self.get_nodes()]
        if not nodes_to_add:
            return False

        self._nodes.update(nodes_to_add)

        self.nodesAdded.emit(nodes_to_add)

        return True


@mixin.theme_mixin
class GraphView(QGraphicsView, object):

    showNodeSearcher = Signal()
    selectionCleared = Signal()
    nodeDoubleClicked = Signal(str)

    def __init__(self, scene=None, parent=None):
        self._model = GraphModel()

        super(GraphView, self).__init__(parent=parent)

        self._undo_stack = QUndoStack(self)

    # =================================================================================================================
    # UNDO STACK
    # =================================================================================================================

    def begin_undo(self, macro_name):
        self._undo_stack.beginMacro(macro_name)

    def end_undo(self):
        self._undo_stack.endMacro()

    def clear_undo_stack(self):
        self._undo_stack.clear()
        gc.collect()

    # =================================================================================================================
    # NODES
    # =================================================================================================================

    def get_nodes(self):
        return list(self._nodes)

    def create_node(self, node_type, name=None, x=0.0, y=0.0, selected=False):
        if not self.editable:
            LOGGER.warning('Cannot create new nodes because edit mode in graph is disabled!')
            return None

        new_node = nodes.create_node_view_from_type(node_type)
        if not new_node:
            LOGGER.warning('Cannot create node of type: "{}"'.format(node_type))
            return None

        new_node.pre_create()
        new_node.set_name(name)
        new_node.set_position(x, y)
        new_node.set_selected(selected)
        new_node.post_create()

        undo_command = nodeadded.NodeAddedCommand(self, new_node)

        self._undo_stack.push(undo_command)

        self.nodeCreated.emit(new_node)

        return new_node

    def add_node(self, node_uuid):
        node_uuids = python.force_list(node_uuid)
        assert node_uuids, 'Failed to add nodes, None is passed'

        nodes_to_add = [uuid_node for uuid_node in node_uuids if uuid_node and uuid_node not in self.get_nodes()]
        if not nodes_to_add:
            return False

        self._nodes.update(nodes_to_add)

        self.nodesAdded.emit(nodes_to_add)

        return True

    def delete_node(self, node_uuid):
        if not node_uuid:
            return

        if node_uuid in self._nodes:
            self._nodes.remove(node_uuid)

        if node_uuid in self._selected_nodes:
            self._selected_nodes.remove(node_uuid)

        self.nodeDeleted.emit(node_uuid)

    def delete_selected_nodes(self):
        selected_nodes = self._selected_nodes.copy()
        if not selected_nodes:
            return

        for node_uuid in selected_nodes:
            self._nodes.remove(node_uuid)
        self._selected_nodes.clear()

        self.nodesDeleted.emit(selected_nodes)


class GraphModel(QObject, object):


    editableChanged = Signal(bool)
    isRootChanged = Signal(bool)
    nodeCreated = Signal(object)

    def __init__(self):
        super(GraphModel, self).__init__()

        self._editable = True
        self._is_root = False
        self._nodes = python.UniqueDict()
        self._connectors = python.UniqueDict()

    def __repr__(self):
        return '<{} object at {}>'.format(self.__class__.__name__, self._uuid)

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, flag):
        self._editable = bool(flag)
        self.editableChanged.emit(self._editable)

    @property
    def is_root(self):
        return self._is_root

    @is_root.setter
    def is_root(self, flag):
        self._is_root = bool(flag)
        self.isRootChanged.emit(self._is_root)

