import cowpy 

logger = cowpy.getLogger()

logger.set_context('subbing')
logger.error('this is from a subfolder')
logger.clear_context()

def functionlog_declared_outside():
    logger.set_context('bare function')
    logger.warning('whoa there buddy, this logger ain\'t declared for the both of us!')

    fnLogger = cowpy.getLogger()
    fnLogger.info('but good thing, this one was created from within functionlog_declared_outside')

functionlog_declared_outside()