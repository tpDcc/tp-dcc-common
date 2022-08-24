#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains graph model implementation
"""

from __future__ import print_function, division, absolute_import

import pprint
import logging
from uuid import uuid4
from collections import Counter

from Qt.QtCore import QObject, Signal

from tpDcc.libs.python import python, name as name_utils

from tpDcc.libs.nodegraph.core import consts
from tpDcc.libs.nodegraph.managers import nodes

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


class Graph(QObject):

    uuidChanged = Signal(object)
    nameChanged = Signal(str)
    nodeAdded = Signal(object)
    nodeDeleted = Signal(str)
    evaluationModelChanged = Signal(object)
    acyclicChanged = Signal(bool)
    editableChanged = Signal(bool)

    def __init__(self):
        super(Graph, self).__init__()

        self._uuid = uuid4()
        self._name = consts.DEFAULT_GRAPH_NAME
        self._nodes = python.UniqueDict()
        self._evaluation_model = consts.GraphEvaluationModel.PUSH
        self._acyclic = True
        self._editable = True

    def __repr__(self):
        return '<{} object at {}>'.format(self.__class__.__name__, self._uuid)

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = value
        self.uuidChanged.emit(self._uuid)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, graph_name):
        self._name = str(graph_name)
        self.nameChanged.emit(self._name)

    @property
    def nodes(self):
        return tuple(self._nodes.values())

    @property
    def evaluation_model(self):
        return self._evaluation_model

    @evaluation_model.setter
    def evaluation_model(self, flag):
        self._evaluation_model = flag
        self.evaluationModelChanged.emit(self._evaluation_model)

    @property
    def acyclic(self):
        return self._acyclic

    @acyclic.setter
    def acyclic(self, flag):
        self._acyclic = bool(flag)
        self.acyclicChanged.emit(self._acyclic)

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, flag):
        self._editable = bool(flag)
        self.editableChanged.emit(self._editable)

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def get(self, full_name):
        split_name = full_name.split('.')
        node = self.get_node(split_name[0])
        if node and len(split_name) == 2:
            port = node.get_input(split_name[1])
            if not port:
                port = node.get_output(split_name[1])
            if port:
                return port

        return node

    def serialize(self):
        LOGGER.debug('Serializing graph ...')
        data = {
            'data_type': self.__class__.__name__,
            'version': '1.0.0',
            'evaluation_model': self._evaluation_model,
            'nodes': dict(),
        }
        for node in self.nodes:
            node_data = node.serialize()
            node_data.pop('uuid')
            data['nodes'][node.uuid] = node_data

        LOGGER.debug(pprint.pformat(data))

        return data

    @classmethod
    def get_ref_counter_from_data(cls, data):
        count = Counter()

        for node_uuid, node_data in data['nodes'].items():
            for input_data in list(node_data['inputs'].values()):
                for source_name in input_data['sources']:
                    source_node = source_name.split('.')[0]
                    count[source_node] -= 1

            for output_data in list(node_data['outputs'].values()):
                for source_name in output_data['sources']:
                    source_node = source_name.split('.')[0]
                    count[source_node] += 1

        if len(count.values()):
            to_add = abs(min(count.values()))
            for k in list(count.keys()):
                count[k] = to_add

        LOGGER.debug(count)

        return count

    @classmethod
    def from_data(cls, data):
        if not isinstance(data, dict) or data.get('data_type') != cls.__name__:
            return

        new_graph = cls()
        new_graph.evaluation_model = data.get('evaluation_model')

        count = cls.get_ref_counter_from_data(data)
        ordered_nodes = sorted(list(data['nodes'].keys()), key=lambda x: count[x])

        for node_uuid in ordered_nodes:
            node_data = data['nodes'][node_uuid]
            node_data['uuid'] = node_uuid
            new_node = nodes.create_node_model_from_template(node_data)
            new_graph.add_node(new_node)

            # Here we force the update of the port values
            for input_uuid, input_data in node_data['inputs'].items():
                input_name = input_data['name']
                input_port = new_node.get_input(input_name)
                for source_name in input_data['sources']:
                    input_port.connect_to(new_graph.get(source_name))
                if not input_port.is_connected():
                    input_port.value = input_data['value']

        return new_graph

    # =================================================================================================================
    # NODES
    # =================================================================================================================

    def create_node(self, node_type, **kwargs):
        if not self._editable:
            return None

        new_node_model = nodes.create_node_model_from_type(node_type, **kwargs)
        if not new_node_model:
            LOGGER.warning('Cannot create node of type: "{}" in graph "{}"'.format(node_type, self))
            return None

        return self.add_node(new_node_model, **kwargs)

    def add_node(self, node_object, **kwargs):
        if not self._editable:
            return

        node_object.name = self.get_unique_node_name(node_object.name)
        node_object.graph = self
        self._nodes[node_object.uuid] = node_object
        for k, v in kwargs.items():
            input_port = node_object.get_input(k)
            if input_port:
                input_port.value = v
        self.nodeAdded.emit(node_object)

        return node_object

    def delete_node(self, node_uuid):
        node_uuid = node_uuid.uuid if hasattr(node_uuid, 'uuid') else node_uuid
        del self._nodes[node_uuid]
        self.nodeDeleted.emit(str(node_uuid))

    def get_unique_node_name(self, name):
        nodes_names = [node_model.name for node_model in list(self._nodes.values())]
        return name_utils.get_unique_name_from_list(nodes_names, name)

    def get_node(self, name):
        for node_uuid, node_model in self._nodes.items():
            if node_model.name == name or node_uuid == name:
                return node_model

        return None

    def get_node_by_uuid(self, uuid):
        return self._nodes.get(uuid, None)
