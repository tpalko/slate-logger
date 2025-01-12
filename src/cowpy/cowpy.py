from enum import Enum 
import logging 
import json
from logging.config import dictConfig
import traceback 
import inspect 
import sys 
import os 
import ast
from unittest.mock import DEFAULT 

FOREGROUND_COLOR_PREFIX = '\033[38;2;'
FOREGROUND_COLOR_SUFFIX = 'm'
FOREGROUND_COLOR_RESET = '\033[0m'
FORMATTER_BASE = '[ %(levelname)8s ] %(asctime)s %(filename)12s:%(lineno)5d %(name)12s  %(message)s'
DEFAULT_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': FORMATTER_BASE
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'WARNING'
        },
    },
    'loggers': {    
        '': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    }
}

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

LEVEL_COLORS = { logging._nameToLevel[k]: LEVEL_COLORS[k] for k in LEVEL_COLORS.keys() }

class CowpyLogger(logging.Logger):

    context = None 

    # -- overriding base 
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        if level not in LEVEL_COLORS:
            raise NotImplementedError(f'There is no {level} in LEVEL_COLORS. Go ahead and check it.')

        ext = { 'color': LEVEL_COLORS[level].value }
        if extra:
            extra.update(ext)
        extra = extra or ext 

        padded = ''
        if self.context:
            padded = self.context[0:8]
        while len(padded) < 8:
            padded = f'{padded} '
        msg = f'[ {padded} ] {msg}'
        
        super(CowpyLogger, self)._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)
    
    def warn(self, msg):
        super(CowpyLogger, self).warning(msg)
    
    def success(self, msg):
        super(CowpyLogger, self).log(level=logging._nameToLevel['SUCCESS'], msg=msg)

    def clear_context(self):
        self.context = None 
        
    def set_context(self, context):
        self.context = context 
    
    def exception(self):
        stack_summary = traceback.extract_tb(sys.exc_info()[2])
        self.error("".join(stack_summary.format()))
        # self.error("\n".join([ f'{s.filename} line {s.line}' for s in stack_summary ]))
        # for line in stack_summary.format():
        #     self.error(line)
        # if logging._nameToLevel[self.log_level.upper()] <= logging.ERROR:
        #     self.error(sys.exc_info()[0])
        #     self.error(sys.exc_info()[1])
        #     for line in stack_summary.format():
        #         self.error(line)
  

class Cowpy(object):
    
    _intlogger = None 
    
    dictConfigs = None 
    _loaded_dict_config = None 
    _fixed_logger_names = [] 
    formatter_ids = None 
    
    context_enabled = False 
    
    def __init__(self, *args, **kwargs):

        self.getLogger(__name__, internal=True)
        self._intlogger.info(f'Cowpy internal logging configured as {__name__}')

        for k in kwargs:
            try:
                self.__getattribute__(k)
                self.__setattr__(k, kwargs[k])
            except:
                self._intlogger.error(f'Cowpy has no {k}')
        

    def _getrc(self, rcpath, logger=None):
        
        if not logger:
            # -- the only time we get here is on the very first self.getLogger call in Cowpy init
            logger = logging.getLogger()
        else:
            logger.set_context('rc fetch')

        if not self.dictConfigs:
            self.dictConfigs = {}

        orig_rc_path = rcpath 

        # -- follow parent folders all the way up, searching desperately for configuration
        while not os.path.exists(os.path.join(rcpath, '.cowpyrc')):
            if rcpath == '/':
                break 
            rcpath = os.path.realpath(os.path.join(rcpath, os.pardir))

        final_rc_path = os.path.join(rcpath, '.cowpyrc')
        rcFileContents = None 

        if self._loaded_dict_config != final_rc_path:

            rcFileContents = DEFAULT_CONFIG

            if os.path.exists(final_rc_path):
                if final_rc_path not in self.dictConfigs:            
                    logger.info(f'{final_rc_path} exists. Opening, reading, and evaluating..')
                    with open(final_rc_path, 'r') as conf:
                        try:
                            self.dictConfigs[final_rc_path] = ast.literal_eval(conf.read())
                        except:
                            logger.error(sys.exc_info()[0])
                            logger.error(sys.exc_info()[1])
                            traceback.print_tb(sys.exc_info()[2])
                
                rcFileContents = self.dictConfigs[final_rc_path]
                
            else:
                logger.warning(f'.cowpyrc at {orig_rc_path} could not be found, opened, read, or evaluated')
                logger.warning(f'Calling dictConfig with default config')            
        
            self._loaded_dict_config = final_rc_path

        return rcFileContents
                        
    def _colorFormatter(self, fmt=FORMATTER_BASE):
        return logging.Formatter(fmt = f'{FOREGROUND_COLOR_PREFIX}%(color)s{FOREGROUND_COLOR_SUFFIX}{fmt}{FOREGROUND_COLOR_RESET}')

    def _handler(self):
        newH = logging.StreamHandler()        
        newH.setFormatter(self._colorFormatter())
        return newH 

    def self_logger(self):
        return self._intlogger or logging.getLogger(__name__)

    def fixLoggerFormatters(self, logger_name):

        if logger_name in self._fixed_logger_names:
            return 

        self._intlogger.info(f'Fixing logger formatters for {logger_name}')

        logger = logging.getLogger(logger_name)
        self._intlogger.info(f'Fixing formatters for {len(logger.handlers)} {logger_name} handlers: {",".join([ h.__class__.__name__ for h in logger.handlers ])}')
        if len(logger.handlers) > 0:
            for h in logger.handlers:
                if h.formatter:
                    if id(h.formatter) not in self.formatter_ids:
                        self._intlogger.info(f'Replacing {h.__class__.__name__} formatter')
                        newF = self._colorFormatter(h.formatter._fmt)
                        self.formatter_ids.append(id(h.formatter))                        
                        h.setFormatter(newF)
                    else:
                        self._intlogger.info(f'Doing nothing for {h.__class__.__name__} formatter (filed as done)')
                else:
                    self._intlogger.info(f'Adding formatter for {h.__class__.__name__}')
                    newF = self._colorFormatter()
                    h.setFormatter(newF)
        else:
            self._intlogger.info(f'No handlers on this new logger, so adding a default')
            logger.addHandler(self._handler())      
        
        self._fixed_logger_names.append(logger_name)

    def getLogger(self, name=None, internal=False):

        if not internal:
            pass 
            # print('------------------- Creating your logger -------------------')

        callingFrame = inspect.getouterframes(inspect.currentframe())[1]
        
        rcFileContents = self._getrc(rcpath=os.path.dirname(callingFrame.filename), logger=self._intlogger)
        
        if rcFileContents:
            if self._intlogger:
                self._intlogger.info(f'Calling dictConfig with')
                self._intlogger.info(json.dumps(rcFileContents, indent=4))
                
            dictConfig(rcFileContents)
            # -- applying a configuration invalidates any ids that might have been in memory
            # -- so we dump our tracking of those IDs
            self.formatter_ids = []
            self._fixed_logger_names = []

        if self._intlogger:
            self._intlogger.clear_context() 

        # print(dir(callingFrame))
        name = name or callingFrame.function
        if name == "<module>":
            name =  os.path.splitext(os.path.basename(callingFrame.filename))[0]
        
        new_logger = logging.getLogger(name)

        if internal:
            self._intlogger = new_logger

        self._intlogger.info(f'Got {name} logger { "(as the internal cowpy logger)" if internal else "" }')
        
        if rcFileContents:
            other_loggers = [ n for n in rcFileContents['loggers'].keys() if n != name ]
            self._intlogger.info(f'Fixing logger formatters for {len(other_loggers)} configured loggers (other than {name})..')
            for logger_name in other_loggers:
                # -- ignore the root logger, this is a bad time 
                if logger_name != '':
                    _ = self.fixLoggerFormatters(logger_name)
        
        self.fixLoggerFormatters(name)

        if not internal:
            pass
            # print('-------------- Finished Creating your logger ---------------')

        return new_logger
