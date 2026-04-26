"""
Settings configuration for SyntheticSense.

This module handles all configuration parameters for the system,
optimized for Raspberry Pi 5 (8GB RAM).
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
import json


@dataclass
class CameraSettings:
    """Camera configuration settings."""
    
    # Camera selection
    use_imx500: bool = False  # Set True if using Sony IMX500 AI camera
    camera_id: int = 0  # Default camera device ID
    
    # Detection settings
    model_type: str = "mobilenet-ssd"  # Options: 'yolov8-nano', 'mobilenet-ssd'
    confidence_threshold: float = 0.6
    detection_interval: float = 0.1  # seconds between detections
    
    # Image processing
    frame_width: int = 640
    frame_height: int = 480
    fps: int = 30
    
    # Object classes to detect
    detect_classes: List[str] = field(default_factory=lambda: [
        "person", "chair", "couch", "potted plant", "bed",
        "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "book", "scissors", "dog", "cat", "bird",
        "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie",
        "suitcase", "frisbee", "skis", "snowboard", "sports ball",
        "kite", "baseball bat", "baseball glove", "skateboard",
        "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple",
        "sandwich", "orange", "broccoli", "carrot", "hot dog",
        "pizza", "donut", "cake", "chair", "car", "motorcycle",
        "airplane", "bus", "train", "truck", "boat", "traffic light",
        "fire hydrant", "stop sign", "parking meter", "bench"
    ])


@dataclass
class HapticSettings:
    """Haptic feedback configuration settings."""
    
    # GPIO configuration (BCM numbering)
    motor_pins: List[int] = field(default_factory=lambda: [
        17, 27, 22,  # Left side motors
        5, 6, 13,    # Center motors
        19, 26, 16   # Right side motors
    ])
    
    # Motor control
    pwm_frequency: int = 1000  # Hz
    default_duty_cycle: float = 0.7  # 70% power
    min_pulse_duration: float = 0.1  # seconds
    max_pulse_duration: float = 0.5  # seconds
    
    # Directional mapping
    left_motors: List[int] = field(default_factory=lambda: [0, 1, 2])
    center_motors: List[int] = field(default_factory=lambda: [3, 4, 5])
    right_motors: List[int] = field(default_factory=lambda: [6, 7, 8])
    
    # Safety
    max_continuous_runtime: float = 2.0  # seconds before cooldown
    cooldown_period: float = 0.5  # seconds


@dataclass
class CommunicationSettings:
    """MQTT communication settings."""
    
    # MQTT broker
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Topics
    topic_prefix: str = "syntheticsense"
    obstacle_topic: str = "obstacles"
    message_topic: str = "messages"
    status_topic: str = "status"
    
    # QoS and reliability
    qos: int = 1  # Quality of Service level (0, 1, or 2)
    retain: bool = False
    keepalive: int = 60  # seconds
    
    # Client ID
    client_id: Optional[str] = None  # Auto-generated if None


@dataclass
class BrailleSettings:
    """Braille encoding settings."""
    
    # Dot positions (standard 6-dot Braille)
    dot_positions: List[tuple] = field(default_factory=lambda: [
        (0, 0),  # Dot 1
        (0, 1),  # Dot 2
        (0, 2),  # Dot 3
        (1, 0),  # Dot 4
        (1, 1),  # Dot 5
        (1, 2),  # Dot 6
    ])
    
    # Timing
    character_duration: float = 0.3  # seconds per character
    word_pause: float = 0.5  # seconds between words
    letter_pause: float = 0.1  # seconds between letters
    
    # Motor mapping for Braille display
    braille_motor_map: List[int] = field(default_factory=lambda: list(range(6)))


@dataclass
class SystemSettings:
    """System-wide settings."""
    
    # Performance
    debug_mode: bool = True
    log_level: str = "INFO"
    enable_logging: bool = True
    
    # Power management
    power_save_mode: bool = False
    auto_shutdown_idle: float = 300.0  # seconds of idle before shutdown
    
    # Thermal management (RPi5 specific)
    thermal_throttling: bool = True
    max_temperature: float = 80.0  # Celsius
    
    # Paths
    log_dir: str = "/var/log/syntheticsense"
    config_dir: str = "/etc/syntheticsense"
    data_dir: str = "/home/pi/syntheticsense_data"


@dataclass
class Settings:
    """Main settings container for SyntheticSense."""
    
    camera: CameraSettings = field(default_factory=CameraSettings)
    haptic: HapticSettings = field(default_factory=HapticSettings)
    communication: CommunicationSettings = field(default_factory=CommunicationSettings)
    braille: BrailleSettings = field(default_factory=BrailleSettings)
    system: SystemSettings = field(default_factory=SystemSettings)
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "camera": self.camera.__dict__,
            "haptic": self.haptic.__dict__,
            "communication": self.communication.__dict__,
            "braille": self.braille.__dict__,
            "system": self.system.__dict__,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert settings to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create Settings from dictionary."""
        settings = cls()
        
        if "camera" in data:
            for key, value in data["camera"].items():
                if hasattr(settings.camera, key):
                    setattr(settings.camera, key, value)
        
        if "haptic" in data:
            for key, value in data["haptic"].items():
                if hasattr(settings.haptic, key):
                    setattr(settings.haptic, key, value)
        
        if "communication" in data:
            for key, value in data["communication"].items():
                if hasattr(settings.communication, key):
                    setattr(settings.communication, key, value)
        
        if "braille" in data:
            for key, value in data["braille"].items():
                if hasattr(settings.braille, key):
                    setattr(settings.braille, key, value)
        
        if "system" in data:
            for key, value in data["system"].items():
                if hasattr(settings.system, key):
                    setattr(settings.system, key, value)
        
        return settings
    
    @classmethod
    def from_json(cls, json_str: str) -> "Settings":
        """Create Settings from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, filepath: str) -> "Settings":
        """Load settings from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def save_to_file(self, filepath: str) -> None:
        """Save settings to JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> List[str]:
        """
        Validate settings and return list of warnings/errors.
        
        Returns:
            List of warning messages (empty if all valid)
        """
        warnings = []
        
        # Validate camera settings
        if self.camera.confidence_threshold < 0 or self.camera.confidence_threshold > 1:
            warnings.append("Camera confidence threshold must be between 0 and 1")
        
        if self.camera.fps <= 0:
            warnings.append("Camera FPS must be positive")
        
        # Validate haptic settings
        if self.haptic.pwm_frequency <= 0:
            warnings.append("PWM frequency must be positive")
        
        if self.haptic.default_duty_cycle < 0 or self.haptic.default_duty_cycle > 1:
            warnings.append("Duty cycle must be between 0 and 1")
        
        # Validate communication settings
        if self.communication.qos not in [0, 1, 2]:
            warnings.append("MQTT QoS must be 0, 1, or 2")
        
        if self.communication.broker_port <= 0 or self.communication.broker_port > 65535:
            warnings.append("Invalid MQTT broker port")
        
        # Validate system settings
        if self.system.max_temperature < 0 or self.system.max_temperature > 100:
            warnings.append("Max temperature must be between 0 and 100 Celsius")
        
        return warnings
