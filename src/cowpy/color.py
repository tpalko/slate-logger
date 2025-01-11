import logging 
from cowpy.common import handler

FOREGROUND_COLOR_PREFIX = '\033[38;2;'
FOREGROUND_COLOR_SUFFIX = 'm'
FOREGROUND_COLOR_RESET = '\033[0m'

class LogColorer(object):

    # -- track configured named loggers to avoid losing changes to handlers and formatters
    _configured_names = None 
    _logger = None 
    __instance__ = None 

    @staticmethod
    def getInstance(**kwargs):
        LogColorer(**kwargs)
        return LogColorer.__instance__

    def __init__(self, *args, **kwargs):

        if not self.__instance__:
            self._configured_names = {}
            if 'logger' in kwargs:
                self._logger = kwargs['logger']
            LogColorer.__instance__ = self 

    def _colorFormatter(self, fmt):
        return logging.Formatter(fmt = f'{FOREGROUND_COLOR_PREFIX}%(color)s{FOREGROUND_COLOR_SUFFIX}{fmt}{FOREGROUND_COLOR_RESET}')

    def get_configured_names(self):
        return self._configured_names
    
    def _is_formatter_colorized(self, logger_name, formatter):
        return logger_name in self._configured_names and id(formatter) in self._configured_names[logger_name]['formatter_ids']

    def _file_colorized_formatter(self, logger_name, formatter):
        if not self._is_formatter_colorized(logger_name, formatter):
            self._configured_names[logger_name] = { 'formatter_ids': [id(formatter)] }

    def postConfigColorization(self, logger_names, default_format):
        '''
            ensures the logger's existing handlers' formatters' format strings are color-wrapped
            existing handlers have such a formatter
            or the logger has at least one handler with such a formatter
        '''        

        for logger_name in logger_names:

            logger = logging.getLogger(logger_name)

            if len(logger.handlers) == 0:
                self._logger.debug(f'{logger_name} logger has no handlers, adding a default')
                new_default_formatter = self._colorFormatter(fmt=default_format)
                logger.addHandler(handler(formatter=new_default_formatter))      
                self._file_colorized_formatter(logger_name, new_default_formatter)

            for h in logger.handlers:
                if h.formatter:
                    # self._logger.debug(dir(h.formatter))
                    if self._is_formatter_colorized(logger_name, h.formatter):
                        self._logger.debug(f'{logger_name} logger {h.__class__.__name__} {h.name} formatter filed as colorized')
                    else:
                        self._logger.debug(f'{logger_name} logger {h.__class__.__name__} {h.name} formatter not filed as colorized, replacing now')
                        colorized_formatter = self._colorFormatter(fmt=h.formatter._fmt)
                        h.setFormatter(colorized_formatter)
                        self._file_colorized_formatter(logger_name, colorized_formatter)
                else:
                    self._logger.debug(f'{logger_name} logger adding default colorized formatter to {h.__class__.__name__} {h.name}')
                    new_default_formatter = self._colorFormatter(fmt=default_format)                    
                    h.setFormatter(new_default_formatter)               
                    self._file_colorized_formatter(logger_name, new_default_formatter)