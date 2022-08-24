#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph canvas model/view class implementation
"""

from __future__ import print_function, division, absolute_import

import logging

from Qt.QtCore import QObject, Signal, QTimer

from tpDcc.libs.python import python, name as name_utils
from tpDcc.libs.qt.core import base, contexts as qt_contexts
from tpDcc.libs.qt.widgets import layouts, stack

from tpDcc.libs.nodegraph.core import graph
from tpDcc.libs.nodegraph.core.views import graph as graph_view
from tpDcc.libs.nodegraph.managers import inputs

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


class GraphCanvas(base.BaseWidget, object):
    def __init__(self, parent=None):

        self._model = GraphCanvasModel()
        self._controller = GraphCanvasController(model=self._model)

        super(GraphCanvas, self).__init__(parent=parent)

        self._tick_timer = QTimer()
        self._last_clock = 0.0
        self._fps = 60

        self.refresh()

        self.start_main_loop()

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def get_main_layout(self):
        main_layout = layouts.VerticalLayout(spacing=1, margins=(1, 1, 1, 1))
        main_layout.setObjectName('graphCanvasWidgetMainLayout')
        return main_layout

    def ui(self):
        super(GraphCanvas, self).ui()

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self._stack = stack.SlidingOpacityStackedWidget(parent=self)
        self.main_layout.addWidget(self._stack)

    def setup_signals(self):
        self._model.activeGraphChanged.connect(self._stack.setCurrentWidget)
        self._model.graphAdded.connect(self._create_graph)

    # =================================================================================================================
    # LOOP
    # =================================================================================================================

    def start_main_loop(self):
        self._tick_timer.timeout.connect(self.main_loop)
        self._tick_timer.start(1000 / 60)

    def stop_main_loop(self):
        self._tick_timer.stop()
        self._tick_timer.timeout.disconnect()

    def main_loop(self):
        delta_time = python.current_processor_time() - self._last_clock
        ds = delta_time * 1000.0
        if ds > 0:
            self._fps = int(1000.0 / ds)

        active_graph = self._model.active_graph
        if active_graph:
            active_graph.tick(delta_time)

        self._last_clock = python.current_processor_time()

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def refresh(self):
        if not self._model.graphs:
            self._create_graph(is_root=True)

    def get_active_graph(self):
        """
        Returns current active graph
        :return: GraphView
        """

        return self._model.active_graph.model

    def get_all_graphs(self):
        """
        Returns all graphs being managed by this manager
        :return: list(GraphModel)
        """

        return [graph_found.model for graph_found in list(self._model.graphs.values())]

    def get_unique_graph_name(self, name):
        """
        Returns unique graph name
        :param name: str
        :return: str
        """

        current_names = [g.name for g in self.get_all_graphs()]
        return name_utils.get_unique_name_from_list(current_names, name)

    def add_graph(self, graph_view, set_as_active=True):
        """
        Adds graph to manager and ensures that graph name is unique
        :param graph_view: graph_view
        """

        self._stack.addWidget(graph_view)

        graph_view.set_title(self.get_unique_graph_name(graph_view.get_title()))
        self._controller.add_graph(graph_view)

        if set_as_active:
            self._controller.set_active_graph(graph_view)

    def create_node(self, node_type, name=None, x=0.0, y=0.0):
        current_active_graph = self.get_active_graph()
        if not current_active_graph:
            LOGGER.warning('Impossible to create node from type "{}" because no active graph found!'.format(node_type))
            return None

        return current_active_graph.create_node(node_type, name=name, x=x, y=y)

    def delete_node(self, node_view):
        current_active_graph = self.get_active_graph()
        if not current_active_graph:
            return

        current_active_graph.delete(node_view)

    def delete_selected_nodes(self):
        current_active_graph = self.get_active_graph()
        if not current_active_graph:
            return

        current_active_graph.delete_selected_nodes()

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _create_graph(self, model=None, is_root=False):
        new_graph = model or graph.Graph()
        new_graph.is_root = is_root
        new_graph_view = graph_view.GraphView(model=new_graph)

        return self.add_graph(new_graph_view, set_as_active=True)


class GraphCanvasModel(QObject):

    graphAdded = Signal(object)
    activeGraphChanged = Signal(object)
    shortcutsEnabledChanged = Signal(bool)
    inputsManagerChanged = Signal(object)

    def __init__(self):
        super(GraphCanvasModel, self).__init__()

        self._graphs = dict()
        self._active_graph = None
        self._shortcuts_enabled = True
        self._inputs_manager = inputs.InputManager()

    @property
    def graphs(self):
        return self._graphs

    @property
    def active_graph(self):
        return self._active_graph

    @active_graph.setter
    def active_graph(self, new_active_graph):
        self._active_graph = new_active_graph
        self.activeGraphChanged.emit(self._active_graph)

    def add_graph(self, graph_view):
        """
        Function used to allow model to notify when a graph is added
        :param graph_view: GraphView
        """

        self._graphs[graph_view.get_uuid()] = graph_view
        self.graphAdded.emit(graph_view)

    @property
    def shortcuts_enabled(self):
        return self._shortcuts_enabled

    @shortcuts_enabled.setter
    def shortcuts_enabled(self, flag):
        self._shortcuts_enabled = bool(flag)
        self.shortcutsEnabledChanged.emit(self._shortcuts_enabled)

    @property
    def inputs_manager(self):
        return self._inputs_manager

    @inputs_manager.setter
    def inputs_manager(self, value):
        self._inputs_manager = value
        self.inputsManagerChanged.emit(self._inputs_manager)


class GraphCanvasController(object):
    def __init__(self, model):
        super(GraphCanvasController, self).__init__()

        self._model = model

    def set_active_graph(self, graph):
        self._model.active_graph = graph

    def add_graph(self, graph):
        with qt_contexts.block_signals(self._model):
            self._model.add_graph(graph)
