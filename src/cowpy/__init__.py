import logging 

# logging.basicConfig(level=logging.DEBUG)

logging.addLevelName(25, 'SUCCESS')

from .cowpy import Cowpy, CowpyLogger #, CowpyConfigurator
logging.setLoggerClass(CowpyLogger)
# logging.config.dictConfigClass = CowpyConfigurator

# print('-------------  Instantiating Cowpy   ----------------')
cs = Cowpy()
# print('--------  Finished Instantiating Cowpy   ------------')

getLogger = cs.getLogger
StreamHandler = logging.StreamHandler