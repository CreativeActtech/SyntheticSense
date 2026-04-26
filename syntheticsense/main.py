"""
Main application module for SyntheticSense.

Integrates all components into a cohesive system for real-time
obstacle detection and haptic communication.
"""

import logging
import time
import signal
import sys
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .config.settings import Settings
from .camera.detector import CameraModule, Detection
from .haptic.controller import HapticController, Direction
from .communication.mqtt_client import MQTTClient
from .utils.braille_encoder import BrailleEncoder
from .utils.logger import setup_logger, ThermalMonitor


logger = logging.getLogger(__name__)


class SystemState(Enum):
    """System operational states."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class SystemStatus:
    """Current system status information."""
    state: SystemState
    uptime: float
    detections_count: int
    messages_sent: int
    temperature: float
    errors: list


class SyntheticSenseApp:
    """
    Main application class for SyntheticSense.
    
    This class orchestrates all system components:
    - Camera module for object detection
    - Haptic controller for feedback
    - MQTT client for communication
    - Braille encoder for messaging
    
    Optimized for Raspberry Pi 5 with thermal management
    and power efficiency.
    """
    
    def __init__(self, config: Optional[Settings] = None):
        """
        Initialize the SyntheticSense application.
        
        Args:
            config: Settings object or None to use defaults
        """
        self.config = config or Settings()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.camera: Optional[CameraModule] = None
        self.haptic: Optional[HapticController] = None
        self.mqtt: Optional[MQTTClient] = None
        self.braille: Optional[BrailleEncoder] = None
        
        # System state
        self.state = SystemState.INITIALIZING
        self.start_time = 0
        self.detections_count = 0
        self.messages_sent = 0
        self.error_log = []
        
        # Thermal monitoring
        self.thermal_monitor: Optional[ThermalMonitor] = None
        
        # Control flags
        self._stop_requested = False
        self._pause_requested = False
        
        logger.info("SyntheticSenseApp initialized")
    
    def _setup_logging(self) -> None:
        """Setup application logging."""
        log_level = self.config.system.log_level
        log_dir = self.config.system.log_dir if self.config.system.enable_logging else None
        
        global logger
        logger = setup_logger(
            name="syntheticsense.app",
            level=log_level,
            log_dir=log_dir if log_dir else "/tmp/syntheticsense",
            enable_file=self.config.system.enable_logging,
        )
    
    def initialize(self) -> bool:
        """
        Initialize all system components.
        
        Returns:
            True if all components initialized successfully
        """
        logger.info("Initializing SyntheticSense system...")
        
        try:
            # Initialize camera
            logger.info("Initializing camera module...")
            self.camera = CameraModule(self.config.camera)
            if not self.camera.initialize():
                logger.error("Failed to initialize camera module")
                return False
            
            # Initialize haptic controller
            logger.info("Initializing haptic controller...")
            self.haptic = HapticController(self.config.haptic)
            if not self.haptic.initialize():
                logger.error("Failed to initialize haptic controller")
                return False
            
            # Initialize MQTT client
            logger.info("Initializing MQTT client...")
            self.mqtt = MQTTClient(self.config.communication)
            if not self.mqtt.connect():
                logger.warning("MQTT connection failed - continuing in offline mode")
            
            # Initialize Braille encoder
            logger.info("Initializing Braille encoder...")
            self.braille = BrailleEncoder(self.config.braille)
            
            # Setup thermal monitoring
            if self.config.system.thermal_throttling:
                self.thermal_monitor = ThermalMonitor(
                    logger,
                    max_temp=self.config.system.max_temperature
                )
            
            # Record start time
            self.start_time = time.time()
            self.state = SystemState.RUNNING
            
            logger.info("SyntheticSense system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self.state = SystemState.ERROR
            self.error_log.append(str(e))
            return False
    
    def run(self) -> None:
        """
        Run the main application loop.
        
        This method starts the detection and feedback cycle,
        processing camera input and generating haptic alerts.
        """
        logger.info("Starting main application loop...")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            while not self._stop_requested:
                # Check for pause
                if self._pause_requested:
                    time.sleep(0.1)
                    continue
                
                # Check thermal status
                if self.thermal_monitor and not self.thermal_monitor.check_temperature():
                    logger.warning("Thermal throttling active - reducing detection rate")
                    time.sleep(0.5)
                
                # Run detection cycle
                self._detection_cycle()
                
                # Small delay to prevent CPU overload
                time.sleep(self.config.camera.detection_interval)
            
            logger.info("Main loop exited")
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.error_log.append(str(e))
            self.state = SystemState.ERROR
        
        finally:
            self.stop()
    
    def _detection_cycle(self) -> None:
        """Execute one detection and feedback cycle."""
        if not self.camera or not self.haptic:
            return
        
        # Detect objects
        detections = self.camera.detect_objects()
        
        if detections:
            self.detections_count += len(detections)
            
            # Group by position
            positions = self.camera.get_detections_by_position(detections)
            
            # Generate haptic alerts for each direction with obstacles
            for position, obs in positions.items():
                if obs:
                    # Get most significant obstacle
                    closest = self.camera.get_closest_obstacle(obs)
                    if closest:
                        # Alert intensity based on confidence
                        intensity = closest.confidence
                        
                        # Generate haptic alert
                        self.haptic.alert_obstacle(position, intensity=intensity)
                        
                        # Publish via MQTT
                        if self.mqtt and self.mqtt.is_connected:
                            self._publish_obstacle_alert(closest, position)
    
    def _publish_obstacle_alert(self, detection: Detection, position: str) -> None:
        """Publish obstacle alert via MQTT."""
        try:
            alert_data = {
                "label": detection.label,
                "confidence": detection.confidence,
                "position": position,
                "bounding_box": detection.bounding_box,
            }
            
            self.mqtt.publish_obstacle_alert(alert_data)
            self.messages_sent += 1
            
        except Exception as e:
            logger.error(f"Failed to publish obstacle alert: {e}")
    
    def send_braille_message(self, text: str) -> bool:
        """
        Send a text message via Braille haptic display.
        
        Args:
            text: Text message to send
            
        Returns:
            True if message sent successfully
        """
        if not self.haptic or not self.braille:
            logger.error("Haptic or Braille module not available")
            return False
        
        logger.info(f"Sending Braille message: {text}")
        
        try:
            self.braille.display_text(self.haptic, text)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Braille message: {e}")
            return False
    
    def pause(self) -> None:
        """Pause the application."""
        logger.info("Pausing application...")
        self._pause_requested = True
        self.state = SystemState.PAUSED
        
        if self.haptic:
            self.haptic.stop_all()
    
    def resume(self) -> None:
        """Resume the application from paused state."""
        logger.info("Resuming application...")
        self._pause_requested = False
        self.state = SystemState.RUNNING
    
    def stop(self) -> None:
        """Stop the application and cleanup resources."""
        logger.info("Stopping SyntheticSense system...")
        
        self._stop_requested = True
        self.state = SystemState.STOPPING
        
        # Stop components
        if self.haptic:
            self.haptic.stop_all()
            self.haptic.cleanup()
        
        if self.camera:
            self.camera.stop()
        
        if self.mqtt:
            self.mqtt.disconnect()
        
        self.state = SystemState.STOPPING
        logger.info("SyntheticSense system stopped")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._stop_requested = True
    
    def get_status(self) -> SystemStatus:
        """
        Get current system status.
        
        Returns:
            SystemStatus object with current state
        """
        uptime = time.time() - self.start_time if self.start_time > 0 else 0
        
        temp = 0.0
        if self.thermal_monitor:
            temp = self.thermal_monitor.get_temperature()
        
        return SystemStatus(
            state=self.state,
            uptime=uptime,
            detections_count=self.detections_count,
            messages_sent=self.messages_sent,
            temperature=temp,
            errors=self.error_log.copy(),
        )
    
    def print_status(self) -> None:
        """Print current system status to console."""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print("SyntheticSense System Status")
        print("=" * 60)
        print(f"State: {status.state.value}")
        print(f"Uptime: {status.uptime:.1f} seconds")
        print(f"Detections: {status.detections_count}")
        print(f"Messages Sent: {status.messages_sent}")
        print(f"Temperature: {status.temperature:.1f}°C")
        
        if status.errors:
            print(f"Errors: {len(status.errors)}")
            for error in status.errors[-5:]:  # Last 5 errors
                print(f"  - {error}")
        
        print("=" * 60 + "\n")
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def main():
    """Main entry point for SyntheticSense application."""
    print("SyntheticSense v0.1.0")
    print("Open-Source Assistive Technology for the Deaf-Blind Community")
    print("-" * 60)
    
    # Create and initialize application
    app = SyntheticSenseApp()
    
    if not app.initialize():
        print("Failed to initialize system")
        sys.exit(1)
    
    print("System initialized successfully")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    # Run application
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        app.stop()
    
    print("System shutdown complete")


if __name__ == "__main__":
    main()
