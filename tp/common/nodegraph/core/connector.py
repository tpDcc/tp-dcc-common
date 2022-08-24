#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains model implementation for connectors
"""

from uuid import uuid4

from Qt.QtCore import QObject, Signal


class Connector(QObject):

    graphChanged = Signal(object)
    uuidChanged = Signal(str)
    sourceChanged = Signal(object)
    targetChanged = Signal(object)

    def __init__(self, uuid=None):
        super(Connector, self).__init__()

        self._graph = None
        self._uuid = str(uuid or uuid4())
        self._source = None
        self._target = None

    # ==============================================================================================
    # PROPERTIES
    # ==============================================================================================

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value
        self.graphChanged.emit(self._graph)

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = str(value)
        self.uuidChanged.emit(self._uuid)

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = value
        self.sourceChanged.emit(self._source)

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        self._target = value
        self.targetChanged.emit(self._target)
