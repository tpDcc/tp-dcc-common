#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains port model implementation
"""

from __future__ import print_function, division, absolute_import

from uuid import uuid4

from Qt.QtCore import QObject, Signal

from tpDcc.libs.python import python

from tpDcc.libs.nodegraph.core import consts


class Port(QObject):

    PACKAGE_NAME = 'tpDcc-libs-nodegraph'
    MODULE_NAME = 'Base'

    IS_VALUE_PORT = False
    IS_EXEC = False
    INTERNAL_DATA_STRUCTURE = None
    COLOR = consts.DEFAULT_PORT_COLOR
    BORDER_COLOR = None
    SUPPORTED_DATA_TYPES = tuple()
    PORT_DATA_TYPE_HINT = tuple()

    executed = Signal(object)
    uuidChanged = Signal(str)
    nodeChanged = Signal(object)
    nameChanged = Signal(str)
    valueChanged = Signal(object)
    directionChanged = Signal(object)
    isConnectedChanged = Signal(bool)
    portConnected = Signal(object)
    portsDisconnected = Signal(list)
    defaultValueChanged = Signal(object)
    structureChanged = Signal(int)
    functionChanged = Signal(object)

    def __init__(
            self, name=None, node=None, direction=None, default_value=None,
            structure=None, uuid=None):
        super(Port, self).__init__()

        self._uuid = str(uuid or uuid4())
        self._direction = direction
        self._name = name
        self._value = None
        self._default_value = default_value
        self._direction = direction
        self._sources = set()
        self._node = node
        self._default_supported_data_types = self.supported_data_types()
        self._structure = structure or consts.PortStructure.Single
        self._current_structure = self._structure
        self._function = None
        self._flags = consts.PortOptions.Storable
        self._orig_flags = self._flags
        self._always_single = False
        self._always_list = False
        self._always_dict = False
        self._can_change = False
        self._connectors = python.UniqueDict()

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    value = property(fget=lambda x: x.get_value(), fset=lambda x, value: x.set_value(value))

    @property
    def data_type(self):
        return self.__class__.__name__

    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, value):
        self._default_value = value
        self.defaultValueChanged.emit(self._default_value)

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = str(value)
        self.uuidChanged.emit(self._uuid)

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, value):
        self._node = value
        self.nodeChanged.emti(self._node)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = str(value)
        self.nameChanged.emit(self._name)

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        self._direction = value
        self.directionChanged.emit(self._direction)

    @property
    def sources(self):
        return self._sources

    @property
    def structure(self):
        return self._structure

    @structure.setter
    def structure(self, value):
        self._structure = value
        self.structureChanged.emit(self._structure)

    @property
    def current_structure(self):
        return self._current_structure

    @property
    def function(self):
        return self._function

    @function.setter
    def function(self, value):
        if self._function:
            try:
                self.executed.disconnect()
            except Exception:
                pass
        self._function = value
        self.executed.connect(self._function)
        self.functionChanged.emit(self._function)

    @property
    def connectors(self):
        return self._connectors.values()

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def is_value_port(self):
        return self.IS_VALUE_PORT

    def is_exec(self):
        return self.IS_EXEC

    def supported_data_types(self):
        return self.SUPPORTED_DATA_TYPES

    def default_supported_data_types(self):
        return self._default_supported_data_types

    def allowed_data_types(self, checked=None, data_types=None, self_check=True, defaults=False):
        """
        Returns a list of allowed data types for this port
        :param checked:
        :param data_types:
        :param self_check:
        :param defaults:
        :return: list(str)
        """

        return list(self.supported_data_types())

    def get_full_name(self, node_as_uuid=False):
        if node_as_uuid:
            return '.'.join((self.node.uuid, self.name))
        else:
            return '.'.join((self.node.get_full_name(), self.name))

    def get_value(self):
        if self._direction == consts.PortDirection.Output:
            if self._node.get_evaluation_model() == consts.GraphEvaluationModel.PULL:
                if self._node.is_dirty:
                    for input_port in self.node.inputs:
                        if input_port.is_connected():
                            for source in input_port.sources:
                                input_port.value = source.value
                    self._node.evaluate()
                    self._node.is_dirty = False

        return self._value

    def set_value(self, value):
        if self._direction == consts.PortDirection.Output:
            if self.is_connected():
                for connected_port in self._sources:
                    if self._node.get_evaluation_model() == consts.GraphEvaluationModel.PUSH:
                        connected_port.value = value

        self._value = value
        self.valueChanged.emit(self._value)

        if self._direction == consts.PortDirection.Input:
            if self._node.get_evaluation_model() == consts.GraphEvaluationModel.PUSH:
                self._node.evaluate()
            elif self._node.get_evaluation_model() == consts.GraphEvaluationModel.PULL:
                self._node.is_dirty = True

    # =================================================================================================================
    # OPTIONS
    # =================================================================================================================

    def enable_options(self, *options):
        """
        Enables flags on port instance
        :param options: list
        """

        for option in options:
            self._flags = self._flags | option
        self._orig_flags = self._flags

    def disable_options(self, *options):
        """
        Disables flags on port instance
        :param options: list
        """

        for option in options:
            self._flags = self._flags & ~option
        self._orig_flags = self._flags

    def option_enabled(self, option):
        """
        Checks whether or not given options is enabled
        :param option:
        """

        return bool(self._flags & option)

    # =================================================================================================================
    # CONNECTIONS
    # =================================================================================================================

    def is_connected(self):
        return len(self._sources) > 0

    def can_change_type_on_connection(self, checked=None, can=True, extra_ports=None, self_check=True):
        """
        Recursive function to determine if port can change its data type
        :param list, checked: optional list of already visited ports
        :param bool can: optional bool that sets if variables must be updated during iteration. Default to True.
        :param list extra_ports: list of non constrained or connected to this port but that want to also check
        :param bool self_check: define if check port itselfo for connected ports. Default to True.
        :return: True if port can become other data type
        :rtype: bool
        """

        checked = python.force_list(checked)
        extra_ports = python.force_list(extra_ports)

        if not self.option_enabled(consts.PortOptions.ChangeTypeOnConnection):
            return False

        connections = list()
        constraints = list()

        return can

    def connect_to(self, port):
        self._sources.add(port)
        port.sources.add(self)

        if self._direction == consts.PortDirection.Input:
            self.value = port.value
        else:
            port.value = self.value

        self.portConnected.emit(port)

    def disconnect_from(self, port=None):

        disconnected_ports = list()

        if port:
            if port in self._sources:
                disconnected_ports.append(port)
                self._sources.remove(port)
        else:
            while self._sources:
                disconnected_ports.append(self._sources.pop())
        if disconnected_ports:
            for disconnected_port in disconnected_ports:
                disconnected_port.sources.remove(self)
            self.portsDisconnected.emit(disconnected_ports)

        return disconnected_ports

    # =================================================================================================================
    # SERIALIZATION
    # =================================================================================================================

    def serialize(self):
        data = {
            'uuid': self.uuid,
            'name': self.name,
            'value': self.value,
            'sources': [port.get_full_name(node_as_uuid=True) for port in self.sources]
        }

        return data

    # =================================================================================================================
    # STRUCTURE
    # =================================================================================================================

    def init_as_array(self, is_array):
        """
        Sets this port to store always a list
        :param bool is_array: flag to define the port
        """

        is_array = bool(is_array)
        self._always_list = is_array
        if is_array:
            self._always_list = False
        self.set_as_array(is_array)

    def init_as_dict(self, is_dict):
        """
         Sets this port to store always a dict
         :param bool is_dict: flag to define the port
         """

        is_dict = bool(is_dict)
        self._always_list = is_dict
        if is_dict:
            self._always_list = False
        self.set_as_dict(is_dict)

    def set_as_array(self, is_array):
        """
        Sets this port to be a list
        :param bool is_array:
        """

        pass

    def set_as_dict(self, is_dict):
        """
        Sets this port to be a dict
        :param bool is_dict:
        """

        pass
