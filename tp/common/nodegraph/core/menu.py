#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains node/graph menu implementations
"""

from __future__ import print_function, division, absolute_import

from distutils.version import LooseVersion

from Qt import QtCore
from Qt.QtGui import QKeySequence

from tpDcc.libs.nodegraph.widgets import actions


class GraphMenu(object):
    def __init__(self, graph_view, menu):
        self._graph = graph_view
        self._menu = menu

    def __repr__(self):
        return '<{}("{}") object at {}>'.format(self.__class__.__name__, self.get_name(), hex(id(self)))

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================
    @property
    def qt_menu(self):
        """
        Returns the wrapped Qt menu
        :return: QMenu
        """

        return self._menu

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def get_name(self):
        """
        Returns the name of the menu
        :return: str, label name
        """

        return self._menu.title()

    def get_menu(self, menu_name):
        """
        Returns chld menu bi its name
        :param menu_name: str, name of the menu
        :return:
        """

        menu = self._menu.get_menu(menu_name)
        if menu:
            return GraphMenu(self._graph, menu)

    def get_command(self, command_name):
        for action in self._menu.actions():
            if not action.menu() and action.text() == command_name:
                return GraphCommand(self._graph, action)

    def all_commands(self):

        def _get_actions(menu):
            actions = list()
            for action in menu.actions():
                if not action.menu():
                    if not action.isSeparator():
                        actions.append(action)
                    else:
                        actions += _get_actions(action.menu())
            return actions

        child_actions = _get_actions(self._menu)

        return [GraphCommand(self._graph, action) for action in child_actions]

    def add_menu(self, menu_name):
        menu = actions.BaseMenu(menu_name, self._menu)
        self._menu.addMenu(menu)
        return GraphMenu(self._graph, menu)

    def add_action(self, action, shortcut=None):
        if LooseVersion(QtCore.qVersion()) > LooseVersion('5.10'):
            action.setShortcutVisibleInContextMenu(True)
        if shortcut:
            action.setShortcut(shortcut)
        qt_action = self._menu.addAction(action)

        return qt_action

    def add_command(self, command_name, fn=None, shortcut=None):
        action = actions.GraphAction(command_name, self._graph)
        action.graph = self._graph
        if LooseVersion(QtCore.qVersion()) > LooseVersion('5.10'):
            action.setShortcutVisibleInContextMenu(True)
        if shortcut:
            action.setShortcut(shortcut)
        if fn:
            action.executed.connect(fn)
        qt_action = self._menu.addAction(action)

        return GraphCommand(self._graph, qt_action)

    def add_separator(self):
        return self._menu.addSeparator()


class GraphCommand(object):
    def __init__(self, graph, action):
        self._graph = graph
        self._action = action

    def __repr__(self):
        return '<{}("{}") object at {}>'.format(self.__class__.__name__, self.get_name(), hex(id(self)))

    @property
    def action(self):
        return self._action

    def get_name(self):
        return self._action.text()

    def set_shortcut(self, shortcut=None):
        shortcut = shortcut or QKeySequence()
        self._action.setShortcut(shortcut)

    def execute(self):
        self._action.trigger()


class NodeMenu(GraphMenu, object):

    NODE_CLASS = None

    def __init__(self, graph_view, node_uuid, parent=None):
        base_menu = actions.BaseMenu(self.NODE_CLASS.__name__, parent=parent)
        base_menu.graph = graph_view
        super(NodeMenu, self).__init__(graph_view=graph_view, menu=base_menu)

        self._node_uuid = node_uuid

    def add_command(self, command_name, fn=None):
        action = actions.NodeAction(command_name, self._graph)
        action.graph = self._graph
        action.node_uuid = self._node_uuid
        if LooseVersion(QtCore.qVersion()) > LooseVersion('5.10'):
            action.setShortcutVisibleInContextMenu(True)
        if fn:
            action.executed.connect(fn)

        self._menu.addAction(action)
