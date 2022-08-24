#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains modules manager implementation
"""

from __future__ import print_function, division, absolute_import

import pkgutil
import logging
import traceback

from tpDcc.libs.python import python, path as path_utils
from tpDcc.libs.nodegraph.core import exceptions, module
from tpDcc.libs.nodegraph import modules

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')

_REGISTERED_MODULES = dict()
_REGISTERED_MODULE_PATHS = dict()
_REGISTERED_MODULE_TYPES = dict()
_REGISTERED_UI_NODES_FACTORIES = dict()
_REGISTERED_UI_PORTS_FACTORIES = dict()
_REGISTERED_INPUT_WIDGET_FACTORIES = dict()
_REGISTERED_TOOLS = dict()
_REGISTERED_PREFERENCES = dict()


def get_modules_path():
    """
    Returns path where default tpDcc-libs-nodegraph modules are located
    :return: str
    """

    return path_utils.clean_path(modules.__path__[0])


def registered_module(module_name, package_name=None):
    """
    Returns registered module with given name and in the given package
    :param module_name: str
    :param package_name: str
    :return: Module or None
    """

    if not module_name:
        return None

    modules_found = registered_modules(package_name)
    if not modules_found:
        return None

    for module_data in modules_found:
        for mod_name, module_found in module_data.items():
            if mod_name == module_name:
                return module_found

    return None


def registered_modules(package_name=None):
    """
    Returns dictionary with the registered modules
    :param package_name: str
    :return:
    """

    if package_name:
        modules_found = list()
        for package, modules_data in _REGISTERED_MODULES.items():
            if package_name != package:
                continue
            modules_found.append(_REGISTERED_MODULES[package_name])
    else:
        modules_found = list(_REGISTERED_MODULES.values())

    return modules_found


def registered_modules_names(package_name=None):
    """
    Returns list of registered module names
    :param package_name: str or None
    :return: list(str)
    """

    module_names = list()

    all_registered_modules = registered_modules(package_name)
    if not registered_modules:
        return module_names

    for module in all_registered_modules:
        module_names.extend()


def registered_modules_paths(package_name):
    """
    Returns dictionary containing registered modules paths
    :param package_name: str
    :return: dict
    """

    return _REGISTERED_MODULE_PATHS.get(package_name, dict())


def registered_ui_nodes_factories(package_name):
    """
    Returns dict containing registered UI nodes factories
    :param package_name: str
    :return: dict
    """

    return _REGISTERED_UI_NODES_FACTORIES.get(package_name, dict())


def registered_ui_ports_factories(package_name):
    """
    Returns dict containing registered UI ports factories
    :param package_name: str
    :return: dict
    """

    return _REGISTERED_UI_PORTS_FACTORIES.get(package_name, dict())


def registered_input_widgets_factories(package_name):
    """
    Returns dict containing registered input widgets
    :return: dict
    """

    return _REGISTERED_INPUT_WIDGET_FACTORIES.get(package_name, dict())


def registered_tools(package_name):
    """
    Returns dict containing registered tools
    :return: dict
    """

    return _REGISTERED_TOOLS.get(package_name, dict())


def registered_preferences(package_name):
    """
    Returns dict containing registered preference widgets
    :return: dict
    """

    return _REGISTERED_PREFERENCES.get(package_name, dict())


def load_modules(package_name, module_paths=None):

    module_paths = python.force_list(module_paths)

    for importer, mod_name, is_pkg in pkgutil.iter_modules(module_paths):
        try:
            if is_pkg:
                mod = importer.find_module(mod_name).load_module(mod_name)
                mod_path = path_utils.clean_path(mod.__path__[0])
                if hasattr(mod, 'MODULE_NAME'):
                    module_name = mod.MODULE_NAME
                else:
                    module_name = mod_name
                mod_class = type(module_name, (module.Module,), {})
                mod_class.PACKAGE_NAME = package_name
                new_module = mod_class(mod_path)
                new_module.PACKAGE_NAME = package_name
                _REGISTERED_MODULES.setdefault(package_name, dict())
                _REGISTERED_MODULE_PATHS.setdefault(package_name, dict())
                _REGISTERED_MODULES[package_name][module_name] = new_module
                _REGISTERED_MODULE_PATHS[package_name][module_name] = mod_path
                LOGGER.info('Module registered: {} |{} | {} | {}'.format(
                    package_name, module_name, mod_path, new_module))
        except Exception as exc:
            LOGGER.error('Error while loading module: {} | {} : {}'.format(
                package_name, mod_name, traceback.format_exc()))
            continue

    # registered_internal_port_data_types = set()
    #
    # for name, module_found in _REGISTERED_MODULES.items():
    #     module_name = module_found.__class__.__name__
    #
    #     for port_class in list(module_found.port_classes.values()):
    #         if port_class.IS_VALUE_PORT:
    #             internal_type = port_class.INTERNAL_DATA_STRUCTURE
    #             if internal_type in registered_internal_port_data_types:
    #                 raise exceptions.PortDataTypeRegistrationException(
    #                     'Impossible to register port "{}". Port with "{}" internal data type already registered: '
    #                     '"{}"'.format(port_class, internal_type, registered_internal_port_data_types[internal_type])
    #                 )
