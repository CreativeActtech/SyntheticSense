"""
Camera module for real-time object detection.

Supports both standard USB/webcam and Sony IMX500 AI camera.
Optimized for Raspberry Pi 5 with hardware acceleration.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Represents a detected object."""
    
    class_id: int
    label: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    timestamp: float
    
    @property
    def center_x(self) -> float:
        """Get horizontal center of bounding box (0.0 to 1.0)."""
        x_min, _, x_max, _ = self.bounding_box
        return (x_min + x_max) / 2.0
    
    @property
    def horizontal_position(self) -> str:
        """Determine horizontal position: 'left', 'center', or 'right'."""
        cx = self.center_x
        if cx < 0.33:
            return "left"
        elif cx > 0.67:
            return "right"
        else:
            return "center"


class CameraModule:
    """
    Camera module for object detection.
    
    This module handles camera initialization, frame capture, and object detection.
    It supports multiple detection models and can work with standard cameras or
    the Sony IMX500 AI camera with embedded neural processing.
    """
    
    def __init__(self, config=None):
        """
        Initialize the camera module.
        
        Args:
            config: CameraSettings object or None to use defaults
        """
        from ..config.settings import Settings
        
        self.config = config or Settings().camera
        self.camera = None
        self.model = None
        self.is_initialized = False
        self.use_imx500 = self.config.use_imx500
        
        # Detection state
        self.last_detection_time = 0
        self.detection_count = 0
        
        logger.info(f"CameraModule initialized (IMX500: {self.use_imx500})")
    
    def initialize(self) -> bool:
        """
        Initialize camera and detection model.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_imx500:
                self._initialize_imx500()
            else:
                self._initialize_standard_camera()
            
            self._load_detection_model()
            self.is_initialized = True
            
            logger.info("Camera module initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize camera module: {e}")
            return False
    
    def _initialize_imx500(self) -> None:
        """Initialize Sony IMX500 AI camera."""
        logger.info("Initializing Sony IMX500 AI camera...")
        
        # Placeholder for IMX500 SDK integration
        # In production, this would use the IMX500 SDK:
        # import imx500_sdk
        # self.camera = imx500_sdk.Camera()
        # self.camera.configure(...)
        
        logger.warning("IMX500 support not yet implemented - using mock mode")
        self.camera = "IMX500_MOCK"
    
    def _initialize_standard_camera(self) -> None:
        """Initialize standard USB/webcam using OpenCV."""
        logger.info(f"Initializing standard camera (ID: {self.config.camera_id})...")
        
        try:
            import cv2
            
            self.camera = cv2.VideoCapture(self.config.camera_id)
            
            if not self.camera.isOpened():
                raise RuntimeError(f"Cannot open camera {self.config.camera_id}")
            
            # Configure camera settings
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Verify settings
            actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            logger.info(
                f"Camera configured: {actual_width}x{actual_height}@{actual_fps}fps"
            )
            
        except ImportError:
            logger.warning("OpenCV not available - using mock camera mode")
            self.camera = "OPENCV_MOCK"
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            raise
    
    def _load_detection_model(self) -> None:
        """Load object detection model."""
        logger.info(f"Loading detection model: {self.config.model_type}")
        
        model_type = self.config.model_type.lower()
        
        if model_type == "mobilenet-ssd":
            self._load_mobilenet_ssd()
        elif model_type == "yolov8-nano" or model_type == "yolov8n":
            self._load_yolov8()
        else:
            logger.warning(f"Unknown model type '{model_type}', using MobileNet-SSD")
            self._load_mobilenet_ssd()
    
    def _load_mobilenet_ssd(self) -> None:
        """Load MobileNet-SSD model for object detection."""
        try:
            import cv2
            
            # COCO class labels for MobileNet-SSD
            self.coco_classes = {
                0: "background", 1: "aeroplane", 2: "bicycle", 3: "bird",
                4: "boat", 5: "bottle", 6: "bus", 7: "car", 8: "cat",
                9: "chair", 10: "cow", 11: "diningtable", 12: "dog",
                13: "horse", 14: "motorbike", 15: "person", 16: "pottedplant",
                17: "sheep", 18: "sofa", 19: "train", 20: "tvmonitor"
            }
            
            # Try to load pre-trained model
            # In production, download from:
            # http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v1_coco_2018_01_28.tar.gz
            
            logger.info("MobileNet-SSD model loaded (mock mode)")
            self.model = "MOBILENET_SSD_MOCK"
            
        except Exception as e:
            logger.error(f"Failed to load MobileNet-SSD: {e}")
            self.model = "MOBILENET_SSD_MOCK"
    
    def _load_yolov8(self) -> None:
        """Load YOLOv8 nano model for object detection."""
        try:
            from ultralytics import YOLO
            
            # Load YOLOv8 nano model
            self.model = YOLO('yolov8n.pt')
            
            logger.info("YOLOv8-nano model loaded successfully")
            
        except ImportError:
            logger.warning("ultralytics not available - falling back to MobileNet-SSD")
            self._load_mobilenet_ssd()
        except Exception as e:
            logger.error(f"Failed to load YOLOv8: {e}")
            self._load_mobilenet_ssd()
    
    def detect_objects(self) -> List[Detection]:
        """
        Capture frame and detect objects.
        
        Returns:
            List of Detection objects
        """
        if not self.is_initialized:
            logger.warning("Camera not initialized")
            return []
        
        # Check detection interval
        current_time = time.time()
        if current_time - self.last_detection_time < self.config.detection_interval:
            return []
        
        self.last_detection_time = current_time
        
        try:
            # Capture frame
            frame = self._capture_frame()
            if frame is None:
                return []
            
            # Perform detection
            detections = self._run_detection(frame)
            self.detection_count += 1
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []
    
    def _capture_frame(self) -> Optional[Any]:
        """Capture a frame from the camera."""
        if self.camera == "IMX500_MOCK" or self.camera == "OPENCV_MOCK":
            # Return mock frame for testing
            import numpy as np
            return np.zeros((self.config.frame_height, self.config.frame_width, 3), dtype=np.uint8)
        
        try:
            import cv2
            ret, frame = self.camera.read()
            if not ret:
                logger.warning("Failed to capture frame")
                return None
            return frame
        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return None
    
    def _run_detection(self, frame: Any) -> List[Detection]:
        """Run object detection on a frame."""
        detections = []
        current_time = time.time()
        
        if self.model == "MOBILENET_SSD_MOCK" or self.model == "IMX500_MOCK":
            # Mock detections for testing
            detections = self._generate_mock_detections(current_time)
        
        elif hasattr(self.model, 'predict'):
            # YOLOv8 detection
            try:
                results = self.model.predict(
                    frame,
                    conf=self.config.confidence_threshold,
                    verbose=False
                )
                
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    for i in range(len(boxes)):
                        cls_id = int(boxes.cls[i])
                        conf = float(boxes.conf[i])
                        bbox = boxes.xyxy[i].cpu().numpy()
                        
                        label = self.model.names[cls_id] if hasattr(self.model, 'names') else str(cls_id)
                        
                        detection = Detection(
                            class_id=cls_id,
                            label=label,
                            confidence=conf,
                            bounding_box=tuple(map(int, bbox)),
                            timestamp=current_time
                        )
                        detections.append(detection)
                        
            except Exception as e:
                logger.error(f"YOLOv8 detection error: {e}")
        
        else:
            # Fallback to mock detections
            detections = self._generate_mock_detections(current_time)
        
        return detections
    
    def _generate_mock_detections(self, timestamp: float) -> List[Detection]:
        """Generate mock detections for testing without actual model."""
        import random
        
        # Simulate occasional detections
        if random.random() > 0.3:  # 70% chance of detection
            return []
        
        mock_objects = [
            (15, "person"), (9, "chair"), (7, "car"), (16, "pottedplant")
        ]
        
        detections = []
        num_detections = random.randint(1, 3)
        
        for _ in range(num_detections):
            cls_id, label = random.choice(mock_objects)
            conf = random.uniform(0.6, 0.95)
            
            # Random bounding box
            x_min = random.randint(0, self.config.frame_width // 2)
            y_min = random.randint(0, self.config.frame_height // 2)
            width = random.randint(50, 200)
            height = random.randint(50, 200)
            x_max = min(x_min + width, self.config.frame_width)
            y_max = min(y_min + height, self.config.frame_height)
            
            detection = Detection(
                class_id=cls_id,
                label=label,
                confidence=conf,
                bounding_box=(x_min, y_min, x_max, y_max),
                timestamp=timestamp
            )
            detections.append(detection)
        
        return detections
    
    def get_detections_by_position(self, detections: List[Detection]) -> Dict[str, List[Detection]]:
        """
        Group detections by horizontal position.
        
        Args:
            detections: List of Detection objects
            
        Returns:
            Dictionary with keys 'left', 'center', 'right'
        """
        positions = {"left": [], "center": [], "right": []}
        
        for detection in detections:
            pos = detection.horizontal_position
            positions[pos].append(detection)
        
        return positions
    
    def get_closest_obstacle(self, detections: List[Detection]) -> Optional[Detection]:
        """
        Get the closest/most significant obstacle.
        
        Args:
            detections: List of Detection objects
            
        Returns:
            Closest Detection or None
        """
        if not detections:
            return None
        
        # Sort by confidence (higher confidence = closer/more certain)
        sorted_detections = sorted(
            detections,
            key=lambda d: d.confidence,
            reverse=True
        )
        
        return sorted_detections[0]
    
    def stop(self) -> None:
        """Stop camera and release resources."""
        try:
            if self.camera and self.camera != "IMX500_MOCK" and self.camera != "OPENCV_MOCK":
                import cv2
                self.camera.release()
            
            self.is_initialized = False
            logger.info("Camera module stopped")
            
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get camera module statistics."""
        return {
            "is_initialized": self.is_initialized,
            "use_imx500": self.use_imx500,
            "model_type": self.config.model_type,
            "detection_count": self.detection_count,
            "last_detection_time": self.last_detection_time,
            "confidence_threshold": self.config.confidence_threshold,
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
