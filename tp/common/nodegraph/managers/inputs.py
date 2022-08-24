#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains custom Inputs Manager implementation for tpDcc-libs-nodegraph
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt

from tpDcc.libs.python import decorators
from tpDcc.libs.qt.core import input
from tpDcc.libs.qt.managers import inputs


@decorators.add_metaclass(decorators.Singleton)
class InputManager(inputs.InputManager, object):
    def __init__(self):
        super(InputManager, self).__init__()

    def _register_default_inputs(self):

        self.register_action(
            input.InputAction(
                name='Viewer.Pan', action_type=input.InputActionType.Mouse,
                group='Navigation', mouse=Qt.MouseButton.MiddleButton | Qt.MouseButton.MidButton))

        self.register_action(
            input.InputAction(
                name='Viewer.Pan', action_type=input.InputActionType.Mouse,
                group='Navigation', mouse=Qt.MouseButton.LeftButton, modifiers=Qt.AltModifier))

        self.register_action(
            input.InputAction(
                name='Viewer.Pan', action_type=input.InputActionType.Mouse,
                group='Navigation', mouse=Qt.MouseButton.MiddleButton | Qt.MouseButton.MidButton,
                modifiers=Qt.AltModifier))

        self.register_action(
            input.InputAction(
                name='Viewer.Zoom', action_type=input.InputActionType.Mouse,
                group='Navigation', mouse=Qt.MouseButton.RightButton, modifiers=Qt.AltModifier))

        self.register_action(
            input.InputAction(
                name='Viewer.RemoveNodes', action_type=input.InputActionType.Keyboard,
                group='Editing', key=Qt.Key_Delete))

        self.register_action(
            input.InputAction(
                name='Viewer.DragNodes', action_type=input.InputActionType.Mouse,
                group='Editing', mouse=Qt.MouseButton.MiddleButton))

        self.register_action(
            input.InputAction(
                name='Viewer.DragNodes', action_type=input.InputActionType.Mouse,
                group='Editing', mouse=Qt.MouseButton.LeftButton))

        self.register_action(
            input.InputAction(
                name='Viewer.DragNodes', action_type=input.InputActionType.Mouse,
                group='Editing', mouse=Qt.MouseButton.MiddleButton, modifiers=Qt.ShiftModifier))

        self.register_action(
            input.InputAction(
                name='Viewer.DragNodes', action_type=input.InputActionType.Mouse,
                group='Editing', mouse=Qt.MouseButton.LeftButton, modifiers=Qt.ShiftModifier))

        self.register_action(
            input.InputAction(
                name='Viewer.SliceConnectors', action_type=input.InputActionType.Mouse,
                group='Editing', mouse=Qt.MouseButton.LeftButton, modifiers=Qt.ShiftModifier | Qt.AltModifier))
