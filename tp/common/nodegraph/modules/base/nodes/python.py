from tpDcc.libs.nodegraph.core import node


class PythonNode(node.Node):

    CATEGORY = 'Common'
    KEYWORDS = ['code', 'expression', 'python', 'custom', 'py']
    DESCRIPTION = 'Python script node'

    def __init__(self, *args, **kwargs):
        super(PythonNode, self).__init__(*args, **kwargs)

        self.input = self.add_input_port('In', data_type='ExecPort')
        self.out = self.add_output_port('Out', data_type='ExecPort')
        self.test = self.add_output_port('Test', data_type='FloatPort')

    def evaluate(self):
        print('Hello World!')

        # self.out = self.create_output_port(port_name='Out', data_type='ExecPort')
