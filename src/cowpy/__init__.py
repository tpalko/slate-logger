import logging 

logging.addLevelName(25, 'SUCCESS')

from .cowpy import Cowpy, CowpyLogger 
logging.setLoggerClass(CowpyLogger)

# print('-------------  Instantiating Cowpy   ----------------')
cs = Cowpy()
# print('--------  Finished Instantiating Cowpy   ------------')

getLogger = cs.getLogger
StreamHandler = logging.StreamHandler
