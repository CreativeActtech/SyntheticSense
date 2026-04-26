"""
MQTT client module for wireless communication.

Enables remote messaging and status reporting via MQTT protocol.
Optimized for reliable communication with QoS support.
"""

import logging
from typing import Optional, Dict, Any, Callable, List
import json
import time
import uuid
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a message for transmission."""
    
    topic: str
    payload: str
    qos: int = 1
    retain: bool = False
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "payload": self.payload,
            "qos": self.qos,
            "retain": self.retain,
            "timestamp": self.timestamp,
        }


class ConnectionStatus(Enum):
    """MQTT connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class MQTTClient:
    """
    MQTT client for wireless communication.
    
    This class provides MQTT publish/subscribe functionality for
    sending obstacle alerts, receiving messages, and reporting status.
    Supports automatic reconnection and message queuing.
    """
    
    def __init__(self, config=None):
        """
        Initialize the MQTT client.
        
        Args:
            config: CommunicationSettings object or None to use defaults
        """
        from ..config.settings import Settings
        
        self.config = config or Settings().communication
        self.client = None
        self.is_connected = False
        self.connection_status = ConnectionStatus.DISCONNECTED
        
        # Message handling
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.message_queue: List[Message] = []
        self.max_queue_size = 100
        
        # Client identification
        self.client_id = self.config.client_id or f"syntheticsense_{uuid.uuid4().hex[:8]}"
        
        # Callbacks
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.on_message_callback: Optional[Callable] = None
        
        logger.info(f"MQTTClient initialized (ID: {self.client_id})")
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            import paho.mqtt.client as mqtt
            
            # Create MQTT client
            self.client = mqtt.Client(
                client_id=self.client_id,
                protocol=mqtt.MQTTv311
            )
            
            # Configure authentication
            if self.config.username and self.config.password:
                self.client.username_pw_set(
                    self.config.username,
                    self.config.password
                )
            
            # Setup callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Set keepalive
            self.client.keepalive = self.config.keepalive
            
            # Connect to broker
            self.connection_status = ConnectionStatus.CONNECTING
            self.client.connect(
                self.config.broker_host,
                self.config.broker_port,
                keepalive=self.config.keepalive
            )
            
            # Start network loop
            self.client.loop_start()
            
            logger.info(
                f"Connecting to MQTT broker at {self.config.broker_host}:{self.config.broker_port}"
            )
            
            return True
            
        except ImportError:
            logger.warning("paho-mqtt not available - using mock mode")
            self._mock_connect()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.connection_status = ConnectionStatus.ERROR
            return False
    
    def _mock_connect(self) -> None:
        """Mock connection for testing without broker."""
        logger.info("Mock MQTT connection established")
        self.is_connected = True
        self.connection_status = ConnectionStatus.CONNECTED
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection event."""
        from paho.mqtt.client import connack_string
        
        if rc == 0:
            self.is_connected = True
            self.connection_status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to MQTT broker: {connack_string(rc)}")
            
            # Subscribe to default topics
            self._subscribe_to_topics()
            
            # Process queued messages
            self._process_message_queue()
            
            if self.on_connect_callback:
                self.on_connect_callback(True)
        else:
            logger.error(f"Connection failed: {connack_string(rc)}")
            self.connection_status = ConnectionStatus.ERROR
            
            if self.on_connect_callback:
                self.on_connect_callback(False)
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection event."""
        from paho.mqtt.client import connack_string
        
        self.is_connected = False
        self.connection_status = ConnectionStatus.DISCONNECTED
        
        logger.warning(f"Disconnected from MQTT broker: {connack_string(rc)}")
        
        if self.on_disconnect_callback:
            self.on_disconnect_callback(rc)
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8') if msg.payload else ""
            
            logger.debug(f"Message received on {topic}: {payload}")
            
            # Call registered handlers
            if topic in self.message_handlers:
                for handler in self.message_handlers[topic]:
                    try:
                        handler(topic, payload)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")
            
            # Call general callback
            if self.on_message_callback:
                self.on_message_callback(topic, payload)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _subscribe_to_topics(self) -> None:
        """Subscribe to default topics."""
        topics = [
            f"{self.config.topic_prefix}/{self.config.message_topic}",
            f"{self.config.topic_prefix}/commands",
        ]
        
        for topic in topics:
            try:
                self.client.subscribe(topic, qos=self.config.qos)
                logger.info(f"Subscribed to {topic}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {topic}: {e}")
    
    def publish(self, topic: str, payload: Any, qos: int = None,
                retain: bool = None) -> bool:
        """
        Publish a message to MQTT broker.
        
        Args:
            topic: Topic to publish to
            payload: Message payload (will be JSON serialized if not string)
            qos: Quality of Service level (uses config default if None)
            retain: Whether to retain message (uses config default if None)
            
        Returns:
            True if published successfully
        """
        if not self.is_connected:
            logger.warning("Not connected to MQTT broker, queuing message")
            self._queue_message(topic, payload, qos, retain)
            return False
        
        try:
            # Serialize payload if needed
            if not isinstance(payload, str):
                payload = json.dumps(payload)
            
            # Use config defaults if not specified
            qos = qos if qos is not None else self.config.qos
            retain = retain if retain is not None else self.config.retain
            
            # Publish message
            result = self.client.publish(
                topic,
                payload,
                qos=qos,
                retain=retain
            )
            
            # Wait for publication if QoS > 0
            if qos > 0:
                result.wait_for_publish()
            
            logger.debug(f"Published to {topic}: {payload[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            self._queue_message(topic, payload, qos, retain)
            return False
    
    def _queue_message(self, topic: str, payload: Any, qos: int,
                       retain: bool) -> None:
        """Queue message for later delivery."""
        if len(self.message_queue) >= self.max_queue_size:
            # Remove oldest message
            self.message_queue.pop(0)
            logger.warning("Message queue full, dropped oldest message")
        
        message = Message(
            topic=topic,
            payload=payload if isinstance(payload, str) else json.dumps(payload),
            qos=qos if qos is not None else self.config.qos,
            retain=retain if retain is not None else self.config.retain
        )
        
        self.message_queue.append(message)
        logger.debug(f"Message queued: {topic}")
    
    def _process_message_queue(self) -> None:
        """Process queued messages after reconnection."""
        while self.message_queue and self.is_connected:
            message = self.message_queue.pop(0)
            self.publish(
                message.topic,
                message.payload,
                qos=message.qos,
                retain=message.retain
            )
    
    def publish_obstacle_alert(self, obstacle_data: Dict[str, Any]) -> bool:
        """
        Publish obstacle detection alert.
        
        Args:
            obstacle_data: Dictionary with obstacle information
            
        Returns:
            True if published successfully
        """
        topic = f"{self.config.topic_prefix}/{self.config.obstacle_topic}"
        
        payload = {
            "type": "obstacle_alert",
            "timestamp": time.time(),
            "data": obstacle_data,
        }
        
        return self.publish(topic, payload, retain=False)
    
    def publish_status(self, status_data: Dict[str, Any]) -> bool:
        """
        Publish system status update.
        
        Args:
            status_data: Dictionary with status information
            
        Returns:
            True if published successfully
        """
        topic = f"{self.config.topic_prefix}/{self.config.status_topic}"
        
        payload = {
            "type": "status_update",
            "timestamp": time.time(),
            "client_id": self.client_id,
            "data": status_data,
        }
        
        return self.publish(topic, payload, retain=True)
    
    def send_message(self, recipient: str, message: str) -> bool:
        """
        Send a text message to a recipient.
        
        Args:
            recipient: Recipient identifier
            message: Message text
            
        Returns:
            True if sent successfully
        """
        topic = f"{self.config.topic_prefix}/{self.config.message_topic}"
        
        payload = {
            "type": "message",
            "recipient": recipient,
            "content": message,
            "timestamp": time.time(),
        }
        
        return self.publish(topic, payload)
    
    def subscribe(self, topic: str, callback: Callable[[str, str], None],
                  qos: int = None) -> bool:
        """
        Subscribe to a topic with callback.
        
        Args:
            topic: Topic to subscribe to
            callback: Function to call on message (topic, payload)
            qos: Quality of Service level
            
        Returns:
            True if subscribed successfully
        """
        if not self.is_connected:
            logger.warning("Cannot subscribe while disconnected")
            return False
        
        try:
            qos = qos if qos is not None else self.config.qos
            
            # Register handler
            if topic not in self.message_handlers:
                self.message_handlers[topic] = []
            self.message_handlers[topic].append(callback)
            
            # Subscribe via MQTT
            self.client.subscribe(topic, qos=qos)
            
            logger.info(f"Subscribed to {topic} with callback")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            
        Returns:
            True if unsubscribed successfully
        """
        if not self.is_connected:
            return False
        
        try:
            self.client.unsubscribe(topic)
            self.message_handlers.pop(topic, None)
            
            logger.info(f"Unsubscribed from {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {topic}: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
            
            self.is_connected = False
            self.connection_status = ConnectionStatus.DISCONNECTED
            
            logger.info("Disconnected from MQTT broker")
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def reconnect(self) -> bool:
        """Attempt to reconnect to MQTT broker."""
        logger.info("Attempting to reconnect to MQTT broker...")
        
        self.connection_status = ConnectionStatus.RECONNECTING
        
        if self.is_connected:
            self.disconnect()
        
        return self.connect()
    
    def get_status(self) -> Dict[str, Any]:
        """Get MQTT client status."""
        return {
            "is_connected": self.is_connected,
            "connection_status": self.connection_status.value,
            "client_id": self.client_id,
            "broker": f"{self.config.broker_host}:{self.config.broker_port}",
            "queued_messages": len(self.message_queue),
            "subscribed_topics": list(self.message_handlers.keys()),
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
