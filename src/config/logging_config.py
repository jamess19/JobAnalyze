"""
Logging Configuration
Cấu hình logging cho crawler module
"""

import os
import logging
from datetime import datetime


def setup_logging(log_level='INFO', log_to_file=True, log_to_console=True):
    """
    Setup logging configuration
    
    :param log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :param log_to_file: Enable file logging
    :param log_to_console: Enable console logging
    :return: Log file path
    """
    # Create logs directory
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'scrapy_{timestamp}.log')
    
    # Configure logging format
    log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Setup handlers
    handlers = []
    
    if log_to_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)
    
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(console_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    return log_file


def get_scrapy_log_settings():
    """
    Get Scrapy-specific log settings
    
    :return: Dictionary of Scrapy log settings
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return {
        'LOG_LEVEL': 'INFO',
        'LOG_FORMAT': '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        'LOG_DATEFORMAT': '%Y-%m-%d %H:%M:%S',
        'LOG_STDOUT': True,
        'LOG_FILE': f'logs/scrapy_{timestamp}.log',
        'LOG_FILE_APPEND': False,
        'LOG_ENCODING': 'utf-8',
    }


def cleanup_old_logs(days=7):
    """
    Clean up log files older than specified days
    
    :param days: Number of days to keep logs
    """
    import time
    
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (days * 86400)  # days * seconds_per_day
    
    removed_count = 0
    for filename in os.listdir(log_dir):
        if filename.endswith('.log'):
            filepath = os.path.join(log_dir, filename)
            file_modified = os.path.getmtime(filepath)
            
            if file_modified < cutoff_time:
                try:
                    os.remove(filepath)
                    removed_count += 1
                    print(f"Removed old log file: {filename}")
                except Exception as e:
                    print(f"Error removing {filename}: {e}")
    
    if removed_count > 0:
        print(f"Cleaned up {removed_count} old log file(s)")
    else:
        print("No old log files to clean up")

