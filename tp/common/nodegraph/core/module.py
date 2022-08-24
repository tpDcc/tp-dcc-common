#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains module implementation
"""

from __future__ import print_function, division, absolute_import

import os
import pkgutil
import inspect
import logging
import importlib

from Qt.QtCore import Signal, QObject

from tpDcc.libs.python import modules

from tpDcc.libs.nodegraph.core import exceptions, factory
from tpDcc.libs.nodegraph.core import node, port, menu, functionlib

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


class Module(QObject):

    PACKAGE_NAME = ''

    nodeClassRegistered = Signal(object)
    portClassRegistered = Signal(object)
    functionLibraryRegistered = Signal(object)
    nodeFactoryClassRegistered = Signal(object)
    portFactoryClassRegistered = Signal(object)
    nodeMenuRegistered = Signal(object)

    def __init__(self, module_path):
        super(Module, self).__init__()

        self._module_path = module_path
        self._node_classes = dict()
        self._node_paths = dict()
        self._node_types = dict()
        self._node_aliases = dict()
        self._port_classes = dict()
        self._port_paths = dict()
        self._port_data_types = dict()
        self._function_libs = dict()
        self._function_lib_paths = dict()
        self._ui_nodes_factory_classes = dict()
        self._ui_nodes_factory_paths = dict()
        self._ui_ports_factory_classes = dict()
        self._ui_ports_factory_paths = dict()
        self._input_widgets_factory_classes = dict()
        self._input_widgets_factory_paths = dict()
        self._tool_classes = dict()
        self._tool_paths = dict()
        self._preference_widget_classes = dict()
        self._preference_widget_paths = dict()
        self._node_menu_classes = dict()

        self.load()

    @property
    def module_path(self):
        """
        Returns path where module is located
        :return: str
        """

        return self._module_path

    @property
    def node_classes(self):
        """
        Returns registered node classes
        :return: list(dict(str, class))
        """

        return self._node_classes

    @property
    def node_paths(self):
        """
        Returns registered node paths
        :return: list(dict(str, str))
        """

        return self._node_paths

    @property
    def node_types(self):
        """
        Returns registered node types
        :return: dict
        """

        return self._node_types

    @property
    def node_aliases(self):
        """
        Returns registered node aliases
        :return: dict
        """

        return self._node_aliases

    @property
    def port_classes(self):
        """
        Returns registered port classes
        :return: list(dict(str, class))
        """

        return self._port_classes

    @property
    def port_paths(self):
        """
        Returns registered port paths
        :return: list(dict(str, str))
        """

        return self._port_paths

    @property
    def function_libs(self):
        """
        Returns registered function libs instances
        :return: list(dict(str, FunctionLibrary))
        """

        return self._function_libs

    @property
    def function_lib_paths(self):
        """
        Returns registered function lib paths
        :return: list(dict(str, str))
        """

        return self._function_lib_paths

    @property
    def ui_nodes_factory_classes(self):
        """
        Returns registered UI nodes factory classes
        :return: list(dict(str, str))
        """

        return self._ui_nodes_factory_classes

    @property
    def ui_nodes_factory_paths(self):
        """
        Returns registered UI nodes factory paths
        :return: list(dict(str, str))
        """

        return self._ui_nodes_factory_paths

    @property
    def ui_ports_factory_classes(self):
        """
        Returns registered UI ports factory classes
        :return: list(dict(str, str))
        """

        return self._ui_ports_factory_classes

    @property
    def ui_ports_factory_paths(self):
        """
        Returns registered UI ports factory paths
        :return: list(dict(str, str))
        """

        return self._ui_ports_factory_paths

    @property
    def input_widgets_factory_classes(self):
        """
        Returns registered input widgets factory classes
        :return: list(dict(str, str))
        """

        return self._input_widgets_factory_classes

    @property
    def tool_classes(self):
        """
        Returns registered tool classes
        :return: list(dict(str, class))
        """

        return self._tool_classes

    @property
    def tool_paths(self):
        """
        Returns registered tool paths
        :return: list(dict(str, str))
        """

        return self._tool_paths

    @property
    def preference_widget_classes(self):
        """
        Returns registered preference widget classes
        :return: list(dict(str, class))
        """

        return self._preference_widget_classes

    @property
    def preference_widget_paths(self):
        """
        Returns registered preference widget paths
        :return: list(dict(str, str)
        """

        return self._preference_widget_paths

    @property
    def node_menu_classes(self):
        return self._node_menu_classes

    def has_node_classes(self):
        """
        Returns whether current module has available nodes or not
        :return: bool
        """

        return bool(self._node_classes)

    def has_port_classes(self):
        """
        Returns whether current module has available ports or not
        :return: bool
        """

        return bool(self._port_classes)

    def has_ui_nodes_factory_classes(self):
        """
        Returns whether current module has available UI nodes factories or not
        :return: bool
        """

        return bool(self._ui_nodes_factory_classes)

    def has_function_lib_classes(self):
        """
        Returns whether current module has available function libraries or not
        :return: bool
        """

        return bool(self._function_libs)

    def register_node_class(self, node_class, alias=None):
        if not node_class:
            return

        node_name = node_class.__name__
        node_path = inspect.getfile(node_class)
        node_type = node_class.node_type

        if node_name in self._node_classes:
            raise exceptions.NodeRegistrationException(
                'Node with name "{}" already registered in module "{}"'.format(node_name, str(self)))
        if node_type in self._node_types:
            raise exceptions.NodeRegistrationException(
                'Node ID "{}" already registered in module "{}".'.format(node_type, str(self)))

        node_class.MODULE_NAME = self.__class__.__name__
        node_class.PACKAGE_NAME = self.PACKAGE_NAME

        self._node_types[node_type] = node_name
        self._node_classes[node_name] = node_class
        self._node_paths[node_name] = node_path

        if alias:
            if alias in self._node_aliases:
                raise exceptions.NodeRegistrationException(
                    'Node Alias "{}" already registered in module for "{}".'.format(alias, self._node_aliases[alias]))
            self._node_aliases[alias] = node_type

        self.nodeClassRegistered.emit(node_class)

    def register_port_class(self, port_class):
        if not port_class:
            return

        port_name = port_class.__name__
        port_path = inspect.getfile(port_class)

        if port_name in self._port_classes:
            raise exceptions.PortRegistrationException(
                'Port with name "{}" already registered in module "{}"'.format(port_name, str(self)))

        if port_class.IS_VALUE_PORT:
            internal_type = port_class.INTERNAL_DATA_STRUCTURE
            if internal_type in list(self._port_data_types.values()):
                raise exceptions.PortDataTypeRegistrationException(
                    'Impossible to register port "{}". Port with "{}" internal data type already registered: '
                    '"{}"'.format(port_class, internal_type, self._port_data_types[internal_type])
                )

        port_class.MODULE_NAME = self.__class__.__name__
        port_class.PACKAGE_NAME = self.PACKAGE_NAME

        self._port_classes[port_name] = port_class
        self._port_paths[port_name] = port_path
        self._port_data_types[port_name] = port_class.INTERNAL_DATA_STRUCTURE

        self.portClassRegistered.emit(port_class)

    def register_function_library(self, function_library_class):
        if not function_library_class:
            return

        function_library_name = function_library_class.__name__
        function_library_path = inspect.getfile(function_library_class)

        if function_library_name in self._function_libs:
            raise exceptions.NodeFunctionLibraryRegistrationException(
                'Node Function Library with name "{}" already registered in module "{}"'.format(
                    function_library_name, str(self)))

        self._function_libs[function_library_name] = function_library_class(module_name=self.__class__.__name__)
        self._function_lib_paths[function_library_name] = function_library_path

        self.functionLibraryRegistered.emit(self._function_libs[function_library_name])

    def register_node_factory_class(self, node_factory_class):
        if not node_factory_class:
            return

        factory_name = node_factory_class.__name__
        factory_path = inspect.getfile(node_factory_class)

        if factory_name in self._ui_nodes_factory_classes:
            raise exceptions.NodeFactoryRegistrationException(
                'Node factory with name "{}" already registered in module "{}"'.format(factory_name, str(self)))

        self._ui_nodes_factory_classes[factory_name] = node_factory_class
        self._ui_nodes_factory_paths[factory_name] = factory_path

        self.nodeFactoryClassRegistered.emit(node_factory_class)

    def register_port_factory_class(self, port_factory_class):
        if not port_factory_class:
            return

        factory_name = port_factory_class.__name__
        factory_path = inspect.getfile(port_factory_class)

        if factory_name in self._ui_ports_factory_classes:
            raise exceptions.PortFactoryRegistrationException(
                'Port factory with name "{}" already registered in module "{}"'.format(factory_name, str(self)))

        self._ui_ports_factory_classes[factory_name] = port_factory_class
        self._ui_ports_factory_paths[factory_name] = factory_path

        self.portFactoryClassRegistered.emit(port_factory_class)

    def register_node_menu(self, node_menu_class):
        if not node_menu_class:
            return

        menu_name = node_menu_class.__name__

        if menu_name in self._node_menu_classes:
            raise exceptions.NodeMenuRegistrationException(
                'Node menu with name "{}" already registered in module "{}"'.format(menu_name, str(self)))

        self._node_menu_classes[menu_name] = node_menu_class

        self.nodeMenuRegistered.emit(node_menu_class)

    def load(self):
        if not self._module_path or not os.path.isdir(self._module_path):
            LOGGER.warning('Module Path is not valid: "{}"!'.format(self._module_path))
            return

        module_name = modules.convert_to_dotted_path(self._module_path)

        for importer, sub_mod_name, is_pkg in pkgutil.walk_packages([self._module_path]):
            import_path = '{}.{}'.format(module_name, sub_mod_name)
            module = importlib.import_module(import_path)
            # Important to allow inspect to retrieve classes from given module
            importer.find_module(sub_mod_name).load_module(sub_mod_name)
            for cname, obj_class in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj_class, node.Node):
                    self.register_node_class(obj_class)
                elif issubclass(obj_class, port.Port):
                    self.register_port_class(obj_class)
                elif issubclass(obj_class, functionlib.FunctionLibrary):
                    self.register_function_library(obj_class)
                elif issubclass(obj_class, factory.NodeFactory):
                    self.register_node_factory_class(obj_class)
                elif issubclass(obj_class, factory.PortFactory):
                    self.register_port_factory_class(obj_class)
                elif issubclass(obj_class, menu.NodeMenu):
                    self.register_node_menu(obj_class)

    def clear_registered_nodes(self):
        """
        Clears registered nodes
        """

        self._node_classes.clear()
        self._node_paths.clear()
        self._node_types.clear()
        self._node_aliases.clear()

    def clear_registered_ports(self):
        """
          Clears registered ports
          """

        self._port_classes.clear()
        self._port_paths.clear()
        self._port_data_types.clear()

    def clear_registered_node_factories(self):
        """
        Clears registered node factories
        """

        self._ui_nodes_factory_classes.clear()
        self._ui_nodes_factory_paths.clear()

    def clear_registered_port_factories(self):
        """
        Clears registered port factories
        """

        self._ui_ports_factory_classes.clear()
        self._ui_ports_factory_paths.clear()
