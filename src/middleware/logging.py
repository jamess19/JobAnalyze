import logging
import sys
from logging.handlers import RotatingFileHandler

class LoggerSetup:
    """Cấu hình logging cho ứng dụng"""
    
    @staticmethod
    def setup_logger(name, log_file='app.log', level=logging.INFO):
        """
        Tạo logger với cấu hình hoàn chỉnh
        
        Args:
            name: Tên của logger
            log_file: Đường dẫn file log
            level: Mức độ logging
            
        Returns:
            logger: Logger đã được cấu hình
        """
        # Tạo logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Tránh duplicate handlers
        if logger.handlers:
            return logger
        
        # Format cho log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console Handler - hiển thị trên terminal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        
        # File Handler với rotation (tự động rotate khi file đạt size)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,  # Giữ 5 file backup
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Error File Handler - riêng cho errors
        error_handler = RotatingFileHandler(
            'error.log',
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Thêm handlers vào logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        
        return logger
