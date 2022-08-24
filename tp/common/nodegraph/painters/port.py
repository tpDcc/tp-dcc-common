#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains port painter functions
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QPointF, QRectF
from Qt.QtGui import QColor, QPolygonF, QPen


def value_port_painter(port_view, painter, option, widget):

    painter.save()

    rect_width = port_view.get_width() / 1.5
    rect_height = port_view.get_height() / 1.5
    rect_x = port_view.boundingRect().center().x() - (rect_width / 2)
    rect_y = port_view.boundingRect().center().y() - (rect_height / 2)
    port_rect = QRectF(rect_x, rect_y, rect_width, rect_height)

    color = QColor(*port_view.get_color())
    border_color = QColor(*port_view.get_border_color()) if port_view.get_border_color() else color.darker(200)
    if port_view.hovered:
        border_color = border_color.lighter(250)

    pen = QPen(border_color, 1.8)
    painter.setPen(pen)
    painter.setBrush(color)
    painter.drawEllipse(port_rect)

    if port_view.hovered or port_view.is_connected():
        painter.setBrush(border_color)
        inner_width = port_rect.width() / 3.5
        inner_height = port_rect.height() / 3.5
        inner_rect = QRectF(
            port_rect.center().x() - inner_width / 2, port_rect.center().y() - inner_height / 2,
            inner_width, inner_height)
        painter.drawEllipse(inner_rect)

    painter.restore()


def exec_port_painter(port_view, painter, option, widget):
    painter.save()

    node = port_view.get_node()
    port_center = port_view.boundingRect().center()
    rect_width = port_view.get_width() / 1.5
    rect_height = port_view.get_height() / 1.5
    rect_x = port_center.x() - (rect_width / 2)
    rect_y = port_center.y() - (rect_height / 2)
    port_rect = QRectF(rect_x, rect_y, rect_width, rect_height)

    color = QColor(*port_view.get_color())
    border_color = QColor(*port_view.get_border_color()) if port_view.get_border_color() else color.darker(200)
    if port_view.hovered:
        border_color = border_color.lighter(250)

    pen = QPen(border_color, 1.8)
    painter.setPen(pen)
    painter.setBrush(color)

    lod = node.viewer().get_lod_value_from_scale()

    if lod < 3:
        pass

    arrow = QPolygonF(
        [QPointF(rect_x, rect_y), QPointF(rect_x + rect_width / 2.0, rect_y), QPointF(rect_x + rect_width, rect_y + rect_width / 2.0),
         QPointF(rect_x + rect_width / 2.0, rect_y + rect_width), QPointF(rect_x, rect_y + rect_width)])
    painter.drawPolygon(arrow)

    if port_view.hovered:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(128, 128, 128, 30))
        painter.drawRoundedRect(port_rect, 3, 3)

    painter.restore()
