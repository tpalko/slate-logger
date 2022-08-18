import logging 

logging.addLevelName(25, 'SUCCESS')

from .slate import Slate, SlateLogger 
logging.setLoggerClass(SlateLogger)

cs = Slate()

getLogger = cs.getLogger
