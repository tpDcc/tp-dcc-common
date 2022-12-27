import numbers

from Qt.QtGui import QColor

from tp.core import log
from tp.common.nodegraph.core import exceptions

logger = log.tpLogger

DATATYPE_REGISTER = dict()


def instancer(cls):
	return cls()


class DataTypes(object):
	"""
	Defines the available socket data types
	"""

	EXEC = 'exec'
	STRING = 'string'
	NUMERIC = 'numeric'
	BOOLEAN = 'boolean'
	LIST = 'list'


@instancer
class DataType(object):
	"""
	Defines the available socket data types
	"""

	def __getattr__(self, name):
		if name in DATATYPE_REGISTER:
			return DATATYPE_REGISTER[name]
		else:
			logger.error('Unregistered datatype: {0}'.format(name))
			raise KeyError

	@classmethod
	def get_basic_types(cls):
		return {
			DataTypes.EXEC: {'class': type(None), 'color': QColor('#FFFFFF'), 'label': '', 'default': None},
			DataTypes.STRING: {'class': str, 'color': QColor('#A203F2'), 'label': 'Name', 'default': ''},
			DataTypes.NUMERIC: {'class': numbers.Complex, 'color': QColor('#DEC017'), 'label': 'Number', 'default': 0.0},
			DataTypes.BOOLEAN: {'class': bool, 'color': QColor('#C40000'), 'label': 'Condition', 'default': False},
			DataTypes.LIST: {'class': list, 'color': QColor('#0BC8F1'), 'label': 'List', 'default': list()}
		}


def get(data_type):
	"""
	Returns data related with given data type name.

	:param str data_type: data type name.
	:return: data type data dictionary.
	:rtype: dict
	"""

	return DATATYPE_REGISTER.get(data_type, dict())


def get_type_name( data_type_dict):
	try:
		type_name = [
			data_type_name for data_type_name, data in DATATYPE_REGISTER.items() if data == data_type_dict][0]
		return type_name
	except IndexError:
		logger.exception('Failed to find data type for class {}'.format(data_type_dict['class']))
		raise IndexError


def register_data_type(type_name, type_class, color, label='custom_data', default_value=None):
	if type_name in DATATYPE_REGISTER.keys():
		logger.error('Datatype {} is already registered!'.format(type_name))
		raise exceptions.InvalidDataTypeRegistrationError

	type_dict = {
		'class': type_class,
		'color': color if isinstance(color, QColor) else QColor(color),
		'label': label,
		'default': default_value
	}
	DATATYPE_REGISTER[type_name.lower()] = type_dict


def load_data_types():
	for type_name, type_data in DataType.get_basic_types().items():
		DATATYPE_REGISTER[type_name] = type_data


load_data_types()
