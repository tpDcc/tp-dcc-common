#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains node model implementation
"""

from __future__ import print_function, division, absolute_import

import logging
from uuid import uuid4

from Qt.QtCore import QObject, Signal

from tpDcc.libs.python import python, name as name_utils

from tpDcc.libs.nodegraph.core import consts, exceptions
from tpDcc.libs.nodegraph.managers import ports

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


class Node(QObject):

    PACKAGE_NAME = consts.DEFAULT_NODE_PACKAGE_NAME
    MODULE_NAME = consts.DEFAULT_NODE_MODULE_NAME

    CATEGORY = consts.DEFAULT_NODE_CATEGORY
    KEYWORDS = consts.DEFAULT_NODE_KEYWORDS
    DESCRIPTION = consts.DEFAULT_NODE_DESCRIPTION

    uuidChanged = Signal(str)
    nameChanged = Signal(str)
    enabledChanged = Signal(bool)
    positionChanged = Signal(tuple)
    inputPortAdded = Signal(str)
    outputPortAdded = Signal(str)
    ticked = Signal(float)

    def __init__(self, name='node', uuid=None):
        super(Node, self).__init__()

        self._uuid = str(uuid or uuid4())
        self._name = name
        self._enabled = True
        self._graph = None
        self._x = 0.0
        self._y = 0.0
        self._is_dirty = True
        self._eval_count = 0
        self._inputs = python.UniqueOrderedDict()
        self._outputs = python.UniqueOrderedDict()
        self._custom_properties = dict()

        self.init_ports()

    def __repr__(self):
        graph_name = self._graph.name if self._graph else str(None)
        return '<class[{}]; name[{}]; graph[{}]>'.format(self.__class__.__name__, self._name, graph_name)

    def __getitem__(self, port_name):
        try:
            return self.getter(port_name)
        except Exception as exc:
            if '<str>' in str(exc):
                try:
                    return self.getter(str(port_name))
                except:
                    raise Exception('Could not find port with name: {}'.format(port_name))
            else:
                raise Exception('Could not find signature for __getitem__: {}'.format(type(port_name)))

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @python.classproperty
    def node_type(cls):
        return '{}.{}'.format(cls.MODULE_NAME, cls.__name__)

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = str(value)
        self.uuidChanged.emit(self._uuid)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = str(value)
        self.nameChanged.emit(self._name)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, flag):
        self._enabled = flag
        self.enabledChanged.emit(self._enabled)

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = float(value)
        self.positionChanged.emit((self._x, self._y))

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = float(value)
        self.positionChanged.emit((self._x, self._y))

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value

    @property
    def is_dirty(self):
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, flag):
        self._is_dirty = bool(flag)

        # Propagate dirtiness through chain if necessary (when using pull graph evaluation model)
        if not self._is_dirty:
            return
        for output_port in self._outputs.values():
            if output_port.is_connected():
                for source in output_port.sources:
                    source.node.is_dirty = True

    @property
    def inputs(self):
        return tuple(self._inputs.values())

    @property
    def outputs(self):
        return tuple(self._outputs.values())

    # =================================================================================================================
    # GETTERS / SETTERS
    # =================================================================================================================

    def get_evaluation_model(self):
        return None if not self._graph else self._graph.evaluation_model

    def get_input(self, name):
        return self._inputs.get(name)

    def get_output(self, name):
        return self._outputs.get(name)

    def get_inputs(self):
        return self._inputs.values()

    def get_outputs(self):
        return self._outputs.values()

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    @staticmethod
    def port_type_hints():
        return NodePortsSuggestionsHelper()

    def get_full_name(self):
        return self.name

    def tick(self, delta_time):
        self.ticked.emit(delta_time)

    def evaluate(self):
        self._eval_count += 1
        LOGGER.debug('Evaluating {}'.format(self))

    # =================================================================================================================
    # SERIALIZATION
    # =================================================================================================================

    @classmethod
    def template(cls):
        template_dict = dict()
        node_attributes = python.get_instance_user_attributes(cls)
        attrs_to_exclude = ['CATEGORY', 'DESCRIPTION', 'KEYWORDS', 'MODULE_NAME', 'PACKAGE_NAME']
        for node_attribute in node_attributes:
            attribute_name = node_attribute[0]
            attribute_value = node_attribute[1]
            if attribute_name in attrs_to_exclude:
                continue
            if isinstance(attribute_value, Signal):
                continue
            elif isinstance(attribute_value, property):
                continue
                # template_dict[node_attribute[0]] = None
            else:
                template_dict[node_attribute[0]] = attribute_value
        template_dict['module'] = cls.MODULE_NAME
        template_dict['package'] = cls.PACKAGE_NAME
        template_dict['class_name'] = cls.__name__

        return template_dict

    def properties(self):
        properties_dict = dict()
        node_attributes = python.get_instance_user_attributes(self)
        attrs_to_exclude = ['CATEGORY', 'DESCRIPTION', 'KEYWORDS', 'MODULE_NAME', 'PACKAGE_NAME']
        for node_attribute in node_attributes:
            attribute_name = node_attribute[0]
            attribute_value = node_attribute[1]
            if attribute_name in attrs_to_exclude or attribute_name.startswith('_'):
                continue
            if isinstance(attribute_value, Signal) or callable(attribute_value):
                continue
            elif isinstance(attribute_value, property):
                properties_dict[node_attribute[0]] = None
            else:
                properties_dict[node_attribute[0]] = attribute_value

        return properties_dict

    def update_properties(self, properties_dict, block_signals=False):
        self.blockSignals(block_signals)
        try:
            for attribute_name, attribute_value in properties_dict.items():
                if hasattr(self, attribute_name):
                    try:
                        setattr(self, attribute_name, attribute_value)
                    except AttributeError:
                        # We make sure that inputs and outputs have the UUIDs of the properties dict
                        if attribute_name == 'inputs':
                            for input in self.inputs:
                                for input_uuid, input_data in attribute_value.items():
                                    if input_data['name'] == input.name:
                                        input.uuid = input_uuid
                        elif attribute_name == 'outputs':
                            for output in self.outputs:
                                for output_uuid, output_data in attribute_value.items():
                                    if output_data['name'] == output.name:
                                        output.uuid = output_uuid
                    except Exception as exc:
                        LOGGER.warning(
                            'Impossible to set node attribute: {} : {} | {}'.format(
                                attribute_name, attribute_value, exc))
                        continue
        finally:
            self.blockSignals(False)

    def get_property(self, name):
        node_properties = self.properties()
        if name in node_properties:
            return node_properties[name]

        return self._custom_properties.get(name, None)

    def set_property(self, name, value):
        node_properties = self.properties()
        if name in node_properties:
            setattr(name, value)
        elif name in self._custom_properties:
            self._custom_properties[name] = value
        else:
            self.add_property(name, value)

    def add_property(self, name, value):
        if name in self.properties():
            raise exceptions.NodePropertyError('"{}" reserved for default property'.format(name))
        if name in self._custom_properties:
            raise exceptions.NodePropertyError('"{}" property already exists'.format(name))

        self._custom_properties[name] = value

    def serialize(self):
        data = self.template()
        data.update(self.properties())
        data.pop('is_dirty', None)
        data.pop('value', None)
        data['graph'] = str(self._graph.uuid) if self._graph else None
        data['inputs'] = dict()
        data['outputs'] = dict()

        for input_name, input_port in self._inputs.items():
            input_data = input_port.serialize()
            input_uuid = input_data.pop('uuid')
            data['inputs'][input_uuid] = input_data

        for output_uuid, output_port in self._outputs.items():
            output_data = output_port.serialize()
            output_data.pop('uuid')
            data['outputs'][output_uuid] = output_data

        return data

    @classmethod
    def from_data(cls, graph, data):
        from tpDcc.libs.nodegraph.managers import nodes

        assert str(graph.uuid) == data['graph']

        new_node = nodes.create_node_model_from_template(data)
        new_node.graph = graph

        for input_uuid, input_data in data['inputs'].items():
            input_name = input_data['name']
            input_port = new_node.get_input(input_name)
            for source_name in input_data['sources']:
                input_port.connect_to(graph.get(source_name))
            if not input_port.is_connected():
                input_port.value = input_data['value']

        for output_uuid, output_data in data['outputs'].items():
            input_name = output_data['name']
            output_port = new_node.get_output(input_name)
            for source_name in output_data['sources']:
                input_port = graph.get(source_name)
                if not input_port.is_connected():
                    input_port.connect_to(output_port)

        return new_node

    def delete(self):
        return self._graph.delete_node(self.uuid)

    # =================================================================================================================
    # PORTS
    # =================================================================================================================

    def init_ports(self):
        pass

    def get_unique_port_name(self, name):
        port_names = [port_found for port_found in list(self._inputs.keys()) + list(self._outputs.keys())]
        return name_utils.get_unique_name_from_list(port_names, name)

    def add_input_port(self, name, data_type, **kwargs):

        function = kwargs.pop('function', None)

        input_port = self._create_port(name, data_type, direction=consts.PortDirection.Input, **kwargs)
        self._inputs[name] = input_port

        structure = input_port.structure
        if structure == consts.PortStructure.Array:
            input_port.init_as_array(True)
        elif structure == consts.PortStructure.Dict:
            input_port.init_as_dict(True)

        if function:
            input_port.function = function

        return input_port

    def add_output_port(self, name, data_type, **kwargs):
        output_port = self._create_port(name, data_type, direction=consts.PortDirection.Output, **kwargs)
        self._outputs[name] = output_port

        return output_port

    def _create_port(self, name, data_type, direction, **kwargs):
        port_name = self.get_unique_port_name(name)
        new_port = ports.create_port_model_by_data_type(
            data_type, name=port_name, node=self, direction=direction, **kwargs)

        return new_port


class NodePortsSuggestionsHelper(object):
    def __init__(self):
        super(NodePortsSuggestionsHelper, self).__init__()

        self._template = {
            'types': {'inputs': [], 'outputs': []},
            'structs': {'inputs': [], 'outputs': []}
        }
        self._input_types = set()
        self._output_types = set()
        self._input_structs = set()
        self._output_structs = set()

    @property
    def input_types(self):
        return self._input_types

    @property
    def output_types(self):
        return self._output_types

    @property
    def input_structs(self):
        return self._input_structs

    @property
    def output_structs(self):
        return self._output_structs

    def add_input_data_type(self, data_type):
        self._input_types.add(data_type)

    def add_output_data_type(self, data_type):
        self._output_types.add(data_type)

    def add_input_struct(self, struct):
        self._input_structs.add(struct)

    def add_output_struct(self, struct):
        self._output_structs.add(struct)