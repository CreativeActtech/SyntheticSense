## **Core Computing & AI Components**
*   **Primary Processor:** Raspberry Pi Zero 2W
    *   *Function:* Runs the main Python control logic, processes data from the AI camera, and handles wireless communication.
*   **Haptic Controller:** Raspberry Pi Pico
    *   *Function:* Manages the precise timing and sequencing of the vibration motor arrays via MicroPython firmware.
*   **AI Vision Sensor:** Sony IMX500
    *   *Function:* Performs on-sensor Edge AI inference for real-time object detection without needing cloud connectivity.

### **Haptic Feedback Hardware**
*   **Vibration Motor Array:** Miniature disc or pancake vibration motors
    *   *Function:* Arranged in a grid to represent Braille cells for communication and in directional groups (left, center, right) for obstacle alerts.
*   **Motor Driver/Multiplexer:** (Required for driving multiple motors from the Pico’s GPIO pins)
    *   *Function:* Ensures the vibration motors receive adequate current and can be controlled individually.

### **Power & Connectivity**
*   **Power Source:** Modular LiPo Battery or portable power bank
    *   *Function:* Provides mobile power for the wearable system.
*   **Power Management Module:** 5V regulator or battery management system (BMS)
    *   *Function:* Ensures stable voltage to the Raspberry Pi boards and safe charging for the battery.
*   **Wireless Module:** Integrated Wi-Fi (via Raspberry Pi Zero 2W)
    *   *Function:* Facilitates remote messaging and updates through the MQTT protocol.

### **Miscellaneous Hardware**
*   **Storage:** 2x MicroSD Cards (High-speed, 16GB+ recommended)
    *   *Function:* Houses the OS and software for both the Pi Zero 2W and the Pico.
*   **Connectivity Cables:** CSI Camera Ribbon Cable (for IMX500) and jumper wires
    *   *Function:* Physical data and power connections between components.
*   **Wearable Housing:** 3D-printed enclosure or adjustable straps
    *   *Function:* Secures the electronics to the user’s body for practical use.

### **Software Requirements (Open Source)**
*   **Operating Systems:** Raspberry Pi OS (Lite) and MicroPython
*   **Libraries:** Python 3.x, NumPy (for encoding), OpenCV, and the IMX500 SDK
*   **Protocols:** MQTT Client for wireless messaging