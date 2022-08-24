#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph scene widget implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QObject, Signal, QPoint, QLineF
from Qt.QtWidgets import QGraphicsScene
from Qt.QtGui import QFont, QColor, QPainter, QPainterPath, QPen
from tpDcc.libs.python import python

from tpDcc.libs.nodegraph.core import consts


class GridModes(object):
    DOTS = 0
    LINES = 1


class GraphScene(QGraphicsScene, object):
    def __init__(self, model=None, parent=None):

        self._model = model or GraphSceneModel()

        super(GraphScene, self).__init__(parent=parent)

        self._setup_signals()

        self.refresh()

    def __repr__(self):
        return '{}.{}(\'{}\')'.format(self.__module__, self.__class__.__name__, self.viewer())

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def drawBackground(self, painter, rect):
        super(GraphScene, self).drawBackground(painter, rect)

        viewer = self.viewer()
        if not viewer:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setBrush(self.backgroundBrush())

        if self._model.grid_mode == GridModes.DOTS:
            pen = QPen(QColor(*self._model.grid_color), 0.65)
            self._draw_dots(painter, rect, pen, self._model.grid_size)
        else:
            zoom = self.viewer().get_zoom()
            if zoom > -0.5:
                pen = QPen(QColor(*self._model.grid_color), 0.65)
                self._draw_grid(painter, rect, pen, self._model.grid_size)
            if self._model.secondary_grid_enabled:
                color = QColor(*self._model.secondary_grid_color) or self.backgroundBrush().color().darker(150)
                if zoom <= 0.0:
                    color = color.darker(100 - int(zoom * 110))
                pen = QPen(color, 0.65)
                self._draw_grid(painter, rect, pen, self._model.grid_size * self._model.grid_spacing)

        if not self._model.editable:
            pen = QPen(QColor(*(90, 90, 90)))
            self._draw_text(painter, pen)

        pen = QPen(self.backgroundBrush().color().lighter(100))
        pen.setCosmetic(True)
        path = QPainterPath()
        path.addRect(rect)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawPath(path)

        painter.restore()

    def mousePressEvent(self, event):
        modifiers = event.modifiers()
        selected_nodes = list()
        if self.viewer():
            selected_nodes = self.viewer().get_selected_nodes()
            if hasattr(self.viewer(), 'sceneMousePressEvent'):
                self.viewer().sceneMousePressEvent(event)
        super(GraphScene, self).mousePressEvent(event)
        keep_selection = any([event.button() in [Qt.MiddleButton, Qt.RightButton], modifiers == Qt.AltModifier])
        if keep_selection:
            for node in selected_nodes:
                node.setSelected(True)

    def mouseReleaseEvent(self, event):
        if self.viewer() and hasattr(self.viewer(), 'sceneMouseReleaseEvent'):
            self.viewer().sceneMouseReleaseEvent(event)
        super(GraphScene, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.viewer() and hasattr(self.viewer(), 'sceneMouseMoveEvent'):
            self.viewer().sceneMouseMoveEvent(event)
        super(GraphScene, self).mouseMoveEvent(event)

    # =================================================================================================================
    # GETTERS / SETTERS
    # =================================================================================================================

    def set_background_color(self, color_tuple):
        self._model.background_color = color_tuple

    def set_grid_color(self, color_tuple):
        self._model.grid_color = color_tuple

    def set_grid_mode(self, mode):
        self._grid_mode = mode

    def get_editable(self):
        return self._model.editable

    def set_editable(self, flag):
        self._model.editable = flag

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def refresh(self):
        self.setBackgroundBrush(QColor(*self._model.background_color))
        self.set_editable(self._model.editable)

    def viewer(self):
        """
        Returns current view of the scene or None if no view is associated
        :return: QGraphicsView
        """

        return self.views()[0] if self.views() else None

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _setup_signals(self):
        self._model.backgroundColorChanged.connect(self._on_background_color_changed)
        self._model.gridColorChanged.connect(self._on_grid_color_changed)
        self._model.gridModeChanged.connect(self._on_grid_mode_changed)
        self._model.editableChanged.connect(self.update)

    def _draw_dots(self, painter, rect, pen, grid_size):
        zoom = self.viewer().get_zoom()
        if zoom < 0:
            grid_size = int(abs(zoom) / 0.3 + 1) * grid_size

        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())

        first_left = left - (left % grid_size)
        first_top = top - (top % grid_size)

        pen.setWidth(grid_size / 10)
        painter.setPen(pen)

        [painter.drawPoint(
            int(x), int(y)) for x in range(first_left, right, grid_size) for y in range(first_top, bottom, grid_size)]

    def _draw_grid(self, painter, rect, pen, grid_size):
        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())

        first_left = left - (left % grid_size)
        first_top = top - (top % grid_size)

        lines = list()
        lines.extend(QLineF(x, top, x, bottom) for x in range(first_left, right, grid_size))
        lines.extend(QLineF(left, y, right, y) for y in range(first_top, bottom, grid_size))

        painter.setPen(pen)
        painter.drawLines(lines)

    def _draw_text(self, painter, pen):
        font = QFont()
        font.setPixelSize(48)
        painter.setFont(font)
        parent = self.viewer()
        pos = QPoint(20, parent.height() - 20)
        painter.setPen(pen)
        painter.drawText(parent.mapToScene(pos), 'Not Editable')

    # =================================================================================================================
    # CALLBACKS
    # =================================================================================================================

    def _on_background_color_changed(self, color_tuple):
        self.setBackgroundBrush(QColor(*color_tuple))

    def _on_grid_color_changed(self, color_tuple):
        pass

    def _on_grid_mode_changed(self, grid_mode):
        pass


class GraphSceneModel(QObject, object):

    editableChanged = Signal(bool)
    backgroundColorChanged = Signal(tuple)
    gridSizeChanged = Signal(int)
    gridSpacingChanged = Signal(int)
    gridColorChanged = Signal(tuple)
    secondaryGridEnabledChanged = Signal(bool)
    secondaryGridColorChanged = Signal(tuple)
    gridModeChanged = Signal(int)

    def __init__(self):
        super(GraphSceneModel, self).__init__()

        self._editable = True
        self._background_color = consts.DEFAULT_GRAPH_SCENE_BACKGROUND_COLOR
        self._grid_size = consts.DEFAULT_GRAPH_SCENE_GRID_SIZE
        self._grid_spacing = consts.DEFAULT_GRAPH_SCENE_GRID_SPACING
        self._grid_color = consts.DEFAULT_GRAPH_SCENE_GRID_COLOR
        self._secondary_grid_enabled = True
        self._secondary_grid_color = consts.DEFAULT_GRAPH_SCENE_SECONDARY_GRID_COLOR
        self._grid_mode = GridModes.LINES

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, flag):
        self._editable = bool(flag)
        self.editableChanged.emit(self._editable)

    @property
    def background_color(self):
        return self._background_color

    @background_color.setter
    def background_color(self, color_tuple):
        self._background_color = python.force_tuple(color_tuple)
        self.backgroundColorChanged.emit(self._background_color)

    @property
    def grid_size(self):
        return self._grid_size

    @grid_size.setter
    def grid_size(self, value):
        self._grid_size = int(value)
        self.gridSizeChanged.emit(self._grid_size)

    @property
    def grid_spacing(self):
        return self._grid_spacing

    @grid_spacing.setter
    def grid_spacing(self, value):
        self._grid_spacing = int(value)
        self.gridSpacingChanged.emit(self._grid_spacing)

    @property
    def grid_color(self):
        return self._grid_color

    @grid_color.setter
    def grid_color(self, color_tuple):
        self._grid_color = python.force_tuple(color_tuple)
        self.gridColorChanged.emit(self._background_color)

    @property
    def secondary_grid_enabled(self):
        return self._secondary_grid_enabled

    @secondary_grid_enabled.setter
    def secondary_grid_enabled(self, value):
        self._secondary_grid_enabled = bool(value)
        self.secondaryGridEnabledChanged.emit(self._secondary_grid_enabled)

    @property
    def secondary_grid_color(self):
        return self._secondary_grid_color

    @secondary_grid_color.setter
    def secondary_grid_color(self, value):
        self._secondary_grid_color = python.force_tuple(value)
        self.secondaryGridColorChanged.emit(self._secondary_grid_color)

    @property
    def grid_mode(self):
        return self._grid_mode

    @grid_mode.setter
    def grid_mode(self, value):
        self._grid_mode = int(value)
        self.gridModeChanged.emit(self._grid_mode)
