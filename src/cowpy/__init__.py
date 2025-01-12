import logging
from cowpy.cowpy import Cowpy, Format
from cowpy.logger import CowpyLogger #, CowpyConfigurator
#from .plugins.gunicorn import CowpyGunicorn

# logging.config.dictConfigClass = CowpyConfigurator

# print('-------------  Instantiating Cowpy   ----------------')
cs = Cowpy()
# print('--------  Finished Instantiating Cowpy   ------------')

FORMAT_DETAILED = Format.DETAILED
FORMAT_STANDARD = Format.STANDARD
FORMAT_USER = Format.USER

getLogger = cs.getLogger

StreamHandler = logging.StreamHandler


