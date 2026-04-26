"""
Braille encoder module for haptic communication.

Converts text to Braille patterns for vibration motor arrays.
Implements standard 6-dot Grade 1 Braille encoding.
"""

import logging
from typing import List, Dict, Optional, Any
import time

logger = logging.getLogger(__name__)


class BrailleEncoder:
    """
    Braille encoder for converting text to haptic patterns.
    
    This class provides text-to-Braille conversion using standard
    6-dot Braille encoding, optimized for haptic motor arrays.
    """
    
    # Standard 6-dot Braille patterns (dots 1-6)
    # Each pattern is a 6-bit number where bit 0 = dot 1, bit 5 = dot 6
    BRAILLE_ALPHABET = {
        'a': 0b010000,  # ⠁
        'b': 0b110000,  # ⠃
        'c': 0b100100,  # ⠉
        'd': 0b101100,  # ⠙
        'e': 0b100010,  # ⠑
        'f': 0b110100,  # ⠋
        'g': 0b111100,  # ⠛
        'h': 0b110010,  # ⠓
        'i': 0b011100,  # ⠊
        'j': 0b011110,  # ⠚
        'k': 0b010001,  # ⠅
        'l': 0b110001,  # ⠇
        'm': 0b100101,  # ⠍
        'n': 0b101101,  # ⠝
        'o': 0b100011,  # ⠕
        'p': 0b110101,  # ⠏
        'q': 0b111101,  # ⠟
        'r': 0b110011,  # ⠗
        's': 0b011101,  # ⠎
        't': 0b011111,  # ⠞
        'u': 0b0100011, # ⠥ (corrected)
        'v': 0b0100011, # ⠧ (corrected below)
        'w': 0b011110,  # ⠺ (special case)
        'x': 0b100111,  # ⠭
        'y': 0b101111,  # ⠽
        'z': 0b101011,  # ⠵
    }
    
    # Fix 'u' and 'v'
    BRAILLE_ALPHABET['u'] = 0b010001  # ⠥
    BRAILLE_ALPHABET['v'] = 0b110001  # ⠧
    
    # Numbers (preceded by number sign ⠼)
    BRAILLE_NUMBERS = {
        '0': 0b010110,  # ⠚
        '1': 0b010000,  # ⠁
        '2': 0b110000,  # ⠃
        '3': 0b100100,  # ⠉
        '4': 0b101100,  # ⠙
        '5': 0b100010,  # ⠑
        '6': 0b110100,  # ⠋
        '7': 0b111100,  # ⠛
        '8': 0b110010,  # ⠓
        '9': 0b011100,  # ⠊
    }
    
    # Common punctuation
    BRAILLE_PUNCTUATION = {
        '.': 0b100100,  # ⠲
        ',': 0b000100,  # ⠂
        '?': 0b100110,  # ⠦
        '!': 0b110110,  # ⠖
        ';': 0b000110,  # ⠆
        ':': 0b000010,  # ⠒
        '-': 0b100000,  # ⠤
        '(': 0b100111,  # ⠣
        ')': 0b011001,  # ⠜
        "'": 0b000001,  # ⠄
        '"': 0b011000,  # ⠦
        '/': 0b001100,  # ⠌
    }
    
    # Special signs
    NUMBER_SIGN = 0b001101  # ⠼
    CAPITAL_SIGN = 0b000001  # ⠠
    SPACE_PATTERN = 0b000000  # Empty
    
    def __init__(self, config=None):
        """
        Initialize the Braille encoder.
        
        Args:
            config: BrailleSettings object or None to use defaults
        """
        from ..config.settings import Settings
        
        self.config = config or Settings().braille
        self.motor_map = self.config.braille_motor_map
        
        # Timing configuration
        self.char_duration = self.config.character_duration
        self.letter_pause = self.config.letter_pause
        self.word_pause = self.config.word_pause
        
        logger.info("BrailleEncoder initialized")
    
    def encode_char(self, char: str) -> Optional[int]:
        """
        Encode a single character to Braille pattern.
        
        Args:
            char: Character to encode
            
        Returns:
            6-bit Braille pattern or None if not encodable
        """
        c = char.lower()
        
        if c in self.BRAILLE_ALPHABET:
            return self.BRAILLE_ALPHABET[c]
        elif c in self.BRAILLE_NUMBERS:
            return self.BRAILLE_NUMBERS[c]
        elif c in self.BRAILLE_PUNCTUATION:
            return self.BRAILLE_PUNCTUATION[c]
        elif c == ' ':
            return self.SPACE_PATTERN
        else:
            logger.warning(f"Cannot encode character: '{char}'")
            return None
    
    def encode_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Encode text into sequence of Braille patterns.
        
        Args:
            text: Text string to encode
            
        Returns:
            List of dictionaries with pattern and metadata
        """
        result = []
        in_number_mode = False
        prev_was_capital = False
        
        i = 0
        while i < len(text):
            char = text[i]
            
            # Handle spaces
            if char == ' ':
                result.append({
                    'char': ' ',
                    'pattern': self.SPACE_PATTERN,
                    'duration': self.word_pause,
                    'is_space': True,
                })
                in_number_mode = False
                i += 1
                continue
            
            # Check for capital letters
            if char.isupper():
                result.append({
                    'char': 'CAP',
                    'pattern': self.CAPITAL_SIGN,
                    'duration': self.char_duration,
                    'is_modifier': True,
                })
                char = char.lower()
            
            # Check for numbers
            if char.isdigit() and not in_number_mode:
                result.append({
                    'char': '#',
                    'pattern': self.NUMBER_SIGN,
                    'duration': self.char_duration,
                    'is_modifier': True,
                })
                in_number_mode = True
            
            # Encode character
            pattern = self.encode_char(char)
            if pattern is not None:
                result.append({
                    'char': char,
                    'pattern': pattern,
                    'duration': self.char_duration,
                    'is_space': False,
                    'is_modifier': False,
                })
                
                # Reset number mode after non-digit
                if not char.isdigit():
                    in_number_mode = False
            
            i += 1
        
        return result
    
    def pattern_to_motors(self, pattern: int) -> List[int]:
        """
        Convert Braille pattern to motor indices.
        
        Args:
            pattern: 6-bit Braille pattern
            
        Returns:
            List of motor indices to activate
        """
        motors = []
        
        for dot in range(6):
            if pattern & (1 << dot):
                if dot < len(self.motor_map):
                    motors.append(self.motor_map[dot])
        
        return motors
    
    def display_character(self, haptic_controller, char: str, 
                         duration: float = None) -> bool:
        """
        Display a single Braille character on haptic array.
        
        Args:
            haptic_controller: HapticController instance
            char: Character to display
            duration: Display duration (uses config default if None)
            
        Returns:
            True if successful
        """
        pattern = self.encode_char(char)
        if pattern is None:
            return False
        
        if duration is None:
            duration = self.char_duration
        
        motors = self.pattern_to_motors(pattern)
        
        if motors:
            haptic_controller.activate_motor(motors[0], duration=duration)
            for motor in motors[1:]:
                haptic_controller.activate_motor(motor, duration=duration)
        
        time.sleep(duration + self.letter_pause)
        return True
    
    def display_text(self, haptic_controller, text: str, 
                    callback: callable = None) -> bool:
        """
        Display full text message as Braille sequence.
        
        Args:
            haptic_controller: HapticController instance
            text: Text to display
            callback: Optional callback for each character
            
        Returns:
            True if successful
        """
        encoded = self.encode_text(text)
        
        for item in encoded:
            if item['is_space']:
                time.sleep(item['duration'])
            else:
                motors = self.pattern_to_motors(item['pattern'])
                
                if motors:
                    # Activate all dots simultaneously
                    for motor in motors:
                        haptic_controller.activate_motor(
                            motor,
                            duration=item['duration']
                        )
                    
                    time.sleep(item['duration'])
                    
                    # Deactivate
                    for motor in motors:
                        haptic_controller.deactivate_motor(motor)
                    
                    # Pause between characters
                    if not item.get('is_modifier'):
                        time.sleep(self.letter_pause)
                
                if callback:
                    try:
                        callback(item['char'], motors)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
        
        return True
    
    def get_braille_unicode(self, pattern: int) -> str:
        """
        Convert Braille pattern to Unicode Braille character.
        
        Args:
            pattern: 6-bit Braille pattern
            
        Returns:
            Unicode Braille character
        """
        # Unicode Braille patterns start at U+2800
        unicode_point = 0x2800 + pattern
        return chr(unicode_point)
    
    def text_to_braille_unicode(self, text: str) -> str:
        """
        Convert text to Unicode Braille string.
        
        Args:
            text: Text to convert
            
        Returns:
            Unicode Braille string
        """
        encoded = self.encode_text(text)
        result = ""
        
        for item in encoded:
            if not item.get('is_modifier'):
                result += self.get_braille_unicode(item['pattern'])
        
        return result
    
    def get_pattern_info(self, pattern: int) -> Dict[str, Any]:
        """
        Get detailed information about a Braille pattern.
        
        Args:
            pattern: 6-bit Braille pattern
            
        Returns:
            Dictionary with pattern details
        """
        dots = []
        for dot in range(6):
            if pattern & (1 << dot):
                dots.append(dot + 1)
        
        return {
            'pattern': pattern,
            'binary': format(pattern, '06b'),
            'active_dots': dots,
            'unicode': self.get_braille_unicode(pattern),
            'motors': self.pattern_to_motors(pattern),
        }
    
    def validate_pattern(self, pattern: int) -> bool:
        """
        Validate a Braille pattern.
        
        Args:
            pattern: Pattern to validate
            
        Returns:
            True if valid 6-bit pattern
        """
        return 0 <= pattern <= 0b111111
