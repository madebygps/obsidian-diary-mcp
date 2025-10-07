"""Logging configuration for the Obsidian Diary MCP server."""

import logging
from pathlib import Path
from datetime import datetime

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

DEBUG_LOG_FILE = LOGS_DIR / f"debug-{datetime.now().strftime('%Y-%m-%d')}.log"


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger that writes to a debug file."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.FileHandler(DEBUG_LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    logger.propagate = False
    
    return logger


template_logger = setup_logger('template')
analysis_logger = setup_logger('analysis')
ollama_logger = setup_logger('ollama')
server_logger = setup_logger('server')


def log_section(logger: logging.Logger, title: str):
    """Log a section header."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  {title}")
    logger.info(f"{'='*60}")
