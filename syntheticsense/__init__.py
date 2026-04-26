"""
SyntheticSense - Open-Source Assistive Technology for the Deaf-Blind Community

This package provides real-time obstacle detection and haptic Braille communication
optimized for Raspberry Pi 5 hardware.
"""

__version__ = "0.1.0"
__author__ = "Julian Anival Gonzalez"
__license__ = "Apache 2.0"

from .config.settings import Settings
from .camera.detector import CameraModule
from .haptic.controller import HapticController
from .communication.mqtt_client import MQTTClient
from .utils.braille_encoder import BrailleEncoder

__all__ = [
    "Settings",
    "CameraModule",
    "HapticController",
    "MQTTClient",
    "BrailleEncoder",
]
