from enum import Enum 
import logging 
from logging.config import dictConfig #, DictConfigurator, dictConfigClass
import traceback 
import inspect 
import sys 
import os 
import json
import ast 

FOREGROUND_COLOR_PREFIX = '\033[38;2;'
FOREGROUND_COLOR_SUFFIX = 'm'
FOREGROUND_COLOR_RESET = '\033[0m'

COLOR_TABLE = {
    'white': '255;255;255',
    'red': '255;0;0',
    'darkred': '192;0;0',
    'green': '0;255;0',
    'orange': '255;165;0',
    'gray': '192;192;192',
    'darkgray': '128;128;128',
    'yellow': '165:165:0'
}

class Color(Enum):
    WHITE = COLOR_TABLE['white']
    RED = COLOR_TABLE['red']
    DARKRED = COLOR_TABLE['darkred']
    GREEN = COLOR_TABLE['green']
    ORANGE = COLOR_TABLE['orange']
    GRAY = COLOR_TABLE['gray']
    DARKGRAY = COLOR_TABLE['darkgray']
    YELLOW = COLOR_TABLE['yellow']

LEVEL_COLORS = {
    'DEBUG': Color.DARKGRAY,
    'INFO': Color.WHITE,
    'WARN': Color.ORANGE,
    'WARNING': Color.ORANGE,
    'SUCCESS': Color.GREEN,
    'ERROR': Color.RED,
    'CRITICAL': Color.DARKRED
}

LOG_LEVEL_DEFAULT = 'INFO'
LOG_LEVEL = os.getenv('LOG_LEVEL', LOG_LEVEL_DEFAULT)
LEVEL_COLORS = { logging._nameToLevel[k]: LEVEL_COLORS[k] for k in LEVEL_COLORS.keys() }
FORMATTER_BASE = '[ %(levelname)7s ] %(asctime)s %(name)s %(filename)12s:%(lineno)-4d %(message)s'

class SlateLogger(logging.Logger):
    
    # def __init__(self, *args, **kwargs):
    #     super(SlateLogger, self).__init__(*args, **kwargs)

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        color_ext = { 'color': LEVEL_COLORS[level].value }
        extra = color_ext if not extra else extra.update(color_ext)
        # print(extra)
        # print([ h.formatter._fmt for h in self.handlers ])
        super(SlateLogger, self)._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)
    
    def warn(self, msg):
        super(SlateLogger, self).warning(msg)
    
    def success(self, msg):
        super(SlateLogger, self).log(level=logging._nameToLevel['SUCCESS'], msg=msg)

class Slate(object):
    
    _intlogger = None 
    logger = None 
    quiet = False 
    headers = True 
    log_level = None 
    context = None 
    dry_run = False 

    dictConfigs = None 
    formatter_ids = None 
    
    def _getrc(self, path=None, logger=None):
        
        if not logger:
            logger = logging.getLogger()

        if not self.dictConfigs:
            self.dictConfigs = {}

        fullpath = os.path.realpath('.slaterc')

        if path:
            fullpath = os.path.join(path, '.slaterc')
        
        if fullpath not in self.dictConfigs:
            if os.path.exists(fullpath):            
                logger.info(f'{fullpath} exists. Opening, reading, and evaluating..')
                with open(fullpath, 'r') as conf:
                    try:
                        self.dictConfigs[fullpath] = ast.literal_eval(conf.read())
                    except:
                        logger.error(sys.exc_info()[0])
                        logger.error(sys.exc_info()[1])
                        traceback.print_tb(sys.exc_info()[2])

        if fullpath in self.dictConfigs:        
            logger.info(f'Calling dictConfig with {fullpath}')
            dictConfig(self.dictConfigs[fullpath])
            self.formatter_ids = []
        else:
            logger.warning(f'{fullpath} could not be found, opened, read, or evaluated')
    
    def _colorFormatter(self, fmt=FORMATTER_BASE):
        return logging.Formatter(fmt = f'{FOREGROUND_COLOR_PREFIX}%(color)s{FOREGROUND_COLOR_SUFFIX}{fmt}{FOREGROUND_COLOR_RESET}')

    def getLogger(self, name=None, internal=False):

        callingFrame = inspect.getouterframes(inspect.currentframe())[1]
        
        self._getrc(path=os.path.dirname(callingFrame.filename), logger=self._intlogger)

        # print(dir(callingFrame))
        name = name or callingFrame.function
        if name == "<module>":
            name = os.path.basename(callingFrame.filename)
        
        new_logger = logging.getLogger(name)
        if internal:
            self._intlogger = new_logger
        
        self._intlogger.info(f'Got -- {name} -- logger')
        
        self._intlogger.info(f'Fixing {len(new_logger.handlers)} handler formatters')
        for h in new_logger.handlers:
            self._intlogger.info(f'fixing formatters for handler {h}')
            if id(h.formatter) not in self.formatter_ids:
                h.setFormatter(self._colorFormatter(h.formatter._fmt))
                self.formatter_ids.append(id(h.formatter))
                self._intlogger.info(f'formatter {id(h.formatter)} processed..')
            else:
                self._intlogger.info(f'formatter {id(h.formatter)} already processed..')

        return new_logger
    
    def __init__(self, *args, **kwargs):

        self.getLogger(__name__, internal=True)
        self._intlogger.info(f'Slate internal logging configured as {__name__}')

    def clear_context(self):
        self.context = None 
        
    def set_context(self, context):
        self.context = context 
    
    def wrap_context(self, message):
        if self.dry_run:
            message = f'[ DRY RUN ] {message}'
        if self.context:
            message = f'[ {self.context} ] {message}'
        return message 
    
    # def _wrap(self, call, message, color=None):
    #     if not self.quiet:
    #         message = self.wrap_context(message)
    #         if color:
    #             call(colorwrapper(message, color))
    #         else:
    #             call(message)
    
    def text(self, message):
        if not self.quiet:
            self.logger.warning(message)
            
    # def debug(self, message):
    #     self._wrap(self.logger.debug, message)
    
    # def info(self, message):
    #     self._wrap(self.logger.info, message)
    
    # def warn(self, message):
    #     self._wrap(self.logger.warning, message)

    # def warning(self, message):
    #     self._wrap(self.logger.warning, message)

    # def success(self, message):
    #     self._wrap(self.logger.info, message)
    
    # def error(self, message):
    #     self._wrap(self.logger.error, message)

    def exception(self, data=False):
        stack_summary = traceback.extract_tb(sys.exc_info()[2])
        self.logger.error(stack_summary)
        if logging._nameToLevel[self.log_level.upper()] <= logging.ERROR:
            self.logger.error(sys.exc_info()[0])
            self.logger.error(sys.exc_info()[1])
            for line in stack_summary.format():
                self.logger.error(line)
