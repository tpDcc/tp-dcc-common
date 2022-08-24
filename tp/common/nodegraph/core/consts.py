#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains constants values used by tpDcc-libs-nodegraph
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt
from Qt.QtWidgets import QGraphicsItem
from Qt.QtGui import QColor

from tpDcc.libs.python import python
if python.is_python2():
    from tpDcc.libs.python.enum import IntEnum, Flag
else:
    from enum import IntEnum, Flag

DEFAULT_GRAPH_NAME = 'root'

DEFAULT_GRAPH_SCENE_BACKGROUND_COLOR = (35, 35, 35)
DEFAULT_GRAPH_SCENE_GRID_COLOR = (60, 60, 60)
DEFAULT_GRAPH_SCENE_SECONDARY_GRID_COLOR = (80, 80, 80)
DEFAULT_GRAPH_SCENE_GRID_SIZE = 50
DEFAULT_GRAPH_SCENE_GRID_SPACING = 4
DEFAULT_GRAPH_SCENE_MINIMUM_ZOOM = -0.95
DEFAULT_GRAPH_SCENE_MAXIMUM_ZOOM = 2.0

ITEM_CACHE_MODE = QGraphicsItem.DeviceCoordinateCache
# ITEM_CACHE_MODE = QGraphicsItem.ItemCoordinateCache
NODE_Z_VALUE = 1
DEFAULT_NODE_PACKAGE_NAME = 'tpDcc-libs-nodegraph'
DEFAULT_NODE_MODULE_NAME = 'Base'
DEFAULT_NODE_CATEGORY = 'Default'
DEFAULT_NODE_KEYWORDS = list()
DEFAULT_NODE_DESCRIPTION = 'Default node description'
DEFAULT_NODE_WIDTH = 100
DEFAULT_NODE_HEIGHT = 80
DEFAULT_NODE_TITLE_HEIGHT = 22
DEFAULT_NODE_COLOR = (13, 18, 23, 255)
DEFAULT_BORDER_COLOR = (74, 84, 85, 255)
DEFAULT_NODE_TEXT_COLOR = (255, 255, 255, 180)
DEFAULT_NODE_HEADER_COLOR = (30, 30, 30, 200)
FLOW_CONTROL_COLOR = (100, 100, 100, 200)
DEFAULT_NODE_ICON = 'python'
DEFAULT_NODE_ICON_SIZE = 24

PORT_Z_VALUE = 2
DEFAULT_PORT_SIZE = 22
DEFAULT_PORT_OFFSET = 15
DEFAULT_PORT_COLOR = (255, 0, 0, 255)
DEFAULT_OUT_EXEC_PORT_NAME = 'outExec'

CONNECTOR_Z_VALUE = -1
DEFAULT_CONNECTOR_COLOR = (170, 95, 30, 255)
DEFAULT_CONNECTOR_THICKNESS = 1

DEFAULT_CONNECTOR_SLICER_COLOR = (255, 50, 75, 255)

WIDGET_Z_VALUE = 3

EMPTY_FUNCTION_RETURN = dict
VARIABLE_TAG = 'VAR'
VARIABLE_DATA_TAG = 'VAR_DATA'

# TODO: All this color stuff should be managed by a theme
ABSOLUTE_BLACK_COLOR = QColor(0, 0, 0, 255)
DARK_GRAY_COLOR = QColor(60, 60, 60)
DIRTY_PEN_COLOR = QColor(250, 250, 250, 200)
GRAY_COLOR = QColor(110, 110, 110)
GREEN_COLOR = QColor(96, 169, 23, 255)
NODE_BACKGROUNDS_COLOR = QColor(40, 40, 40, 200)
NODE_NAME_RECT_BLUE_COLOR = QColor(28, 74, 149, 200)
NODE_NAME_RECT_GREEN = QColor(74, 124, 39, 200)
NODE_SELECTED_PEN_COLOR = QColor(200, 200, 200, 150)
RED_COLOR = QColor(255, 0, 0, 255)
WHITE_COLOR = QColor(255, 255, 255, 200)
YELLOW_COLOR = QColor(255, 211, 25)
ORANGE_COLOR = QColor(209, 84, 0)
GRAPH_LABEL_COLOR = QColor(255, 255, 255, 50)
INVALID_NODE_PEN_COLOR = RED_COLOR
EXPOSED_PROPERTIES_COLOR = NODE_NAME_RECT_BLUE_COLOR
MAIN_COLOR = QColor(215, 128, 26)
BACKGROUND_COLOR = QColor(53, 53, 53)
BACKGROUND_BRIGHT_COLOR = QColor(82, 82, 82)
CONSOLE_COLOR = QColor(35, 35, 35)


class NodeTypes(object):
    """
    Sets the type of the nodes (callable or pure)
    """

    Callable = 0
    Pure = 1


class GraphEvaluationModel(object):
    # In a Push model, each time we set a port value, we need to evaluate the node
    PUSH = 0

    # In a Pull model, instead of evaluating the node each time a value port is set, we evaluate the node ONLY
    # when we need the result.
    PULL = 1


class GraphViewerManipulationMode(IntEnum):
    NONE = 0
    SELECT = 1
    PAN = 2
    MOVE = 3
    ZOOM = 4
    COPY = 5
    SLICER = 6


class GraphViewerConnectorLayout(IntEnum):
    STRAIGHT = 0
    CURVED = 1
    ANGLE = 2


class GraphViewerLayoutDirection(IntEnum):
    HORIZONTAL = 0
    VERTICAL = 1


class PortDirection(IntEnum):
    Input = 0
    Output = 1


class PortStructure(object):
    """
    Defines the data structures a port can hold
    """

    Single = 0                  # Single Data Structure
    Array = 1                   # Python List Structure
    Dict = 2                    # Python Dict
    Multi = 3                   # It can be any of the previous ones on connection/user action

    @staticmethod
    def from_value(value):
        if isinstance(value, list):
            return PortStructure.Array
        elif isinstance(value, dict):
            return PortStructure.Dict
        else:
            return PortStructure.Single


class PortOptions(Flag):
    # Port can hold array data structure
    ArraySupported = 1
    # Port can hold dict data structure
    DictSupported = 2
    # Port will only support other ports with array data structure
    SupportsOnlyArrays = 4
    # Enable port to allow more that one input connection.
    AllowMultipleConnections = 8
    #  Used by AnyPort to check if it can change its data type on new connection
    ChangeTypeOnConnection = 16
    # Specifies if port was created dynamically (on runtime)
    RenamingEnabled = 32
    # Specifies if port was created dynamically (on runtime)
    Dynamic = 64
    # Port will always be seen as dirty (computation needed)
    AlwaysPushDirty = 128
    # Determines if port data can be stored when port is serialized
    Storable = 256
    # Special flag that allow a port to be AnyPort, which means non typed without been marked as error.
    # By default, AnyPort must be initialized with some data type. Use in list and non type nodes.
    AllowAny = 512
    # Dicts are constructed with DictElement objects. So dict ports will only allow other dicts until its flag is
    # enabled. Used in makeDict node
    DictElementSupported = 1024


class ConnectorStyles(object):

    DEFAULT = Qt.SolidLine
    DASHED = Qt.DashLine
    DOTTED = Qt.DotLine


class NodeLibraryMeta(object):

    CATEGORY = 'Category'
    KEYWORDS = 'Keywords'
    CACHE_ENABLED = 'CacheEnabled'


class PortSpecifiers(object):
    """
    Class that defines port specifiers constants
    """

    # Specify supported data types list
    SUPPORTED_DATA_TYPES = 'supporteDataTypes'
    # Specify constraint key
    CONSTRAINT = 'constraint'
    # Specify struct constraint key
    STRUCT_CONSTRAINT = 'structConstraint'
    # Specify enable options
    ENABLED_OPTIONS = 'enabledOptions'
    # Specify disable options
    DISABLED_OPTIONS = 'disabledOptions'
    # Specify widget variant string
    INPUT_WIDGET_VARIANT = 'inputWidgetVariant'
    # Specify description for pot, which will be used as tooltip
    DESCRIPTION = 'Description'
    # Specific for sting port. If given, combo box will be created
    VALUE_LIST = 'ValueList'
    # Specific for ints and floats. If given, slider will be created instead of value box
    VALUE_RANGE = 'ValueRange'
    # Specify custom value dragger steps
    DRAGGER_STEPS = 'DraggerSteps'


class NodeProperties(object):
    HIDDEN = 0      # Property hidden in properties view
    LABEL = 2
    LINEEDIT = 3
    TEXTEDIT = 4
    COMBO = 5
    CHECKBOX = 6
    SPINBOX = 7
    COLORPICKER = 8
    SLIDER = 9
    FILE = 10
    FILESAVE = 11
    VECTOR2 = 12
    VECTOR3 = 13
    VECTOR4 = 14
    FLOAT = 15
    INT = 16
    BUTTON = 17
