import logging
import json
import threading
from datetime import datetime
from typing import Optional
import sys

class CorrelationContext:
    _local = threading.local()
    
    @classmethod
    def get_id(cls) -> Optional[str]:
        return getattr(cls._local, 'correlation_id', None)
        
    @classmethod
    def set_id(cls, correlation_id: str):
        cls._local.correlation_id = correlation_id
        
    @classmethod
    def clear(cls):
        if hasattr(cls._local, 'correlation_id'):
            del cls._local.correlation_id

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            "correlation_id": CorrelationContext.get_id()
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

class ColorFormatter(logging.Formatter):
    COLORS = {
        'WARNING': '\033[93m',
        'INFO': '\033[92m',
        'DEBUG': '\033[94m',
        'CRITICAL': '\033[91m',
        'ERROR': '\033[91m'
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET
        record.msg = f"{color}{record.msg}{reset}"
        return super().format(record)

def setup_logger(name: str, log_file: Optional[str] = None, level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
            
    return logger

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
