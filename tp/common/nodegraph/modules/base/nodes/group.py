#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains group node model/view implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, Signal, QPointF, QRectF
from Qt.QtWidgets import QGraphicsItem
from Qt.QtGui import QCursor, QColor, QPainterPath, QPen

from tpDcc.libs.python import python

from tpDcc.libs.nodegraph.core import consts
from tpDcc.libs.nodegraph.core import node
from tpDcc.libs.nodegraph.core.views import node as node_view, port as port_view, connector as connector_view


class NodesGroup(node.Node, object):

    CATEGORY = 'Default'
    KEYWORDS = list()
    DESCRIPTION = 'Group Node'

    textChanged = Signal(str)
    nodesChanged = Signal(set)

    def __init__(self, *args, **kwargs):
        super(NodesGroup, self).__init__(*args, **kwargs)

        self._text = ''
        self._nodes = set()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = str(value)
        self.textChanged.emit(self._text)

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, nodes_list):
        self._nodes = set(python.force_list(nodes_list))
        self.nodesChanged.emit(self._nodes)


class NodesGroupView(node_view.BaseNodeView, object):
    def __init__(self, model, parent=None):

        self._minimum_size = (80, 80)

        super(NodesGroupView, self).__init__(model=model or NodesGroup(), parent=parent)

        self.setZValue(consts.CONNECTOR_Z_VALUE - 1)

        self._model.nodes = tuple(self.get_uuid())

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def setup_ui(self):
        super(NodesGroupView, self).setup_ui()

        self._sizer = NodesGroupSizer(size=20.0, parent=self)
        self._sizer.set_position(*self._minimum_size)

    def setup_signals(self):
        super(NodesGroupView, self).setup_signals()

        self._model.textChanged.connect(self._on_text_changed)

    def mouseDoubleClickEvent(self, event):
        viewer = self.viewer()
        if viewer:
            viewer.nodeDoubleClicked.emit(self.get_uuid())

        super(NodesGroupView, self).mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        current_scene = self.scene()

        if event.button() == Qt.LeftButton and current_scene:
            pos = event.scenePos()
            rect = QRectF(pos.x() - 5, pos.y() - 5, 10, 10)
            item = current_scene.items(rect)[0]
            if isinstance(item, (port_view.PortView, connector_view.ConnectorView)):
                self.setFlag(self.ItemIsMovable, False)
                return
            if self.isSelected():
                return

            viewer = self.viewer()
            if viewer:
                [selected_node.setSelected(False) for selected_node in viewer.get_selected_nodes()]

            nodes_dict = self.get_nodes(include_intersects=False)
            self._model.nodes.update(list(nodes_dict.keys()))
            for node_uuid in self._model.nodes:
                node_view = nodes_dict.get(node_uuid, None)
                if not node_view:
                    continue
                node_view.setSelected(True)

        # We do not call super to avoid default selection management
        # super(NodesGroupView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super(NodesGroupView, self).mouseReleaseEvent(event)

        self.setFlag(self.ItemIsMovable, True)
        nodes_dict = self.get_nodes(include_intersects=False)
        for node_uuid in self._model.nodes:
            node_view = nodes_dict.get(node_uuid, None)
            if not node_view:
                continue
            node_view.setSelected(True)
        self._model.nodes = self.get_uuid()

    def paint(self, painter, option, widget):
        painter.save()

        rect = self.boundingRect()
        orig_color = self.get_color()
        color = QColor(*orig_color)
        color.setAlpha(100)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        title_rect = QRectF(0.0, 0.0, rect.width(), 20.0)
        painter.setBrush(QColor(*orig_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(title_rect)

        if self._model.text:
            painter.setPen(QColor(*self.get_text_color()))
            text_rect = QRectF(title_rect.x() + 5.0, title_rect.height() + 2.0, rect.width() - 5.0, rect.height())
            painter.setPen(QColor(*self.get_text_color()))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.TextWordWrap, self._model.text)

        if self.isSelected():
            selected_color = color.lighter(150)
            painter.setBrush(selected_color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(rect)

        title_text_rect = QRectF(title_rect.x(), title_rect.y() + 1.2, rect.width(), title_rect.height())
        painter.setPen(QColor(*self.get_text_color()))
        painter.drawText(title_text_rect, Qt.AlignCenter, self.get_name())

        path = QPainterPath()
        path.addRect(rect)
        border_color = QColor(*self.get_border_color() or self.get_color())
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

        painter.restore()

    def set_width(self, width):
        super(NodesGroupView, self).set_width(width)
        self._sizer.set_position(self._width, self._height)

    def set_height(self, height):
        super(NodesGroupView, self).set_height(height)
        self._sizer.set_position(self._width, self._height)

    def post_create(self):
        viewer = self.viewer()
        if not viewer:
            return

        selected_nodes = viewer.get_selected_nodes()
        if selected_nodes:
            padding = 40
            scene = viewer.scene()
            group = scene.createItemGroup(selected_nodes)
            rect = group.boundingRect()
            scene.destroyItemGroup(group)
            self.set_position((rect.x() - padding, rect.y() - padding))
            self._sizer.set_position(rect.width() + (padding * 2), rect.height() + (padding * 2))

    # ==============================================================================================
    # GETTERS / SETTERS
    # ==============================================================================================

    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = value

    def get_minimum_size(self):
        return self._minimum_size

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def get_nodes(self, include_intersects=False):

        nodes = dict()

        if not self.scene():
            return nodes

        rect_map = self.mapToScene(self.boundingRect())
        rect = rect_map.boundingRect()
        items = self.scene().items(rect, mode=Qt.IntersectsItemShape if include_intersects else Qt.ContainsItemShape)
        for item in items:
            if item == self or item == self._sizer or not isinstance(item, node_view.BaseNodeView):
                continue
            nodes[item.get_uuid()] = item

        return nodes

    def auto_resize(self, nodes=None):
        nodes = nodes or list(self.get_nodes(include_intersects=True).values())
        if nodes:
            padding = 40
            nodes_rect = self._get_combined_rect(nodes)
            self.set_position(nodes_rect.x() - padding, nodes_rect.y() - padding)
            self._sizer.set_position(nodes_rect.width() + (padding * 2), nodes_rect.height() + (padding * 2))
            return

        width, height = self._minimum_size
        self._sizer.set_position(width, height)

    # ==============================================================================================
    # INTERNAL
    # ==============================================================================================

    def _get_combined_rect(self, node_items):
        group = self.scene().createItemGroup(node_items)
        rect = group.boundingRect()
        self.scene().destroyItemGroup(group)

        return rect

    # ==============================================================================================
    # CALLBACKS
    # ==============================================================================================

    def update_sizer_position(self, pos):
        self._width = pos.x() + self._sizer.size
        self._height = pos.y() + self._sizer.size

    # ==============================================================================================
    # CALLBACKS
    # ==============================================================================================

    def _on_width_changed(self, width):
        super(NodesGroupView, self)._on_width_changed(width)

        self._sizer.set_position(self.get_width(), self.get_height())

    def _on_height_changed(self, height):
        super(NodesGroupView, self)._on_height_changed(height)

        self._sizer.set_position(self.get_width(), self.get_height())

    def _on_text_changed(self):
        self.update(self.boundingRect())

    def _on_min_size_changed(self, size_tuple):
        self._sizer.set_pos(size_tuple)


class NodesGroupSizer(QGraphicsItem, object):
    def __init__(self, size=6.0, parent=None):
        super(NodesGroupSizer, self).__init__(parent)

        self.setFlags(self.ItemIsSelectable | self.ItemIsMovable | self.ItemSendsScenePositionChanges)
        self.setCursor(QCursor(Qt.SizeFDiagCursor))
        self.setToolTip('Double click to auto-resize')

        self._size = size

    # ==============================================================================================
    # PROPERTIES
    # ==============================================================================================

    @property
    def size(self):
        return self._size

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def boundingRect(self):
        return QRectF(0.0, 0.0, self._size, self._size)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange:
            parent_item = self.parentItem()
            min_size_x, min_size_y = parent_item.get_minimum_size()
            x = min_size_x if value.x() < min_size_x else value.x()
            y = min_size_y if value.y() < min_size_y else value.y()
            value = QPointF(x, y)
            parent_item.update_sizer_position(value)
            return value

        return super(NodesGroupSizer, self).itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        parent_item = self.parentItem()
        parent_item.auto_resize()

    def paint(self, painter, option, widget):
        painter.save()

        rect = self.boundingRect()
        parent_item = self.parentItem()
        if parent_item and parent_item.isSelected():
            color = QColor(*parent_item.get_border_color() or parent_item.get_color())
        else:
            color = QColor(*parent_item.get_color())
            color.darker(110)

        path = QPainterPath()
        path.moveTo(rect.topRight())
        path.lineTo(rect.bottomRight())
        path.lineTo(rect.bottomLeft())
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, painter.brush())

        painter.restore()

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def set_position(self, x, y):
        x -= self._size
        y -= self._size
        self.setPos(x, y)
