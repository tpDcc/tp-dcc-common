#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains ports manager implementation
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc.libs.nodegraph.core.views import port as port_view
from tpDcc.libs.nodegraph.managers import modules

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


def create_port_model_by_data_type(port_data_type, package_name=None, **kwargs):

    package_modules = modules.registered_modules(package_name)
    if not package_modules:
        return None

    port_model_class = None
    for module_data in package_modules:
        if port_model_class:
            break
        for mod_name, module in module_data.items():
            port_classes = module.port_classes
            if port_data_type in port_classes:
                port_model_class = port_classes[port_data_type]
                break
    if not port_model_class:
        return None

    return port_model_class(**kwargs)


def create_port_view_from_model(port_model, owning_node):
    module_name = port_model.MODULE_NAME
    port_package = port_model.PACKAGE_NAME
    module = modules.registered_module(module_name, port_package)
    if not module:
        LOGGER.warning('Not module found "{} ({}) found'.format(module_name, port_package))
        return None

    module_port_factories = module.ui_ports_factory_classes
    if not module_port_factories:
        return None

    for factory_name, factory in module_port_factories.items():
        new_port_view = factory.create(port_model, owning_node)
        if new_port_view:
            return new_port_view

    # If no specific factory view is found we just create a standard port view
    return port_view.PortView(model=port_model)
