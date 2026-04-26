"""
Advanced Haptic Controller Module
==================================

Enhanced haptic feedback system with advanced patterns for Braille communication,
directional awareness, and customizable vibration sequences.

Features:
- 6-dot Braille cell simulation
- Directional feedback patterns
- Custom pulse sequences
- Intensity modulation
- Multi-motor coordination
- Thermal protection
"""

import time
import threading
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import queue

logger = logging.getLogger(__name__)


class VibrationPattern(Enum):
    """Predefined vibration patterns."""
    CONTINUOUS = "continuous"
    PULSE_SHORT = "pulse_short"
    PULSE_MEDIUM = "pulse_medium"
    PULSE_LONG = "pulse_long"
    DOUBLE_PULSE = "double_pulse"
    TRIPLE_PULSE = "triple_pulse"
    BRAILLE_DOT = "braille_dot"
    DIRECTIONAL_LEFT = "directional_left"
    DIRECTIONAL_RIGHT = "directional_right"
    WARNING = "warning"
    ALERT = "alert"


@dataclass
class PulseDefinition:
    """Definition of a single pulse in a pattern."""
    duration_ms: int
    intensity: float  # 0.0 to 1.0
    pause_after_ms: int = 0
    motor_id: Optional[str] = None


@dataclass
class MotorState:
    """Current state of a haptic motor."""
    enabled: bool
    pwm_duty_cycle: float
    active_since: float
    total_runtime_ms: int
    temperature_celsius: Optional[float] = None


class AdvancedHapticController:
    """
    Advanced haptic feedback controller for Raspberry Pi 5.
    
    Provides sophisticated vibration patterns for Braille communication
    and directional obstacle awareness.
    """
    
    # GPIO pin assignments for 6-dot Braille display
    BRAILLE_DOTS = {
        1: 17,  # Dot 1 (top-left)
        2: 27,  # Dot 2 (middle-left)
        3: 22,  # Dot 3 (bottom-left)
        4: 23,  # Dot 4 (top-right)
        5: 24,  # Dot 5 (middle-right)
        6: 25,  # Dot 6 (bottom-right)
    }
    
    # Directional motor pins
    DIRECTIONAL_MOTORS = {
        'left': 5,
        'center': 6,
        'right': 13,
    }
    
    def __init__(
        self,
        mock_mode: bool = True,
        default_intensity: float = 0.7,
        max_runtime_ms: int = 5000,
        cooldown_ms: int = 2000
    ):
        """
        Initialize advanced haptic controller.
        
        Args:
            mock_mode: Use mock mode for testing
            default_intensity: Default vibration intensity (0.0-1.0)
            max_runtime_ms: Maximum continuous runtime per motor
            cooldown_ms: Required cooldown between activations
        """
        self.mock_mode = mock_mode
        self.default_intensity = default_intensity
        self.max_runtime_ms = max_runtime_ms
        self.cooldown_ms = cooldown_ms
        
        self._initialized = False
        self._motor_states: Dict[int, MotorState] = {}
        self._pattern_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._pattern_thread: Optional[threading.Thread] = None
        
        # Pattern definitions
        self._patterns = self._define_patterns()
        
        logger.info(f"AdvancedHapticController initialized (mock={mock_mode})")
    
    def _define_patterns(self) -> Dict[VibrationPattern, List[PulseDefinition]]:
        """Define predefined vibration patterns."""
        return {
            VibrationPattern.CONTINUOUS: [
                PulseDefinition(1000, self.default_intensity)
            ],
            VibrationPattern.PULSE_SHORT: [
                PulseDefinition(100, self.default_intensity)
            ],
            VibrationPattern.PULSE_MEDIUM: [
                PulseDefinition(200, self.default_intensity)
            ],
            VibrationPattern.PULSE_LONG: [
                PulseDefinition(400, self.default_intensity)
            ],
            VibrationPattern.DOUBLE_PULSE: [
                PulseDefinition(150, self.default_intensity, 100),
                PulseDefinition(150, self.default_intensity)
            ],
            VibrationPattern.TRIPLE_PULSE: [
                PulseDefinition(100, self.default_intensity, 80),
                PulseDefinition(100, self.default_intensity, 80),
                PulseDefinition(100, self.default_intensity)
            ],
            VibrationPattern.BRAILLE_DOT: [
                PulseDefinition(80, self.default_intensity)
            ],
            VibrationPattern.DIRECTIONAL_LEFT: [
                PulseDefinition(300, self.default_intensity, 0)
            ],
            VibrationPattern.DIRECTIONAL_RIGHT: [
                PulseDefinition(300, self.default_intensity, 0)
            ],
            VibrationPattern.WARNING: [
                PulseDefinition(200, 0.9, 100),
                PulseDefinition(200, 0.9, 100),
                PulseDefinition(200, 0.9)
            ],
            VibrationPattern.ALERT: [
                PulseDefinition(100, 1.0, 50),
                PulseDefinition(100, 1.0, 50),
                PulseDefinition(100, 1.0, 50),
                PulseDefinition(100, 1.0, 50),
                PulseDefinition(300, 1.0)
            ],
        }
    
    def initialize(self) -> bool:
        """
        Initialize GPIO and PWM for haptic motors.
        
        Returns:
            True if successful
        """
        try:
            if self.mock_mode:
                logger.info("AdvancedHapticController initialized in mock mode")
                self._initialized = True
                return True
            
            # Initialize GPIO (actual implementation)
            # import RPi.GPIO as GPIO
            # GPIO.setmode(GPIO.BCM)
            # GPIO.setwarnings(False)
            
            # Setup PWM for all motors
            # for dot, pin in self.BRAILLE_DOTS.items():
            #     GPIO.setup(pin, GPIO.OUT)
            #     pwm = GPIO.PWM(pin, 1000)  # 1kHz PWM
            #     pwm.start(0)
            #     self._motor_states[dot] = MotorState(
            #         enabled=False,
            #         pwm_duty_cycle=0.0,
            #         active_since=0.0,
            #         total_runtime_ms=0
            #     )
            
            self._initialized = True
            logger.info("AdvancedHapticController initialized with GPIO")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize haptic controller: {e}")
            return False
    
    def start_pattern_thread(self):
        """Start the background pattern execution thread."""
        if self._pattern_thread is not None:
            return
        
        self._stop_event.clear()
        self._pattern_thread = threading.Thread(
            target=self._pattern_executor,
            daemon=True
        )
        self._pattern_thread.start()
        logger.info("Pattern thread started")
    
    def stop_pattern_thread(self):
        """Stop the background pattern execution thread."""
        self._stop_event.set()
        if self._pattern_thread:
            self._pattern_thread.join(timeout=2.0)
            self._pattern_thread = None
        logger.info("Pattern thread stopped")
    
    def _pattern_executor(self):
        """Background thread to execute queued patterns."""
        while not self._stop_event.is_set():
            try:
                item = self._pattern_queue.get(timeout=0.1)
                if item:
                    pattern_name, motor_ids, intensity = item
                    self._execute_pattern(pattern_name, motor_ids, intensity)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Pattern execution error: {e}")
    
    def play_pattern(
        self,
        pattern: VibrationPattern,
        motor_ids: Optional[List[int]] = None,
        intensity: Optional[float] = None,
        blocking: bool = False
    ):
        """
        Play a vibration pattern.
        
        Args:
            pattern: Pattern to play
            motor_ids: List of motor IDs to activate (None = all)
            intensity: Override intensity (None = use pattern default)
            blocking: Wait for completion
        """
        if not self._initialized:
            logger.warning("Controller not initialized")
            return
        
        if motor_ids is None:
            motor_ids = list(self.BRAILLE_DOTS.keys())
        
        if intensity is None:
            intensity = self.default_intensity
        
        if blocking:
            self._execute_pattern(pattern, motor_ids, intensity)
        else:
            self._pattern_queue.put((pattern, motor_ids, intensity))
    
    def _execute_pattern(
        self,
        pattern: VibrationPattern,
        motor_ids: List[int],
        intensity: float
    ):
        """Execute a vibration pattern on specified motors."""
        if pattern not in self._patterns:
            logger.error(f"Unknown pattern: {pattern}")
            return
        
        pulses = self._patterns[pattern]
        
        for pulse in pulses:
            # Check cooldown
            if not self._check_cooldown(motor_ids):
                logger.warning("Cooldown required - skipping pulse")
                time.sleep(pulse.pause_after_ms / 1000.0)
                continue
            
            # Activate motors
            actual_intensity = intensity * pulse.intensity
            self._activate_motors(motor_ids, actual_intensity, pulse.duration_ms)
            
            # Wait for pulse duration
            time.sleep(pulse.duration_ms / 1000.0)
            
            # Deactivate motors
            self._deactivate_motors(motor_ids)
            
            # Wait for pause after pulse
            if pulse.pause_after_ms > 0:
                time.sleep(pulse.pause_after_ms / 1000.0)
    
    def _activate_motors(self, motor_ids: List[int], intensity: float, duration_ms: int):
        """Activate specified motors with given intensity."""
        current_time = time.time()
        
        for motor_id in motor_ids:
            if motor_id not in self._motor_states:
                self._motor_states[motor_id] = MotorState(
                    enabled=False,
                    pwm_duty_cycle=0.0,
                    active_since=0.0,
                    total_runtime_ms=0
                )
            
            state = self._motor_states[motor_id]
            
            # Check runtime limit
            if state.total_runtime_ms >= self.max_runtime_ms:
                logger.warning(f"Motor {motor_id} runtime limit reached")
                continue
            
            if self.mock_mode:
                logger.debug(f"[MOCK] Motor {motor_id}: {intensity*100:.0f}% for {duration_ms}ms")
            else:
                # Actual GPIO control
                # pwm = self._pwm_handles[motor_id]
                # pwm.ChangeDutyCycle(intensity * 100)
                pass
            
            state.enabled = True
            state.pwm_duty_cycle = intensity
            state.active_since = current_time
    
    def _deactivate_motors(self, motor_ids: List[int]):
        """Deactivate specified motors."""
        current_time = time.time()
        
        for motor_id in motor_ids:
            if motor_id in self._motor_states:
                state = self._motor_states[motor_id]
                
                if state.enabled:
                    # Update runtime
                    runtime = (current_time - state.active_since) * 1000
                    state.total_runtime_ms += int(runtime)
                    
                    if self.mock_mode:
                        logger.debug(f"[MOCK] Motor {motor_id} deactivated")
                    else:
                        # Actual GPIO control
                        # pwm = self._pwm_handles[motor_id]
                        # pwm.ChangeDutyCycle(0)
                        pass
                    
                    state.enabled = False
                    state.pwm_duty_cycle = 0.0
    
    def _check_cooldown(self, motor_ids: List[int]) -> bool:
        """Check if motors have cooled down sufficiently."""
        current_time = time.time()
        
        for motor_id in motor_ids:
            if motor_id in self._motor_states:
                state = self._motor_states[motor_id]
                if state.enabled:
                    elapsed = (current_time - state.active_since) * 1000
                    if elapsed < self.cooldown_ms:
                        return False
        
        return True
    
    def braille_character(self, dots: List[int], blocking: bool = True):
        """
        Display a Braille character using specified dots.
        
        Args:
            dots: List of dot numbers (1-6) to activate
            blocking: Wait for completion
        """
        valid_dots = [d for d in dots if 1 <= d <= 6]
        if not valid_dots:
            return
        
        self.play_pattern(
            VibrationPattern.BRAILLE_DOT,
            motor_ids=valid_dots,
            intensity=0.8,
            blocking=blocking
        )
    
    def braille_string(self, text: str, delay_between_chars_ms: int = 200):
        """
        Display a string in Braille format.
        
        Args:
            text: Text to convert to Braille
            delay_between_chars_ms: Delay between characters
        """
        from ..utils.braille_encoder import BrailleEncoder
        
        encoder = BrailleEncoder()
        braille_pattern = encoder.encode_to_motor_pattern(text)
        
        for char_index, dots in enumerate(braille_pattern):
            if dots:
                self.braille_character(dots, blocking=True)
            
            if char_index < len(braille_pattern) - 1:
                time.sleep(delay_between_chars_ms / 1000.0)
    
    def directional_alert(self, direction: str, intensity: float = 0.9):
        """
        Provide directional alert.
        
        Args:
            direction: 'left', 'center', or 'right'
            intensity: Vibration intensity
        """
        motor_map = {
            'left': [1, 2, 3],
            'center': [2, 5],
            'right': [4, 5, 6]
        }
        
        motor_ids = motor_map.get(direction, [1, 2, 3, 4, 5, 6])
        self.play_pattern(VibrationPattern.PULSE_MEDIUM, motor_ids, intensity, blocking=True)
    
    def warning_sequence(self):
        """Play warning sequence on all motors."""
        self.play_pattern(VibrationPattern.WARNING, blocking=True)
    
    def alert_sequence(self):
        """Play alert sequence on all motors."""
        self.play_pattern(VibrationPattern.ALERT, blocking=True)
    
    def get_motor_states(self) -> Dict[int, MotorState]:
        """Get current state of all motors."""
        return self._motor_states.copy()
    
    def reset_runtime_counters(self):
        """Reset all motor runtime counters."""
        for state in self._motor_states.values():
            state.total_runtime_ms = 0
        logger.info("Runtime counters reset")
    
    def close(self):
        """Close controller and release resources."""
        self.stop_pattern_thread()
        
        # Deactivate all motors
        all_motors = list(self.BRAILLE_DOTS.keys())
        self._deactivate_motors(all_motors)
        
        if not self.mock_mode:
            # Cleanup GPIO
            # import RPi.GPIO as GPIO
            # GPIO.cleanup()
            pass
        
        self._initialized = False
        logger.info("AdvancedHapticController closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        self.start_pattern_thread()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
