#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains node searcher widget implementation
"""

from __future__ import print_function, division, absolute_import

import uuid
import json
import logging
from collections import OrderedDict
try:
    from inspect import getfullargspec as getargspec
except ImportError:
    from inspect import getargspec

from Qt.QtCore import Qt, Signal, QObject, QSize, QPoint, QStringListModel, QMimeData
from Qt.QtWidgets import QSizePolicy, QWidget, QFrame, QSplitter, QSizeGrip, QTextBrowser, QTreeWidget, QCompleter
from Qt.QtWidgets import QAbstractItemView, QTreeWidgetItem, QTreeWidgetItemIterator
from Qt.QtGui import QCursor, QColor, QPainter, QDrag

from tpDcc.managers import resources
from tpDcc.libs.python import python, strings
from tpDcc.libs.qt.core import base, contexts as qt_contexts
from tpDcc.libs.qt.widgets import layouts, lineedit, search

from tpDcc.libs.nodegraph.core import consts, node
from tpDcc.libs.nodegraph.managers import modules

LOGGER = logging.getLogger('tpDcc-libs-nodegraph')


class NodeSearcherWidget(base.BaseWidget, object):
    def __init__(self, graph_view, parent=None):

        self._model = NodeSearcherModel()
        self._controller = NodeSearcherController(model=self._model)

        self._dragging = False
        self._last_cursor_pos = QPoint(0, 0)
        self._graph_view = graph_view

        super(NodeSearcherWidget, self).__init__(parent=parent or graph_view)

        self.refresh()

    @property
    def model(self):
        return self._model

    def ui(self):
        super(NodeSearcherWidget, self).ui()

        self.setMouseTracking(True)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)

        main_frame = QFrame()
        main_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        frame_layout = layouts.VerticalLayout(spacing=1, margins=(1, 1, 1, 1))
        main_frame.setLayout(frame_layout)
        self.main_layout.addWidget(main_frame)

        splitter = QSplitter()
        frame_layout.addWidget(splitter)

        self._size_grip = None
        if self._model.grips_enabled:
            self._size_grip = NodeSearcherSizeGrip(parent=self)
            size_grip_layout = layouts.HorizontalLayout(spacing=1, margins=(1, 1, 1, 1))
            size_grip_layout.addStretch()
            size_grip_layout.addWidget(self._size_grip)
            frame_layout.addLayout(size_grip_layout)

        self._node_tree_widget = QWidget()
        node_tree_layout = layouts.VerticalLayout(spacing=1, margins=(1, 1, 1, 1))
        self._node_tree_widget.setLayout(node_tree_layout)
        self._node_info_widget = QTextBrowser()
        self._node_info_widget.setFocusPolicy(Qt.NoFocus)
        self._node_info_widget.setOpenExternalLinks(True)
        self._node_info_widget.setVisible(self._model.node_info_enabled)
        splitter.addWidget(self._node_tree_widget)
        splitter.addWidget(self._node_info_widget)

        self._line_edit = NodeSearcherLine(model=self._model, parent=self)
        self._search_widget = search.SearchFindWidget(search_line=self._line_edit, parent=self)

        self._tree_widget = NodeSearcherTree(
            graph_view=self._graph_view, model=self._model, controller=self._controller)
        node_tree_layout.addWidget(self._search_widget)
        node_tree_layout.addWidget(self._tree_widget)

    def setup_signals(self):
        self._line_edit.textChanged.connect(self._controller.set_search_text)
        self._node_info_widget.textChanged.connect(self._on_set_node_info_text)

        self._model.searchTextChanged.connect(self._line_edit.setText)
        self._model.nodeDescriptionChanged.connect(self._on_node_description_changed)

    def hideEvent(self, event):
        self._dragging = False

    def showEvent(self, event):
        self._dragging = False
        self.refresh()

    def sizeHint(self):
        return QSize(500, 300)

    def mousePressEvent(self, event):
        super(NodeSearcherWidget, self).mousePressEvent(event)
        if self._model.grips_enabled:
            if event.pos().y() >= self.geometry().height() - 30:
                self._dragging = True
                self._last_cursor_pos = QCursor.pos()

    def mouseReleaseEvent(self, event):
        super(NodeSearcherWidget, self).mouseReleaseEvent(event)
        self._dragging = False

    def mouseMoveEvent(self, event):
        super(NodeSearcherWidget, self).mouseMoveEvent(event)
        if self._model.grips_enabled and self._dragging:
            delta = QCursor.pos() - self._last_cursor_pos
            current_pos = self.pos()
            self.move(current_pos + delta)
            self._last_cursor_pos = QCursor.pos()

    def refresh(self, pattern='', port_direction=None, port_structure=consts.PortStructure.Single):
        self._controller.set_packages_to_load(self._model.packages_to_load)
        self._controller.set_search_text(self._model.search_text)
        self._controller.set_node_description(self._model.node_description)

        self._tree_widget.refresh(pattern=pattern, port_direction=port_direction, port_structure=port_structure)

    def focus(self):
        """
        Set the focus to the line edit widget
        """

        self._line_edit.setFocus()

    def reset_text(self):
        """
        Resets the text
        """

        with qt_contexts.block_signals(self._line_edit):
            self._line_edit.setText('')

    def _on_set_node_info_text(self):
        self._controller.set_node_description(self._node_info_widget.toHtml())

    def _on_node_description_changed(self, text):
        self._node_info_widget.blockSignals(True)
        try:
            self._node_info_widget.setHtml(strings.rst_to_html(text))
        except Exception:
            self._node_info_widget.setPlainText(text)
        finally:
            self._node_info_widget.blockSignals(False)


class NodeSearcherSizeGrip(QSizeGrip, object):
    def __init__(self, parent=None):
        super(NodeSearcherSizeGrip, self).__init__(parent)

    def sizeHint(self):
        return QSize(13, 13)

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = event.rect()
        painter.setBrush(QColor(80, 80, 80, 255))
        painter.drawRoundedRect(rect, 3, 3)
        painter.drawPixmap(rect, resources.pixmap('enlarge', category='icons', theme='color'))
        painter.end()


class NodeSearcherLineCompleter(QCompleter, object):
    def __init__(self, parent=None):
        super(NodeSearcherLineCompleter, self).__init__(parent=parent)

        self.setCompletionMode(self.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseInsensitive)


class NodeSearcherLine(lineedit.BaseLineEdit, object):
    def __init__(self, text='', input_mode=None, model=None, parent=None):

        self._model = model or NodeSearcherModel()

        super(NodeSearcherLine, self).__init__(text=text, input_mode=input_mode, parent=parent)

        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setMinimumSize(200, 22)
        self.setTextMargins(2, 0, 2, 0)
        self.setPlaceholderText('Enter node name ...')

        self._completer = NodeSearcherLineCompleter(parent=self)
        self.setCompleter(self._completer)

        self._setup_signals()

    def showEvent(self, event):
        self.setFocus()
        self.completer().popup().show()
        self.completer().complete()

    def mousePressEvent(self, event):
        if not self.text():
            self.completer().complete()

    def _setup_signals(self):
        popup = self._completer.popup()
        popup.clicked.connect(self._on_search)
        self.returnPressed.connect(self._on_search)

        self._model.nodesDataChanged.connect(self._on_nodes_data_changed)

    def _on_search(self, index):
        print('Searching ...', index)

    def _on_nodes_data_changed(self, nodes_data):
        node_names = list(nodes_data.keys())
        self._completer.setModel(QStringListModel(node_names))


class NodeSearcherTree(QTreeWidget, object):
    def __init__(self, graph_view, model=None, controller=None, parent=None):

        self._model = model or NodeSearcherModel()
        self._controller = controller or NodeSearcherController(model=self._model)
        self._graph_view = graph_view

        super(NodeSearcherTree, self).__init__(parent=parent or graph_view)

        self.setFrameShape(QFrame.NoFrame)
        self.setFrameShadow(QFrame.Sunken)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setAnimated(True)

        self._setup_signals()

    def update(self):
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if item.is_category:
                continue
            if not item.parent():
                item.setBackground(0, consts.BACKGROUND_BRIGHT_COLOR)
            else:
                item.setBackground(0, consts.BACKGROUND_BRIGHT_COLOR.lighter(150))
            iterator += 1
        super(NodeSearcherTree, self).update()

    def mousePressEvent(self, event):
        super(NodeSearcherTree, self).mousePressEvent(event)

        item_clicked = self.currentItem()
        if not item_clicked or item_clicked.is_category:
            return

        root_item = item_clicked
        is_py_node = root_item.is_py_node
        is_compound_node = root_item.is_compound_node

        while root_item.parent():
            root_item = root_item.parent()
            if not root_item.is_category:
                is_py_node = root_item.is_py_node
                is_compound_node = root_item.is_compound_node

        module_name = root_item.text(0)
        pressed_text = item_clicked.text(0)
        lib_name = item_clicked.lib_name

        if pressed_text in self._model.category_paths:
            event.ignore()
            return

        node_data = node.Node.template()
        node_data['module'] = module_name
        node_data['name'] = pressed_text
        node_data['uuid'] = str(uuid.uuid4())
        node_data['is_py_node'] = is_py_node
        node_data['is_compound_node'] = is_compound_node

        drag = QDrag(self)
        mime_data = QMimeData()
        pressed_text = json.dumps(node_data)
        mime_data.setText(pressed_text)
        drag.setMimeData(mime_data)
        drag.exec_()

    def refresh(self, pattern='', port_direction=None, port_structure=consts.PortStructure.Single):
        if self._model.use_drag_drop:
            self.setDragEnabled(True)
            self.setDragDropMode(QAbstractItemView.DragOnly)
        else:
            self.setDragEnabled(False)
            self.setDragDropMode(QAbstractItemView.NoDragDrop)

        data_type = None
        if self._graph_view.pressed_port:
            data_type = self._graph_view.pressed_port.get_data_type()

        self._controller.update_modules_data(
            data_type=data_type, pattern=pattern, port_direction=port_direction, port_structure=port_structure)

        if self._model.search_text and data_type is None:
            self._expand_categories()

        self.sortItems(0, Qt.AscendingOrder)

    def _setup_signals(self):
        self.currentItemChanged.connect(self._controller.set_current_item)

        self._model.categoryPathsChanged.connect(self._on_update_categories)
        self._model.nodesDataChanged.connect(self._on_update_nodes)
        self._model.currentSelectedItemChanged.connect(self._on_current_selected_item_changed)
        self._model.searchTextChanged.connect(self.refresh)

    def _find_item_with_path(self, category_path):
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if hasattr(item, 'path') and item.path == category_path:
                return item
            iterator += 1

        return None

    def _expand_categories(self):
        category_paths = self._model.category_paths
        for category_path, category_data in category_paths.items():
            parent_path = category_data['parent_path']
            if parent_path:
                parent_item = self._find_item_with_path(parent_path)
                if parent_item:
                    self.setItemExpanded(parent_item, True)
            item = self._find_item_with_path(category_path)
            if item:
                self.setItemExpanded(item, True)

    def _on_update_categories(self, category_paths):
        self.clear()

        for category_path, category_data in category_paths.items():
            category_text = category_data['text']
            parent_path = category_data['parent_path']
            if not parent_path:
                category_item = QTreeWidgetItem(self)
                category_item.path = category_path
                category_item.is_category = True
                category_item.is_py_node = False
                category_item.is_compound_node = False
                category_item.setFlags(Qt.ItemIsEnabled)
                category_item.setText(0, category_text)
                category_item.setBackground(0, consts.BACKGROUND_BRIGHT_COLOR)
            else:
                parent_item = self._find_item_with_path(parent_path)
                if not parent_item:
                    LOGGER.warning(
                        'Category "{}" not added because parent category item "{}" was not found!'.format(
                            category_path, parent_path))
                    continue
                child_item = QTreeWidgetItem(parent_item)
                child_item.path = category_path
                child_item.is_category = True
                child_item.is_py_node = False
                child_item.is_compound_node = False
                child_item.setFlags(Qt.ItemIsEnabled)
                child_item.setText(0, category_text)
                child_item.setBackground(0, consts.BACKGROUND_BRIGHT_COLOR.lighter(150))

    def _on_update_nodes(self, nodes_data):
        for node_name, node_data in nodes_data.items():
            node_path = node_data['path']
            node_doc = node_data['description']
            module_name = node_data.get('module_name', None)
            node_path_item = self._find_item_with_path(node_path)
            if not node_path_item:
                LOGGER.warning(
                    'Node "{}" not added because node path item "{}" was not found!'.format(node_name, node_path))
                continue
            node_item = QTreeWidgetItem(node_path_item)
            node_item.is_category = False
            node_item.is_py_node = False
            node_item.is_compound_node = False
            node_item.setFlags(Qt.ItemIsEnabled)
            node_item.setText(0, node_name)
            node_item.doc_string = node_doc
            node_item.lib_name = module_name

    def _on_current_selected_item_changed(self, item_text):
        if not self._model.node_info_enabled:
            return

        current_selected_items = self.findItems(item_text, Qt.MatchExactly | Qt.MatchRecursive)
        if not current_selected_items:
            return
        curr_item = current_selected_items[0]

        doc_string = curr_item.doc_string if hasattr(curr_item, 'doc_string') and not curr_item.is_category else ''
        self._controller.set_node_description(doc_string)


class NodeSearcherModel(QObject, object):

    gripsEnabledChanged = Signal(bool)
    nodeInfoEnableChanged = Signal(bool)
    useDragDropChanged = Signal(bool)
    searchTextChanged = Signal(str)
    nodeDescriptionChanged = Signal(str)
    categoryPathsChanged = Signal(dict)
    nodesDataChanged = Signal(dict)
    currentSelectedItemChanged = Signal(str)
    packagesToLoadChanged = Signal(list)
    suggestionsEnabledChanged = Signal(bool)

    def __init__(self):
        super(NodeSearcherModel, self).__init__()

        self._grips_enabled = True
        self._node_info_enabled = True
        self._use_drag_drop = True
        self._search_text = ''
        self._node_description = ''
        self._category_paths = dict()
        self._nodes_data = dict()
        self._current_item = None
        self._packages_to_load = ['tpDcc-libs-nodegraph']
        self._suggestions_enabled = False

    @property
    def grips_enabled(self):
        return self._grips_enabled

    @grips_enabled.setter
    def grips_enabled(self, flag):
        self._grips_enabled = bool(flag)
        self.gripsEnabledChanged.emit(self._grips_enabled)

    @property
    def node_info_enabled(self):
        return self._node_info_enabled

    @property
    def use_drag_drop(self):
        return self._use_drag_drop

    @use_drag_drop.setter
    def use_drag_drop(self, flag):
        self._use_drag_drop = bool(flag)
        self.useDragDropChanged.emit(self._use_drag_drop)

    @node_info_enabled.setter
    def node_info_enabled(self, flag):
        self._node_info_enabled = bool(flag)
        self.nodeInfoEnableChanged.emit(self._node_info_enabled)

    @property
    def search_text(self):
        return self._search_text

    @search_text.setter
    def search_text(self, value):
        self._search_text = str(value)
        self.searchTextChanged.emit(self._search_text)

    @property
    def node_description(self):
        return self._node_description

    @node_description.setter
    def node_description(self, value):
        self._node_description = str(value)
        self.nodeDescriptionChanged.emit(self._node_description)

    @property
    def category_paths(self):
        return self._category_paths

    @category_paths.setter
    def category_paths(self, categories_dict):
        self._category_paths = categories_dict
        self.categoryPathsChanged.emit(self._category_paths)

    @property
    def nodes_data(self):
        return self._nodes_data

    @nodes_data.setter
    def nodes_data(self, data_dict):
        self._nodes_data = data_dict
        self.nodesDataChanged.emit(self._nodes_data)

    @property
    def current_item(self):
        return self._current_item

    @current_item.setter
    def current_item(self, value):
        self._current_item = str(value)
        self.currentSelectedItemChanged.emit(self._current_item)

    @property
    def packages_to_load(self):
        return self._packages_to_load

    @packages_to_load.setter
    def packages_to_load(self, packages_list):
        self._packages_to_load = python.force_list(packages_list)
        self.packagesToLoadChanged.emit(self._packages_to_load)

    @property
    def suggestions_enabled(self):
        return self._suggestions_enabled

    @suggestions_enabled.setter
    def suggestions_enabled(self, flag):
        self._suggestions_enabled = bool(flag)
        self.suggestionsEnabledChanged.emit(self._suggestions_enabled)


class NodeSearcherController(object):
    def __init__(self, model):
        super(NodeSearcherController, self).__init__()

        self._model = model

    def set_grips_enabled(self, flag):
        self._model.grips_enabled = flag

    def set_node_info_enabled(self, flag):
        self._model.node_info_enabled = flag

    def set_search_text(self, value):
        self._model.search_text = value

    def set_node_description(self, value):
        self._model.node_description = value

    def set_category_paths(self, paths_list):
        self._model.category_paths = paths_list

    def set_current_item(self, tree_item):
        tree_text = tree_item.text(0) if tree_item else ''
        self._model.current_item = tree_text

    def set_packages_to_load(self, packages_list):
        self._model.packages_to_load = packages_list

    def set_suggestions_enabled(self, flag):
        self._model.suggestions_enabled = flag

    def get_modules(self):
        modules_found = list()
        for package_name in self._model.packages_to_load:
            package_modules = modules.registered_modules(package_name)
            modules_found.extend(package_modules)

        return modules_found

    def update_modules_data(
            self, data_type=None, pattern='', port_direction=None, port_structure=consts.PortStructure.Single):

        nodes_data = dict()
        category_paths = OrderedDict()

        registered_modules = self.get_modules()
        if not registered_modules:
            LOGGER.warning('No modules registered.')
            return nodes_data

        for module_data in registered_modules:
            for module_name, module in module_data.items():

                # Function Libraries
                for lib_name, lib in module.function_libs.items():
                    functions = lib.functions
                    for name, fn in functions.items():
                        fn_lib_name = fn.__annotations__['lib']
                        fn_arg_names = getargspec(fn).args
                        fn_input_types = set()
                        fn_output_types = set()
                        fn_input_structs = set()
                        fn_output_structs = set()

                        if fn.__annotations__['node_type'] == consts.NodeTypes.Callable:
                            fn_input_types.add('ExecPort')
                            fn_output_types.add('ExecPort')
                            fn_input_structs.add(consts.PortStructure.Single)
                            fn_output_structs.add(consts.PortStructure.Single)
                        if fn.__annotations__['return']:
                            fn_output_types.add(fn.__annotations__['return'][0])
                            fn_output_structs.add(consts.PortStructure.from_value(fn.__annotations__['return'][1]))

                        for index in range(len(fn_arg_names)):
                            input_data = fn.__annotations__[fn_arg_names[index]]
                            fn_input_types.add(input_data[0])
                            fn_input_structs.add(consts.PortStructure.from_value(input_data[1]))

                        node_category_path = '{}|{}'.format(
                            module_name, fn.__annotations__['meta'][consts.NodeLibraryMeta.CATEGORY])
                        keywords = fn.__annotations__['meta'][consts.NodeLibraryMeta.KEYWORDS]
                        check_str = name + node_category_path + ''.join(keywords)
                        if pattern.lower() in check_str.lower():
                            if data_type is None:
                                self.set_suggestions_enabled(False)
                                nodes_data[name] = {
                                    'path': node_category_path, 'description': fn.__doc__, 'module_name': lib_name}
                            else:
                                self.set_suggestions_enabled(True)
                                if port_direction == consts.PortDirection.Output:
                                    if port_structure != consts.PortStructure.Multi:
                                        has_multi_ports = consts.PortStructure.Multi in fn_input_structs
                                        if data_type in fn_input_types and (
                                                port_structure in fn_input_structs or has_multi_ports):
                                            nodes_data[name] = {
                                                'path': node_category_path, 'description': fn.__doc__,
                                                'module_name': lib_name}
                                    elif data_type in fn_input_types:
                                        nodes_data[name] = {
                                            'path': node_category_path, 'description': fn.__doc__,
                                            'module_name': lib_name}
                                else:
                                    if port_structure != consts.PortStructure.Multi:
                                        has_multi_ports = consts.PortStructure.Multi in fn_output_structs
                                        if data_type in fn_output_types and (
                                                port_structure in fn_input_structs or has_multi_ports):
                                            nodes_data[name] = {
                                                'path': node_category_path, 'description': fn.__doc__,
                                                'module_name': lib_name}
                                        elif data_type in fn_output_types:
                                            nodes_data[name] = {
                                                'path': node_category_path, 'description': fn.__doc__,
                                                'module_name': lib_name}

                # Nodes
                for node_class in list(module.node_classes.values()):
                    if node_class.__name__ in ('GetVar', 'SetVar'):
                        continue
                    node_category_path = '{}|{}'.format(module_name, node_class.CATEGORY)
                    check_str = node_class.__name__ + node_category_path + ''.join(node_class.KEYWORDS)
                    if self._model.search_text.lower() not in check_str.lower():
                        continue

                    if not data_type:
                        nodes_data[node_class.__name__] = {
                            'path': node_category_path, 'description': node_class.DESCRIPTION}
                    else:
                        hints = node_class.port_type_hints()
                        if port_direction == consts.PortDirection.Output:
                            if port_structure != consts.PortStructure.Multi:
                                has_multi_ports = consts.PortStructure.Multi in hints.input_structs
                                if data_type in hints.input_types and (
                                        port_structure in hints.input_structs or has_multi_ports):
                                    nodes_data[node_class.__name__] = {
                                        'path': node_category_path, 'description': node_class.DESCRIPTION}
                            elif data_type in hints.input_types:
                                nodes_data[node_class.__name__] = {
                                    'path': node_category_path, 'description': node_class.DESCRIPTION}
                        else:
                            if port_structure != consts.PortStructure.Multi:
                                has_multi_ports = consts.PortStructure.Multi in hints.output_structs
                                if data_type in hints.output_types and (
                                        port_structure in hints.output_structs or has_multi_ports):
                                    nodes_data[node_class.__name__] = {
                                        'path': node_category_path, 'description': node_class.DESCRIPTION}
                            elif data_type in hints.output_types:
                                nodes_data[node_class.__name__] = {
                                    'path': node_category_path, 'description': node_class.DESCRIPTION}

        # Fill data
        for node_name, node_data in nodes_data.items():
            node_path = node_data['path'].split('|')
            category_path = ''
            for folder_id in range(len(node_path)):
                folder_name = node_path[folder_id]
                if folder_id == 0:
                    category_path = folder_name
                    if category_path not in category_paths:
                        category_paths[category_path] = {
                            'parent_path': None, 'text': folder_name}
                else:
                    parent_category_path = category_path
                    category_path += '|{}'.format(folder_name)
                    if category_path not in category_paths:
                        category_paths[category_path] = {
                            'parent_path': parent_category_path, 'text': folder_name}

        self._model.category_paths = category_paths
        self._model.nodes_data = nodes_data

    def clear_search(self):
        self._model.search_text = ''
