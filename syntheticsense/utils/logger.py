"""
Logging utility for SyntheticSense.

Provides centralized logging configuration with file and console output.
Optimized for Raspberry Pi 5 with log rotation and thermal monitoring.
"""

import logging
import os
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str,
    level: str = "INFO",
    log_dir: str = "/var/log/syntheticsense",
    enable_file: bool = True,
    enable_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Setup and configure a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_file: Enable file logging
        enable_console: Enable console logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    if enable_file:
        try:
            # Ensure log directory exists
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"{name.replace('.', '_')}.log")
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}", file=sys.stderr)
            enable_file = False
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_system_logger(level: str = "INFO") -> logging.Logger:
    """
    Get the main system logger.
    
    Args:
        level: Logging level
        
    Returns:
        Configured system logger
    """
    return setup_logger("syntheticsense", level=level)


def log_system_info(logger: logging.Logger) -> None:
    """
    Log system information for debugging.
    
    Args:
        logger: Logger instance
    """
    import platform
    import psutil
    
    try:
        logger.info("=" * 60)
        logger.info("System Information")
        logger.info("=" * 60)
        logger.info(f"Platform: {platform.platform()}")
        logger.info(f"Python: {platform.python_version()}")
        logger.info(f"Machine: {platform.machine()}")
        logger.info(f"Processor: {platform.processor()}")
        
        # CPU info
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        logger.info(f"CPU Count: {cpu_count}")
        if cpu_freq:
            logger.info(f"CPU Frequency: {cpu_freq.current:.2f} MHz")
        
        # Memory info
        memory = psutil.virtual_memory()
        logger.info(f"Memory Total: {memory.total / (1024**3):.2f} GB")
        logger.info(f"Memory Available: {memory.available / (1024**3):.2f} GB")
        
        # Disk info
        disk = psutil.disk_usage('/')
        logger.info(f"Disk Total: {disk.total / (1024**3):.2f} GB")
        logger.info(f"Disk Free: {disk.free / (1024**3):.2f} GB")
        
        logger.info("=" * 60)
        
    except ImportError:
        logger.warning("psutil not available - skipping system info")
    except Exception as e:
        logger.error(f"Error logging system info: {e}")


class ThermalMonitor:
    """
    Monitor Raspberry Pi temperature and log warnings.
    
    Optimized for Raspberry Pi 5 thermal management.
    """
    
    def __init__(self, logger: logging.Logger, max_temp: float = 80.0):
        """
        Initialize thermal monitor.
        
        Args:
            logger: Logger instance
            max_temp: Maximum safe temperature in Celsius
        """
        self.logger = logger
        self.max_temp = max_temp
        self.last_temp = 0.0
    
    def get_temperature(self) -> float:
        """
        Get current CPU temperature.
        
        Returns:
            Temperature in Celsius, or 0.0 if unavailable
        """
        try:
            # Try RPi-specific methods first
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
                    self.last_temp = temp
                    return temp
            
            # Fallback to psutil
            import psutil
            sensors = psutil.sensors_temperatures()
            if 'cpu_thermal' in sensors:
                temp = sensors['cpu_thermal'][0].current
                self.last_temp = temp
                return temp
            
        except Exception as e:
            self.logger.debug(f"Could not read temperature: {e}")
        
        return 0.0
    
    def check_temperature(self) -> bool:
        """
        Check temperature and log warning if too high.
        
        Returns:
            True if temperature is safe, False if throttling recommended
        """
        temp = self.get_temperature()
        
        if temp > 0:
            if temp >= self.max_temp:
                self.logger.warning(
                    f"High temperature detected: {temp:.1f}°C "
                    f"(threshold: {self.max_temp}°C)"
                )
                return False
            elif temp >= self.max_temp - 10:
                self.logger.info(f"Temperature elevated: {temp:.1f}°C")
        
        return True
    
    def log_temperature(self) -> None:
        """Log current temperature."""
        temp = self.get_temperature()
        if temp > 0:
            self.logger.debug(f"Current temperature: {temp:.1f}°C")
