import logging 

logging.addLevelName(25, 'SUCCESS')

from .cowpy import Cowpy, CowpyLogger 
logging.setLoggerClass(CowpyLogger)

cs = Cowpy()

getLogger = cs.getLogger
