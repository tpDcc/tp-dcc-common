#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph viewer class implementation
"""

from __future__ import print_function, division, absolute_import

import json

from Qt.QtCore import Qt, QObject, Signal, QPoint, QPointF, QRectF
from Qt.QtWidgets import QGraphicsView, QMenuBar, QGraphicsTextItem
from Qt.QtGui import QFont, QColor, QPainter

from tpDcc.libs.python import mathlib
from tpDcc.libs.qt.core import input

from tpDcc.libs.nodegraph.core import consts, node
from tpDcc.libs.nodegraph.widgets import scene, actions, nodesearcher


class GraphViewer(QGraphicsView, object):

    showNodeSearcher = Signal()
    selectionCleared = Signal()

    def __init__(self, canvas, scene=None, parent=None):

        self._model = GraphViewerModel()
        self._canvas = canvas

        super(GraphViewer, self).__init__(parent=parent or canvas)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing)
        self.setCacheMode(QGraphicsView.CacheBackground)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self.resize(1000, 800)

        self._last_size = self.size()
        self._left_mouse_pressed = False
        self._right_mouse_pressed = False
        self._middle_mouse_pressed = False
        self._mouse_pos = QPointF(0.0, 0.0)
        self._last_mouse_pos = QPointF(0.0, 0.0)
        self._prev_mouse_pos = QPoint(self.width(), self.height())
        self._pressed_item = None
        self._temp_node = None

        menubar = QMenuBar(self)
        menubar.setNativeMenuBar(False)
        menubar.setMaximumWidth(0)
        self._context_menu = actions.BaseMenu('NodeGraph', self)
        self._context_node_menu = actions.BaseMenu('Nodes', self)
        menubar.addMenu(self._context_menu)
        menubar.addMenu(self._context_node_menu)
        self._context_node_menu.setEnabled(False)
        self._node_searcher = nodesearcher.NodeSearcherWidget(parent=self)
        self._node_searcher.setVisible(False)

        self._graph_label = QGraphicsTextItem()
        self._graph_label.setFlags(QGraphicsTextItem.ItemIgnoresTransformations)
        self._graph_label.setDefaultTextColor(QColor(255, 255, 255, 50))
        self._graph_label.setPlainText('Hello World')
        self._graph_label.setFont(QFont('Impact', 20, 1))
        self._graph_label.setZValue(5)

        self._setup_signals()

        if scene:
            self.set_scene(scene)
        self.set_scene_rect(QRectF(0, 0, self.size().width(), self.size().height()))

        self.refresh()

    def __repr__(self):
        return '{}.{}()'.format(self.__module__, self.__class__.__name__)

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
        center = pos or self._model.scene_rect.center()
        width = self._model.scene_rect.width() / scale[0]
        height = self._model.scene_rect.height() / scale[1]
        self.set_scene_rect(QRectF(
            center.x() - (center.x() - self._model.scene_rect.left()) / scale[0],
            center.y() - (center.y() - self._model.scene_rect.top()) / scale[1], width, height))

    def drawBackground(self, painter, rect):
        super(GraphViewer, self).drawBackground(painter, rect)
        polygon = self.mapToScene(self.viewport().rect())
        # self._graph_label.setPos(polygon[1] - QPointF(self._graph_label.boundingRect().width(), 0))
        self._graph_label.setPos(polygon[0])

    def resizeEvent(self, event):
        delta = max(self.size().width() / self._last_size.width(), self.size().height() / self._last_size.height())
        self._set_zoom(delta)
        self._last_size = self.size()
        super(GraphViewer, self).resizeEvent(event)

    def wheelEvent(self, event):
        if hasattr(event, 'angleDelta'):
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.angleDelta().x()
        else:
            delta = event.delta()

        self._set_zoom(delta, pos=event.pos())

        super(GraphViewer, self).wheelEvent(event)

    def mouseDoubleClickEvent(*args, **kwargs):
        pass

    def mousePressEvent(self, event):

        modifiers = event.modifiers()
        current_input = input.InputAction(
            name='temp', action_type=input.InputActionType.Mouse,
            group='temp', mouse=event.button(), modifiers=modifiers)

        alt_modifier = modifiers == Qt.AltModifier
        shift_modifier = modifiers == Qt.ShiftModifier

        self._left_mouse_pressed = True if event.button() == Qt.LeftButton else self._left_mouse_pressed
        self._right_mouse_pressed = True if event.button() == Qt.RightButton else self._right_mouse_pressed
        self._middle_mouse_pressed = True if event.button() == Qt.MiddleButton else self._middle_mouse_pressed

        self._prev_mouse_pos = event.pos()
        self._pressed_item = self.itemAt(event.pos())

        if self._model.scene.get_editable():
            if current_input in self._model.inputs_manager['Viewer.Pan']:
                self.set_manipulation_mode(consts.GraphViewerManipulationMode.PAN)
            elif current_input in self._model.inputs_manager['Viewer.Zoom']:
                self.set_manipulation_mode(consts.GraphViewerManipulationMode.ZOOM)

        if not self._pressed_item:
            self._canvas.clear_selection()
            if self._node_searcher.isVisible():
                self.toggle_node_searcher()
        else:
            if isinstance(self._pressed_item, node.NodeView):
                if modifiers in [Qt.NoModifier, Qt.AltModifier]:
                    self._canvas.select_node(self._pressed_item)
                if modifiers == Qt.ControlModifier and event.button() == Qt.LeftButton:
                    self._canvas.select_node(self._pressed_item) if self._pressed_item.get_selected() \
                        else self._canvas.deselect_node(self._pressed_item)
                if modifiers == Qt.ShiftModifier:
                    self._canvas.select_node(self._pressed_item, replace=False)

            if current_input in self._model.inputs_manager['Viewer.DragNodes']:
                self.set_manipulation_mode(consts.GraphViewerManipulationMode.MOVE)

        # if not valid:
        #     super(GraphViewer, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._left_mouse_pressed = False if event.button() == Qt.LeftButton else self._left_mouse_pressed
        self._right_mouse_pressed = False if event.button() == Qt.RightButton else self._right_mouse_pressed
        self._middle_mouse_pressed = False if event.button() == Qt.MiddleButton else self._middle_mouse_pressed

        self._model.manipulation_mode = consts.GraphViewerManipulationMode.NONE

        super(GraphViewer, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):

        self._mouse_pos = event.pos()
        mouse_delta = QPointF(self._mouse_pos) - self._prev_mouse_pos

        alt_modifier = event.modifiers() == Qt.AltModifier
        shift_modifier = event.modifiers() == Qt.ShiftModifier

        if self._model.manipulation_mode == consts.GraphViewerManipulationMode.PAN:
            self._set_pan(mouse_delta.x(), mouse_delta.y())
        elif self._model.manipulation_mode == consts.GraphViewerManipulationMode.ZOOM:
            self._set_zoom(mouse_delta.x())
        elif self._model.manipulation_mode == consts.GraphViewerManipulationMode.MOVE:
            scaled_delta = mouse_delta / self.get_current_view_scale()
            self._canvas.move_selected_nodes(scaled_delta.x(), scaled_delta.y())

        self._prev_mouse_pos = event.pos()
        super(GraphViewer, self).mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        super(GraphViewer, self).dragEnterEvent(event)

        if event.mimeData().hasUrls():
            event.ignore()
        elif event.mimeData().hasFormat('text/plain'):
            event.accept()
            scene_pos = self.mapToScene(event.pos())
            mime = str(event.mimeData().text())
            json_data = json.loads(mime)

            module_name = json_data['module']

            try:
                self._temp_node.is_temp = False
                self._temp_node = None
            except Exception:
                pass
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('text/plain'):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        super(GraphViewer, self).dragLeaveEvent(event)

    def dropEvent(self, event):
        pass

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        current_input = input.InputAction(
            name='temp', action_type=input.InputActionType.Keyboard, group='temp', key=event.key(), modifiers=modifiers)

        self._canvas.process_input(current_input)

        super(GraphViewer, self).keyPressEvent(event)

    def contextMenuEvent(self, event):
        self._right_mouse_pressed = False
        context_menu = None

        if self._context_node_menu.isEnabled():
            pos = self.mapToScene(self._prev_mouse_pos)

        context_menu = context_menu or self._context_menu
        if len(context_menu.actions()) > 0:
            if context_menu.isEnabled():
                context_menu.exec_(event.globalPos())
            else:
                return super(GraphViewer, self).contextMenuEvent(event)
        else:
            self.showNodeSearcher.emit()

    # =================================================================================================================
    # GETTERS/SETTERS
    # =================================================================================================================

    def set_scene(self, new_scene):
        self._model.scene = new_scene

    def set_label_text(self, label_text):
        self._model.label_text = label_text

    def set_scene_rect(self, rect):
        self._model.scene_rect = rect

    def set_zoom(self, value):
        self._model.zoom = value

    def set_manipulation_mode(self, mode_index):
        self._model.manipulation_mode = mode_index

    def set_shortcuts_enabled(self, flag):
        self._model.shortcuts_enabled = flag

    def get_inputs_manager(self):
        return self._model.inputs_manager

    def set_inputs_manager(self, value):
        self._model.inputs_manager = value

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def refresh(self):
        if not self._model.scene:
            self.set_scene(scene.GraphScene(parent=self))
        self._update_scene()

        self.set_label_text(self._model.label_text)

    def get_zoom(self):
        """
        Returns the zoom of the graph viewer
        :return: float
        """

        transform = self.transform()
        current_scale = (transform.m11(), transform.m22())
        return float('{:0.2f}'.format(current_scale[0] - 1.0))

    def reset_zoom(self, center=None):
        """
        Resets the zoom to its initial value
        """

        scene_rect = QRectF(0, 0, self.size().width(), self.size().height())
        if center:
            scene_rect.translate(center - self._scene_range.center())
        self.set_scene_rect(scene_rect)

    def toggle_node_searcher(self):
        pos = self._prev_mouse_pos
        state = not self._node_searcher.isVisible()
        if state:
            rect = self._node_searcher.rect()
            new_pos = QPoint(pos.x() - rect.width() / 2, pos.y() - rect.height() / 2)
            self._node_searcher.move(new_pos)
            self._node_searcher.setVisible(state)
            rect = self.mapToScene(rect).boundingRect()
            self.scene().update(rect)
        else:
            self._node_searcher.setVisible(state)
            self.clearFocus()

    def get_current_view_scale(self):
        return self.transform().m22()

    def reset_scale(self):
        self.resetMatrix()

    def get_lod_value_from_scale(self, scale=None):
        scale = scale if scale is not None else self.get_current_view_scale()
        scale_percentage = mathlib.get_range_percentage(self._model.minimum_zoom, self._model.maximum_zoom, scale)
        lod = mathlib.lerp(self._model.num_lods, 1, scale_percentage)
        return int(round(lod))

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _setup_signals(self):
        self._model.sceneChanged.connect(self._on_scene_changed)
        self._model.sceneRectChanged.connect(self._on_scene_rect_changed)
        self._model.labelTextChanged.connect(self._graph_label.setPlainText)
        self._model.zoomChanged.connect(self._on_zoom_changed)
        self._model.manipulationModeChanged.connect(self._on_manipulation_mode_changed)

    def _update_scene(self, scene_rect=None):
        self.setSceneRect(scene_rect or self._model.scene_rect)
        self.fitInView(scene_rect or self._model.scene_rect, Qt.KeepAspectRatio)

    def _set_zoom(self, value, sensitivity=None, pos=None):
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
        if self._model.minimum_zoom >= zoom:
            if scale == 0.9:
                return
        if self._model.maximum_zoom <= zoom:
            if scale == 1.1:
                return
        self.scale(scale, scale, pos)

    def _set_pan(self, pos_x, pos_y):
        speed = self._model.scene_rect.width() * 0.0015
        x = -pos_x * speed
        y = -pos_y * speed
        scene_rect = self._model.scene_rect
        scene_rect.adjust(x, y, x, y)
        self.set_scene_rect(scene_rect)

    # =================================================================================================================
    # CALLBACKS
    # =================================================================================================================

    def _on_scene_changed(self, new_scene):
        # new_scene.setItemIndexMethod(QGraphicsScene.NoIndex)
        self.setScene(new_scene)
        self._update_scene()
        self.scene().addItem(self._graph_label)

    def _on_scene_rect_changed(self, scene_rect):
        self._update_scene(scene_rect)

    def _on_zoom_changed(self, value):
        if value == 0:
            self.reset_zoom()
            return
        zoom = self.get_zoom()
        if zoom < 0.0:
            if not (self._model.minimum_zoom <= zoom <= self._model.maximum_zoom):
                return
        else:
            if not (self._model.minimum_zoom <= value <= self._model.maximum_zoom):
                return
        value = value - zoom
        self._set_zoom(value, 0.0)

    def _on_manipulation_mode_changed(self, manipulation_mode):
        if manipulation_mode == consts.GraphViewerManipulationMode.NONE:
            self.viewport().setCursor(Qt.ArrowCursor)
        elif manipulation_mode == consts.GraphViewerManipulationMode.SELECT:
            self.viewport().setCursor(Qt.ArrowCursor)
        elif manipulation_mode == consts.GraphViewerManipulationMode.PAN:
            self.viewport().setCursor(Qt.OpenHandCursor)
        elif manipulation_mode == consts.GraphViewerManipulationMode.MOVE:
            self.viewport().setCursor(Qt.ArrowCursor)
        elif manipulation_mode == consts.GraphViewerManipulationMode.ZOOM:
            self.viewport().setCursor(Qt.SizeHorCursor)
        elif manipulation_mode == consts.GraphViewerManipulationMode.COPY:
            self.viewport().setCursor(Qt.ArrowCursor)


class GraphViewerModel(QObject, object):

    labelTextChanged = Signal(str)
    sceneChanged = Signal(object)
    sceneRectChanged = Signal(tuple)
    minimumZoomChanged = Signal(float)
    maximumZoomChanged = Signal(float)
    zoomChanged = Signal(float)
    zoomFactorChanged = Signal(float)
    numLodsChanged = Signal(int)
    manipulationModeChanged = Signal(int)
    inputsManagerChanged = Signal(object)

    def __init__(self):
        super(GraphViewerModel, self).__init__()

        self._scene = None
        self._scene_rect = QRectF(0, 0, 0, 0)
        self._label_text = ''
        self._minimum_zoom = consts.DEFAULT_GRAPH_SCENE_MINIMUM_ZOOM
        self._maximum_zoom = consts.DEFAULT_GRAPH_SCENE_MAXIMUM_ZOOM
        self._zoom = 1.0
        self._zoom_factor = 1.0
        self._num_lods = 5
        self._manipulation_mode = consts.GraphViewerManipulationMode.NONE
        self._shortcuts_enabled = True
        self._inputs_manager = None

    @property
    def nodes(self):
        return self._nodes

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, value):
        self._scene = value
        self.sceneChanged.emit(self._scene)

    @property
    def scene_rect(self):
        return self._scene_rect

    @scene_rect.setter
    def scene_rect(self, rect):
        self._scene_rect = rect
        self.sceneRectChanged.emit(self._scene_rect)

    @property
    def label_text(self):
        return self._label_text

    @label_text.setter
    def label_text(self, value):
        self._label_text = str(value)
        self.labelTextChanged.emit(self._label_text)

    @property
    def minimum_zoom(self):
        return self._minimum_zoom

    @minimum_zoom.setter
    def minimum_zoom(self, value):
        self._minimum_zoom = float(value)
        self.minimumZoomChanged.emit(self._minimum_zoom)

    @property
    def maximum_zoom(self):
        return self._maximum_zoom

    @maximum_zoom.setter
    def maximum_zoom(self, value):
        self._maximum_zoom = float(value)
        self.maximumZoomChanged.emit(self.maximum_zoom)

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, value):
        self._zoom = float(value)
        self.zoomChanged.emit(self._zoom)

    @property
    def zoom_factor(self):
        return self._zoom_factor

    @zoom_factor.setter
    def zoom_factor(self, value):
        self._zoom_factor = float(value)
        self.zoomFactorChanged.emit(self._zoom_factor)

    @property
    def num_lods(self):
        return self._num_lods

    @num_lods.setter
    def num_lods(self, value):
        self._num_lods = int(value)
        self.numLodsChanged.emit(self._num_lods)

    @property
    def manipulation_mode(self):
        return self._manipulation_mode

    @manipulation_mode.setter
    def manipulation_mode(self, value):
        self._manipulation_mode = int(value)
        self.maximumZoomChanged.emit(self._manipulation_mode)

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

