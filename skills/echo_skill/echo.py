"""
Echo Skill - A simple demonstration skill for SkillKit

This skill echoes back the user's input with optional formatting.
It always prepends [Test Success] to the response.
"""

import json
import logging
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger("chatbot")


class EchoSkill:
    """
    A simple echo skill that returns the user's input with optional formatting.
    
    This skill demonstrates the basic structure of a SkillKit skill and
    can be used as a template for creating new skills.
    
    The skill always prepends [Test Success] to the response to indicate
    successful skill execution.
    """
    
    def __init__(self):
        """Initialize the echo skill with metadata."""
        self.name = "echo"
        self.description = "Echo back the user's input with optional formatting options - always returns [Test Success] prefix"
        self.version = "1.0.0"
        self.author = "Chatbot Framework"
        self.category = "utility"
        self.tags = ["echo", "utility", "demo", "testing", "success"]
        self.test_prefix = "[Test Success] "
    
    def execute(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Execute the echo skill.
        
        Args:
            input_text: The text to echo back
            **kwargs: Optional parameters:
                - uppercase (bool): Convert text to uppercase
                - prefix (str): Custom prefix for the response (default: "Echo")
                - repeat_count (int): Number of times to repeat the echo
        
        Returns:
            Dict with success status, response, and data
        """
        logger.info(f"🔧 EchoSkill executing with input: {input_text[:100]}...")
        
        # Extract optional parameters with defaults
        uppercase = kwargs.get('uppercase', False)
        prefix = kwargs.get('prefix', 'Echo')
        repeat_count = kwargs.get('repeat_count', 1)
        
        # Validate parameters
        if not isinstance(input_text, str):
            return {
                'success': False,
                'error': 'Input must be a string',
                'data': {'input': input_text}
            }
        
        if not isinstance(repeat_count, int) or repeat_count < 1:
            repeat_count = 1
        
        if repeat_count > 10:
            logger.warning(f"⚠️ Repeat count {repeat_count} exceeds maximum (10), limiting to 10")
            repeat_count = 10
        
        # Process the input
        processed_text = input_text
        if uppercase:
            processed_text = processed_text.upper()
        
        # Generate response with [Test Success] prefix
        if repeat_count > 1:
            # For multiple repeats, add [Test Success] to each echo
            echo_parts = [f"{self.test_prefix}{prefix}: {processed_text}"] * repeat_count
            response = " | ".join(echo_parts)
        else:
            response = f"{self.test_prefix}{prefix}: {processed_text}"
        
        # Log the result
        logger.info(f"✅ EchoSkill completed with [Test Success]: {response[:100]}...")
        
        # Return structured result
        return {
            "success": True,
            "response": response,
            "data": {
                "input": input_text,
                "processed": processed_text,
                "length": len(input_text),
                "uppercase": uppercase,
                "repeat_count": repeat_count,
                "prefix": prefix,
                "skill_version": self.version,
                "test_prefix": self.test_prefix.strip()
            }
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get detailed skill information.
        
        Returns:
            Dict with skill metadata
        """
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'category': self.category,
            'tags': self.tags,
            'type': 'SkillKit',
            'source': 'skillkit',
            'test_prefix': self.test_prefix.strip()
        }


# IMPORTANT: This is the factory function that SkillKit looks for
def create_skill():
    """Factory function to create an instance of the echo skill."""
    return EchoSkill()


# For direct testing
if __name__ == "__main__":
    # Test the echo skill
    skill = EchoSkill()
    
    print("🧪 Testing Echo Skill with [Test Success]")
    print("=" * 60)
    
    # Test 1: Basic echo
    result = skill.execute("Hello World")
    print(f"Basic echo: {result['response']}")
    
    # Test 2: Uppercase
    result = skill.execute("Hello World", uppercase=True)
    print(f"Uppercase: {result['response']}")
    
    # Test 3: Custom prefix
    result = skill.execute("Hello World", prefix="REPLY")
    print(f"Custom prefix: {result['response']}")
    
    # Test 4: Repeat
    result = skill.execute("Hello World", repeat_count=3)
    print(f"Repeat: {result['response']}")