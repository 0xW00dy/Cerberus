import logging
from rich.logging import RichHandler

logging.SUCCESS = 25
logging.addLevelName(logging.SUCCESS, 'SUCCESS')
setattr(logging, 'success', lambda message, *args: logging.root._log(logging.SUCCESS, message, args))

class LogFormatter(logging.Formatter):
    def __init__(self, fmt='%(message)s'):
        logging.Formatter.__init__(self, fmt)
    
