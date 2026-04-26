"""
Performance Monitoring Module
==============================

Real-time performance monitoring for Raspberry Pi 5, including:
- CPU utilization tracking
- Memory usage monitoring
- Thermal management
- Frame rate analysis
- Latency measurement
- Power consumption estimates

Optimized for RPi5's quad-core Cortex-A76 architecture.
"""

import time
import threading
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import deque
import os

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Current performance metrics."""
    timestamp: float
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    temperature_celsius: float = 0.0
    fps: float = 0.0
    detection_latency_ms: float = 0.0
    haptic_latency_ms: float = 0.0
    thermal_throttled: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_mb': self.memory_used_mb,
            'memory_total_mb': self.memory_total_mb,
            'temperature_celsius': self.temperature_celsius,
            'fps': self.fps,
            'detection_latency_ms': self.detection_latency_ms,
            'haptic_latency_ms': self.haptic_latency_ms,
            'thermal_throttled': self.thermal_throttled
        }


class PerformanceMonitor:
    """
    Real-time performance monitor for Raspberry Pi 5.
    
    Provides comprehensive system monitoring including CPU, memory,
    thermal, and application-specific metrics.
    """
    
    # Thermal thresholds for RPi5 (in Celsius)
    TEMP_WARNING = 70.0
    TEMP_CRITICAL = 80.0
    TEMP_THROTTLE = 85.0
    
    def __init__(
        self,
        sample_interval_s: float = 1.0,
        history_size: int = 60
    ):
        """
        Initialize performance monitor.
        
        Args:
            sample_interval_s: Interval between samples in seconds
            history_size: Number of samples to keep in history
        """
        self.sample_interval_s = sample_interval_s
        self.history_size = history_size
        
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._metrics_history: deque = deque(maxlen=history_size)
        self._current_metrics = PerformanceMetrics(timestamp=time.time())
        
        # Timing trackers
        self._frame_times: deque = deque(maxlen=30)
        self._detection_latencies: deque = deque(maxlen=30)
        self._haptic_latencies: deque = deque(maxlen=30)
        
        # RPi5 specific info
        self._total_memory_mb = self._get_total_memory()
        
        logger.info(f"PerformanceMonitor initialized (interval={sample_interval_s}s)")
    
    def _get_total_memory(self) -> float:
        """Get total system memory in MB."""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        # Convert from kB to MB
                        return float(line.split()[1]) / 1024.0
        except Exception as e:
            logger.warning(f"Could not read memory info: {e}")
        return 8192.0  # Default to 8GB for RPi5
    
    def _get_cpu_percent(self) -> float:
        """Get CPU utilization percentage."""
        try:
            # Read CPU stats from /proc/stat
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                parts = line.split()
                if parts[0] == 'cpu':
                    # Calculate CPU usage
                    idle = float(parts[4])
                    total = sum(float(x) for x in parts[1:8])
                    
                    if hasattr(self, '_prev_idle') and hasattr(self, '_prev_total'):
                        idle_delta = idle - self._prev_idle
                        total_delta = total - self._prev_total
                        
                        if total_delta > 0:
                            cpu_percent = (1.0 - (idle_delta / total_delta)) * 100.0
                            self._prev_idle = idle
                            self._prev_total = total
                            return max(0.0, min(100.0, cpu_percent))
                    
                    self._prev_idle = idle
                    self._prev_total = total
                    
        except Exception as e:
            logger.debug(f"Could not read CPU stats: {e}")
        
        return 0.0
    
    def _get_memory_info(self) -> tuple:
        """Get memory usage information."""
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_info = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = float(parts[1].strip().split()[0])  # in kB
                        mem_info[key] = value
                
                total = mem_info.get('MemTotal', 0) / 1024.0  # MB
                available = mem_info.get('MemAvailable', 0) / 1024.0  # MB
                used = total - available
                
                percent = (used / total * 100.0) if total > 0 else 0.0
                
                return percent, used, total
                
        except Exception as e:
            logger.debug(f"Could not read memory info: {e}")
            return 0.0, 0.0, self._total_memory_mb
    
    def _get_temperature(self) -> float:
        """Get CPU temperature in Celsius."""
        try:
            # Try thermal zone first
            for tz in ['/sys/class/thermal/thermal_zone0/temp',
                      '/sys/class/hwmon/hwmon0/temp1_input']:
                if os.path.exists(tz):
                    with open(tz, 'r') as f:
                        temp = float(f.read().strip()) / 1000.0
                        return temp
            
            # Fallback: try vcgencmd
            import subprocess
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if result.returncode == 0:
                # Parse "temp=45.6'C"
                output = result.stdout.strip()
                if '=' in output:
                    temp_str = output.split('=')[1].replace("'C", "")
                    return float(temp_str)
                    
        except Exception as e:
            logger.debug(f"Could not read temperature: {e}")
        
        return 25.0  # Default ambient temperature
    
    def _check_thermal_throttle(self) -> bool:
        """Check if system is thermally throttled."""
        try:
            import subprocess
            result = subprocess.run(
                ['vcgencmd', 'get_throttled'],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if result.returncode == 0:
                # Parse throttle status
                output = result.stdout.strip()
                if '=' in output:
                    throttle_val = int(output.split('=')[1], 16)
                    # Bit 0-2 indicate current throttling
                    return (throttle_val & 0x7) != 0
        except Exception:
            pass
        
        # Fallback: check temperature
        return self._current_metrics.temperature_celsius >= self.TEMP_THROTTLE
    
    def start(self):
        """Start the monitoring thread."""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("PerformanceMonitor started")
    
    def stop(self):
        """Stop the monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
        logger.info("PerformanceMonitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                self._update_metrics()
                time.sleep(self.sample_interval_s)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
    
    def _update_metrics(self):
        """Update current metrics."""
        timestamp = time.time()
        
        cpu_percent = self._get_cpu_percent()
        mem_percent, mem_used, mem_total = self._get_memory_info()
        temperature = self._get_temperature()
        thermal_throttled = self._check_thermal_throttle()
        
        # Calculate FPS from frame times
        fps = 0.0
        if len(self._frame_times) > 1:
            avg_frame_time = sum(self._frame_times) / len(self._frame_times)
            if avg_frame_time > 0:
                fps = 1.0 / avg_frame_time
        
        # Average latencies
        detection_latency = (
            sum(self._detection_latencies) / len(self._detection_latencies)
            if self._detection_latencies else 0.0
        )
        haptic_latency = (
            sum(self._haptic_latencies) / len(self._haptic_latencies)
            if self._haptic_latencies else 0.0
        )
        
        self._current_metrics = PerformanceMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=mem_percent,
            memory_used_mb=mem_used,
            memory_total_mb=mem_total,
            temperature_celsius=temperature,
            fps=fps,
            detection_latency_ms=detection_latency,
            haptic_latency_ms=haptic_latency,
            thermal_throttled=thermal_throttled
        )
        
        self._metrics_history.append(self._current_metrics)
        
        # Log warnings
        if temperature >= self.TEMP_WARNING:
            logger.warning(f"High temperature: {temperature:.1f}°C")
        if temperature >= self.TEMP_CRITICAL:
            logger.critical(f"Critical temperature: {temperature:.1f}°C")
        if thermal_throttled:
            logger.warning("System is thermally throttled")
    
    def record_frame_time(self, duration_s: float):
        """Record frame processing time."""
        self._frame_times.append(duration_s)
    
    def record_detection_latency(self, latency_ms: float):
        """Record detection latency."""
        self._detection_latencies.append(latency_ms)
    
    def record_haptic_latency(self, latency_ms: float):
        """Record haptic response latency."""
        self._haptic_latencies.append(latency_ms)
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self._current_metrics
    
    def get_metrics_history(self) -> List[PerformanceMetrics]:
        """Get metrics history."""
        return list(self._metrics_history)
    
    def get_average_fps(self, window_s: float = 5.0) -> float:
        """Get average FPS over time window."""
        if not self._frame_times:
            return 0.0
        
        recent = list(self._frame_times)[-int(window_s * 10):]  # Assume ~10 FPS max
        if not recent:
            return 0.0
        
        avg_time = sum(recent) / len(recent)
        return 1.0 / avg_time if avg_time > 0 else 0.0
    
    def get_average_temperature(self, window_s: float = 10.0) -> float:
        """Get average temperature over time window."""
        samples = int(window_s / self.sample_interval_s)
        recent = list(self._metrics_history)[-samples:]
        
        if not recent:
            return self._current_metrics.temperature_celsius
        
        return sum(m.temperature_celsius for m in recent) / len(recent)
    
    def is_thermal_safe(self) -> bool:
        """Check if temperature is within safe limits."""
        return self._current_metrics.temperature_celsius < self.TEMP_WARNING
    
    def get_summary(self) -> str:
        """Get human-readable performance summary."""
        m = self._current_metrics
        return (
            f"Performance Summary:\n"
            f"  CPU: {m.cpu_percent:.1f}%\n"
            f"  Memory: {m.memory_used_mb:.0f}/{m.memory_total_mb:.0f} MB ({m.memory_percent:.1f}%)\n"
            f"  Temperature: {m.temperature_celsius:.1f}°C\n"
            f"  FPS: {m.fps:.1f}\n"
            f"  Detection Latency: {m.detection_latency_ms:.1f}ms\n"
            f"  Haptic Latency: {m.haptic_latency_ms:.1f}ms\n"
            f"  Thermal Throttled: {m.thermal_throttled}"
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
