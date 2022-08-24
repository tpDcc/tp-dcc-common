#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains implementation for selection rectangle widget
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QPointF
from Qt.QtWidgets import QGraphicsWidget
from Qt.QtGui import QColor, QPen


class SelectionRect(QGraphicsWidget, object):

    BACKGROUND_COLOR = QColor(100, 100, 100, 50)
    BACKGROUND_ADD_COLOR = QColor(0, 100, 0, 50)
    BACKGROUND_SUB_COLOR = QColor(100, 0, 0, 50)
    BACKGROUND_SWITCH_COLOR = QColor(0, 0, 100, 50)
    PEN = QPen(QColor(255, 255, 255), 1.0, Qt.DashLine)

    def __init__(self, graph, mouse_down_pos, modifiers):
        super(SelectionRect, self).__init__()

        self.setZValue(2)

        self._graph = graph
        self._mouse_down_pos = mouse_down_pos
        self._modifiers = modifiers
        self._select_fully_intersection_items = False

        self._graph.scene().addItem(self)
        self.setPos(self._mouse_down_pos)
        self.resize(0, 0)

    @property
    def select_fully_intersection_items(self):
        return self._select_fully_intersection_items

    @select_fully_intersection_items.setter
    def select_fully_intersection_items(self, flag):
        self._select_fully_intersection_items = flag

    def collidesWithItem(self, item):
        if self._select_fully_intersection_items:
            return self.sceneBoundingRect().contains(item.sceneBoundingRect())
        return super(SelectionRect, self).collidesWithItem(item)

    def paint(self, painter, option, widget):
        rect = self.windowFrameRect()
        if self._modifiers == Qt.NoModifier:
            painter.setBrush(self.BACKGROUND_COLOR)
        if self._modifiers == Qt.ShiftModifier:
            painter.setBrush(self.BACKGROUND_ADD_COLOR)
        elif self._modifiers == Qt.ControlModifier:
            painter.setBrush(self.BACKGROUND_SWITCH_COLOR)
        elif self._modifiers == Qt.ControlModifier | Qt.ShiftModifier:
            painter.setBrush(self.BACKGROUND_SUB_COLOR)

        painter.setPen(self.PEN)
        painter.drawRect(rect)

    def set_drag_point(self, drag_point, modifiers):
        self._modifiers = modifiers
        top_left = QPointF(self._mouse_down_pos)
        bottom_right = QPointF(drag_point)
        if drag_point.x() < self._mouse_down_pos.x():
            top_left.setX(drag_point.x())
            bottom_right.setX(self._mouse_down_pos.x())
        if drag_point.y() < self._mouse_down_pos.y():
            top_left.setY(drag_point.y())
            bottom_right.setY(self._mouse_down_pos.y())
        self.setPos(top_left)
        self.resize(bottom_right.x() - top_left.x(), bottom_right.y() - top_left.y())

    def destroy(self):
        self._graph.scene().removeItem(self)
