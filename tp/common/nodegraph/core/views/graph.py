#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph view implementation
"""

from __future__ import print_function, division, absolute_import

import gc
import json
import logging
from functools import partial

from Qt.QtCore import Qt, Signal, QObject, QPoint, QPointF, QRect, QRectF
from Qt.QtWidgets import QMenuBar, QShortcut, QUndoStack, QUndoView, QMessageBox
from Qt.QtWidgets import QGraphicsView, QGraphicsTextItem, QGraphicsItem, QGraphicsWidget, QGraphicsProxyWidget
from Qt.QtGui import QCursor, QFont, QColor, QPainter, QKeySequence

from tpDcc.libs.python import python, mathlib
from tpDcc.libs.qt.core import mixin, qtutils, input, contexts as qt_contexts

from tpDcc.libs.nodegraph.core import consts, common, menu
from tpDcc.libs.nodegraph.managers import inputs, nodes
from tpDcc.libs.nodegraph.widgets import scene, actions, nodesearcher, selectionrect, autopanner
from tpDcc.libs.nodegraph.core import graph as graph_model
from tpDcc.libs.nodegraph.core.views import node as node_view, port as port_view, connector as connector_view
from tpDcc.libs.nodegraph.commands import nodemoved, slicedconnectors
from tpDcc.libs.nodegraph.modules.base.nodes import group


LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


@mixin.theme_mixin
class GraphView(QGraphicsView, object):

    SCENE_CLASS = scene.GraphScene

    nodeSelected = Signal(str)
    nodesMoved = Signal(dict)

    def __init__(self, model, parent=None):
        self._model = model or graph_model.Graph()

        self._node_views = python.UniqueDict()

        super(GraphView, self).__init__(parent=parent)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setRenderHint(QPainter.HighQualityAntialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing)
        self.setCacheMode(QGraphicsView.CacheBackground)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self.resize(1000, 800)

        self._left_mouse_pressed = False
        self._right_mouse_pressed = False
        self._middle_mouse_pressed = False
        self._num_lods = 5
        self._minimum_zoom = consts.DEFAULT_GRAPH_SCENE_MINIMUM_ZOOM
        self._maximum_zoom = consts.DEFAULT_GRAPH_SCENE_MAXIMUM_ZOOM
        self._manipulation_mode = consts.GraphViewerManipulationMode.NONE
        self._scene_rect = QRectF(0, 0, self.size().width(), self.size().height())
        self._mouse_pos = QPointF(0.0, 0.0)
        self._mouse_release_pos = QPointF(0.0, 0.0)
        self._prev_mouse_pos = QPointF(0.0, 0.0)
        self._current_pressed_key = None
        self._pressed_item = None
        self._pressed_port = None
        self._released_item = None
        self._released_port = None
        self._last_size = self.size()
        self._is_resizing = False
        self._node_positions = dict()
        self._connector_layout = consts.GraphViewerConnectorLayout.CURVED
        self._layout_direction = consts.GraphViewerLayoutDirection.HORIZONTAL
        self._temp_node = None

        self._inputs_manager = inputs.InputManager()
        self._undo_stack = QUndoStack(self)
        self._undo_view = None

        self._graph_label = GraphTitleLabel()
        self._graph_label.setFlags(QGraphicsTextItem.ItemIgnoresTransformations)
        self._graph_label.setDefaultTextColor(QColor(255, 255, 255, 50))
        self._graph_label.setFont(QFont('Impact', 20, 1))
        self._graph_label.setZValue(5)

        self._realtime_line = connector_view.RealtimeConnector()
        self._slicer_line = connector_view.ConnectorSlicer()
        self._over_slicer_connectors = list()
        self._draw_realtime_line = False
        self._draw_slicer_line = False
        self._selection_rect = None
        self._mouse_press_selected_nodes = list()
        self._mouse_press_selected_connectors = list()

        menubar = QMenuBar(self)
        menubar.setNativeMenuBar(False)
        menubar.setMaximumWidth(0)
        self._show_context_menu = True
        self._context_menu = actions.BaseMenu('NodeGraph', self)
        menubar.addMenu(self._context_menu)

        self._auto_panner = autopanner.AutoPanner()

        self._node_searcher = nodesearcher.NodeSearcherWidget(graph_view=self)
        self._node_searcher.setVisible(False)
        tab = QShortcut(QKeySequence(Qt.Key_Tab), self)
        tab.activated.connect(self.toggle_node_searcher)

        self.setScene(self.SCENE_CLASS())
        self.scene().addItem(self._graph_label)
        self._update_scene()

        self._setup_menu()
        self.setup_signals()

        self.refresh()

    def __repr__(self):
        return '{}.{}()'.format(self.__module__, self.__class__.__name__)

    def setup_signals(self):
        self._model.nameChanged.connect(self._graph_label.setPlainText)
        self._model.nodeAdded.connect(partial(common.add_node, self))
        self._model.nodeDeleted.connect(partial(common.delete_node, self))

        # self._graph_label.signals.textChanged.connect(partial(self._call_witout_signals, self._controller.set_name))

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def model(self):
        return self._model

    @property
    def node_views(self):
        return self._node_views

    @property
    def pressed_port(self):
        return self._pressed_port

    @property
    def draw_realtime_line(self):
        return self._draw_realtime_line

    @property
    def realtime_line(self):
        return self._realtime_line

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def scale(self, scale_x, scale_y, pos=None):
        """
        Overrides Qt.QWidget scale function
        :param scale_x: float
        :param scale_y: float
        :param pos:
        :return:
        """

        scale = [scale_x, scale_y]
        center = pos or self._scene_rect.center()
        width = self._scene_rect.width() / scale[0]
        height = self._scene_rect.height() / scale[1]
        self._scene_rect = QRectF(
            center.x() - (center.x() - self._scene_rect.left()) / scale[0],
            center.y() - (center.y() - self._scene_rect.top()) / scale[1], width, height)
        self._update_scene()

    def drawBackground(self, painter, rect):
        super(GraphView, self).drawBackground(painter, rect)
        polygon = self.mapToScene(self.viewport().rect())
        # self._graph_label.setPos(polygon[1] - QPointF(self._graph_label.boundingRect().width(), 0))
        self._graph_label.setPos(polygon[0])

    def resizeEvent(self, event):
        delta = max(self.size().width() / self._last_size.width(), self.size().height() / self._last_size.height())
        self._set_zoom(delta)
        self._last_size = self.size()
        super(GraphView, self).resizeEvent(event)

    def mousePressEvent(self, event):
        super(GraphView, self).mousePressEvent(event)

        self._show_context_menu = True
        self._left_mouse_pressed = True if event.button() == Qt.LeftButton else False
        self._right_mouse_pressed = True if event.button() == Qt.RightButton else False
        self._middle_mouse_pressed = True if event.button() == Qt.MiddleButton else False

        self._pressed_item = self.itemAt(event.pos())
        self._pressed_port = self.find_port_near_position(event.pos())
        node_item = self.node_view_from_instance(self._pressed_item)
        map_pos = self.mapToScene(event.pos())

        modifiers = event.modifiers()
        current_input = input.InputAction(
            name='temp', action_type=input.InputActionType.Mouse,
            group='temp', mouse=event.button(), modifiers=modifiers)

        if any([not self._pressed_item,
                isinstance(self._pressed_item, connector_view.ConnectorView) and modifiers != Qt.AltModifier]):

            self._is_resizing = False

            if self._left_mouse_pressed and self._current_pressed_key:
                if self._current_pressed_key == Qt.Key_B:
                    spawn_pos = map_pos
                    print('Spawn node ...')

            if isinstance(node_item, group.NodesGroup):
                self._is_resizing = True
                node_item.setSelected(False)

            if not self._is_resizing:
                if isinstance(self._pressed_item, connector_view.ConnectorView) and \
                        modifiers == Qt.NoModifier and self._left_mouse_pressed:
                    closest_port = self.find_port_near_position(event.pos(), 20)
                    if closest_port:
                        print(closest_port)

            if self._left_mouse_pressed and modifiers in [Qt.NoModifier, Qt.ShiftModifier,
                                                          Qt.ControlModifier, Qt.ControlModifier | Qt.ShiftModifier]:
                self.set_manipulation_mode(consts.GraphViewerManipulationMode.SELECT)
                self._selection_rect = selectionrect.SelectionRect(
                    graph=self, mouse_down_pos=map_pos, modifiers=modifiers)
                self._selection_rect.select_fully_intersection_items = False
                self._mouse_press_selected_nodes = [node for node in self.get_selected_nodes()]
                self._mouse_press_selected_connectors = [connector for connector in self.get_selected_connectors()]
                if modifiers not in [Qt.ShiftModifier, Qt.ControlModifier]:
                    self.clear_selection()
            else:
                if self._selection_rect:
                    self._selection_rect.destroy()
                    self._selection_rect = None

            if current_input in self._inputs_manager['Viewer.Pan']:
                self.set_manipulation_mode(consts.GraphViewerManipulationMode.PAN)
            elif current_input in self._inputs_manager['Viewer.Zoom']:
                self.set_manipulation_mode(consts.GraphViewerManipulationMode.ZOOM)
            if current_input in self._inputs_manager['Viewer.SliceConnectors']:
                self.set_manipulation_mode(consts.GraphViewerManipulationMode.SLICER)
                self._draw_slicer_line = True
                self._slicer_line.draw_path(map_pos, map_pos)
                self._slicer_line.setVisible(True)
            self.hide_node_searcher()
        else:
            if self._left_mouse_pressed and modifiers == Qt.NoModifier:
                if self._pressed_port and self.model.editable:
                    self._start_realtime_connection(self._pressed_port)
                    return

    def mouseReleaseEvent(self, event):

        self._auto_panner.stop()

        modifiers = event.modifiers()
        self._left_mouse_pressed = False if event.button() == Qt.LeftButton else True
        self._right_mouse_pressed = False if event.button() == Qt.RightButton else True
        self._middle_mouse_pressed = False if event.button() == Qt.MiddleButton else True

        self._mouse_release_pos = event.pos()
        self._released_item = self.itemAt(event.pos())
        self._released_port = self.find_port_near_position(event.pos())

        if self._manipulation_mode == consts.GraphViewerManipulationMode.SELECT and self._selection_rect:
            self._selection_rect.destroy()
            self._selection_rect = None
        elif self._manipulation_mode == consts.GraphViewerManipulationMode.SLICER or self._slicer_line.isVisible():
            self._slice_connectors(self._slicer_line.path())
            slicer_point = QPointF(0.0, 0.0)
            self._slicer_line.setVisible(False)
            self._slicer_line.draw_path(slicer_point, slicer_point)
            self._draw_slicer_line = False
            for over_connector in self._over_slicer_connectors:
                over_connector.ready_to_slice = False
            self._over_slicer_connectors = list()

        moved_nodes = {
            node_item: scene_pos for node_item, scene_pos in self._node_positions.items()
            if node_item.get_position() != scene_pos
        }
        if moved_nodes:
            self.begin_undo('Move Nodes')
            for node_item, prev_pos in moved_nodes.items():
                self._undo_stack.push(
                    nodemoved.NodeMovedUndoCommand(self, node_item.get_uuid(), node_item.get_position(), prev_pos))
            self.end_undo()
            self.nodesMoved.emit(moved_nodes)
        self._node_positions.clear()

        for node in self.get_all_nodes():
            node.setFlag(QGraphicsItem.ItemIsMovable)
            node.setFlag(QGraphicsItem.ItemIsSelectable)

        connect_ports = not self._pressed_port == self._released_port
        for i in [self._pressed_port, self._released_port]:
            if not i or not isinstance(i, port_view.PortView):
                connect_ports = False
                break
        if connect_ports:
            if common.cycle_check(self._pressed_port.model, self._released_port.model):
                connect_ports = False
            if connect_ports:
                common.connect_port(self, self._pressed_port.model, self._released_port.model)

        if self._draw_realtime_line:
            self._end_realtime_connection()

        if self._manipulation_mode == consts.GraphViewerManipulationMode.ZOOM:
            self._show_context_menu = False

        if event.button() == Qt.LeftButton and self._released_port is None:
            if isinstance(self._pressed_item, port_view.PortView) and modifiers == Qt.NoModifier:
                self.toggle_node_searcher(
                    port_direction=self._pressed_item.get_direction(),
                    port_structure=self._pressed_item.get_current_structure())

        self._pressed_item = None
        self._pressed_port = None
        self._mouse_press_selected_connectors = list()
        self._mouse_press_selected_nodes = list()
        self.set_manipulation_mode(consts.GraphViewerManipulationMode.NONE)

        super(GraphView, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super(GraphView, self).mouseMoveEvent(event)

        modifiers = event.modifiers()
        self._mouse_pos = event.pos()
        mouse_delta = QPointF(self._mouse_pos) - self._prev_mouse_pos
        map_pos = self.mapToScene(event.pos())

        # Select Mode
        if self._manipulation_mode == consts.GraphViewerManipulationMode.SELECT:
            self._selection_rect.set_drag_point(map_pos, modifiers=modifiers)
            all_nodes = self.get_all_nodes()
            all_connectors = self.get_all_connectors()

            # Inverse selection
            if modifiers == Qt.ControlModifier:
                for node in all_nodes:
                    node_selected = node.isSelected()
                    node_collides = self._selection_rect.collidesWithItem(node)
                    if node in self._mouse_press_selected_nodes:
                        if node_selected and node_collides:
                            node.setSelected(False)
                        elif not node_selected and not node_collides:
                            node.setSelected(True)
                    else:
                        if not node_selected and node_collides:
                            node.setSelected(True)
                        elif node_selected and not node_collides:
                            if node not in self._mouse_press_selected_nodes:
                                node.setSelected(False)
                for connector in all_connectors:
                    connector_selected = connector.isSelected()
                    connector_collides = QGraphicsItem.collidesWithItem(self._selection_rect, connector)
                    if connector in self._mouse_press_selected_connectors:
                        if connector_selected and connector_collides:
                            connector.setSelected(False)
                        elif not connector_selected and not connector_collides:
                            connector.setSelected(True)
                    else:
                        if not connector_selected and connector_collides:
                            connector.setSelected(True)
                        elif connector_selected and not connector_collides:
                            if connector not in self._mouse_press_selected_connectors:
                                connector.setSelected(False)

            # Add to Selection
            elif modifiers == Qt.ShiftModifier:
                for node in all_nodes:
                    if not node.isSelected() and self._selection_rect.collidesWithItem(node):
                        node.setSelected(True)
                    elif node.isSelected() and not self._selection_rect.collidesWithItem(node):
                        if node not in self._mouse_press_selected_connectors:
                            node.setSelected(False)
                for connector in all_connectors:
                    if not connector.isSelected() and QGraphicsItem.collidesWithItem(self._selection_rect, connector):
                        connector.setSelected(True)
                    elif connector.isSelected() and not QGraphicsItem.collidesWithItem(self._selection_rect, connector):
                        connector.setSelected(False)

            # Remove from Selection
            elif modifiers == Qt.ControlModifier | Qt.ShiftModifier:
                for node in all_nodes:
                    if self._selection_rect.collidesWithItem(node):
                        node.setSelected(False)
                for connector in all_connectors:
                    if QGraphicsItem.collidesWithItem(self._selection_rect, connector):
                        connector.setSelected(False)

            # Normal Selection
            else:
                self.clear_selection()
                for node in all_nodes:
                    if not node.isSelected() and self._selection_rect.collidesWithItem(node):
                        node.setSelected(True)
                    elif node.isSelected() and not self._selection_rect.collidesWithItem(node):
                        node.setSelected(False)
                for connector in all_connectors:
                    if not connector.isSelected() and QGraphicsItem.collidesWithItem(self._selection_rect, connector):
                        connector.setSelected(True)
                    elif connector.isSelected() and not QGraphicsItem.collidesWithItem(self._selection_rect, connector):
                        connector.setSelected(False)

        # Slicer Mode
        elif self._manipulation_mode == consts.GraphViewerManipulationMode.SLICER:
            if self._slicer_line not in self.scene().items():
                self.scene().addItem(self._slicer_line)
            p1 = self._slicer_line.path().pointAtPercent(0)
            p2 = self.mapToScene(self._prev_mouse_pos)
            self._slicer_line.draw_path(p1, p2)
            self._slicer_line.show()
            self._connectors_ready_to_slice(self._slicer_line.path())
            self._prev_mouse_pos = event.pos()
            super(GraphView, self).mouseMoveEvent(event)
            return

        # Pan Mode
        elif self._manipulation_mode == consts.GraphViewerManipulationMode.PAN:
            self._set_pan(mouse_delta.x(), mouse_delta.y())

        # Zoom Mode
        elif self._manipulation_mode == consts.GraphViewerManipulationMode.ZOOM:
            self._set_zoom(mouse_delta.x())

        self._prev_mouse_pos = event.pos()
        self._auto_panner.tick(self.viewport().rect(), event.pos())

    def keyPressEvent(self, event):
        super(GraphView, self).keyPressEvent(event)

        modifiers = event.modifiers()
        self._current_pressed_key = event.key()

        if self._manipulation_mode == consts.GraphViewerManipulationMode.SELECT and self._selection_rect:
            map_pos = self.mapToScene(self._mouse_pos)
            self._selection_rect.set_drag_point(map_pos, modifiers=modifiers)
            self.viewport().repaint()

    def keyReleaseEvent(self, event):
        super(GraphView, self).keyReleaseEvent(event)

        modifiers = event.modifiers()

        if self._manipulation_mode == consts.GraphViewerManipulationMode.SELECT and self._selection_rect:
            map_pos = self.mapToScene(self._mouse_pos)
            self._selection_rect.set_drag_point(map_pos, modifiers=modifiers)
            self.viewport().repaint()

        self._current_pressed_key = None

    def wheelEvent(self, event):
        if hasattr(event, 'angleDelta'):
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.angleDelta().x()
        else:
            delta = event.delta()

        self._set_zoom(delta, pos=event.pos())

        super(GraphView, self).wheelEvent(event)

    def dragEnterEvent(self, event):
        super(GraphView, self).dragEnterEvent(event)

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            print(urls)
        elif event.mimeData().hasFormat('text/plain'):
            scene_pos = self.mapToScene(event.pos())
            event.accept()
            mime = str(event.mimeData().text())
            node_template = json.loads(mime)
            if consts.VARIABLE_TAG in node_template:
                return

            node_template['x'] = scene_pos.x()
            node_template['y'] = scene_pos.y()

            # module_name = json_data['module']
            # node_type = json_data['type']
            # lib_name = json_data['lib']

            try:
                self._temp_node.is_temp = False
                self._temp_node = None
            except Exception:
                pass

            self._temp_node = nodes.create_node_view_from_template(node_template)
            self.scene().addItem(self._temp_node)

    def dragMoveEvent(self, event):
        self._mouse_pos = event.pos()
        scene_pos = self.mapToScene(self._mouse_pos)

        if event.mimeData().hasFormat('text/plain'):
            event.setDropAction(Qt.MoveAction)
            event.accept()
            if self._temp_node:
                self._temp_node.setPos(scene_pos)

        else:
            super(GraphView, self).dragMoveEvent(event)

    def contextMenuEvent(self, event):
        self._right_mouse_pressed = False
        context_menu = None

        if not self._show_context_menu:
            return

        pos = self.mapToScene(self._prev_mouse_pos)
        near_nodes = self._find_items_near_scene_pos(pos, item_type=node_view.BaseNodeView)
        if near_nodes:
            node = near_nodes[0]
            node_menu_class = nodes.find_menu(node.model.__class__)
            if node_menu_class:
                node_menu = node_menu_class(self, node.get_uuid(), parent=self)
                context_menu = node_menu.qt_menu

        context_menu = context_menu or self._context_menu
        if len(context_menu.actions()) > 0:
            if context_menu.isEnabled():
                context_menu.exec_(event.globalPos())
            else:
                return super(GraphView, self).contextMenuEvent(event)
        else:
            self.showNodeSearcher.emit()

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def tick(self, delta_time):
        if self._auto_panner.is_active():
            delta = self._auto_panner.delta * -1
            self._set_pan(delta.x(), delta.y())

        for connector in self.get_all_connectors():
            connector.tick(delta_time)

    def shutdown(self):
        self.scene().clear()

    def refresh(self):
        self._graph_label.setPlainText(self._model.name)

    def get_uuid(self):
        return self._model.uuid

    def get_title(self):
        return self._graph_label.toPlainText()

    def set_title(self, title):
        self._graph_label.setPlainText(str(title))

    def get_connector_layout(self):
        return self._connector_layout

    def set_connector_layout(self, value):
        self._connector_layout = value

    def get_layout_direction(self):
        return self._layout_direction

    def set_layout_direction(self, value):
        self._layout_direction = value

    def select_all(self):
        # self.begin_undo('Select All')
        [node.setSelected(True) for node in self.get_all_nodes()]
        # self.end_undo()

    def clear_selection(self):
        # self.begin_undo('Clear Selection')
        [node.setSelected(False) for node in self.get_selected_nodes()]
        [connector.setSelected(False) for connector in self.get_selected_connectors()]
        # self.end_undo()

    # =================================================================================================================
    # NODES
    # =================================================================================================================

    def node_view_from_instance(self, instance):
        """
        Returns node view from given node view instance
        :param instance: QGraphicsItem
        :return: variant
        """

        if isinstance(instance, node_view.BaseNodeView):
            return instance
        n = instance
        while (isinstance(n, QGraphicsItem) or isinstance(n, QGraphicsWidget) or isinstance(
                n, QGraphicsProxyWidget)) and n.parentItem():
            n = n.parentItem()
        if isinstance(n, node_view.BaseNodeView):
            return n

        return None

    def get_node_by_uuid(self, node_uuid):
        """
        Returns node view from a given UUID
        :param node_uuid: str
        :return:
        """

        return self._node_views.get(node_uuid, None)

    def get_all_nodes(self, filtered_classes=None):
        """
        Returns all nodes in current graph
        :param filtered_classes: If given, only nodes with given classes will be taken into account
        :return: list
        """

        all_nodes = list()
        current_scene = self.scene()
        if not current_scene:
            return all_nodes

        filtered_classes = python.force_list(filtered_classes)
        if node_view.BaseNodeView not in filtered_classes:
            filtered_classes.append(node_view.BaseNodeView)
        filtered_classes = python.force_tuple(filtered_classes)

        for item in current_scene.items():
            if not item or not isinstance(item, filtered_classes):
                continue
            all_nodes.append(item)

        return all_nodes

    def get_selected_nodes(self, filtered_classes=None):

        selected_nodes = list()
        current_scene = self.scene()
        if not current_scene:
            return selected_nodes

        filtered_classes = python.force_list(filtered_classes)
        if node_view.BaseNodeView not in filtered_classes:
            filtered_classes.append(node_view.BaseNodeView)
        filtered_classes = python.force_tuple(filtered_classes)

        for item in current_scene.selectedItems():
            if not item or not isinstance(item, filtered_classes):
                continue
            selected_nodes.append(item)

        return selected_nodes

    def toggle_node_searcher(self, port_direction=None, port_structure=consts.PortStructure.Single):
        pos = self._prev_mouse_pos
        state = not self._node_searcher.isVisible()
        if state:
            rect = self._node_searcher.rect()
            new_pos = QPoint(pos.x() - rect.width() / 2, pos.y() - rect.height() / 2)
            self._node_searcher.move(new_pos)
            # self._node_searcher.move(QCursor.pos())
            self._node_searcher.setVisible(state)
            self._node_searcher.show()
            self._node_searcher.refresh(port_direction=port_direction, port_structure=port_structure)
            self._node_searcher.reset_text()
            self._node_searcher.focus()
            rect = self.mapToScene(rect).boundingRect()
            self.scene().update(rect)
        else:
            self._node_searcher.setVisible(state)
            # self.clearFocus()

    def hide_node_searcher(self):
        self._node_searcher.setVisible(False)
        # self.clearFocus()

    # =================================================================================================================
    # PORTS
    # =================================================================================================================

    def find_port_near_position(self, scene_pos, tolerance=3):
        tolerance = tolerance * self.get_current_view_scale()
        rect = QRect(
            QPoint(scene_pos.x() - tolerance, scene_pos.y() - tolerance),
            QPoint(scene_pos.x() + tolerance, scene_pos.y() + tolerance))
        items = self.items(rect)
        # ports = [i for i in items if isinstance(i, port.PortView) and type(i) is not port.PortGroup]
        ports = [item for item in items if isinstance(item, port_view.PortView)]

        return ports[0] if len(ports) > 0 else None


    # =================================================================================================================
    # CONNECTORS
    # =================================================================================================================

    def get_all_connectors(self):
        """
        Returns all connectors in current graph
        :return: list
        """

        all_connectors = list()
        current_scene = self.scene()
        if not current_scene:
            return all_connectors

        for item in current_scene.items():
            if not item or not isinstance(item, connector_view.ConnectorView):
                continue
            all_connectors.append(item)

        return all_connectors

    def get_selected_connectors(self):

        selected_connectors = list()
        current_scene = self.scene()
        if not current_scene:
            return selected_connectors

        for item in current_scene.selectedItems():
            if not item or not isinstance(item, connector_view.ConnectorView):
                continue
            selected_connectors.append(item)

        return selected_connectors

    # =================================================================================================================
    # VIEWPORT / SCENE
    # =================================================================================================================

    def set_manipulation_mode(self, mode_index):
        if mode_index == consts.GraphViewerManipulationMode.NONE:
            self.viewport().setCursor(Qt.ArrowCursor)
        elif mode_index == consts.GraphViewerManipulationMode.SELECT:
            self.viewport().setCursor(Qt.ArrowCursor)
        elif mode_index == consts.GraphViewerManipulationMode.PAN:
            self.viewport().setCursor(Qt.OpenHandCursor)
        elif mode_index == consts.GraphViewerManipulationMode.MOVE:
            self.viewport().setCursor(Qt.ArrowCursor)
        elif mode_index == consts.GraphViewerManipulationMode.ZOOM:
            self.viewport().setCursor(Qt.SizeHorCursor)
        elif mode_index == consts.GraphViewerManipulationMode.COPY:
            self.viewport().setCursor(Qt.ArrowCursor)

        self._manipulation_mode = mode_index

    def get_zoom(self):
        """
        Returns the zoom of the graph viewer
        :return: float
        """

        transform = self.transform()
        current_scale = (transform.m11(), transform.m22())
        return float('{:0.2f}'.format(current_scale[0] - 1.0))

    def zoom_in(self):
        """
        Sets the node graph zoom in by 0.1
        """

        zoom = self.get_zoom() + 100
        self._set_zoom(zoom)

    def zoom_out(self):
        """
        Sets the node graph zoom out by 0.1
        """

        zoom = self.get_zoom() - 100
        self._set_zoom(zoom)

    def reset_zoom(self, center=None):
        """
        Resets the zoom to its initial value
        """

        self._scene_rect = QRectF(0, 0, self.size().width(), self.size().height())
        if center:
            self._scene_rect.translate(center - self._scene_rect.center())
        self._update_scene()

    def get_current_view_scale(self):
        """
        Returns current transform scale of the graph view
        :return:
        """

        return self.transform().m22()

    def reset_scale(self):
        """
        Resets current transform scale of the graph view
        :return:
        """
        self.resetMatrix()

    def get_lod_value_from_scale(self, scale=None):
        """
        Returns the current view LOD value taking into account view scale
        :param scale: float or None, scale to get LOD of. If not given, current view scale will be used instead.
        :return: int, lod index
        """

        scale = scale if scale is not None else self.get_current_view_scale()
        scale_percentage = mathlib.get_range_percentage(self._minimum_zoom, self._maximum_zoom, scale)
        lod = mathlib.lerp(self._num_lods, 1, scale_percentage)
        return int(round(lod))

    def sceneMousePressEvent(self, event):
        """
         Viewer scene mouse press event. Takes priority over viewer event.
         :param event:
         :return:
         """

        if self._manipulation_mode == consts.GraphViewerManipulationMode.PAN:
            return

        pos = event.scenePos()

        node_items = self._find_items_near_scene_pos(pos, node_view.BaseNodeView, 3, 3)
        if node_items:
            selected_node = node_items[0]
            for node_item in node_items:
                self._node_positions[node_item] = node_item.get_position()
            if event.button() == Qt.LeftButton:
                self.nodeSelected.emit(selected_node.get_uuid())

    def sceneMouseMoveEvent(self, event):
        """
        Viewer scene mouse move event. Takes priority over viewer event.
        :param event:
        :return:
        """

        if not self._draw_realtime_line or not self._pressed_port:
            return

        pos = self.mapFromScene(event.scenePos())
        mouse_rect = QRect(QPoint(pos.x() - 3, pos.y() - 2), QPoint(pos.x() + 3, pos.y() + 2))
        hover_items = self.items(mouse_rect)
        hovered_ports = [hover_item for hover_item in hover_items if isinstance(hover_item, port_view.PortView)]
        ports_can_be_connected = False
        if hovered_ports:
            hovered_port = hovered_ports[0]
            if isinstance(self._pressed_item, port_view.PortView):
                ports_can_be_connected = common.can_connect_ports(self._pressed_item.model, hovered_port.model)
                if ports_can_be_connected:
                    self._realtime_line.draw_path(self._pressed_item, hovered_port)

        if not ports_can_be_connected:
            pos = event.scenePos()
            # items = self.scene().items(pos)
            # if items and isinstance(items[0], port_view.PortView):
            #     x = items[0].boundingRect().width() / 2
            #     y = items[0].boundingRect().height() / 2
            #     pos = items[0].scenePos()
            #     pos.setX(pos.x() + x)
            #     pos.setY(pos.y() + y)
            self._realtime_line.draw_path(self._pressed_port, cursor_pos=pos)

    # =================================================================================================================
    # CONTEXT MENU
    # =================================================================================================================

    def context_menus(self):
        return {
            'graph': self._context_menu
        }

    def get_context_menu(self, menu_name):
        menus = self.context_menus()
        if menus.get(menu_name):
            if menu_name == 'graph':
                return menu.GraphMenu(self, menus[menu_name])
            elif menu == 'nodes':
                return menu.NodeMenu(self, menus[menu_name])

    # =================================================================================================================
    # UNDO STACK
    # =================================================================================================================

    def begin_undo(self, macro_name):
        self._undo_stack.beginMacro(macro_name)

    def end_undo(self):
        self._undo_stack.endMacro()

    def push_undo(self, undo_command):
        self._undo_stack.push(undo_command)

    def clear_undo_stack(self, *args, **kwargs):
        show_dialog = kwargs.pop('show_dialog', True)
        if show_dialog:
            res = qtutils.show_question(self, 'Clear Undo History', 'Are you sure you want to clear all undo history?')
            if not res == QMessageBox.Yes:
                return

        self._undo_stack.clear()
        gc.collect()

    def get_undo_view(self):
        if not self._undo_view:
            self._undo_view = QUndoView(self._undo_stack)
            self._undo_view.setWindowTitle('Undo View')

        return self._undo_view

    def show_undo_view(self):
        undo_view = self.get_undo_view()
        undo_view.show()

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _setup_menu(self):
        root_menu = self.get_context_menu('graph')

        file_menu = root_menu.add_menu('&File')
        edit_menu = root_menu.add_menu('&Edit')

        file_menu.add_command('Zoom In', self.zoom_in, '=')
        file_menu.add_command('Zoom Out', self.zoom_out, '-')
        file_menu.add_command('Reset Zoom', self.reset_zoom, 'H')

        undo_action = self._undo_stack.createUndoAction(self, '&Undo')
        edit_menu.add_action(undo_action, shortcut=QKeySequence.Undo)
        redo_action = self._undo_stack.createRedoAction(self, '&Redo')
        edit_menu.add_action(redo_action, shortcut=QKeySequence.Redo)
        edit_menu.add_separator()
        edit_menu.add_command('Clear Undo History', self.clear_undo_stack)
        edit_menu.add_command('Show Undo View', self.show_undo_view)
        edit_menu.add_separator()
        edit_menu.add_command('Delete', common.delete_selected_nodes, QKeySequence.Delete)
        edit_menu.add_separator()
        edit_menu.add_command('Select All', self.select_all, 'Ctrl+A')
        edit_menu.add_command('Deselect All', self.clear_selection, 'Ctrl+Shift+A')
        edit_menu.add_command('Enable/Disable', common.disable_selected_nodes, 'D')

    def _call_witout_signals(self, fn, *args, **kwargs):
        """
        Internal function used to call specific functions without emitting signals in the view model
        :param fn:
        :return:
        """

        with qt_contexts.block_signals(self._model):
            return fn(*args, **kwargs)

    def _update_scene(self):
        """
        Internal function that updates and fit in view current scene
        :return:
        """
        self.setSceneRect(self._scene_rect)
        self.fitInView(self._scene_rect, Qt.KeepAspectRatio)

    def _start_realtime_connection(self, selected_port_view):
        if not selected_port_view:
            return

        if self._realtime_line not in self.scene().items():
            self.scene().addItem(self._realtime_line)

        selected_port_view.topLevelItem().setFlag(QGraphicsItem.ItemIsMovable, False)
        selected_port_view.topLevelItem().setFlag(QGraphicsItem.ItemIsSelectable, False)
        self._draw_realtime_line = True
        self._realtime_line.setVisible(True)
        self._auto_panner.start()

    def _end_realtime_connection(self):
        self._draw_realtime_line = False
        self._realtime_line.reset_path()
        self._realtime_line.setVisible(False)
        # if self._realtime_line in self.scene().items():
        #     self.remove_item_by_name('RealTimeLine')

    def _combined_items_rect(self, items):
        """
        Returns a QRectangle with the area of all given nodes
        :param items: list(QGraphicsItem)
        :return: QRect
        """

        current_scene = self.scene()
        if not current_scene:
            return QRect()

        group = current_scene.createItemGroup(items)
        nodes_rect = group.boundingRect()
        current_scene.destroyItemGroup(group)

        return nodes_rect

    def _find_items_near_scene_pos(self, scene_pos, item_type=None, width=20, height=20):
        items = list()

        current_scene = self.scene()
        if not current_scene:
            return items

        x, y = scene_pos.x() - width, scene_pos.y() - height
        rect = QRectF(x, y, width, height)
        items_to_exclude = [self._realtime_line, self._slicer_line]
        for item in current_scene.items(rect):
            if item in items_to_exclude:
                continue
            if not item_type or isinstance(item, item_type):
                items.append(item)

        return items

    def _set_zoom(self, value, sensitivity=None, pos=None):
        """
        Internal function that sets the zoom of the graph view
        :param value: float
        :param sensitivity: float or None
        :param pos: QPointF
        """

        if pos:
            pos = self.mapToScene(pos)
        if sensitivity is None:
            scale = 1.001 ** value
            self.scale(scale, scale, pos)
            return
        if value == 0.0:
            return
        scale = (0.9 + sensitivity) if value < 0.0 else (1.1 - sensitivity)
        zoom = self.get_zoom()
        if self._minimum_zoom >= zoom:
            if scale == 0.9:
                return
        if self._maximum_zoom <= zoom:
            if scale == 1.1:
                return
        self.scale(scale, scale, pos)

    def _set_pan(self, pos_x, pos_y):
        """
        Internal function that sets the panning of the graph view
        :param pos_x: QPointF
        :param pos_y: QPointF
        :return:
        """

        speed = self._scene_rect.width() * 0.0015
        x = -pos_x * speed
        y = -pos_y * speed
        self._scene_rect.adjust(x, y, x, y)
        self._update_scene()

    def _connectors_ready_to_slice(self, slicer_path):
        """
        Internal function that updates connectors painter depending of a connector its ready to be sliced or not
        :param slicer_path:
        :return:
        """

        over_connectors = [item for item in self.scene().items(slicer_path) if isinstance(
            item, connector_view.ConnectorView)]
        if not over_connectors:
            for over_connector in self._over_slicer_connectors:
                over_connector.ready_to_slice = False
            self._over_slicer_connectors = list()
        else:
            for over_connector in over_connectors:
                over_connector.ready_to_slice = True
                if over_connector not in self._over_slicer_connectors:
                    self._over_slicer_connectors.append(over_connector)
            connectors_to_clean = list()
            for over_connector in self._over_slicer_connectors:
                if over_connector not in over_connectors:
                    connectors_to_clean.append(over_connector)
            for over_connector in connectors_to_clean:
                over_connector.ready_to_slice = False

    def _slice_connectors(self, slicer_path):
        """
        Internal function that slice connectors located inside given path
        :param slicer_path:
        :return:
        """

        current_scene = self.scene()
        if not current_scene:
            return

        connectors_in_path = [item for item in current_scene.items(slicer_path) if isinstance(
            item, connector_view.ConnectorView) and item != self._slicer_line]
        if not connectors_in_path:
            return

        connectors_ports = list()
        for connector in connectors_in_path:
            source_view = connector.source
            target_view = connector.target
            source_model = source_view.model
            target_model = target_view.model
            connectors_ports.append([target_model, source_model])
        if not connectors_ports:
            return

        self.begin_undo('Sliced Connectors')
        self._undo_stack.push(slicedconnectors.SlicedConnectorsUndoCommand(self, connectors_ports))
        self.end_undo()


class GraphTitleLabelSignals(QObject):

    textChanged = Signal(str)


class GraphTitleLabel(QGraphicsTextItem):

    def __init__(self):
        super(GraphTitleLabel, self).__init__()

        self.signals = GraphTitleLabelSignals()

        self.setFlags(QGraphicsTextItem.ItemIgnoresTransformations)
        self.setDefaultTextColor(QColor(255, 255, 255, 50))
        self.setFont(QFont('Impact', 20, 1))
        self.setZValue(5)

    def setPlainText(self, *args, **kwargs):
        super(GraphTitleLabel, self).setPlainText(*args, **kwargs)
        self.signals.textChanged.emit(self.toPlainText())
