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
FORMATTER_BASE = '[ %(levelname)8s ] %(asctime)s %(filename)12s:%(lineno)5d %(name)12s %(context)-12s %(message)s'

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

DEFAULT_RC_PATH = '__DEFAULT_RC_PATH__'

class CowpyConfigurator():

    _config = None 

    def __init__(self, *args, **kwargs):
        self._config = args[0]

    def configure(self):
        pass 

class CowpyLogger(logging.Logger):

    context = None 

    # -- overriding base 
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        if level not in LEVEL_COLORS:
            raise NotImplementedError(f'There is no {level} in LEVEL_COLORS. Go ahead and check it.')

        extra = extra or {}

        extra.update({ 
            'color': LEVEL_COLORS[level].value,
            'context': f'[ {self.context or "-"} ]'
        })

        # padded = ''
        # context = True
        # if self.context:
        #     for h in self.handlers:
        #         if h.formatter and h.formatter._fmt.find('context') < 0:
        #             context = False 
        #             break 
        #     if context:
        #         extra.update({'context': f'[ {self.context} ]'})
        #     padded = self.context[0:8]
        # while len(padded) < 8:
        #     padded = f'{padded} '
        # msg = f'[ {padded} ] {msg}'
        
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
        full_error_text = f'{sys.exc_info()[1]}: {sys.exc_info()[0]} {"".join(stack_summary.format())}'
        self.error(full_error_text)
        # self.error(sys.exc_info()[0])
        # self.error(sys.exc_info()[1])
        # self.error("".join(stack_summary.format()))
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
    _loaded_dict_config_path = None 
    _fixed_logger_names = [] 
    formatter_ids = None 
    
    context_enabled = False 
    
    def __init__(self, *args, **kwargs):

        # -- set internal logger 
        self._intlogger = self.getLogger(__name__)

        self._log_internal('debug', f'Cowpy internal logging configured as {__name__}')

        for k in kwargs:
            try:
                self.__getattribute__(k)
                self.__setattr__(k, kwargs[k])
            except:
                self._log_internal('error', f'Cowpy has no {k}')
    
    def _get_default_config(self, logger_name, level='WARNING'):

        return {
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
                    'level': f'{level}'
                },
            },
            'loggers': {    
                f'{logger_name}': {
                    'handlers': ['console'],
                    'level': f'{level}',
                    'propagate': False,
                },
            }
        }

    def _getrc_path(self, calling_filename):
        
        self._log_internal_context('cowpy rc path')

        if not self.dictConfigs:
            self.dictConfigs = {}

        # -- realpath will resolve symlinked calling code 
        calling_folder = os.path.dirname(os.path.realpath(calling_filename))
        self._log_internal('debug', f'Using {calling_folder} as calling folder')
        rc_folder = calling_folder 
        final_rc_path = None 

        # -- follow parent folders all the way up, searching desperately for configuration
        while not os.path.exists(os.path.join(rc_folder, '.cowpyrc')):
            if rc_folder == '/':
                self._log_internal('debug', f'Reached the root folder with no RC')
                rc_folder = None 
                break 
            self._log_internal('debug', f'RC not found in rc_folder, going up one..')
            rc_folder = os.path.realpath(os.path.join(rc_folder, os.pardir))

        if rc_folder:
            final_rc_path = os.path.join(rc_folder, '.cowpyrc')

        # -- we already checked above, but double check 
        if final_rc_path and not os.path.exists(final_rc_path):
            final_rc_path = None 
        
        if not final_rc_path:
            self._log_internal('warning', f'.cowpyrc in {calling_folder} or its parents could not be found, opened, read, or evaluated')
            self._log_internal('warning', f'Calling dictConfig with default config')  
            final_rc_path = DEFAULT_RC_PATH
        
        self._log_internal_context(None)

        return final_rc_path
    
    def _fix_config_formatters(self, config_dict):
        formatters = config_dict['formatters'] if 'formatters' in config_dict else {}                        
        for handler_name in config_dict['handlers'].keys():
            handler = config_dict['handlers'][handler_name]
            if handler['class'] != 'logging.StreamHandler':
                continue 
            if 'formatter' in handler:
                formatter_name = handler['formatter']
                if formatter_name not in formatters:
                    self._log_internal('debug', f'Adding a base formatter for handler {handler_name} {formatter_name}')
                    formatters[formatter_name] = { 'format': FORMATTER_BASE }
                else:
                    self._log_internal('debug', f'Found formatter {formatters[formatter_name]} for handler {handler_name}')
            else:
                self._log_internal('debug', f'Setting handler {handler_name} formatter to "default"')
                handler['formatter'] = 'default'
                if 'default' not in formatters:
                    self._log_internal('debug', f'Adding missing "default" formatter')
                    formatters['default'] = { 'format': FORMATTER_BASE }
        config_dict['formatters'] = formatters
        # return config_dict

    def _load_rc_contents(self, rc_path, logger_name):

        rcFileContents = None 

        if os.path.exists(rc_path):
            if rc_path not in self.dictConfigs:            
                self._log_internal('debug', f'{rc_path} exists. Opening, reading, and evaluating..')
                with open(rc_path, 'r') as conf:
                    try:
                        config_dict = ast.literal_eval(conf.read())
                        self._log_internal('debug', json.dumps(config_dict, indent=4))
                        self._fix_config_formatters(config_dict)
                        self.dictConfigs[rc_path] = config_dict
                    except:
                        self._log_internal('error', sys.exc_info()[0])
                        self._log_internal('error', sys.exc_info()[1])
                        traceback.print_tb(sys.exc_info()[2])
            
            rcFileContents = self.dictConfigs[rc_path]            

        if not rcFileContents:

            if rc_path != DEFAULT_RC_PATH:
                self._log_internal('warning', f'RC not found from {rc_path}, getting default config')

            rcFileContents = self._get_default_config(logger_name=logger_name)

        return rcFileContents
    
    def _colorFormatter(self, fmt=FORMATTER_BASE):
        return logging.Formatter(fmt = f'{FOREGROUND_COLOR_PREFIX}%(color)s{FOREGROUND_COLOR_SUFFIX}{fmt}{FOREGROUND_COLOR_RESET}')

    def _handler(self):
        newH = logging.StreamHandler()        
        newH.setFormatter(self._colorFormatter())
        return newH 

    def _log_internal(self, level, msg):
        
        _local_logger = self._intlogger
        if not _local_logger:
            _local_logger = logging.getLogger(__name__)
            
        _local_logger.log(level=logging._nameToLevel[level.upper()], msg=msg, stacklevel=3)

    def _log_internal_context(self, context):
        if self._intlogger:
            self._intlogger.set_context(context)

    def fixLoggerFormatters(self, logger_name):

        if logger_name in self._fixed_logger_names:
            return 

        logger = logging.getLogger(logger_name)
        self._log_internal('debug', f'Fixing formatters for {len(logger.handlers)} {logger_name} handlers: {",".join([ h.__class__.__name__ for h in logger.handlers ])}')
        if len(logger.handlers) > 0:
            for h in logger.handlers:
                if h.formatter:
                    # self._log_internal('debug', dir(h.formatter))
                    if id(h.formatter) not in self.formatter_ids:
                        self._log_internal('debug', f'Replacing {h.__class__.__name__} formatter')
                        newF = self._colorFormatter(h.formatter._fmt)
                        self.formatter_ids.append(id(h.formatter))                        
                        h.setFormatter(newF)
                    else:
                        self._log_internal('debug', f'Doing nothing for {h.__class__.__name__} formatter (filed as done)')
                else:
                    self._log_internal('debug', f'Adding formatter for {h.__class__.__name__}')
                    h.setFormatter(self._colorFormatter())
        else:
            self._log_internal('debug', f'No handlers on this new logger, so adding a default')
            logger.addHandler(self._handler())      
        
        self._fixed_logger_names.append(logger_name)

    def getLogger(self, name=None):
        
        self._log_internal('debug', f'Someone is asking for a logger ({name})!')
        callingFrame = inspect.getouterframes(inspect.currentframe())[1]
        
        self._log_internal('debug', inspect.getouterframes(inspect.currentframe())[1].filename)
        # self._log_internal('debug', f'{dir(callingFrame.frame)}')
        # self._log_internal('debug', f'{dir(callingFrame.frame.f_code)}')
        # self._log_internal('debug', f'{callingFrame.frame.f_code.co_names}')

        # self._log_internal('debug', f'have calling frame: {callingFrame.function}, fallback is {name}')
        # print(dir(callingFrame))
        if not name:            
            name = callingFrame.function
            self._log_internal('debug', f'Logger name changed to {name}')

        if name == "<module>":            
            name =  os.path.splitext(os.path.basename(callingFrame.filename))[0]
            self._log_internal('debug', f'Logger name changed to {name}')
            # self._log_internal('debug', f'<module> is no good, so going for calling frame filename: {name}')

        self._log_internal('debug', f'vvvvvvvvvvvvvvvvvvv getting logger: {name} vvvvvvvvvvvvvvvvvvvvvvvvvv')

        rc_path = self._getrc_path(calling_filename=callingFrame.filename)
        
        rcFileContents = None 

        if self._loaded_dict_config_path != rc_path:

            self._log_internal('debug', f'loading contents of RC file {rc_path}')
            rcFileContents = self._load_rc_contents(rc_path, name)      

            self._log_internal('debug', f'Calling dictConfig with')
            self._log_internal('debug', json.dumps(rcFileContents, indent=4))
                
            dictConfig(rcFileContents)    
        
            self._loaded_dict_config_path = rc_path

            # -- applying a configuration invalidates any ids that might have been in memory
            # -- so we dump our tracking of those IDs
            self.formatter_ids = []
            self._fixed_logger_names = []
            
            

            other_loggers = [ n for n in rcFileContents['loggers'].keys() if n != name ]
            # self._log_internal('info', f'Fixing logger formatters for {len(other_loggers)} configured loggers (other than {name}): { ",".join(other_loggers)}')
            for logger_name in other_loggers:
                # -- ignore the root logger, this is a bad time 
                if logger_name != '':
                    _ = self.fixLoggerFormatters(logger_name)
            
            self.fixLoggerFormatters(name)

        else:
            self._log_internal('debug', f'RC found is what is already loaded')            

        self._log_internal('debug', f'^^^^^^^^^^^^^^^^^^ getting logger: {name} ^^^^^^^^^^^^^^^^^^^^^^^^')

        named_logger = logging.getLogger(name)
        self._log_internal('info', f'Got {name} logger')
        return named_logger
