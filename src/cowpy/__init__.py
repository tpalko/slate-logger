

# logging.basicConfig(level=logging.DEBUG)

# logging.addLevelName(25, 'SUCCESS')

from .cowpy import Cowpy, Format
from .logger import CowpyLogger #, CowpyConfigurator
# logging.setLoggerClass(CowpyLogger)

# logging.config.dictConfigClass = CowpyConfigurator

# print('-------------  Instantiating Cowpy   ----------------')
cs = Cowpy()
# print('--------  Finished Instantiating Cowpy   ------------')

FORMAT_DETAILED = Format.DETAILED
FORMAT_STANDARD = Format.STANDARD
FORMAT_USER = Format.USER

getLogger = cs.getLogger
# autoLogger = cs.autoLogger
# autoConfig = cs.checkAndApplyFromPath

import logging 

StreamHandler = logging.StreamHandler

#from .plugins.gunicorn import CowpyGunicorn
