#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains view implementation for connectors
"""

from Qt.QtCore import Qt, QObject, Signal, QPointF, QLineF, QTimeLine
from Qt.QtWidgets import QGraphicsPathItem, QGraphicsEllipseItem
from Qt.QtGui import QColor, QPen, QPainterPath, QPolygonF, QPainterPathStroker

from tpDcc.libs.python import python

from tpDcc.libs.nodegraph.core import consts
from tpDcc.libs.nodegraph.core import connector
from tpDcc.libs.nodegraph.painters import connector as connector_painters


class ConnectorSignals(QObject):
    visibilityChanged = Signal(bool)


class ConnectorView(QGraphicsPathItem, object):
    def __init__(self, model=None, parent=None):
        super(ConnectorView, self).__init__(parent=parent)

        self._model = model or connector.Connector()
        self.signals = ConnectorSignals()

        self.setZValue(consts.CONNECTOR_Z_VALUE)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setFlags(QGraphicsPathItem.ItemIsSelectable)
        self.setCacheMode(consts.ITEM_CACHE_MODE)

        self._color = consts.DEFAULT_CONNECTOR_COLOR
        self._style = consts.ConnectorStyles.DEFAULT
        self._thickness = consts.DEFAULT_CONNECTOR_THICKNESS
        self._active = False
        self._highlight = False
        self._ready_to_slice = False
        self._pen = QPen(QColor(*self.get_color()), self.get_thickness(), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self._source = None
        self._target = None

        size = 4.0
        self._arrow = QPolygonF()
        self._arrow.append(QPointF(-size, size))
        self._arrow.append(QPointF(0.0, -size * 1.5))
        self._arrow.append(QPointF(size, size))

    # ==============================================================================================
    # PROPERTIES
    # ==============================================================================================

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    @property
    def active(self):
        return self._active

    @property
    def highlighted(self):
        return self._highlight

    @property
    def ready_to_slice(self):
        return self._ready_to_slice

    @ready_to_slice.setter
    def ready_to_slice(self, flag):
        if flag != self._ready_to_slice:
            self._ready_to_slice = bool(flag)
            self.update()

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def shape(self):
        painter_path = QPainterPathStroker()
        painter_path.setWidth(10.0)
        painter_path.setCapStyle(Qt.SquareCap)
        return painter_path.createStroke(self.path())

    def itemChange(self, change, value):
        if change == self.ItemVisibleChange:
            self.signals.visibilityChanged.emit(bool(value))

        return super(ConnectorView, self).itemChange(change, value)

    def hoverEnterEvent(self, event):
        self.activate()
        super(ConnectorView, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.reset()
        super(ConnectorView, self).hoverLeaveEvent(event)

    def paint(self, painter, option, widget):
        connector_painters.draw_default_connector(self, painter, option, widget)

    # ==============================================================================================
    # GETTERS / SETTERS
    # ==============================================================================================

    def get_uuid(self):
        return self._model.uuid

    def get_color(self):
        return self._color

    def get_style(self):
        return self._style

    def get_thickness(self):
        return self._thickness

    def get_arrow(self):
        return self._arrow

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def tick(self, delta_time):
        pass
        # self.perform_evaluation_feedback()

    def pre_create(self):
        pass

    def post_create(self):
        source_port_view = self._get_source_port()
        target_port_view = self._get_target_port()
        if not source_port_view or not target_port_view:
            return False

        self.set_connections(source_port_view, target_port_view)
        self.draw_path(source_port_view, target_port_view)

        # source_port = self.source
        # if source_port and source_port.is_exec():
        #     self._bubble = QGraphicsEllipseItem(-2.5, -2.5, 5, 5, self)
        #     self._bubble.setBrush(QColor(*self.get_color()))
        #     self._bubble.setPen(self._pen)
        #     point = self.path().pointAtPercent(0.0)
        #     self._bubble.setPos(point)
        #     self._should_animate = False
        #     self._timeline = QTimeLine(2000)
        #     self._timeline.frameChanged.connect(self._on_timeline_frame_changed)
        #     self._timeline.setFrameRange(0, 100)
        #     self._timeline.setLoopCount(0)

        return True

    def _on_timeline_frame_changed(self, frame_num):
        # percentage = python.current_processor_time() - self._source.get_last_execution_time()
        # self._should_animate = percentage < 0.5
        point = self.path().pointAtPercent(float(frame_num) / float(self._timeline.endFrame()))
        self._bubble.setPos(point)
        if not self._should_animate:
            self._timeline.stop()
            self._bubble.hide()

    def perform_evaluation_feedback(self, *args, **kwargs):
        if self._timeline.state() == QTimeLine.State.NotRunning:
            self._should_animate = True
            self._bubble.show()
            self._timeline.start()

    def viewer(self):
        current_scene = self.scene()
        if not current_scene:
            return None

        return current_scene.viewer()

    def activate(self):
        self._active = True
        # color = QColor(*self.get_color()).lighter(125)
        # pen = QPen(color, 2.5, consts.ConnectorStyles.DEFAULT)
        # self.setPen(pen)

    def highlight(self):
        self._highlight = True
        # color = QColor(*self.get_color()).lighter(225)
        # pen = QPen(color, 2.5, consts.ConnectorStyles.DEFAULT)
        # self.setPen(pen)

    def set_connections(self, source_port_view, target_port_view):
        if not source_port_view or not target_port_view:
            return

        source_port_view.connectors[self.get_uuid()] = self
        target_port_view.connectors[self.get_uuid()] = self

        self._source = source_port_view
        self._target = target_port_view

    def draw_path(self, start_port=None, end_port=None, cursor_pos=None):
        """
        Draws path between ports
        :param start_port: PortView, port used to draw the starting point
        :param end_port: PortView or None, port used to draw the end point
        :param cursor_pos: , QPointF or None, if specified cursor this position will be used to raw the end point
        """

        start_port = start_port or self._source

        if not start_port:
            return

        pos1 = start_port.scenePos()
        pos1.setX(pos1.x() + (start_port.boundingRect().width() / 2))
        pos1.setY(pos1.y() + (start_port.boundingRect().height() / 2))
        if cursor_pos:
            pos2 = cursor_pos
        else:
            if not end_port:
                end_port = self._target
            if end_port:
                pos2 = end_port.scenePos()
                pos2.setX(pos2.x() + (start_port.boundingRect().width() / 2))
                pos2.setY(pos2.y() + (start_port.boundingRect().height() / 2))
            else:
                return

        line = QLineF(pos1, pos2)
        path = QPainterPath()
        path.moveTo(line.x1(), line.y1())

        viewer = self.viewer()
        if viewer:
            if viewer.get_connector_layout() == consts.GraphViewerConnectorLayout.STRAIGHT:
                path.lineTo(pos2)
                self.setPath(path)
            else:
                if viewer.get_layout_direction() == consts.GraphViewerLayoutDirection.HORIZONTAL:
                    self._draw_path_horizontal(start_port, pos1, pos2, path)
                elif viewer.get_layout_direction() == consts.GraphViewerLayoutDirection.VERTICAL:
                    self._draw_path_vertical(start_port, pos1, pos2, path)

    def reset(self):
        self._active = False
        self._highlight = False
        # color = QColor(*self.get_color())
        # pen = QPen(color, 2, self.get_style())
        # self.setPen(pen)

    def reset_path(self):
        path = QPainterPath(QPointF(0.0, 0.0))
        self.setPath(path)

    # ==============================================================================================
    # PORTS
    # ==============================================================================================

    def delete(self):
        source_port_view = self._source
        target_port_view = self._target

        source_port_view.connectors.pop(self.get_uuid())
        target_port_view.connectors.pop(self.get_uuid())

        if self.scene():
            self.scene().removeItem(self)

        source_port_view.update()
        target_port_view.update()

    # ==============================================================================================
    # INTERNAL
    # ==============================================================================================

    def _get_source_port(self):
        viewer = self.viewer()
        if not viewer:
            return None

        source_port_model = self._model.source
        if not source_port_model:
            return None

        source_node_uuid = source_port_model.node.uuid
        source_node_view = viewer.get_node_by_uuid(source_node_uuid)
        if not source_node_view:
            return None

        source_port_view = source_node_view.get_output_by_uuid(source_port_model.uuid)

        return source_port_view

    def _get_target_port(self):
        viewer = self.viewer()
        if not viewer:
            return None

        target_port_model = self._model.target
        if not target_port_model:
            return None

        target_node_uuid = target_port_model.node.uuid
        target_node_view = viewer.get_node_by_uuid(target_node_uuid)
        if not target_node_view:
            return None

        target_port_view = target_node_view.get_input_by_uuid(target_port_model.uuid)

        return target_port_view

    def _draw_path_horizontal(self, start_port, pos1, pos2, path):

        viewer = self.viewer()
        if not viewer:
            self.setPath(path)
            return

        connector_layout = viewer.get_connector_layout()

        if connector_layout == consts.GraphViewerConnectorLayout.CURVED:
            offset_x1 = pos1.x()
            offset_x2 = pos2.x()
            tangent = abs(offset_x1 - offset_x2)
            max_width = start_port.boundingRect().width()
            tangent = min(tangent, max_width)
            if start_port.get_direction() == consts.PortDirection.Input:
                offset_x1 -= tangent
                offset_x2 += tangent
            else:
                offset_x1 += tangent
                offset_x2 -= tangent
            point1 = QPointF(offset_x1, pos1.y())
            point2 = QPointF(offset_x2, pos2.y())
            path.cubicTo(point1, point2, pos2)
            self.setPath(path)
        elif connector_layout == consts.GraphViewerConnectorLayout.ANGLE:
            offset_x1 = pos1.x()
            offset_x2 = pos2.x()
            distance = abs(offset_x1 - offset_x2) / 2
            if start_port.get_direction() == consts.PortDirection.Input:
                offset_x1 -= distance
                offset_x2 += distance
            else:
                offset_x1 += distance
                offset_x2 -= distance
            point1 = QPointF(offset_x1, pos1.y())
            point2 = QPointF(offset_x2, pos2.y())
            path.lineTo(point1)
            path.lineTo(point2)
            path.lineTo(pos2)
            self.setPath(path)

    def _draw_path_vertical(self, start_pos, pos1, pos2, path):
        pass


class RealtimeConnector(ConnectorView, object):
    def __init__(self):
        super(RealtimeConnector, self).__init__()

        self.name = 'RealTimeLine'

        self.setZValue(consts.WIDGET_Z_VALUE + 1)

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def paint(self, painter, option, widget):
        connector_painters.draw_realtime_connector(self, painter, option, widget)

    def tick(self, delta_time):
        pass

    def pre_create(self):
        pass

    def post_create(self):
        pass


class ConnectorSliderSignals(QObject):
    visibilityChanged = Signal(bool)


class ConnectorSlicer(QGraphicsPathItem, object):
    def __init__(self):
        super(ConnectorSlicer, self).__init__()

        self.signals = ConnectorSliderSignals()
        self.setZValue(consts.WIDGET_Z_VALUE + 2)

    # ==============================================================================================
    # OVERRIDES
    # ==============================================================================================

    def paint(self, painter, option, widget):
        connector_painters.draw_slicer_connector(self, painter, option, widget)

    def itemChange(self, change, value):
        if change == self.ItemVisibleChange:
            self.signals.visibilityChanged.emit(bool(value))

        return super(ConnectorSlicer, self).itemChange(change, value)

    # ==============================================================================================
    # BASE
    # ==============================================================================================

    def draw_path(self, p1, p2):
        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)
        self.setPath(path)
