"""
Haptic controller module for vibration motor control.

Provides directional haptic feedback and Braille pattern generation
optimized for Raspberry Pi 5 GPIO control.
"""

import logging
from typing import List, Dict, Optional, Any
from enum import Enum
import time
import threading

logger = logging.getLogger(__name__)


class Direction(Enum):
    """Directional positions for haptic feedback."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    ALL = "all"


class HapticController:
    """
    Haptic controller for managing vibration motors.
    
    This class controls an array of vibration motors to provide
    directional feedback and Braille communication patterns.
    Optimized for Raspberry Pi 5 GPIO with PWM support.
    """
    
    def __init__(self, config=None):
        """
        Initialize the haptic controller.
        
        Args:
            config: HapticSettings object or None to use defaults
        """
        from ..config.settings import Settings
        
        self.config = config or Settings().haptic
        self.motor_pins = self.config.motor_pins
        self.is_initialized = False
        self.pwm_objects = {}
        
        # State tracking
        self.active_motors = set()
        self.last_activation_time = {}
        self.runtime_tracker = {}
        
        # Thread safety
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        logger.info(f"HapticController initialized with {len(self.motor_pins)} motors")
    
    def initialize(self) -> bool:
        """
        Initialize GPIO and PWM for motor control.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._setup_gpio()
            self._setup_pwm()
            self.is_initialized = True
            
            logger.info("Haptic controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize haptic controller: {e}")
            return False
    
    def _setup_gpio(self) -> None:
        """Setup GPIO pins for motor control."""
        try:
            import RPi.GPIO as GPIO
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup all motor pins as output
            for pin in self.motor_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            logger.info(f"GPIO setup complete for {len(self.motor_pins)} pins")
            
        except ImportError:
            logger.warning("RPi.GPIO not available - using mock mode")
            self._mock_gpio_setup()
        except Exception as e:
            logger.error(f"GPIO setup failed: {e}")
            raise
    
    def _mock_gpio_setup(self) -> None:
        """Mock GPIO setup for testing without hardware."""
        logger.info("Mock GPIO setup - no hardware control")
        # In mock mode, we just track state without actual GPIO
    
    def _setup_pwm(self) -> None:
        """Setup PWM for motor speed control."""
        try:
            import RPi.GPIO as GPIO
            
            # Create PWM objects for each motor
            for i, pin in enumerate(self.motor_pins):
                pwm = GPIO.PWM(pin, self.config.pwm_frequency)
                pwm.start(0)  # Start at 0% duty cycle
                self.pwm_objects[i] = pwm
            
            logger.info(f"PWM setup complete at {self.config.pwm_frequency}Hz")
            
        except ImportError:
            logger.warning("PWM not available - using mock mode")
            self._mock_pwm_setup()
        except Exception as e:
            logger.error(f"PWM setup failed: {e}")
            raise
    
    def _mock_pwm_setup(self) -> None:
        """Mock PWM setup for testing."""
        logger.info("Mock PWM setup - simulating motor control")
        # Track PWM state in software
        for i in range(len(self.motor_pins)):
            self.pwm_objects[i] = {"duty_cycle": 0, "running": False}
    
    def activate_motor(self, motor_index: int, duration: float = None, 
                      duty_cycle: float = None) -> bool:
        """
        Activate a specific vibration motor.
        
        Args:
            motor_index: Index of motor to activate (0 to n-1)
            duration: Duration in seconds (None for continuous)
            duty_cycle: PWM duty cycle (0.0 to 1.0), uses default if None
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized:
            logger.warning("Haptic controller not initialized")
            return False
        
        if motor_index < 0 or motor_index >= len(self.motor_pins):
            logger.error(f"Invalid motor index: {motor_index}")
            return False
        
        with self._lock:
            try:
                dc = duty_cycle if duty_cycle is not None else self.config.default_duty_cycle
                dc_percent = min(100.0, max(0.0, dc * 100))
                
                # Check runtime limits
                current_time = time.time()
                if motor_index in self.runtime_tracker:
                    start_time = self.runtime_tracker[motor_index]
                    elapsed = current_time - start_time
                    
                    if elapsed >= self.config.max_continuous_runtime:
                        logger.warning(f"Motor {motor_index} reached max runtime, applying cooldown")
                        self.deactivate_motor(motor_index)
                        time.sleep(self.config.cooldown_period)
                
                # Activate motor
                if isinstance(self.pwm_objects[motor_index], dict):
                    # Mock mode
                    self.pwm_objects[motor_index]["duty_cycle"] = dc_percent
                    self.pwm_objects[motor_index]["running"] = True
                else:
                    # Real GPIO
                    import RPi.GPIO as GPIO
                    self.pwm_objects[motor_index].ChangeDutyCycle(dc_percent)
                
                self.active_motors.add(motor_index)
                self.last_activation_time[motor_index] = current_time
                
                if motor_index not in self.runtime_tracker:
                    self.runtime_tracker[motor_index] = current_time
                
                logger.debug(f"Motor {motor_index} activated at {dc_percent}% duty cycle")
                
                # Handle timed activation
                if duration is not None:
                    self._schedule_deactivation(motor_index, duration)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to activate motor {motor_index}: {e}")
                return False
    
    def deactivate_motor(self, motor_index: int) -> bool:
        """
        Deactivate a specific vibration motor.
        
        Args:
            motor_index: Index of motor to deactivate
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized:
            return False
        
        if motor_index < 0 or motor_index >= len(self.motor_pins):
            return False
        
        with self._lock:
            try:
                if isinstance(self.pwm_objects[motor_index], dict):
                    # Mock mode
                    self.pwm_objects[motor_index]["duty_cycle"] = 0
                    self.pwm_objects[motor_index]["running"] = False
                else:
                    # Real GPIO
                    self.pwm_objects[motor_index].ChangeDutyCycle(0)
                
                self.active_motors.discard(motor_index)
                self.runtime_tracker.pop(motor_index, None)
                
                logger.debug(f"Motor {motor_index} deactivated")
                return True
                
            except Exception as e:
                logger.error(f"Failed to deactivate motor {motor_index}: {e}")
                return False
    
    def _schedule_deactivation(self, motor_index: int, duration: float) -> None:
        """Schedule motor deactivation after specified duration."""
        def deactivate():
            time.sleep(duration)
            if not self._stop_event.is_set():
                self.deactivate_motor(motor_index)
        
        thread = threading.Thread(target=deactivate, daemon=True)
        thread.start()
    
    def activate_direction(self, direction: Direction, duration: float = 0.3,
                          duty_cycle: float = None) -> bool:
        """
        Activate motors for a specific direction.
        
        Args:
            direction: Direction (LEFT, CENTER, RIGHT, ALL)
            duration: Activation duration in seconds
            duty_cycle: PWM duty cycle
            
        Returns:
            True if successful
        """
        motor_indices = []
        
        if direction == Direction.LEFT:
            motor_indices = self.config.left_motors
        elif direction == Direction.CENTER:
            motor_indices = self.config.center_motors
        elif direction == Direction.RIGHT:
            motor_indices = self.config.right_motors
        elif direction == Direction.ALL:
            motor_indices = list(range(len(self.motor_pins)))
        
        success = True
        for idx in motor_indices:
            if idx < len(self.motor_pins):
                if not self.activate_motor(idx, duration=duration, duty_cycle=duty_cycle):
                    success = False
        
        return success
    
    def alert_obstacle(self, position: str, intensity: float = 1.0) -> bool:
        """
        Generate haptic alert for obstacle detection.
        
        Args:
            position: Obstacle position ('left', 'center', 'right')
            intensity: Alert intensity (0.0 to 1.0)
            
        Returns:
            True if alert generated successfully
        """
        direction_map = {
            "left": Direction.LEFT,
            "center": Direction.CENTER,
            "right": Direction.RIGHT
        }
        
        direction = direction_map.get(position.lower(), Direction.CENTER)
        
        # Pulse pattern for attention
        duty_cycle = min(1.0, max(0.0, self.config.default_duty_cycle * intensity))
        
        # Double pulse pattern
        for _ in range(2):
            self.activate_direction(direction, duration=0.15, duty_cycle=duty_cycle)
            time.sleep(0.2)
        
        return True
    
    def pulse_pattern(self, motor_indices: List[int], pattern: List[float], 
                     repetitions: int = 1) -> bool:
        """
        Execute a custom pulse pattern on specified motors.
        
        Args:
            motor_indices: List of motor indices to activate
            pattern: List of durations [on_time, off_time, on_time, off_time, ...]
            repetitions: Number of times to repeat pattern
            
        Returns:
            True if pattern executed successfully
        """
        for rep in range(repetitions):
            for i, duration in enumerate(pattern):
                if i % 2 == 0:  # ON phase
                    for idx in motor_indices:
                        self.activate_motor(idx, duration=duration)
                else:  # OFF phase
                    time.sleep(duration)
                
                if self._stop_event.is_set():
                    return False
        
        return True
    
    def stop_all(self) -> None:
        """Stop all active motors immediately."""
        with self._lock:
            for motor_index in list(self.active_motors):
                self.deactivate_motor(motor_index)
        
        logger.info("All motors stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current haptic controller status."""
        return {
            "is_initialized": self.is_initialized,
            "active_motors": list(self.active_motors),
            "total_motors": len(self.motor_pins),
            "pwm_frequency": self.config.pwm_frequency,
            "default_duty_cycle": self.config.default_duty_cycle,
        }
    
    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        self._stop_event.set()
        self.stop_all()
        
        try:
            import RPi.GPIO as GPIO
            
            # Stop all PWM
            for pwm in self.pwm_objects.values():
                if not isinstance(pwm, dict):
                    pwm.stop()
            
            GPIO.cleanup()
            logger.info("GPIO cleanup complete")
            
        except ImportError:
            logger.info("Mock mode - no GPIO cleanup needed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        self.is_initialized = False
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
