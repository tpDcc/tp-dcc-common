#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains node painter functions
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QRectF, QSizeF
from Qt.QtGui import QColor, QPainterPath, QPen, QFontMetrics

from tpDcc.libs.nodegraph.core import consts


def default_node_painter(node_view, painter, option, widget, debug_mode=False):
    painter.save()

    background_border = 0.5
    border_width = 0.4 if not node_view.isSelected() else 1.2
    background_border *= border_width
    radius = 3
    title_color = QColor(*node_view.get_header_color())
    background_color = QColor(*node_view.get_color())
    border_color = QColor(*node_view.get_border_color())
    if node_view.isSelected():
        background_color = background_color.lighter(150)
        title_color = title_color.lighter(150)
    # if node_view.get_is_temporal():
    #     background_color.setAlpha(50)
    #     background_color = background_color.lighter(50)

    lod = node_view.viewer().get_lod_value_from_scale()
    show_details = lod < 4

    # Rect used for both background and border
    rect = QRectF(
        background_border, background_border,
        node_view.get_width() - (background_border * 2), node_view.get_height() - (background_border * 2))
    left = rect.left()
    top = rect.top()

    background_path = QPainterPath()

    painter.setBrush(background_color)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(rect, radius, radius) if show_details else painter.drawRect(rect)

    title_height = node_view.get_title_height()
    label_rect = QRectF(
        background_border, background_border,
        node_view.get_width() - (background_border * 2), node_view.get_title_height())
    border_path = QPainterPath()
    border_path.setFillRule(Qt.WindingFill)
    if show_details:
        border_path.addRoundedRect(label_rect, radius, radius)
        square_size = node_view.get_title_height() / 2
        # Fill bottom rounded borders
        border_path.addRect(QRectF(left, top + title_height - square_size, square_size, square_size))
        border_path.addRect(QRectF(
            (left + node_view.get_width()) - square_size, top + title_height - square_size,
            square_size - (background_border * 2), square_size))
    else:
        border_path.addRect(label_rect)
    painter.setBrush(title_color)
    painter.fillPath(border_path, painter.brush())

    if not node_view.is_valid():
        pen = QPen(consts.INVALID_NODE_PEN_COLOR, 1.5, Qt.DashLine)
    else:
        pen = QPen(border_color, border_width)
    pen.setCosmetic(show_details and node_view.viewer().get_zoom() < 0.0)
    background_path.addRoundedRect(rect, radius, radius) if show_details else background_path.addRect(rect)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(pen)

    if debug_mode:
        painter.setPen(QPen(Qt.blue, 0.75))
        painter.drawRect(rect)
        painter.setPen(QPen(Qt.green, 0.75))
        painter.drawRect(label_rect)
    else:
        painter.drawPath(background_path)

    painter.restore()


def disabled_node_painter(node_view, painter, option, widget):
    painter.save()

    margin = 20
    half_margin = margin / 2
    rect = node_view.boundingRect()
    distance_rect = QRectF(
        rect.left() - half_margin, rect.top() - half_margin, rect.width() + margin, rect.height() + margin)
    pen = QPen(QColor(*node_view.get_color()), 8)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawLine(distance_rect.topLeft(), distance_rect.bottomRight())
    painter.drawLine(distance_rect.topRight(), distance_rect.bottomLeft())

    background_color = QColor(*node_view.get_color())
    background_color.setAlpha(100)
    bg_margin = -0.5
    half_bg_margin = bg_margin / 2
    background_rect = QRectF(
        distance_rect.left() - half_bg_margin, distance_rect.top() - half_bg_margin,
        distance_rect.width() + bg_margin, distance_rect.height() + bg_margin)
    painter.setPen(QPen(QColor(0, 0, 0, 0)))
    painter.setBrush(background_color)
    painter.drawRoundedRect(background_rect, 5, 5)

    pen = QPen(QColor(155, 0, 0, 255), 0.7)
    painter.setPen(pen)
    painter.drawLine(distance_rect.topLeft(), distance_rect.bottomRight())
    painter.drawLine(distance_rect.topRight(), distance_rect.bottomLeft())

    point_size = 4.0
    half_size = point_size / 2
    point_pos = (
        distance_rect.topLeft(), distance_rect.topRight(), distance_rect.bottomLeft(), distance_rect.bottomRight())
    painter.setBrush(QColor(255, 0, 0, 255))
    for p in point_pos:
        p.setX(p.x() - half_size)
        p.setY(p.y() - half_size)
        point_rect = QRectF(p, QSizeF(point_size, point_size))
        painter.drawEllipse(point_rect)

    disabled_text = node_view.get_text()
    if disabled_text:
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        font_metrics = QFontMetrics(font)
        font_width = font_metrics.width(disabled_text)
        font_height = font_metrics.height()
        text_width = font_width * 1.25
        text_height = font_height * 2.25
        text_bg_rect = QRectF(
            (rect.width() / 2) - (text_width / 2), (rect.height() / 2) - (text_height / 2), text_width, text_height)
        painter.setPen(QPen(QColor(255, 0, 0), 0.5))
        painter.setBrush(QColor(*node_view.get_color()))
        painter.drawRoundedRect(text_bg_rect, 2, 2)
        text_rect = QRectF(
            (rect.width() / 2) - (font_width / 2),
            (rect.height() / 2) - (font_height / 2),
            text_width * 2, font_height * 2)
        painter.setPen(QPen(QColor(255, 0, 0), 1))
        painter.drawText(text_rect, disabled_text)

    painter.restore()
