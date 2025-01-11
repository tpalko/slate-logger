from enum import Enum 
import logging 
import traceback 
import sys 

COLUMN_WIDTH = 224

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

FORMAT_TABLE_PADDING = {
    'standard': 8 + 15 + 23 + 12 + 3 + 9 + 5,
    'user': 0,
    'detailed': 67
}

LEVEL_COLORS = {
    'DEBUG': Color.DARKGRAY,
    'INFO': Color.WHITE,
    'WARN': Color.ORANGE,
    'WARNING': Color.ORANGE,
    'SUCCESS': Color.GREEN,
    'ERROR': Color.RED,
    'CRITICAL': Color.DARKRED
}
logging.addLevelName(25, 'SUCCESS')

LEVEL_COLORS = { logging._nameToLevel[k]: LEVEL_COLORS[k] for k in LEVEL_COLORS.keys() }

class CowpyLogger(logging.Logger):

    context = None 

    def _chunk_msg(self, msg):
        str_msg = str(msg)
        chunked = ""
        '''
[  DEBUG] 2024-11-27 08:17:58,405  database.py:463  database [ - ] <-- 67
        '''
        padding = "".join([ ' ' for x in range(FORMAT_TABLE_PADDING['detailed']) ])
        line_width = COLUMN_WIDTH - len(padding)
        cursor = 0
        while len(str_msg[cursor:]) > 0:
            
            next_break = str_msg[cursor:].find('\n')
            # - new line not found in the next line of the log message itself 
            if (next_break < 0 or next_break > line_width):
                # - new line found after this line, so it's not relevant here
                if len(str_msg[cursor:]) > line_width:
                    next_break = line_width
                # - no new line found at all
                else:
                    next_break = len(str_msg[cursor:])
            
            this_line = str_msg[cursor:cursor+next_break]
            
            if len(str_msg) > cursor+next_break:
                while str_msg[cursor+next_break] not in ['\n', ' ']:
                    next_break -= 1
                this_line = str_msg[cursor:cursor+next_break]

            chunked += f'{this_line}' #.lstrip(" ")}'
            cursor += len(f'{this_line}')
            if len(str_msg[cursor:]) > 0:
                if str_msg[cursor] != '\n':
                    chunked += '\n'
                else:
                    chunked += '\n'
                    cursor += 1
                chunked += padding
        return chunked

    # -- overriding base 
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=2):

        if level not in LEVEL_COLORS:
            raise NotImplementedError(f'There is no {level} in LEVEL_COLORS. Go ahead and check it.')

        extra = extra or {}

        extra.update({ 
            'color': LEVEL_COLORS[level].value,
            'context': f'[{self.context[0:3] if self.context else " - "}]'
        })
        
        super(CowpyLogger, self)._log(level, self._chunk_msg(msg), args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)
    
    def warn(self, msg):
        super(CowpyLogger, self).warning(msg)
    
    def success(self, msg):
        self._log(level=logging._nameToLevel['SUCCESS'], msg=msg, args=None, stacklevel=3)

    def error(self, msg):
        self._log(level=logging.ERROR, msg=msg, args=None, stacklevel=4)

    def clear_context(self):
        self.context = None 
        
    def set_context(self, context):
        self.context = context 
    
    def exception(self):
        stack_summary = traceback.extract_tb(sys.exc_info()[2])
        tabs = "" #\t\t\t\t"
        summary_format = stack_summary.format()        
        error_header = f'{sys.exc_info()[0].__name__}: {sys.exc_info()[1]}'
        full_error_text = f'{error_header}\n{tabs}{tabs.join(summary_format)}'
        self.error(full_error_text)
        return error_header
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

logging.setLoggerClass(CowpyLogger)