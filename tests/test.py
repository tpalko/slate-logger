import sys
import os 
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'src'))

import slate
logger = slate.getLogger()

logger.debug("edebug")
logger.warn('hey dooder')
logger.warning('this is  a warning')

class TestSlate(object):

    logger = None 
    classlogger = slate.getLogger()

    def __init__(self, *args, **kwargs):
        self.logger = slate.getLogger()

    def doathing(self):
        self.logger.error('done a thing')
    
    def anotherthing(self):
        self.classlogger.info('wait, from a class level logger??')

tcs = TestSlate()
tcs.doathing()
tcs.anotherthing()

import testsubfolder.another 

import blankconfig.blank

tcs.doathing()
tcs.anotherthing()

logger.success('SUICCESSE!@ after all that!?')

logger.critical('error after all that!?')