#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains generic functions used by different tpDcc-libs-nodegraph modules
"""

from __future__ import print_function, division, absolute_import

import contextlib

from tpDcc.libs.nodegraph.core import consts, connector
from tpDcc.libs.nodegraph.core.views import connector as connector_view
from tpDcc.libs.nodegraph.commands import nodedeleted, portconnected


# ==============================================================================================
# GRAPH
# ==============================================================================================

@contextlib.contextmanager
def block_graph_signals(graph_view):
    graph_view.blockSignals(True)
    graph_view.model.blockSignals(True)
    try:
        yield graph_view
    finally:
        graph_view.model.blockSignals(False)
        graph_view.blockSignals(False)


# ==============================================================================================
# NODES
# ==============================================================================================

def add_node(graph_view, node_object):
    from tpDcc.libs.nodegraph.commands import nodeadded

    if not node_object or not graph_view.model.editable:
        return

    graph_view.push_undo(nodeadded.NodeAddedUndoCommand(graph_view, node_object))


def delete_node(graph_view, node_object):
    if not node_object or not graph_view.model.editable:
        return

    graph_view.push_undo(nodedeleted.NodeDeletedUndoCommand(graph_view, node_object.serialize()))


def delete_nodes(graph_view, node_objects_to_delete):
    if not graph_view.model.editable:
        return

    graph_view.begin_undo('Delete Nodes')
    [graph_view.push_undo(
        nodedeleted.NodeDeletedUndoCommand(graph_view, node.serialize())) for node in node_objects_to_delete]
    graph_view.end_undo()


def delete_selected_nodes(graph_view):
    selected_nodes = [node.model for node in graph_view.get_selected_nodes()]
    delete_nodes(graph_view, selected_nodes)


def disable_nodes(graph_view, nodes, mode=None):
    if not nodes or not graph_view.model.editable:
        return
    mode = mode or not nodes[0].is_enabled()
    if len(nodes) > 1:
        # macro_text = {False: 'Enable', True: 'Disable'}[mode]
        # macro_text = '{} ({})'.format(macro_text, len(nodes))
        # graph_view.begin_undo(macro_text)
        [node.set_enabled(mode) for node in nodes]
        # graph_view.end_undo()
    else:
        nodes[0].set_enabled(mode)


def disable_selected_nodes(graph_view, mode=None, filtered_classes=None):
    selected_nodes = graph_view.get_selected_nodes(filtered_classes=filtered_classes)
    disable_nodes(graph_view, selected_nodes, mode=mode)


def cycle_check(source_model, target_model):

    # if source_model.direction == consts.PortDirection.Input:
    #     source_model, target_model = target_model, source_model
    #
    # start = source_model
    #
    # if source_model in target_model.sources:
    #     return True
    # for i in target_model.sources:
    #     if cycle_check(start, i):
    #         return True
    #
    # return False

    port_types = {consts.PortDirection.Input: 'outputs', consts.PortDirection.Output: 'inputs'}
    if source_model.direction == consts.PortDirection.Input:
        source_model, target_model = target_model, source_model

    start_node = source_model.node
    check_nodes = [target_model.node]
    while check_nodes:
        check_node = check_nodes.pop(0)
        for check_port in getattr(check_node, port_types[target_model.direction]):
            if check_port.sources:
                for port in check_port.sources:
                    if port.node != start_node:
                        check_nodes.append(port.node)
                    else:
                        return True

    return False


# ==============================================================================================
# PORTS
# ==============================================================================================

def are_ports_connected(source_model, target_model):
    """
    Returns whether or not two ports are connected
    :param source_model: Node
    :param target_model: Node
    :return:
    """

    if source_model.direction == target_model.direction:
        return False
    if source_model.node.uuid == target_model.node.uuid:
        return False
    if source_model.direction == consts.PortDirection.Input:
        source_model, target_model = target_model, source_model
    if target_model in source_model.sources and source_model in target_model.sources:
        return True

    return False


def can_connect_ports(source_model, target_model):
    """
    Returns whether or not the connection between two ports its possible
    :param source_model:
    :param target_model:
    :return:
    """

    if source_model is None or target_model is None:
        return False
    if source_model.direction == target_model.direction:
        return False
    if are_ports_connected(source_model, target_model):
        return False
    if source_model.node.uuid == target_model.node.uuid:
        return False

    if cycle_check(source_model, target_model):
        return False

    if source_model.direction == consts.PortDirection.Input:
        source_model, target_model = target_model, source_model

    if source_model.is_exec() and target_model.is_exec():
        return True
    elif source_model.is_exec() and not target_model.is_exec():
        return False
    elif not source_model.is_exec() and target_model.is_exec():
        return False

    if target_model.sources:
        return False

    if source_model.sources:
        return False

    if not source_model.node.graph or not target_model.node.graph:
        return False

    if source_model.node.graph != target_model.node.graph:
        return False

    if source_model.is_value_port() and target_model.is_value_port():
        if source_model.data_type in target_model.allowed_data_types(
                [], target_model.supported_data_types()) or \
                target_model.data_type in source_model.allowed_data_types([], source_model.supported_data_types()):
            a = source_model.data_type == 'AnyPort' and not source_model.can_change_type_on_connection(
                [], source_model.option_enabled(consts.PortOptions.ChangeTypeOnConnection), [])
            b = target_model.can_change_type_on_connection(
                [], target_model.option_enabled(consts.PortOptions.ChangeTypeOnConnection), []) and not \
                target_model.option_enabled(consts.PortOptions.AllowAny)
            c = not target_model.can_change_type_on_connection(
                [], target_model.option_enabled(consts.PortOptions.ChangeTypeOnConnection), []) and not \
                target_model.option_enabled(consts.PortOptions.AllowAny)
            if all([a, b or c]):
                return False
            return True
        else:
            if source_model.data_type not in source_model.supported_data_types():
                return False
            if all([source_model.data_type in list(target_model.allowed_data_types(
                    [], target_model.default_supported_data_types(),
                    self_check=target_model.option_enabled(consts.PortOptions.AllowMultipleConnections),
                    defaults=True)) + ['AnyPort'],
                    target_model.check_free(
                        [], self_check=target_model.option_enabled(consts.PortOptions.AllowMultipleConnections))]):
                return True
            if all([target_model.data_type in list(source_model.allowed_data_types(
                    [], source_model.default_supported_data_types(), defaults=True)) + ['AnyPort'],
                    source_model.check_free([])]):
                return True

        return False

    return True


def connect_ports(graph_view, start_port_view, end_port_view):
    if not graph_view.model.editable or (not start_port_view or not end_port_view):
        return False
    if not graph_view.draw_realtime_line or not graph_view.realtime_line.isVisible():
        return False

    start_port_model = start_port_view.model
    end_port_model = end_port_view.model

    if not can_connect_ports(start_port_model, end_port_model):
        return False

    if graph_view.model.acyclic and cycle_check(start_port_model, end_port_model):
        graph_view._end_realtime_connection()
        return False

    graph_view.begin_undo('Connect Node(s)')
    graph_view.push_undo(portconnected.PortConnectedUndoCommand(start_port_model, end_port_model))
    graph_view.end_undo()

    return True


def connect_port(graph_view, source_port_object, target_port_object):
    if not graph_view or not source_port_object or not target_port_object:
        return None

    graph_view.push_undo(portconnected.PortConnectedUndoCommand(graph_view, source_port_object, target_port_object))


def disconnect_port(source_port, target_ports):
    print('disconnenenenenene')


# ==============================================================================================
# CONNECTORS
# ==============================================================================================

def add_connector(scene, view_connector):
    if not scene:
        return

    view_connector.pre_create()
    scene.addItem(view_connector)
    view_connector.post_create()


def create_connector(scene, source_port_model, target_port_model):
    if not source_port_model or not target_port_model:
        return False

    new_connector = connector.Connector()

    if target_port_model.direction == consts.PortDirection.Output:
        new_connector.source = target_port_model
        new_connector.target = source_port_model
    else:
        new_connector.source = source_port_model
        new_connector.target = target_port_model

    new_connector_view = connector_view.ConnectorView(model=new_connector)
    add_connector(scene, new_connector_view)

    return True
