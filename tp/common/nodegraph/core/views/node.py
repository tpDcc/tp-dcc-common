#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph node view implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, Signal, QRectF
from Qt.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsPixmapItem, QGraphicsDropShadowEffect
from Qt.QtGui import QColor

from tpDcc.managers import resources
from tpDcc.libs.python import python
from tpDcc.libs.qt.core import mixin, contexts as qt_contexts

from tpDcc.libs.nodegraph.core import consts, common
from tpDcc.libs.nodegraph.core import node
from tpDcc.libs.nodegraph.managers import ports
from tpDcc.libs.nodegraph.painters import node as node_painters


@mixin.theme_mixin
class BaseNodeView(QGraphicsItem):
    def __init__(self, model, parent=None, **kwargs):
        super(BaseNodeView, self).__init__(parent=parent)

        self._model = model or node.Node()

        self.setFlags(self.ItemIsSelectable | self.ItemIsMovable)
        self.setZValue(consts.NODE_Z_VALUE)
        self.setCacheMode(consts.ITEM_CACHE_MODE)

        self._item_shadow = QGraphicsDropShadowEffect()
        self._item_shadow.setBlurRadius(35)
        self._item_shadow.setXOffset(3)
        self._item_shadow.setYOffset(3)
        self._item_shadow.setColor(QColor(0, 0, 0, 200))
        self.setGraphicsEffect(self._item_shadow)

        self._width = consts.DEFAULT_NODE_WIDTH
        self._height = consts.DEFAULT_NODE_HEIGHT
        self._title_height = consts.DEFAULT_NODE_TITLE_HEIGHT
        self._color = consts.DEFAULT_NODE_COLOR
        self._border_color = consts.DEFAULT_BORDER_COLOR
        self._text_color = consts.DEFAULT_NODE_TEXT_COLOR
        self._header_color = kwargs.pop('header_color', consts.DEFAULT_NODE_HEADER_COLOR)
        self._proxy_mode = False
        self._proxy_mode_threshold = 70

        self.setup_ui()
        self.setup_signals()

        self.refresh()

    def __repr__(self):
        return '{}.{}(\'{}\')'.format(self.__module__, self.__class__.__name__, self._model.name)

    def setup_ui(self):
        pass

    def setup_signals(self):
        self._model.positionChanged.connect(self.setPos)

    # ==============================================================================================
    # PROPERTIES
    # ==============================================================================================

    @property
    def model(self):
        return self._model

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def boundingRect(self):
        return QRectF(0.0, 0.0, self._width, self._height)

    def setPos(self, *args):
        with qt_contexts.block_signals(self._model):
            try:
                self._model.x = args[0]
                self._model.y = args[1]
            except TypeError:
                self._model.x = args[0].x()
                self._model.y = args[0].y()
        super(BaseNodeView, self).setPos(*args)

    # ==============================================================================================
    # GETTERS / SETTERS
    # ==============================================================================================

    def get_uuid(self):
        return self._model.uuid

    def get_name(self):
        return self._model.name

    def is_enabled(self):
        return self._model.enabled

    def set_enabled(self, flag):
        self._model.enabled = flag

    def get_width(self):
        return self._width

    def set_width(self, width):
        self._width = width

    def get_height(self):
        return self._height

    def set_height(self, height):
        self._height = height

    def get_title_height(self):
        return self._title_height

    def get_color(self):
        return self._color

    def get_border_color(self):
        return self._border_color

    def get_header_color(self):
        return self._header_color

    def get_text_color(self):
        return self._text_color

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def is_valid(self):
        return True

    def viewer(self):
        if not self.scene():
            return None

        return self.scene().viewer()

    def pre_create(self):
        pass

    def post_create(self):
        pass

    def refresh(self):
        self.set_position((self._model.x, self._model.y))

    def get_position(self):
        if not self.scene():
            return 0.0, 0.0

        return [float(self.scenePos().x()), float(self.scenePos().y())]

    def set_position(self, scene_position):
        self.setPos(scene_position[0], scene_position[1])

    def delete(self):
        scene = self.scene()
        if not scene:
            return
        graph_view = self.viewer()
        if not graph_view:
            return

        for input_view in list(self._input_ports.values()):
            if input_view.is_connected():
                sources = input_view.get_sources()
                if not sources:
                    continue
                for source_view in sources:
                    input_view.model.disconnect_from(source_view.model)

        for output_view in list(self._output_ports.values()):
            if output_view.is_connected():
                sources = output_view.get_sources()
                if not sources:
                    continue
                for source_view in sources:
                    source_view.model.disconnect_from(output_view.model)

        graph_view.node_views.pop(self.get_uuid())

        # We call it to properly delete item with QGraphicsEffected attached to it
        # https://forum.qt.io/topic/75510/deleting-qgraphicsitem-with-qgraphicseffect-leads-to-segfault
        self.prepareGeometryChange()
        self.setGraphicsEffect(None)
        scene.removeItem(self)
        del (self)

    # ==============================================================================================
    # LODS
    # ==============================================================================================

    def auto_switch_proxy_mode(self):
        # if self.cacheMode() == consts.ITEM_CACHE_MODE:
        #     return
        rect = self.sceneBoundingRect()
        top_left = self.viewer().mapToGlobal(self.viewer().mapFromScene(rect.topLeft()))
        top_right = self.viewer().mapToGlobal(self.viewer().mapFromScene(rect.topRight()))
        with_in_screen = top_right.x() - top_left.x()
        self.set_proxy_mode(with_in_screen < self._proxy_mode_threshold)

    def set_proxy_mode(self, proxy_mode):
        if proxy_mode == self._proxy_mode:
            return False

        self._proxy_mode = proxy_mode

        visible = not proxy_mode

        self._item_shadow.setEnabled(visible)

        return True

    def _on_model_enabled_changed(self, flag):
        pass


class NodeView(BaseNodeView):
    def __init__(self, model, parent=None, **kwargs):

        self._input_ports = python.UniqueDict()
        self._output_ports = python.UniqueDict()
        self._input_texts = python.UniqueDict()
        self._output_texts = python.UniqueDict()

        super(NodeView, self).__init__(model=model, parent=parent, **kwargs)

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def setup_ui(self):
        self._title_item = NodeTitle(self._model.name, parent=self)

        # icon_pixmap = resources.pixmap(consts.DEFAULT_NODE_ICON)
        icon_pixmap = resources.pixmap('user')
        if icon_pixmap.size().height() > consts.DEFAULT_NODE_ICON_SIZE:
            icon_pixmap = icon_pixmap.scaledToHeight(consts.DEFAULT_NODE_ICON_SIZE, Qt.SmoothTransformation)
        self._icon_item = QGraphicsPixmapItem(icon_pixmap, self)
        self._icon_item.setTransformationMode(Qt.SmoothTransformation)

        self._disabled_item = NodeDisabled('DISABLED', self)

    def setup_signals(self):
        super(NodeView, self).setup_signals()

    def paint(self, painter, option, widget):
        self.auto_switch_proxy_mode()
        node_painters.default_node_painter(self, painter=painter, option=option, widget=widget)

    def pre_create(self):
        super(NodeView, self).pre_create()

        input_ports = self._model.get_inputs()
        output_ports = self._model.get_outputs()

        for input_port_model in input_ports:
            input_view = ports.create_port_view_from_model(port_model=input_port_model, owning_node=self)
            self._add_port(input_view)

        for output_port_model in output_ports:
            output_view = ports.create_port_view_from_model(port_model=output_port_model, owning_node=self)
            self._add_port(output_view)

        self.draw()

    def post_create(self):
        super(NodeView, self).post_create()

        for input_view in list(self._input_ports.values()):
            if input_view.is_connected():
                sources = input_view.get_sources()
                if not sources:
                    continue
                for source_view in sources:
                    if not input_view.find_connector(source_view):
                        common.create_connector(input_view.scene(), input_view.model, source_view.model)

        for output_view in list(self._output_ports.values()):
            if output_view.is_connected():
                sources = output_view.get_sources()
                if not sources:
                    continue
                for source_view in sources:
                    if not output_view.find_connector(source_view):
                        common.create_connector(output_view.scene(), output_view.model, source_view.model)

    def set_proxy_mode(self, proxy_mode):
        valid = super(NodeView, self).set_proxy_mode(proxy_mode)
        if not valid:
            return

        visible = not proxy_mode

        self._title_item.setVisible(visible)

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def draw(self):
        height = self._title_item.boundingRect().height()
        self._set_base_size(add_height=height)
        self._align_title()
        self._align_icon()
        self._align_ports(vertical_offset=height)

        self.update()

    # ==============================================================================================
    # PORTS
    # ==============================================================================================

    def get_ports(self):
        return list(self._input_ports.values()) + list(self._output_ports.values())

    def get_inputs(self):
        return list(self._input_ports.values())

    def get_outputs(self):
        return list(self._output_ports.values())

    def get_connected_inputs(self):
        inputs = self.get_inputs()
        return [input_port for input_port in inputs if input_port.is_connected()]

    def get_connected_outputs(self):
        outputs = self.get_outputs()
        return [output_port for output_port in outputs if output_port.is_connected()]

    def get_input_by_uuid(self, uuid):
        return self._input_ports.get(uuid, None)

    def get_output_by_uuid(self, uuid):
        return self._output_ports.get(uuid, None)

    def get_port_by_uuid(self, uuid):
        port_view = self.get_input_by_uuid(uuid)
        if not port_view:
            port_view = self.get_output_by_uuid(uuid)

        return port_view

    # ==============================================================================================
    # SERIALIZATION
    # ==============================================================================================

    def get_property(self, name):
        return self._model.get_property(name)

    def set_property(self, name, value):
        return self._model.set_property(name, value)

    def add_property(self, name, value, items=None, range=None, widget_type=consts.NodeProperties.HIDDEN,
                     tab='Properties', ext=None, funcs=None):

        tab = tab or 'Properties'

        self._model.add_property(name, value)

    # ==============================================================================================
    # INTERNAL
    # ==============================================================================================

    def _add_port(self, port_view):
        port_text = QGraphicsTextItem(port_view.get_name(), self)
        font = port_text.font()
        font.setPointSize(8)
        port_text.setFont(font)
        port_text.setCacheMode(consts.ITEM_CACHE_MODE)
        if port_view.get_direction() == consts.PortDirection.Input:
            self._input_ports[port_view.get_uuid()] = port_view
            self._input_texts[port_view.get_uuid()] = port_text
        elif port_view.get_direction() == consts.PortDirection.Output:
            self._output_ports[port_view.get_uuid()] = port_view
            self._output_texts[port_view.get_uuid()] = port_text
        # if self.scene():
        #     self.post_create()

        return port_view

    def _calculate_size(self, add_width=0.0, add_height=0.0):
        """
        Internal function that returns the minimum node size
        :param add_width: float, additional width
        :param add_height: float, additional height
        """

        width = 0
        height = self._title_item.boundingRect().height()

        port_height = 0.0
        if self._input_texts:
            input_widths = list()
            for port_uuid, port_text in self._input_texts.items():
                port_view = self._input_ports[port_uuid]
                input_width = port_view.boundingRect().width() - consts.DEFAULT_PORT_OFFSET
                if port_text.isVisible():
                    input_width += port_text.boundingRect().width() / 1.5
                input_widths.append(input_width)
            width += max(input_widths)
            port_height = port_view.boundingRect().height()

        if self._output_texts:
            output_widths = list()
            for port_uuid, port_text in self._output_texts.items():
                port_view = self._output_ports[port_uuid]
                output_width = port_view.boundingRect().width()
                if port_text.isVisible():
                    output_width += port_text.boundingRect().width() / 1.5
                output_widths.append(output_width)
            width += max(output_widths)
            port_height = port_view.boundingRect().height()

        in_count = len([in_port for in_port in list(self._input_ports.values()) if in_port.isVisible()])
        out_count = len([in_port for in_port in list(self._output_ports.values()) if in_port.isVisible()])
        height += port_height * max([in_count, out_count])

        width += add_width
        height += add_height

        return width, height

    def _set_base_size(self, add_width=0.0, add_height=0.0):
        """
        Internal function used to initialize node size while drawing it
        :param add_width: float, additional width
        :param add_height: float, additional height
        """

        self._width = consts.DEFAULT_NODE_WIDTH
        self._height = consts.DEFAULT_NODE_HEIGHT
        new_width, new_height = self._calculate_size(add_width, add_height)
        if new_width > self._width:
            self._width = new_width
        if new_height > self._height:
            self._height = new_height

    def _align_title(self, horizontal_offset=0.0, vertical_offset=0.0):
        """
        Internal function used to align node title to  center-top of the node
        :param horizontal_offset: float, horizontal offset
        :param vertical_offset: float, vertical offset
        """

        text_rect = self._title_item.boundingRect()
        text_x = (self._width / 2) - (text_rect.width() / 2)
        # text_y = text_rect.height() * -1
        text_y = text_rect.height() * -1 + (text_rect.height())
        text_x += horizontal_offset
        text_y += vertical_offset
        self._title_item.setPos(text_x, text_y)

    def _align_icon(self, horizontal_offset=0.0, vertical_offset=0.0):
        """
        Internal function used to align node icon to center-left of the node
        :param horizontal_offset: float, horizontal offset
        :param vertical_offset: float, vertical offset
        """

        x = 2.0 + horizontal_offset
        y = horizontal_offset
        self._icon_item.setPos(x, y)

    def _align_ports(self, vertical_offset=0.0):
        width = self._width
        text_offset = consts.DEFAULT_PORT_OFFSET - 2
        spacing = 1

        input_views = list(self._input_ports.values())
        if input_views:
            port_width = input_views[0].boundingRect().width()
            port_height = input_views[0].boundingRect().height()
            port_x = (port_width / 2) * -1
            port_y = vertical_offset
            for input_view in input_views:
                input_view.setPos(port_x, port_y)
                port_y += port_height + spacing
        for port_uuid, text_item in self._input_texts.items():
            port_view = self._input_ports[port_uuid]
            if port_view.isVisible():
                text_x = port_view.boundingRect().width() / 2 - text_offset
                text_item.setPos(text_x, port_view.y() - 1.5)

        output_views = list(self._output_ports.values())
        if output_views:
            port_width = output_views[0].boundingRect().width()
            port_height = output_views[0].boundingRect().height()
            port_x = width - (port_width / 2)
            port_y = vertical_offset
            for output_view in output_views:
                output_view.setPos(port_x, port_y)
                port_y += port_height + spacing
        for port_uuid, text_item in self._output_texts.items():
            port_view = self._output_ports[port_uuid]
            if port_view.isVisible():
                text_x = port_view.x() - (text_item.boundingRect().width() - text_offset)
                text_item.setPos(text_x, port_view.y() - 1.5)


class NodeTitle(QGraphicsTextItem, object):

    editingFinished = Signal(str)

    def __init__(self, text, parent=None):
        super(NodeTitle, self).__init__(text, parent)

        self.setFlags(QGraphicsItem.ItemIsFocusable)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self._is_editing = False

    def mousePressEvent(self, event):
        self.setTextInteractionFlags(Qt.TextEditable)
        self._is_editing = True
        super(NodeTitle, self).mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.finish_edit()
        super(NodeTitle, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        self.finish_edit()

    def finish_edit(self):
        if self._is_editing:
            self.setTextInteractionFlags(Qt.NoTextInteraction)
            self._is_editing = False
            self.editingFinished.emit(self.toPlainText())


class NodeDisabled(QGraphicsItem, object):
    def __init__(self, text=None, parent=None):
        super(NodeDisabled, self).__init__(parent)

        self.setZValue(consts.WIDGET_Z_VALUE + 2)
        self.setVisible(False)
        self._color = (0, 0, 0, 255)
        self._text = text

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def boundingRect(self):
        return self.parentItem().boundingRect()

    def paint(self, painter, option, widget):
        node_painters.disabled_node_painter(self, painter, option, widget)

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def get_color(self):
        return self._color

    def get_text(self):
        return self._text