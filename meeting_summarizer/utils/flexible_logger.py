import os
import sys
from datetime import datetime
from typing import Union, TextIO, Optional
from config.settings import Settings
from pathlib import Path

class Logger:
    """
    A flexible logger that can write to both console and file with configurable options.
    
    Usage:
    1. Basic usage (like print):
        logger = Logger()
        logger.log("This is a log message")
   
    2. Configuring log levels and output:
        logger = Logger(
            log_file="app.log", 
            console_output=True, 
            file_output=True, 
            log_level="DEBUG"
        )
    """
    
    def __init__(
        self, 
        name: str = "app",  # Use name to distinguish different log files
        console_output: bool = True, 
        file_output: bool = False, 
        log_level: str = "INFO",
        log_format: str = "[{timestamp}] [{level}] {message}"
    ):
        """
        Initialize the Logger with various configuration options.
        
        :param name: Logger name, used as log file name (e.g., "proofreader" -> "proofreader.log")
        :param console_output: Whether to print logs to console
        :param file_output: Whether to write logs to file
        :param log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        :param log_format: Custom format for log messages
        """
        self.console_output = console_output
        self.file_output = file_output
        self.log_level = log_level.upper()
        self.log_format = log_format
        
        # Get config directory and create logs directory
        settings = Settings()
        self.log_dir = Path(settings.config_dir) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set log file path
        self.log_file = self.log_dir / f"{name}.log"
        
        # Log level hierarchy
        self.log_levels = {
            "DEBUG": 0,
            "INFO": 1,
            "WARNING": 2,
            "ERROR": 3,
            "CRITICAL": 4
        }
    
    def _format_message(self, message: str, level: str) -> str:
        """Format the log message with timestamp and level."""
        return self.log_format.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level=level,
            message=message
        )
    
    def log(
        self, 
        *messages: Union[str, object], 
        level: str = "INFO", 
        sep: str = " ", 
        end: str = "\n"
    ):
        """Log messages with flexibility similar to print()."""
        # Convert all messages to strings
        str_messages = [str(msg) for msg in messages]
        message = sep.join(str_messages)
        
        # Validate log level
        level = level.upper()
        if level not in self.log_levels:
            level = "INFO"
        
        # Check if message should be logged based on log level
        if self.log_levels.get(level, 1) >= self.log_levels.get(self.log_level, 1):
            formatted_message = self._format_message(message + end, level)
            
            # Console output
            if self.console_output:
                print(formatted_message, end='', file=sys.stderr)
            
            # File output
            if self.file_output:
                try:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write(formatted_message)
                except Exception as e:
                    print(f"Error writing to log file: {e}", file=sys.stderr)
    
    def debug(self, *messages: Union[str, object], sep: str = " ", end: str = "\n"):
        """Shortcut for logging debug messages"""
        self.log(*messages, level="DEBUG", sep=sep, end=end)
    
    def info(self, *messages: Union[str, object], sep: str = " ", end: str = "\n"):
        """Shortcut for logging info messages"""
        self.log(*messages, level="INFO", sep=sep, end=end)
    
    def warning(self, *messages: Union[str, object], sep: str = " ", end: str = "\n"):
        """Shortcut for logging warning messages"""
        self.log(*messages, level="WARNING", sep=sep, end=end)
    
    def error(self, *messages: Union[str, object], sep: str = " ", end: str = "\n"):
        """Shortcut for logging error messages"""
        self.log(*messages, level="ERROR", sep=sep, end=end)
    
    def critical(self, *messages: Union[str, object], sep: str = " ", end: str = "\n"):
        """Shortcut for logging critical messages"""
        self.log(*messages, level="CRITICAL", sep=sep, end=end)

# Usage examples
if __name__ == "__main__":
    # Console output example
    logger1 = Logger(name="test1", console_output=True, log_level="DEBUG")
    logger1.debug("This is a debug message")
    logger1.info("This is an info message")
    
    # File output example
    logger2 = Logger(name="test2", console_output=False, file_output=True)
    logger2.warning("This is a warning message")
    logger2.error("This is an error message")
    
    # Output to both console and file
    logger3 = Logger(name="test3", console_output=True, file_output=True)
    logger3.critical("This is a critical error")
