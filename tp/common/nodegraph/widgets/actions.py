#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains menu and actions for widgets
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Signal
from Qt.QtWidgets import QMenu, QAction


class BaseMenu(QMenu, object):
    def __init__(self, *args, **kwargs):
        super(BaseMenu, self).__init__(*args, **kwargs)

        self._node_class = None
        self._graph = None

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value


class GraphAction(QAction, object):

    executed = Signal(object)

    def __init__(self, *args, **kwargs):
        super(GraphAction, self).__init__(*args, **kwargs)

        self._graph = None
        self.triggered.connect(self._on_triggered)

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value

    def _on_triggered(self):
        self.executed.emit(self._graph)


class NodeAction(GraphAction):

    executed = Signal(object, object)

    def __init__(self, *args, **kwargs):
        super(NodeAction, self).__init__(*args, **kwargs)

        self._node_uuid = None

    @property
    def node_uuid(self):
        return self._node_uuid

    @node_uuid.setter
    def node_uuid(self, value):
        self._node_uuid = value

    def _on_triggered(self):
        node = self._graph.get_node_by_uuid(self._node_uuid)
        self.executed.emit(self._graph.model, node.model)
