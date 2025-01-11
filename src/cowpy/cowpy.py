from enum import Enum 
import logging 
import json
from logging.config import dictConfig
from cowpy.color import LogColorer
from cowpy.common import handler
import inspect 
import sys 
import os 
import ast
# from unittest.mock import DEFAULT 

FORMAT_TABLE = {
    'standard': '[ %(levelname)7s ] %(asctime)s %(name)12s %(context)s %(message)s',
    'user': '%(message)s',
    'detailed': '[%(levelname)7s] %(asctime)s %(filename)12s:%(lineno)3d %(name)9s %(context)s %(message)s'
}

class Format(Enum):
    STANDARD = FORMAT_TABLE['standard']
    USER = FORMAT_TABLE['user']
    DETAILED = FORMAT_TABLE['detailed']


DEFAULT_RC_PATH = '__DEFAULT_RC_PATH__'

# class CowpyConfigurator():

#     _config = None 

#     def __init__(self, *args, **kwargs):
#         self._config = args[0]

#     def configure(self):
#         pass 

class Cowpy(object):
    
    _intlogger = None 
    
    _colorized_formatters = None 
    _applied_configs = None 
    _config_cache = None 
    _forced_loggers = None
    
    tmp_name = None 

    context_enabled = False 
    
    def __init__(self, *args, **kwargs):

        # -- track IDs of formatters that have been color-wrapped to avoid double wrapping
        self._colorized_formatters = {}
        # -- track filepaths of applied configs to avoid losing post-apply changes to handlers and formatters
        self._applied_configs = []
        # -- cache configs loaded from disk to touch disk less 
        self._config_cache = {}
        
        self._forced_loggers = [] 

        # intlogger_level = logging.WARNING
        # if 'level' in kwargs:
        #     intlogger_level = kwargs['level']
        #     del kwargs['level']
        
        # -- set internal logger 
        self._intlogger = logging.getLogger('__cowpy__')

        LogColorer.getInstance(logger=self._intlogger)
        self._applyConfig(config=self._get_internal_config(level=logging.INFO), skip_colorization=True)

        for k in kwargs:
            try:
                self.__getattribute__(k)
                self.__setattr__(k, kwargs[k])
                self._log_debug(f'set Cowpy {k} -> {kwargs[k]}')
            except:
                print(f'Cowpy has no {k}')
                self._log_error(f'Cowpy has no {k}')
    
    def _get_internal_config(self, level=logging.WARNING):

        format_string = Format.DETAILED 
        if isinstance(format_string, Format):
            format_string = format_string.value 

        config = {
            'formatters': {
                'default': { 
                    'format': format_string
                },
            },
            'handlers': {
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': 'cowpy_internal.log',
                    'formatter': 'default',
                    'level': f'{logging._levelToName[level]}'
                },
            },
            'loggers': {    
                '__cowpy__': {
                    'handlers': ['file'],
                    'level': f'{logging._levelToName[level]}',            
                },
            }
        }
        
        return config 
    
    def _get_default_config(self, logger_name, level=logging.WARNING, format=Format.STANDARD, root_level=None):

        format_string = format 
        if isinstance(format_string, Format):
            format_string = format_string.value 

        config = {
            'formatters': {
                'default': { 
                    'format': format_string
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'default',
                    'level': f'{logging._levelToName[level]}'
                },
            },
            'loggers': {    
                f'{logger_name}': {
                    'handlers': ['console'],
                    'level': f'{logging._levelToName[level]}',            
                },
            }
        }

        if root_level:
            config['root'] = {
                'handlers': ['console'],
                'level': f'{logging._levelToName[root_level]}',
            }
        
        return config 

    def _getrc_path(self, calling_filename):
        '''Returns path of .cowpyrc in calling_filename parent folder hierarchy or DEFAULT_RC_PATH if none found'''
        self._log_internal_context('cowpy rc path')

        # -- realpath will resolve symlinked calling code 
        calling_folder = os.path.dirname(os.path.realpath(calling_filename))
        self._log_debug(f'looking for RC in {calling_folder} and parents')
        rc_folder = calling_folder 
        final_rc_path = os.path.join(rc_folder, '.cowpyrc')

        # -- follow parent folders all the way up, searching desperately for configuration
        while rc_folder != '/' and not os.path.exists(final_rc_path):
            self._log_debug(f'{rc_folder} / {final_rc_path}')
            rc_folder = os.path.realpath(os.path.join(rc_folder, os.pardir))
            final_rc_path = os.path.join(rc_folder, '.cowpyrc')

        # -- we already checked above, but double check 
        if os.path.exists(final_rc_path):
            self._log_debug(f'found RC: {calling_folder} -> {final_rc_path}')        
        else:
            self._log_debug(f'using default config, no RC found in {calling_folder}')            
            final_rc_path = None # DEFAULT_RC_PATH
        
        self._log_internal_context(None)

        return final_rc_path
    
    def _fix_config_formatters(self, config_dict, default_format=Format.STANDARD): 
        '''Ensures each handler has a present formatter, populating handler.formatter and formatters appropriately to do so'''
        
        formatters = config_dict['formatters'] if 'formatters' in config_dict else {}                        

        for handler_name in config_dict['handlers'].keys():
            handler = config_dict['handlers'][handler_name]

            fmt = default_format
            
            if 'format' in handler:                
                fmt = eval(handler['format'])
                self._log_info(f'handler {handler_name} has format attribute {handler["format"]}, will use {fmt}')
                del handler['format']
                if not isinstance(fmt, Format):
                    raise ValueError(f'{handler["format"]} is not a valid cowpy Format')
            else:
                self._log_info(f'handler {handler_name} has no format attribute, will use {fmt}')

            # if handler['class'] != 'logging.StreamHandler':
            #     continue 

            handler_formatter_name = formatter_name = fmt.name.lower()
            if 'formatter' in handler:
                handler_formatter_name = handler['formatter']
            else:
                self._log_info(f'handler {handler_name} has no formatter, setting to {formatter_name}')
                handler['formatter'] = formatter_name

            if formatter_name not in formatters:
                self._log_info(f'{handler_name} formatter {formatter_name} missing, adding it')
                formatters[formatter_name] = { 'format': fmt.value }
            else:
                self._log_debug(f'found formatter {formatters[formatter_name]} as {formatter_name} for handler {handler_name}')
            
        config_dict['formatters'] = formatters
        # return config_dict

    def _cache_config_from_path(self, rc_path):
        '''Assumes rc_path is set, returns parsed contents and None if parsing fails'''

        if rc_path not in self._config_cache:            
            self._log_debug(f'{rc_path} exists. Opening, reading, and evaluating..')
            with open(rc_path, 'r') as conf:
                try:
                    config_dict = ast.literal_eval(conf.read())
                    self._log_debug(json.dumps(config_dict, indent=4))                    
                    self._config_cache[rc_path] = config_dict
                except:
                    print(f'{sys.exc_info()[1]}')
                    self._log_error('exception')                    
                    
        return self._config_cache[rc_path]

    def _log_debug(self, msg):
        self._log_internal(level='debug', msg=msg, stacklevel=4)
        
    def _log_info(self, msg):
        self._log_internal(level='info', msg=msg, stacklevel=4)

    def _log_error(self, msg):
        self._log_internal(level='error', msg=msg, stacklevel=4)

    def _log_internal(self, level, msg, stacklevel=3): #, dont_call_get_logger_name=False):
        
        self._intlogger.log(level=logging._nameToLevel[level.upper()], msg=msg, stacklevel=stacklevel)
        
        # _local_logger = self._intlogger
        # if not _local_logger:
        #     if not self.tmp_name:
        #         self.tmp_name = self._get_logger_name() if not dont_call_get_logger_name else __name__
        #     _local_logger = logging.getLogger(self.tmp_name)
        
        # if isinstance(_local_logger, CowpyLogger) and level == 'exception':
        #     _local_logger.exception()
        # else:
        #     _local_logger.log(level=logging._nameToLevel[level.upper()], msg=msg, stacklevel=3)

    def _log_internal_context(self, context):
        if self._intlogger:
            self._intlogger.set_context(context)

    def _file_config(self):
        pass 
                
    def _get_logger_name(self, name=None, callingFrame=None):

        names = [__name__]

        if callingFrame:
            fn_name = callingFrame.function 
            mod_name = os.path.splitext(os.path.basename(callingFrame.filename))[0]
            names = [ n for n in [fn_name, mod_name] if n not in ['<module>', '__init__', None] ]
        else:
            for i, frame in enumerate(inspect.getouterframes(inspect.currentframe())):
                fn_name = frame.function 
                mod_name = os.path.splitext(os.path.basename(frame.filename))[0]
                names = [ n for n in [mod_name] if n not in ['<module>', '__init__', None] ]
                self._log_info(f'potential frame names [outer frame {i}]: {names}')
                if len(names) > 0:
                    break 
                self._log_debug(f'that someone is {frame} / {frame.filename}')
                self._log_debug(inspect.getmodulename(frame.filename))
                self._log_debug(f'{dir(callingFrame.frame)}')
                self._log_debug(f'{dir(callingFrame.frame.f_code)}')
                self._log_debug(f'{callingFrame.frame.f_code.co_names}')

        self._log_debug(f'have calling frame: {callingFrame.function}, fallback is {name}')
        # print(dir(callingFrame))        

        if name in ['<module>', '__init__', None] and len(names) > 0:
            self._log_debug(f'{name} logger name changing to {names[0]}')
            name = names[0]          

        return name 

    def _fix_config(self, config):
        '''Standardizes config. Ensures config has version=1, disable_existing_loggers=False, and propagate=False for each logger'''

        if 'version' not in config:
            config['version'] = 1

        if 'disable_existing_loggers' not in config:        
            config['disable_existing_loggers'] = False 

        if 'loggers' in config:
            for logger_name in config['loggers'].keys():
                if 'propagate' not in config['loggers'][logger_name]:
                    config['loggers'][logger_name]['propagate'] = False 
    
    def _scrape_config(self, config):
        
        if 'loggers' in config:

            for logger_name in self._forced_loggers:
                if logger_name in config['loggers']:
                    del config['loggers'][logger_name]

            self._forced_loggers.extend([ n for n 
                                         in config['loggers'].keys() 
                                         if 'force' in config['loggers'][n] 
                                         and config['loggers'][n]['force'].lower() in ['true'] 
                                        ])
            
    def _applyConfig(self, config, skip_colorization=False):
        '''Applies given config, after some custom tweaking, and before post-configuring its handlers' formatters'''

        self._fix_config(config) 
        self._scrape_config(config)
        self._fix_config_formatters(config)

        self._log_info(f'Calling dictConfig with')
        self._log_info(json.dumps(config, indent=4))
        # self._log_info(json.dumps(config, indent=4))
        
        dictConfig(config)    
        
        if not skip_colorization:

            logger_names = []
            if 'loggers' in config:
                logger_names = [ n for n in config['loggers'].keys() if n not in [''] ]
            
            if 'root' in config:
                logger_names.append('root')
                
            self._log_info(f'fixing {len(logger_names)} logger formatters: { ",".join(logger_names)}')
            LogColorer.getInstance().postConfigColorization(logger_names=logger_names, default_format=Format.STANDARD.value)

        self._log_debug(LogColorer.getInstance().get_configured_names())

    def checkAndApplyFromPath(self, rc_path):
        '''Given nothing, will find the caller's config and apply it if the found path hasn't been applied yet'''

        if rc_path: 
            if rc_path in self._applied_configs:
                self._log_info(f'{rc_path} already applied, will not apply again')
            else:
                self._log_info(f'{rc_path} not yet applied, validating and applying')
                config = self._cache_config_from_path(rc_path)
                self._applyConfig(config=config)
                self._applied_configs.append(rc_path)
                return True 

        return False 

    def checkAndApplyFromParams(self, name, level, format):

        if name in LogColorer.getInstance().get_configured_names():
            self._log_debug(f'logger {name} already configured')
        else:
            self._log_debug(f'logger {name} not yet configured, getting default at level {level} / format {format} (or defaults)')
            default_config_args = {
                'logger_name': name
            }
            if level:
                default_config_args.update({'level': level})
            if format:
                default_config_args.update({'format': format})
            config = self._get_default_config(**default_config_args)
            self._applyConfig(config=config)
            return True 

        return False             
    
    def getLogger(self, name=None, level=None, format=None, use_local_rc=True, auto_gen_config=True):

        # -- ensures level is logging numeral value
        if level and level not in logging._levelToName:
            if level.upper() in logging._nameToLevel:
                level = logging._nameToLevel[level.upper()]
            else:
                raise ValueError(f'{level} is not valid as a level. choose from {[ l for l in logging._levelToName.keys() ]}')

        '''
        
        FrameInfo(
            frame=<frame at 0x7f74a535f8a0, file '/media/floor/development/github.com/cowpy/src/cowpy/cowpy.py', line 463, code getLogger>, 
            filename='/media/floor/development/github.com/cowpy/src/cowpy/cowpy.py', 
            lineno=459, 
            function='getLogger', 
            code_context=['        outer_frames = inspect.getouterframes(current_frame)\n'], 
            index=0, 
            positions=Positions(lineno=459, end_lineno=459, col_offset=23, end_col_offset=60)
        ),
        
        FrameInfo(
            frame=<frame at 0x7f74a5774400, file '/media/floor/development/github.com/jroutes/src/jroutes/serving.py', line 155, code __init__>,        
            filename='/media/floor/development/github.com/jroutes/src/jroutes/serving.py', 
            lineno=155, 
            function='__init__', 
            code_context=["        self.logger = cowpy.getLogger('jroutes.serving')\n"], 
            index=0, 
            positions=Positions(lineno=155, end_lineno=155, col_offset=22, end_col_offset=56)
        ), 
        FrameInfo(
            frame=<frame at 0x7f74a5f6dc00, file '/media/floor/development/github.com/jroutes/src/jroutes/serve.py', line 60, code <module>>,        
            filename='/media/floor/development/github.com/jroutes/src/jroutes/serve.py', 
            lineno=60, 
            function='<module>', 
            code_context=['    japp = JroutesApplication(gunicorn_settings)\n'], 
            index=0, 
            positions=Positions(lineno=60, end_lineno=60, col_offset=11, end_col_offset=48)
        ), 
        FrameInfo(
            frame=<frame at 0x7f74a5f33760, file '<frozen runpy>', line 88, code _run_code>, 
            filename='<frozen runpy>', 
            lineno=88, 
            function='_run_code', 
            code_context=None, 
            index=None, 
            positions=Positions(lineno=88, end_lineno=88, col_offset=4, end_col_offset=27)
        ), 
        FrameInfo(
            frame=<frame at 0x7f74a5f86640, file '<frozen runpy>', line 198, code _run_module_as_main>, 
            filename='<frozen runpy>', 
            lineno=198, 
            function='_run_module_as_main', 
            code_context=None, 
            index=None, 
            positions=Positions(lineno=198, end_lineno=199, col_offset=11, end_col_offset=42)
        )        
        '''
        
        # self._log_info(f'getLogger current frame: {current_frame}')
        # self._log_info(f'getLogger outer frames: {json.dumps([ f"{f.filename}:{f.lineno}" for f in outer_frames ], indent=4)}')
        # self._log_info(f'getLogger calling frame: {callingFrame}')

        current_frame = inspect.currentframe()
        outer_frames = inspect.getouterframes(current_frame)
        us = outer_frames[0].filename 
        cursor = 0
        while us == outer_frames[cursor].filename:
            cursor += 1

        callingFrame = outer_frames[cursor]
        
        name = self._get_logger_name(name, callingFrame)
        self._log_internal_context(name)
        self._log_info(f'{name} is asking for a logger')

        rc_path = None 
        
        if use_local_rc:            
            rc_path = rc_path or self._getrc_path(calling_filename=callingFrame.filename)

        if not self.checkAndApplyFromPath(rc_path) and auto_gen_config:
            self.checkAndApplyFromParams(name, level, format)

        '''
        If our logger has been configured already, we would only want to reconfigure it if
        1. we're now asking for a different level or formatting
        And in that case, not a full reconfigure, but only get the existing logger
        and tweaking level or formatting to satisfy the request.
        Level is relatively straightforward.
        Formatting involves iterating over the handlers, checking the state of the formatter of each
        and changing if necessary - and probably only for StreamHandler.
        '''
            
        named_logger = logging.getLogger(name)

        self._log_internal_context('format-level-override')

        if level and named_logger.level != level:
            self._log_debug(f'logger {name} configured at {logging._levelToName[named_logger.level]}, requested {logging._levelToName[level]}')
            named_logger.setLevel(level)
        
        format_string = format 
        if isinstance(format_string, Format):
            self._log_debug(f'logger {name} fixing provided Format enum {format_string} to enum value {format_string.value}')
            format_string = format_string.value 

        named_logger = logging.getLogger(name)

        if format_string is not None:            
            for h in [ h for h in named_logger.handlers if isinstance(h, logging.StreamHandler) ]:
                self._log_debug(f'comparing named logger "{named_logger}" StreamHandler formatter {h.formatter._fmt} and provided formatter {format_string}')
                if h.formatter._fmt != format_string:
                    self._log_debug(f'Not a match, setting the handler formatter format to {format_string}')
                    h.formatter._fmt = format_string 
                else:
                    self._log_debug('match enough!')

        self._log_internal_context(None)
        
        self._log_debug(f'got {name} logger -- { logging._levelToName[named_logger.level] }-- {",".join([ h.__class__.__name__ + ":" + logging._levelToName[h.level] for h in named_logger.handlers ])}')
        return named_logger

if __name__ == "__main__":

    cs = Cowpy(level='debug')
    cs.checkAndApplyFromPath(rc_path=os.path.join(os.path.dirname(os.path.realpath(__file__)), '.cowpyrc'))
    
    testlogger = cs.getLogger('test')

    testlogger.warning('debug test logger -- warning')
    testlogger.success('debug test logger -- success')
    testlogger.error('debug test logger -- error')

    testlogger = cs.getLogger('test', level=logging.DEBUG)
    testlogger.warning('debug test logger -- warning')
    testlogger.success('debug test logger -- success')
    testlogger.error('debug test logger -- error')
    # againlogger = cs.getLogger('again', level='warning')
    # againlogger.warning('warning again logger -- warning')
    # againlogger.success('warning again logger -- success')
    # againlogger.error('warning again logger -- error')
    testlogger.warning('debug test logger -- warning')
    testlogger.success('debug test logger -- success')
    testlogger.error('debug test logger -- error')
