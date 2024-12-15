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
        name: str = "app",  # 使用名称来区分不同的日志文件
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
        
        # 获取配置目录并创建日志目录
        settings = Settings()
        self.log_dir = Path(settings.config_dir) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志文件路径
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

# 示例使用
if __name__ == "__main__":
    # 控制台输出示例
    logger1 = Logger(name="test1", console_output=True, log_level="DEBUG")
    logger1.debug("这是一个调试信息")
    logger1.info("这是一个普通信息")
    
    # 文件输出示例
    logger2 = Logger(name="test2", console_output=False, file_output=True)
    logger2.warning("这是一个警告信息")
    logger2.error("这是一个错误信息")
    
    # 同时输出到控制台和文件
    logger3 = Logger(name="test3", console_output=True, file_output=True)
    logger3.critical("这是一个关键错误")
