#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains nodes manager implementation
"""

from __future__ import print_function, division, absolute_import

import uuid
import logging

from tpDcc.libs.nodegraph.core import node
from tpDcc.libs.nodegraph.core.views import node as node_view
from tpDcc.libs.nodegraph.managers import modules

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


def create_node_model_from_class_name(node_class_name, package_name=None, **kwargs):

    package_modules = modules.registered_modules(package_name)
    if not package_modules:
        return None

    node_model_class = None
    for module_data in package_modules:
        if node_model_class:
            break
        for mod_name, module in module_data.items():
            if node_class_name in module.node_classes:
                node_model_class = module.node_classes[node_class_name]
                break
    if not node_model_class:
        if node_class_name == 'Node':
            node_model_class = node.Node
        else:
            return None

    return node_model_class(**kwargs)


def create_node_model_from_class(node_class, **kwargs):

    node_name = kwargs.pop('name', node_class)
    module_name = node_class.MODULE_NAME if hasattr(node_class, 'MODULE_NAME') else None

    if not module_name or module_name not in modules.registered_modules():
        module_name = None
        package_modules = modules.registered_modules(node_class.PACKAGE_NAME)
        for module_data in package_modules:
            if module_name:
                break
            for mod_name, module in module_data.items():
                if node_class in list(module.node_classes.values()):
                    module_name = mod_name
                    break
    if not module_name:
        return None

    node_template = node_class.template()
    node_template['type'] = node_class.node_type
    node_template['uuid'] = str(uuid.uuid4())
    node_template['name'] = node_name
    node_template['class_name'] = node_class.__name__
    node_template['module'] = module_name
    node_template['package'] = node_class.PACKAGE_NAME
    node_template['x'] = kwargs.pop('x', 0.0)
    node_template['y'] = kwargs.pop('y', 0.0)

    return create_node_model_from_template(node_template)


def create_node_model_from_type(node_type, package_name=None, **kwargs):

    package_modules = modules.registered_modules(package_name)
    if not package_modules:
        return None

    node_class = None
    for module_data in package_modules:
        if node_class:
            break
        for mod_name, module in module_data.items():
            if node_type in module.node_types:
                node_name = module.node_types[node_type]
                if node_name in module.node_classes:
                    node_class = module.node_classes[node_name]
                    break
    if not node_class:
        return None

    return create_node_model_from_class(node_class, **kwargs)


def create_node_model_from_template(node_template):

    module_name = node_template.pop('module')
    node_uuid = node_template.pop('uuid')
    node_type = node_template.pop('node_type')
    node_package = node_template.pop('package')
    node_class_name = node_template.pop('class_name')
    module = modules.registered_module(module_name, node_package)
    if not module:
        LOGGER.warning('Not node "{} ({}) found in {} | {}'.format(node_uuid, node_type, node_package, module_name))
        return None

    node_model = create_node_model_from_class_name(node_class_name, package_name=node_package, uuid=node_uuid)
    assert node_model, 'Node "{}" not found in module "{}"'.format(node_class_name, module_name)

    node_model.update_properties(node_template, block_signals=True)

    return node_model


def create_node_view_from_type(node_type, package_name=None):
    node_model = create_node_model_from_type(node_type, package_name=package_name)
    if not node_model:
        return None
    new_node_view = create_node_view_from_model(node_model)

    return new_node_view


def create_node_view_from_template(node_template):
    module_name = node_template['module']
    node_package = node_template['package']
    module = modules.registered_module(module_name, node_package)
    if not module:
        LOGGER.warning('Not module found "{} ({})'.format(module_name, node_package))
        return None
    node_model = create_node_model_from_template(node_template)
    if not node_model:
        return None

    return create_node_view_from_model(node_model)


def create_node_view_from_model(node_model):
    module_name = node_model.MODULE_NAME
    node_package = node_model.PACKAGE_NAME
    module = modules.registered_module(module_name, node_package)
    if not module:
        LOGGER.warning('Not module found "{} ({}) found'.format(module_name, node_package))
        return None

    module_node_factories = module.ui_nodes_factory_classes
    if not module_node_factories:
        return None

    for factory_name, factory in module_node_factories.items():
        new_node_view = factory.create(node_model)
        if new_node_view:
            return new_node_view

    # If no specific factory view is found we just create a standard node view
    return node_view.NodeView(model=node_model)


def find_menu(node_class):
    for module in modules.registered_modules():
        for module_name, module_data in module.items():
            registered_node_menus = module_data.node_menu_classes
            if not registered_node_menus:
                continue
            for menu_name, menu_class in registered_node_menus.items():
                if not hasattr(menu_class, 'NODE_CLASS') or not menu_class.NODE_CLASS:
                    continue
                if menu_class.NODE_CLASS == node_class:
                    return menu_class

    return None
