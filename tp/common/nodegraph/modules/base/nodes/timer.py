from tpDcc.libs.nodegraph.core import consts, node, menu


class Timer(node.Node):

    CATEGORY = 'FlowControl'
    KEYWORDS = ['flow', 'timer', 'loop']
    DESCRIPTION = 'Allow to execute graph loop'
    HEADER_COLOR = consts.FLOW_CONTROL_COLOR

    def __init__(self, *args, **kwargs):
        super(Timer, self).__init__(*args, **kwargs)

        self._accum = 0.0
        self._is_working = False

        # self.out = self.create_input_port(port_name='In', data_type='ExecPort')
        # self.begin = self.create_input_port(port_name='Start', data_type='IntPort', default_value=0)
        # self.end = self.create_input_port(port_name='End', data_type='IntPort', default_value=0)
        # self.out = self.create_output_port(port_name='Out', data_type='ExecPort')

        self.start = self.add_input_port('Start', data_type='ExecPort', default_value=None, function=self.start)
        self.stop = self.add_input_port('Stop', data_type='ExecPort', default_value=None, function=self.stop)
        self.interval = self.add_input_port('delta(s)', data_type='IntPort', default_value=0.2)
        self.out = self.add_output_port(consts.DEFAULT_OUT_EXEC_PORT_NAME, data_type='ExecPort')

    @staticmethod
    def port_type_hints():
        helper = node.NodePortsSuggestionsHelper()
        helper.add_input_data_type('ExecPort')
        helper.add_input_data_type('FloatPort')
        helper.add_input_data_type('ExecPort')
        helper.add_input_struct(consts.PortStructure.Single)
        helper.add_output_struct(consts.PortStructure.Single)

        return helper

    def tick(self, delta_time):
        super(Timer, self).tick(delta_time)

        if self._is_working:
            interval = self.intervla.value
            if interval < 0.02:
                interval = 0.02
            self._accum += delta_time
            if self._accum >= interval:
                self.out.call()
                self._accum = 0.0

    def start(self, *args, **kwargs):
        self._accum = 0.0
        self._is_working = True

    def stop(self, *args, **kwargs):
        self._is_working = False
        self._accum = 0.0


class TimerMenu(menu.NodeMenu):

    NODE_CLASS = Timer

    def __init__(self, *args, **kwargs):
        super(TimerMenu, self).__init__(*args, **kwargs)

        self.add_command('Run', self.run)

    def run(self, graph, node):
        return node.evaluate()
