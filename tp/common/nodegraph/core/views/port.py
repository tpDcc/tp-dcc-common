#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains port view implementation
"""

from __future__ import print_function, division, absolute_import

from functools import partial

from Qt.QtCore import QRectF
from Qt.QtWidgets import QGraphicsItem

from tpDcc.libs.python import python
from tpDcc.libs.qt.core import mixin

from tpDcc.libs.nodegraph.core import consts, common
from tpDcc.libs.nodegraph.core import port
from tpDcc.libs.nodegraph.painters import port as port_painters


@mixin.theme_mixin
class PortView(QGraphicsItem, object):
    def __init__(self, model=None, parent=None):
        super(PortView, self).__init__(parent)

        self._model = model or port.Port()

        self.setAcceptHoverEvents(True)
        self.setFlag(self.ItemIsSelectable, False)
        self.setFlag(self.ItemSendsScenePositionChanges, True)
        self.setZValue(consts.PORT_Z_VALUE)
        self.setCacheMode(consts.ITEM_CACHE_MODE)

        self._hovered = False
        self._width = consts.DEFAULT_PORT_SIZE
        self._height = consts.DEFAULT_PORT_SIZE
        self._connectors = python.UniqueDict()

        self.setup_signals()

    def __str__(self):
        return '{}.PortView("{}")'.format(self.__module__, self._model.name)

    def __repr__(self):
        return '{}.PortView("{}")'.format(self.__module__, self._model.name)

    def setup_signals(self):
        self._model.portConnected.connect(self._on_port_connected)
        self._model.portsDisconnected.connect(partial(common.disconnect_port, self))

    # ==============================================================================================
    # PROPERTIES
    # ==============================================================================================

    @property
    def model(self):
        return self._model

    @property
    def connectors(self):
        return self._connectors

    @property
    def hovered(self):
        return self._hovered

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def boundingRect(self):
        return QRectF(0.0, 0.0, self._width + consts.DEFAULT_PORT_OFFSET, self._height)

    def itemChange(self, change, value):
        if change == self.ItemScenePositionHasChanged:
            self.redraw_connectors()
        return super(PortView, self).itemChange(change, value)

    def hoverEnterEvent(self, event):
        self._hovered = True
        super(PortView, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        super(PortView, self).hoverLeaveEvent(event)

    def paint(self, painter, option, widget):
        port_painters.value_port_painter(self, painter, option, widget)

    # ==============================================================================================
    # GETTERS / SETTERS
    # ==============================================================================================

    def get_node(self):
        # TODO: Here we should use model node property to access it
        return self.parentItem()

    def get_uuid(self):
        return self._model.uuid

    def get_name(self):
        return self._model.name

    def get_direction(self):
        return self._model.direction

    def get_width(self):
        return self._width

    def get_height(self):
        return self._height

    def get_color(self):
        return self._model.COLOR

    def get_border_color(self):
        return self._model.BORDER_COLOR

    def get_connectors(self):
        return list(self._connectors.values())

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def viewer(self):
        current_scene = self.scene()
        if not current_scene:
            return

        return current_scene.viewer()

    def is_exec(self):
        """
        Returns whether or not this port is an executable one or not
        :return: bool
        """

        return self._model.IS_EXEC

    def is_connected(self):
        return self._model.is_connected()

    def center(self):
        return self.boundingRect().center()

    def get_sources(self):
        source_views = list()
        viewer = self.viewer()
        if not viewer:
            return source_views
        sources = self._model.sources
        for source in sources:
            source_node = source.node
            node_view = viewer.get_node_by_uuid(source_node.uuid)
            if not node_view:
                continue
            port_view = node_view.get_port_by_uuid(source.uuid)
            if not port_view:
                continue
            source_views.append(port_view)

        return source_views

    def get_data_type(self):
        return self._model.data_type

    def get_current_structure(self):
        return self._model.current_structure

    # ==============================================================================================
    # CONNECTORS
    # ==============================================================================================

    def find_connector(self, port):
        connectors = self.get_connectors()
        if not connectors:
            return

        source_uuids = [self.model.uuid, port.model.uuid]
        for connector in connectors:
            if connector.source.get_uuid() in source_uuids and connector.target.get_uuid() in source_uuids:
                return connector

        return None

    def remove_connector(self, ports):
        if not ports:
            return False
        ports = python.force_list(ports)

        connectors = self._connectors.copy()
        for connector_uuid, connector_view in connectors.items():
            connector_ports = [connector_view.source, connector_view.target]
            for connector_port in connector_ports:
                for port in ports:
                    if connector_port.get_uuid() == port.uuid:
                        connector_view.delete()

        return True

    def redraw_connectors(self):
        connector_views = self.get_connectors()
        for connector_found in connector_views:
            if self.get_direction() == consts.PortDirection.Input:
                connector_found.draw_path(connector_found.source, self)
            else:
                connector_found.draw_path(self, connector_found.target)

    def _on_port_connected(self, port_object):
        common.connect_port(self.viewer(), self.model, port_object)
