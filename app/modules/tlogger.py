import logging
import os, sys
# from pythonjsonlogger import jsonlogger
from functools import wraps
from io import StringIO

COLOUR_FORMATTER = os.environ.get('COLOUR_FORMATTER', False)

# Be sure this is set to False/Commented out before you deploy to AWS!
# COLOUR_FORMATTER = True

CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0


def newobj(method):
    @wraps(method)
    # Well, newobj can be decorated with function, but we will cover the case
    # where it decorated with method
    def inner(self, *args, **kwargs):
        obj = self.__class__.__new__(self.__class__)
        obj.__dict__ = self.__dict__.copy()
        method(obj, *args, **kwargs)
        return obj

    return inner


class TLogger():
    """
    TLogger : Wrapper class for Standard Python logger with some presets
                to help down on code duplication and enforce project wide standards

    Parameters:
        name        : Name of the Logger
        infoLevel   : logging level of the Logger (e.g. logging.DEBUG/INFO/WARNING/ERROR)
        fileHandler : string file path to the file handler log file (e.g. /logs/xyz.log)
    """

    def __init__(self, name: str, infoLevel=logging.INFO, fileHandler=None):
        try:
            if name is None:
                raise ValueError("Name argument not specified")

            logformat = '%(asctime)s %(levelname)s [%(name)s %(funcName)s] %(message)s'
            self.logformat = logformat
            self.name = name.upper()
            self.logger = logging.getLogger(self.name)
            self.logger.setLevel(infoLevel)

            self.add_consolehandler(infoLevel, logformat)

            if fileHandler is not None:
                fh = logging.FileHandler(fileHandler)
                fh.setLevel(infoLevel)
                fh.setFormatter(logging.Formatter(logformat))
                self.logger.addHandler(fh)

        except Exception as e:
            if self.logger:
                self.logger.error(str(e))

    def error(self, message):
        self.logger.error(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def debug(self, message):
        self.logger.debug(message)

    def critical(self, message):
        self.logger.critical(message, stack_info=True, exc_info=True)

    def setLevel(self, infoLevel):
        # Python's standard Logging has lots of design issues, especially with its API and expected behaviours
        # To dynamically reset the loglevel, you need to also change the parent levels as well as all handlers!
        self.logger.parent.setLevel(infoLevel)
        for handler in self.logger.parent.handlers:
            handler.setLevel(infoLevel)

        self.logger.setLevel(infoLevel)
        for handler in self.logger.handlers:
            handler.setLevel(infoLevel)

        return self.logger.level

    @newobj
    def add_consolehandler(self, infoLevel=logging.INFO,
                           logformat='%(asctime)s %(levelname)s [%(name)s %(funcName)s] %(message)s'):
        sh = logging.StreamHandler()
        sh.setLevel(infoLevel)

        formatter = ColourFormatter(logformat) if COLOUR_FORMATTER else logging.Formatter(logformat)
        sh.setFormatter(formatter)
        self.logger.addHandler(sh)

    @newobj
    def add_filehandler(self, fileHandlerPath, infoLevel=logging.INFO,
                        logformat='%(asctime)s %(levelname)s [%(name)s %(funcName)s] %(message)s'):
        fh = logging.FileHandler(fileHandlerPath)
        fh.setLevel(infoLevel)
        fh.setFormatter(logging.Formatter(logformat))
        self.logger.addHandler(fh)

    @newobj
    def add_jsonhandler(self, infoLevel=logging.INFO,
                        logformat='%(asctime)s %(levelname)s %(name)s %(funcName)s %(message)s'):
        # from pythonjsonlogger import jsonlogger

        jsonlog_handler = logging.StreamHandler()
        # json_formatter = jsonlogger.JsonFormatter(logformat, reserved_attrs=RESERVED_ATTRS)
        json_formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "funcname": "%(funcName)s", "message": "%(message)s"}')
        jsonlog_handler.setFormatter(json_formatter)
        jsonlog_handler.setLevel(infoLevel)
        self.logger.addHandler(jsonlog_handler)

    @newobj
    def add_jsonfilehandler(self, fileHandlerPath, infoLevel=logging.INFO,
                            logformat='%(asctime)s %(levelname)s %(name)s %(funcName)s %(message)s'):
        # from pythonjsonlogger import jsonlogger

        # 'asctime','levelname', 'name', 'funcName', message

        RESERVED_ATTRS = (
            'args',  'created', 'exc_info', 'exc_text', 'filename',
            'levelno', 'lineno', 'module', 'msecs', 'msg',  'pathname', 'process',
            'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName')

        jsonlog_handler = logging.FileHandler(fileHandlerPath)
        # json_formatter = jsonlogger.JsonFormatter(logformat, reserved_attrs=RESERVED_ATTRS)
        json_formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "funcname": "%(funcName)s", "message": "%(message)s"}')
        jsonlog_handler.setFormatter(json_formatter)
        jsonlog_handler.setLevel(infoLevel)
        self.logger.addHandler(jsonlog_handler)

    def list_loggers(self):
        """https://stackoverflow.com/a/60988312/1622880"""
        rootlogger = self.logger
        print(rootlogger)
        for h in rootlogger.handlers:
            print('     %s' % h)

        for nm, lgr in logging.Logger.manager.loggerDict.items():
            print('+ [%-20s] %s ' % (nm, lgr))
            if not isinstance(lgr, logging.PlaceHolder):
                for h in lgr.handlers:
                    print('     %s' % h)

    '''https://stackoverflow.com/questions/31999627/storing-logger-messages-in-a-string'''
    @newobj
    def add_stringiohandler(self, infoLevel=logging.INFO):
        stringio_stream = StringIO()
        self.add_consolehandler(stream=stringio_stream)


class ColourFormatter(logging.Formatter):

    def __init__(self, logformat="%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"):
        grey = "\x1b[38;21m"
        green = "\x1b[32;21m"
        yellow = "\x1b[33;21m"
        red = "\x1b[31;21m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"

        self.FORMATS = {
            logging.DEBUG: grey + logformat + reset,
            logging.INFO: green + logformat + reset,
            logging.WARNING: yellow + logformat + reset,
            logging.ERROR: red + logformat + reset,
            logging.CRITICAL: bold_red + logformat + reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
