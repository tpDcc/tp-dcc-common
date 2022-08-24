#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains view implementation for ExecPort
"""

from tpDcc.libs.nodegraph.core.views import port
from tpDcc.libs.nodegraph.painters import port as port_painters


class ExecPortView(port.PortView, object):
    def __init__(self, model=None, parent=None):
        super(ExecPortView, self).__init__(model=model, parent=parent)

    def paint(self, painter, option, widget):
        port_painters.exec_port_painter(self, painter, option, widget)

    def hoverEnterEvent(self, event):
        super(ExecPortView, self).hoverEnterEvent(event)
        self.update()
        self._hovered = True
        event.accept()
