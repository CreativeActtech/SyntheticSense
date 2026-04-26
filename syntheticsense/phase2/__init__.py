"""
SyntheticSense - Phase 2: Hardware Integration & Optimization
=============================================================

This module provides enhanced hardware integration for Raspberry Pi 5,
including Sony IMX500 AI camera support, GPU acceleration, and advanced
haptic feedback patterns.

Key Features:
- Sony IMX500 SDK integration (placeholder for actual SDK)
- RPi5 GPU-accelerated inference
- Advanced haptic patterns for Braille communication
- Real-time performance monitoring
- Thermal-aware processing
"""

__version__ = "2.0.0"
__author__ = "SyntheticSense Team"

from .camera.imx500_camera import IMX500Camera
from .haptic.advanced_controller import AdvancedHapticController
from .optimization.performance_monitor import PerformanceMonitor
from .optimization.gpu_accelerator import GPUAccelerator
from .tests.integration_tests import IntegrationTestSuite

__all__ = [
    'IMX500Camera',
    'AdvancedHapticController',
    'PerformanceMonitor',
    'GPUAccelerator',
    'IntegrationTestSuite',
]
