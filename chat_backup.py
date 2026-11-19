"""
Advanced Chatbot Framework with LLM Integration
Chatbot that uses Ollama LLM for intelligent responses
Enhanced with SkillKit for modular skill management

Architecture:
1. AI (LLM) - Detects intent and selects skills (Stage 1/3)
2. Select Skills - Decides which skill(s) to use (Stage 1/3)
3. Skill Manual - The actual skill execution (Stage 2/3)
4. Execute Skill function - Runs the skill (Stage 2/3)
5. Format Final Answer - LLM formats the response (Stage 3/3)

Skill Selection Logic:
- If query starts with "echo" → Pass "echo" skill to LLM
- If query is data-related → Pass "dax_query" skill with schema + SKILL.md to LLM
"""

import re
import json
import sys
import logging
import requests
import importlib
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
from enum import Enum
from collections import Counter, defaultdict

# ==================== Status Types ====================

class ChatStatus(str, Enum):
    """Status types for frontend updates."""
    IDLE = "idle"
    THINKING = "thinking"
    DEFINING_INTENT = "defining_intent"
    SELECTING_SKILLS = "selecting_skills"
    EXECUTING_SKILL = "executing_skill"
    FORMATTING_ANSWER = "formatting_answer"
    COMPLETE = "complete"
    ERROR = "error"

# ==================== Logging Setup ====================
# Use a flag to prevent duplicate handler addition
if not hasattr(logging, '_chatbot_logger_configured'):
    logging._chatbot_logger_configured = True
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

logger = logging.getLogger("chatbot")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Prevent propagation to root logger

# Only add handler if logger doesn't have any
if not logger.handlers:
    # Color formatter for console
    class ColorFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'LLM': '\033[35m',      # Magenta for LLM
            'TOOL': '\033[34m',     # Blue for tools
            'SKILL': '\033[36m',    # Cyan for skills
            'DISCOVERY': '\033[33m', # Yellow for discovery
            'SELECT': '\033[32m',   # Green for selection
            'EXECUTE': '\033[34m',  # Blue for execution
            'FORMAT': '\033[35m',   # Magenta for formatting
            'TIMING': '\033[33m',   # Yellow for timing
            'STATUS': '\033[36m',   # Cyan for status
            'STAGE': '\033[32m',    # Green for stage
            'SCHEMA': '\033[36m',   # Cyan for schema
            'CHAR': '\033[33m',     # Yellow for character count
            'RESET': '\033[0m'
        }
        
        def format(self, record):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            if hasattr(record, 'color'):
                color = self.COLORS.get(record.color, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
            return super().format(record)

    # Add custom log levels
    logging.addLevelName(25, "LLM")
    logging.addLevelName(26, "TOOL")
    logging.addLevelName(27, "SKILL")
    logging.addLevelName(28, "DISCOVERY")
    logging.addLevelName(29, "SELECT")
    logging.addLevelName(30, "EXECUTE")
    logging.addLevelName(31, "FORMAT")
    logging.addLevelName(32, "TIMING")
    logging.addLevelName(33, "STATUS")
    logging.addLevelName(34, "STAGE")
    logging.addLevelName(35, "SCHEMA")
    logging.addLevelName(36, "CHAR")

    def llm_log(self, message, *args, **kwargs):
        if self.isEnabledFor(25):
            self._log(25, message, args, **kwargs)

    def tool_log(self, message, *args, **kwargs):
        if self.isEnabledFor(26):
            self._log(26, message, args, **kwargs)
    
    def skill_log(self, message, *args, **kwargs):
        if self.isEnabledFor(27):
            self._log(27, message, args, **kwargs)
    
    def discovery_log(self, message, *args, **kwargs):
        if self.isEnabledFor(28):
            self._log(28, message, args, **kwargs)
    
    def select_log(self, message, *args, **kwargs):
        if self.isEnabledFor(29):
            self._log(29, message, args, **kwargs)
    
    def execute_log(self, message, *args, **kwargs):
        if self.isEnabledFor(30):
            self._log(30, message, args, **kwargs)
    
    def format_log(self, message, *args, **kwargs):
        if self.isEnabledFor(31):
            self._log(31, message, args, **kwargs)
    
    def timing_log(self, message, *args, **kwargs):
        if self.isEnabledFor(32):
            self._log(32, message, args, **kwargs)
    
    def status_log(self, message, *args, **kwargs):
        if self.isEnabledFor(33):
            self._log(33, message, args, **kwargs)
    
    def stage_log(self, message, *args, **kwargs):
        if self.isEnabledFor(34):
            self._log(34, message, args, **kwargs)
    
    def schema_log(self, message, *args, **kwargs):
        if self.isEnabledFor(35):
            self._log(35, message, args, **kwargs)
    
    def char_log(self, message, *args, **kwargs):
        if self.isEnabledFor(36):
            self._log(36, message, args, **kwargs)

    logging.Logger.llm = llm_log
    logging.Logger.tool = tool_log
    logging.Logger.skill = skill_log
    logging.Logger.discovery = discovery_log
    logging.Logger.select = select_log
    logging.Logger.execute = execute_log
    logging.Logger.format = format_log
    logging.Logger.timing = timing_log
    logging.Logger.status = status_log
    logging.Logger.stage = stage_log
    logging.Logger.schema = schema_log
    logging.Logger.char = char_log

    # Apply formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColorFormatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(console_handler)

# ==================== Path Setup ====================

current_dir = Path(__file__).parent.absolute()

paths_to_add = [
    str(current_dir / "skills"),
    str(current_dir / "skills" / "echo_skill"),
    str(current_dir / "skills" / "dax_query_skill"),
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)
        logger.debug(f"📁 Added to path: {path}")

# ==================== Import SkillKit ====================

SKILLKIT_AVAILABLE = False
SkillManager = None

try:
    from skillkit import SkillManager
    SKILLKIT_AVAILABLE = True
    logger.info("✅ SkillKit imported successfully!")
except ImportError as e:
    logger.warning(f"⚠️ SkillKit not available. Install with: pip install skillkit")
    logger.warning(f"   Error: {e}")

# ==================== LLM Configuration ====================

OLLAMA_HOST = "10.1.2.226"
OLLAMA_PORT = 11434
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
MODEL_NAME = "qwen3.5:35b"

# ==================== Skill Loading Helper ====================

def load_skill_from_directory(skill_dir: Path):
    """Load a skill from a directory by importing the Python module."""
    try:
        skill_path = str(skill_dir)
        if skill_path not in sys.path:
            sys.path.insert(0, skill_path)
        
        import_attempts = ['echo', skill_dir.name, f'{skill_dir.name}.echo']
        
        for attempt in import_attempts:
            try:
                logger.debug(f"   Attempting to import: {attempt}")
                module = importlib.import_module(attempt)
                
                if hasattr(module, 'create_skill'):
                    logger.debug(f"   Found create_skill in {attempt}")
                    skill_instance = module.create_skill()
                    return skill_instance
                
                if hasattr(module, 'EchoSkill'):
                    logger.debug(f"   Found EchoSkill in {attempt}")
                    skill_class = getattr(module, 'EchoSkill')
                    skill_instance = skill_class()
                    return skill_instance
            except ImportError as e:
                logger.debug(f"   Import failed for {attempt}: {e}")
                continue
        
        logger.warning(f"   Could not import skill from {skill_dir}")
        return None
    except Exception as e:
        logger.error(f"   Error loading skill from {skill_dir}: {e}")
        return None

# ==================== SkillKit Wrapper ====================

class SkillKitWrapper:
    """Wrapper for SkillKit to provide consistent interface with existing skill system."""
    
    def __init__(self):
        self.skill_manager = None
        self._initialized = False
        self._skill_cache = {}
        self._discovery_details = []
        
        if SKILLKIT_AVAILABLE and SkillManager:
            try:
                logger.discovery("=" * 80)
                logger.discovery("🔍 STARTING SKILL DISCOVERY")
                logger.discovery("=" * 80)
                
                logger.discovery("📋 Initializing SkillManager...")
                self.skill_manager = SkillManager()
                
                logger.discovery("🔎 Discovering skills...")
                self.skill_manager.discover()
                self._initialized = True
                
                self._cache_skills()
                self._log_discovery_details()
                self._load_python_skills()
                
                # Directly register DAX Query skill
                self._register_dax_query_skill()
                
                skills = self.get_skill_list()
                logger.discovery("=" * 80)
                logger.discovery(f"✅ DISCOVERY COMPLETE: {len(skills)} skill(s) found")
                logger.discovery("=" * 80)
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize SkillKit: {e}")
                self._initialized = False
    
    def _register_dax_query_skill(self):
        """Directly register the DAX Query skill."""
        try:
            from skills.dax_query_skill.dax_query import DAXQuerySkill, create_skill
            skill_instance = create_skill()
            if hasattr(skill_instance, 'execute'):
                self._skill_cache[skill_instance.name] = skill_instance
                logger.discovery(f"   ✅ Directly registered DAX Query skill: {skill_instance.name}")
                return True
            return False
        except Exception as e:
            logger.warning(f"   ⚠️ Error registering DAX Query skill: {e}")
            return False
    
    def _load_python_skills(self):
        """Manually load skills from Python files in the skills directory."""
        skills_dir = Path(__file__).parent / "skills"
        if not skills_dir.exists():
            return
        
        logger.discovery("📦 Manually loading Python skills...")
        for skill_folder in skills_dir.iterdir():
            if skill_folder.is_dir():
                py_files = list(skill_folder.glob("*.py"))
                if py_files:
                    skill_instance = load_skill_from_directory(skill_folder)
                    if skill_instance and hasattr(skill_instance, 'execute'):
                        self._skill_cache[skill_instance.name] = skill_instance
                        logger.discovery(f"   ✅ Manually loaded skill: {skill_instance.name}")
    
    def _log_discovery_details(self):
        """Log detailed discovery information."""
        try:
            skills = self.skill_manager.list_skills() if hasattr(self.skill_manager, 'list_skills') else []
            if skills:
                logger.discovery(f"📦 Found {len(skills)} skill(s) from SkillKit")
        except Exception as e:
            logger.error(f"❌ Failed to log discovery details: {e}")
    
    def _cache_skills(self):
        """Cache discovered skills."""
        if not self.skill_manager:
            return
        try:
            skills = self.skill_manager.list_skills()
            for skill in skills:
                self._skill_cache[skill.name] = skill
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache skills: {e}")
    
    def get_skill_list(self) -> List[Dict[str, Any]]:
        if not self._initialized or not self.skill_manager:
            return []
        skills = []
        try:
            for skill in self.skill_manager.list_skills():
                skills.append({
                    'name': skill.name,
                    'description': skill.description,
                    'source': 'skillkit',
                    'version': getattr(skill, 'version', 'unknown'),
                    'category': getattr(skill, 'category', 'general')
                })
        except Exception as e:
            logger.warning(f"⚠️ Failed to get skill list: {e}")
        return skills
    
    def get_skill_by_name(self, skill_name: str):
        return self._skill_cache.get(skill_name)
    
    def get_skill_documentation(self, skill_name: str) -> str:
        """Get the full SKILL.md content for a skill."""
        try:
            skill = self.get_skill_by_name(skill_name)
            if skill and hasattr(skill, 'get_skill_documentation'):
                return skill.get_skill_documentation()
            
            skill_md_path = Path(__file__).parent / "skills" / f"{skill_name}_skill" / "SKILL.md"
            if not skill_md_path.exists():
                skill_md_path = Path(__file__).parent / "skills" / skill_name / "SKILL.md"
            
            if skill_md_path.exists():
                with open(skill_md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"📄 Loaded SKILL.md for {skill_name}: {len(content):,} characters")
                    return content
            else:
                logger.warning(f"⚠️ SKILL.md not found for {skill_name}")
                return ""
        except Exception as e:
            logger.warning(f"⚠️ Error loading SKILL.md for {skill_name}: {e}")
            return ""
    
    def execute_skill(self, skill_name: str, input_text: str, **kwargs) -> Dict[str, Any]:
        if not self._initialized:
            return {'success': False, 'error': 'SkillKit not initialized', 'skill': skill_name}
        
        try:
            skill = self._skill_cache.get(skill_name)
            if skill and hasattr(skill, 'execute'):
                result = skill.execute(input_text, **kwargs)
                return {
                    'success': True,
                    'result': result,
                    'skill': skill_name,
                    'input': input_text,
                    'source': 'skillkit-direct'
                }
            else:
                return {
                    'success': False,
                    'error': f"Skill '{skill_name}' not found or has no execute method",
                    'skill': skill_name
                }
        except Exception as e:
            logger.error(f"❌ Skill execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'skill': skill_name
            }
    
    def is_available(self) -> bool:
        return self._initialized
    
    def get_skill(self, skill_name: str):
        return self._skill_cache.get(skill_name)
    
    def get_discovery_details(self) -> List[Dict[str, Any]]:
        return self._discovery_details

# ==================== LLM Client ====================

class LLMClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = MODEL_NAME):
        self.base_url = base_url
        self.model = model
        self.timeout = 120
        self._check_connection()
    
    def _check_connection(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name') for m in models]
                if self.model not in model_names:
                    logger.warning(f"⚠️ Model '{self.model}' not found. Available: {', '.join(model_names)}")
                else:
                    logger.info(f"✅ Connected to Ollama, using model: {self.model}")
                return True
            return False
        except Exception as e:
            logger.warning(f"⚠️ Cannot connect to Ollama at {self.base_url}: {e}")
            return False
    
    def _count_chars(self, text: str, label: str = "") -> int:
        """Count characters and log the count with a label."""
        count = len(text)
        logger.char(f"📊 {label} character count: {count:,} chars")
        return count
    
    def _log_prompt_details(self, system_content: str, user_content: str, label: str = "Prompt"):
        """Log detailed prompt information including character count and preview."""
        total_chars = len(system_content) + len(user_content)
        logger.char("=" * 80)
        logger.char(f"📊 {label} - PROMPT ANALYSIS")
        logger.char("=" * 80)
        logger.char(f"📋 System prompt: {len(system_content):,} chars")
        logger.char(f"📋 User prompt: {len(user_content):,} chars")
        logger.char(f"📋 Total prompt: {total_chars:,} chars")
        
        if total_chars > 8000:
            logger.warning(f"⚠️ Prompt is quite long ({total_chars:,} chars). May exceed context window.")
        elif total_chars > 4000:
            logger.info(f"ℹ️ Prompt is moderately long ({total_chars:,} chars).")
        
        logger.char("=" * 80)
        return total_chars
    
    def _log_llm_messages(self, messages: List[Dict[str, str]], label: str = "LLM Request") -> str:
        """Log all messages sent to LLM to a file for debugging."""
        try:
            debug_dir = Path(__file__).parent / "debug"
            debug_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            debug_file = debug_dir / f"llm_messages_{timestamp}.txt"
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"LLM MESSAGES LOG - {datetime.now().isoformat()}\n")
                f.write(f"LABEL: {label}\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Total Messages: {len(messages)}\n")
                f.write(f"Model: {self.model}\n")
                f.write("-" * 40 + "\n\n")
                
                for i, msg in enumerate(messages):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    
                    f.write(f"=== MESSAGE {i+1}: {role.upper()} ===\n")
                    f.write(f"Length: {len(content):,} characters\n")
                    f.write("-" * 40 + "\n")
                    f.write(content + "\n")
                    f.write("\n" + "=" * 40 + "\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("END OF LOG\n")
                f.write("=" * 80 + "\n")
            
            logger.llm(f"💾 LLM messages saved to: {debug_file}")
            return str(debug_file)
        except Exception as e:
            logger.warning(f"Could not save LLM messages log: {e}")
            return ""
    
    def _save_debug_log(self, prompt_type: str, system_content: str, user_content: str, raw_response: str = "", 
                        question: str = "", elapsed: float = 0) -> str:
        """Save full debug logs including prompts and responses to file."""
        try:
            debug_dir = Path(__file__).parent / "debug"
            debug_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            debug_file = debug_dir / f"llm_debug_{timestamp}.txt"
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"LLM DEBUG LOG - {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"PROMPT TYPE: {prompt_type}\n")
                f.write(f"QUESTION: {question}\n")
                f.write(f"ELAPSED TIME: {elapsed:.2f}s\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("SYSTEM PROMPT (FULL):\n")
                f.write("=" * 80 + "\n")
                f.write(system_content + "\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("USER PROMPT (FULL):\n")
                f.write("=" * 80 + "\n")
                f.write(user_content + "\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("FULL RAW RESPONSE:\n")
                f.write("=" * 80 + "\n")
                if raw_response:
                    f.write(raw_response + "\n")
                else:
                    f.write("⚠️ EMPTY RESPONSE RECEIVED!\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("END OF LOG\n")
                f.write("=" * 80 + "\n")
            
            logger.llm(f"💾 Full debug log saved to: {debug_file}")
            return str(debug_file)
        except Exception as e:
            logger.warning(f"Could not save debug file: {e}")
            return ""
    
    def _extract_json_from_response(self, raw_response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from the raw response while preserving spaces.
        Handles multi-line JSON with newlines and indentation.
        """
        if not raw_response:
            return None
        
        logger.debug(f"📝 Attempting to extract JSON from response length: {len(raw_response)}")
        
        # Method 1: Try to parse the entire response as JSON
        try:
            result = json.loads(raw_response)
            logger.debug("✅ Extracted JSON using Method 1")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️ Method 1 failed: {e}")
        
        # Method 2: Remove markdown code blocks and try
        try:
            cleaned = re.sub(r'```json\s*', '', raw_response)
            cleaned = re.sub(r'```\s*', '', cleaned)
            cleaned = cleaned.strip()
            result = json.loads(cleaned)
            logger.debug("✅ Extracted JSON using Method 2")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️ Method 2 failed: {e}")
        
        # Method 3: Find JSON object with regex (preserve spaces)
        try:
            # Match JSON with proper structure, including nested objects
            pattern = r'\{[^{}]*\}'
            matches = re.findall(pattern, raw_response, re.DOTALL)
            for match in matches:
                try:
                    result = json.loads(match)
                    logger.debug("✅ Extracted JSON using Method 3")
                    return result
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.debug(f"⚠️ Method 3 failed: {e}")
        
        # Method 4: Remove ONLY newlines, but keep spaces
        try:
            # Remove newlines but keep spaces
            cleaned = raw_response.replace('\n', ' ').replace('\r', ' ')
            # Collapse multiple spaces to single space
            cleaned = re.sub(r'\s+', ' ', cleaned)
            # Find JSON object
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = cleaned[start:end]
                result = json.loads(json_str)
                logger.debug("✅ Extracted JSON using Method 4")
                return result
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️ Method 4 failed: {e}")
        
        # Method 5: Try to extract JSON with nested objects (complex pattern)
        try:
            # Match JSON with nested objects - more flexible pattern
            pattern = r'\{[^{}]*"skills_to_use"[^{}]*\}'
            matches = re.findall(pattern, raw_response, re.DOTALL)
            for match in matches:
                try:
                    result = json.loads(match)
                    logger.debug("✅ Extracted JSON using Method 5")
                    return result
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.debug(f"⚠️ Method 5 failed: {e}")
        
        # Method 6: Fix common JSON issues and try again
        try:
            start = raw_response.find('{')
            end = raw_response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw_response[start:end]
                # Remove newlines
                json_str = json_str.replace('\n', ' ').replace('\r', ' ')
                # Fix trailing commas
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*\]', ']', json_str)
                # Fix escaped quotes
                json_str = json_str.replace('\\"', '"')
                # Fix any double commas
                json_str = re.sub(r',\s*,', ',', json_str)
                result = json.loads(json_str)
                logger.debug("✅ Extracted JSON using Method 6")
                return result
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️ Method 6 failed: {e}")
        
        # Method 7: More aggressive cleaning - try to extract the JSON object
        try:
            # Remove everything before the first { and after the last }
            start = raw_response.find('{')
            end = raw_response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = raw_response[start:end]
                # Remove all newlines and extra spaces
                json_str = ' '.join(json_str.split())
                # Fix any broken JSON issues
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*\]', ']', json_str)
                json_str = json_str.replace('\\"', '"')
                # Remove trailing commas
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*\]', ']', json_str)
                result = json.loads(json_str)
                logger.debug("✅ Extracted JSON using Method 7")
                return result
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️ Method 7 failed: {e}")
        
        # Method 8: Try using a more lenient approach - find the JSON by looking for key patterns
        try:
            # Look for the pattern of a JSON object with skills_to_use
            patterns = [
                r'\{[^{}]*"skills_to_use"\s*:\s*\[[^\]]*\][^{}]*\}',
                r'\{[^{}]*"skill_parameters"\s*:\s*\{[^{}]*\}[^{}]*\}',
                r'\{[^{}]*"query_type"\s*:\s*"[^"]*"[^{}]*\}',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, raw_response, re.DOTALL)
                for match in matches:
                    try:
                        # Clean up the match
                        cleaned = ' '.join(match.split())
                        result = json.loads(cleaned)
                        logger.debug(f"✅ Extracted JSON using Method 8")
                        return result
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.debug(f"⚠️ Method 8 failed: {e}")
        
        logger.warning(f"⚠️ Could not extract JSON from response")
        logger.warning(f"   Response preview: {raw_response[:200]}...")
        return None
    
    def _generate_fallback_dax_query(self, question: str, schema_info: Optional[str] = None) -> Optional[str]:
        """Generate a DAX query based on the user's question when LLM fails."""
        question_lower = question.lower()
        dax_query = None
        
        if 'how many' in question_lower or 'count' in question_lower:
            if 'fail' in question_lower or 'failed' in question_lower:
                dax_query = "EVALUATE ROW(\"Failed Assets\", CALCULATE(COUNTROWS('Assets'), 'Assets'[Validation Result] = \"Fail\"))"
                logger.info("   🔍 Detected: Count failed assets")
            elif 'pass' in question_lower or 'passed' in question_lower:
                dax_query = "EVALUATE ROW(\"Passed Assets\", CALCULATE(COUNTROWS('Assets'), 'Assets'[Validation Result] = \"Pass\"))"
                logger.info("   🔍 Detected: Count passed assets")
            elif 'all' in question_lower or 'total' in question_lower:
                dax_query = "EVALUATE ROW(\"Total Assets\", COUNTROWS('Assets'))"
                logger.info("   🔍 Detected: Count all assets")
            elif 'asset' in question_lower:
                dax_query = "EVALUATE ROW(\"Total Assets\", COUNTROWS('Assets'))"
                logger.info("   🔍 Detected: Count all assets")
        elif 'table' in question_lower or 'schema' in question_lower:
            dax_query = "EVALUATE SELECTCOLUMNS(FILTER(INFO.VIEW.TABLES(), [IsHidden] = FALSE), 'Table Name', [Name], 'Table Description', [Description]) ORDER BY [Table Name]"
            logger.info("   🔍 Detected: Schema query")
        elif 'show' in question_lower or 'list' in question_lower or 'get' in question_lower:
            if 'asset' in question_lower:
                dax_query = "EVALUATE 'Assets'"
                logger.info("   🔍 Detected: Show all assets")
            elif 'progress' in question_lower:
                dax_query = "EVALUATE 'Assets_progress'"
                logger.info("   🔍 Detected: Show progress data")
            elif 'attribute' in question_lower:
                dax_query = "EVALUATE 'Assets_attributes'"
                logger.info("   🔍 Detected: Show attributes")
        
        return dax_query
    
    def _clean_key(self, key: str) -> str:
        """Remove brackets from key if present."""
        if key.startswith('[') and key.endswith(']'):
            return key[1:-1]
        if key.startswith('Assets[') and key.endswith(']'):
            return key[7:-1]
        return key
    
    def _extract_value_from_row(self, row: Dict[str, Any], field: str, default: str = "") -> str:
        """Extract a value from a row, handling both direct keys and attribute_json."""
        cleaned_field = self._clean_key(field)
        
        # Try exact match
        if field in row:
            val = row[field]
            if val is not None and str(val).strip():
                return str(val).strip()
        
        # Try with cleaned field
        if cleaned_field in row:
            val = row[cleaned_field]
            if val is not None and str(val).strip():
                return str(val).strip()
        
        # Try with bracket format: Assets[field]
        bracketed = f"Assets[{cleaned_field}]"
        if bracketed in row:
            val = row[bracketed]
            if val is not None and str(val).strip():
                return str(val).strip()
        
        # Try with bracket format: [field]
        bracketed2 = f"[{cleaned_field}]"
        if bracketed2 in row:
            val = row[bracketed2]
            if val is not None and str(val).strip():
                return str(val).strip()
        
        # Try to extract from attribute_json
        attr_json = row.get('Assets[attribute_json]', row.get('attribute_json', row.get('[attribute_json]', '')))
        if attr_json:
            try:
                data = json.loads(attr_json)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k == field or k == cleaned_field:
                            return str(v) if v is not None else default
                    for k, v in data.items():
                        if k.lower() == field.lower() or k.lower() == cleaned_field.lower():
                            return str(v) if v is not None else default
            except json.JSONDecodeError:
                pass
        
        return default
    
    def _build_detailed_summary(self, rows: List[Dict]) -> Dict[str, Any]:
        """Build a detailed summary with distributions and statistics."""
        if not rows:
            return {
                'total': 0,
                'validation': {'pass': 0, 'fail': 0, 'other': 0},
                'distributions': {},
                'top_validation_issues': [],
                'display_fields': [],
                'field_mapping': {}
            }
        
        # Field mapping
        field_mapping = {
            'CEDD_I_AssetID': 'Asset ID',
            'client_asset_id': 'Asset ID',
            'Family Name': 'Family Name',
            'Validation Result': 'Validation Result',
            'Validation Remarks': 'Validation Remarks',
            'Space ID': 'Space ID',
            'CEDD_I_SpaceID': 'Space ID',
            'CAT Code': 'CAT Code'
        }
        
        # Determine which fields exist
        sample_row = rows[0]
        display_fields = []
        for key, display_name in field_mapping.items():
            exists = False
            for row_key in sample_row.keys():
                clean_row_key = self._clean_key(row_key)
                if clean_row_key == key:
                    exists = True
                    break
            if not exists:
                attr_json = sample_row.get('Assets[attribute_json]', sample_row.get('attribute_json', ''))
                if attr_json:
                    try:
                        data_obj = json.loads(attr_json)
                        if isinstance(data_obj, dict) and key in data_obj:
                            exists = True
                    except:
                        pass
            if exists and display_name not in display_fields:
                display_fields.append(display_name)
        
        if not display_fields:
            display_fields = ['Asset ID', 'Family Name', 'Validation Result', 'Validation Remarks']
        
        # Build distributions
        distributions = defaultdict(Counter)
        remarks_counter = Counter()
        cat_code_counter = Counter()
        
        validation_counts = {'pass': 0, 'fail': 0, 'other': 0}
        
        for row in rows:
            # Count pass/fail
            result_val = self._extract_value_from_row(row, 'Validation Result', '')
            if 'Pass' in result_val:
                validation_counts['pass'] += 1
            elif 'Fail' in result_val or 'Validation Failed' in result_val:
                validation_counts['fail'] += 1
            else:
                validation_counts['other'] += 1
            
            # Collect distributions for display fields
            for field in display_fields:
                key = None
                for k, v in field_mapping.items():
                    if v == field:
                        key = k
                        break
                if key:
                    value = self._extract_value_from_row(row, key, 'Unknown')
                    distributions[field][value] += 1
            
            # Collect validation remarks
            remark = self._extract_value_from_row(row, 'Validation Remarks', '')
            if remark:
                import re
                cat_match = re.search(r"CAT Code\s*'([^']+)'", remark)
                if cat_match:
                    cat_code = cat_match.group(1)
                    remarks_counter[f"CAT Code '{cat_code}' not found"] += 1
                    cat_code_counter[cat_code] += 1
                else:
                    remarks_counter[remark] += 1
        
        # Build top validation issues
        top_issues = []
        for issue, count in remarks_counter.most_common(10):
            top_issues.append({'issue': issue, 'count': count})
        
        return {
            'total': len(rows),
            'validation': validation_counts,
            'distributions': distributions,
            'top_validation_issues': top_issues,
            'display_fields': display_fields,
            'field_mapping': field_mapping
        }
    
    def _build_aggregate_result(self, label: str, value: Any, dax_query: str = "") -> str:
        """
        Build a clean aggregate result for the LLM.
        Only shows the single value, no table or distributions.
        """
        lines = []
        
        if dax_query:
            lines.append(f"**DAX Query Used:** `{dax_query}`")
            lines.append("")
        
        lines.append(f"## 📊 Query Result")
        lines.append("")
        lines.append(f"### {label}: **{value}**")
        lines.append("")
        lines.append(f"*This is a single value result from an aggregate query.*")
        
        return "\n".join(lines)
    
    def _build_comprehensive_result(self, skill_results: List[Dict[str, Any]], all_rows: List[Dict], dax_query: str = "", max_sample_rows: int = 5) -> str:
        """
        Build a comprehensive result text for the LLM.
        Only includes a SAMPLE of the data (first 5 rows) for context.
        """
        lines = []
        
        # DAX Query
        if dax_query:
            lines.append(f"**DAX Query Used:** `{dax_query}`")
            lines.append("")
        
        # Get summary from data
        total_rows = len(all_rows)
        lines.append(f"## 📊 Query Results")
        lines.append(f"**Total Rows:** {total_rows}")
        lines.append("")
        
        if total_rows == 0:
            lines.append("### ℹ️ No data found")
            lines.append("")
            lines.append("The query returned 0 rows. This means no records matched the criteria.")
            return "\n".join(lines)
        
        # Build summary statistics
        summary = self._build_detailed_summary(all_rows)
        
        # Add summary section
        lines.append("### 📈 Summary Statistics")
        lines.append("")
        lines.append(f"- **Total records in this result:** {summary['total']}")
        lines.append(f"- **Passed:** {summary['validation']['pass']}")
        lines.append(f"- **Failed:** {summary['validation']['fail']}")
        lines.append(f"- **Other:** {summary['validation']['other']}")
        lines.append("")
        
        if summary['total'] > 0:
            pass_rate = summary['validation']['pass'] / summary['total'] * 100
            fail_rate = summary['validation']['fail'] / summary['total'] * 100
            lines.append(f"**Pass Rate:** {pass_rate:.1f}%")
            lines.append(f"**Fail Rate:** {fail_rate:.1f}%")
            lines.append("")
        
        # Add field distributions (only top values)
        lines.append("### 📊 Field Distributions")
        lines.append("")
        
        for field_name, distribution in summary.get('distributions', {}).items():
            if distribution:
                lines.append(f"**{field_name}:**")
                # Only show top 3 values to keep it concise
                for value, count in list(distribution.items())[:3]:
                    percentage = count / summary['total'] * 100
                    lines.append(f"  - `{value}`: {count} ({percentage:.1f}%)")
                if len(distribution) > 3:
                    lines.append(f"  - ... and {len(distribution) - 3} more values")
                lines.append("")
        
        # Add top validation issues
        if summary.get('top_validation_issues'):
            lines.append("### 🔴 Top Validation Issues")
            lines.append("")
            for issue in summary['top_validation_issues'][:3]:
                lines.append(f"- **{issue['issue']}**: {issue['count']} assets")
            lines.append("")
        
        # Add sample data (ONLY FIRST 5 rows for context)
        lines.append(f"### 📋 Sample Data (First {min(max_sample_rows, total_rows)} rows)")
        lines.append("")
        lines.append("| # | " + " | ".join(summary['display_fields']) + " |")
        lines.append("| " + " | ".join(["---"] * (len(summary['display_fields']) + 1)) + " |")
        
        sample_rows = all_rows[:max_sample_rows]
        for idx, row in enumerate(sample_rows, 1):
            row_values = [str(idx)]
            for field in summary['display_fields']:
                key = None
                for k, v in summary['field_mapping'].items():
                    if v == field:
                        key = k
                        break
                if key:
                    value = self._extract_value_from_row(row, key, '')
                    row_values.append(str(value) if value else '')
                else:
                    row_values.append('')
            lines.append("| " + " | ".join(row_values) + " |")
        
        if total_rows > max_sample_rows:
            lines.append(f"\n*... and {total_rows - max_sample_rows} more rows*")
        
        # Add context note
        lines.append("")
        lines.append("*⚠️ This is a filtered result set. The counts above represent assets matching the filter criteria, not the total asset population.*")
        
        return "\n".join(lines)
    
    def _get_result_context(self, skill_results: List[Dict[str, Any]], dax_query: str = "") -> str:
        """
        Generate context about the results based on the DAX query used.
        """
        if not dax_query:
            return "The results are from a data query."
        
        context = []
        dax_lower = dax_query.lower()
        
        # Check if this is a filtered query
        if "filter" in dax_lower or "where" in dax_lower or "=" in dax_lower:
            context.append("- This is a **filtered result set**. The count represents assets matching specific criteria, not all assets.")
            
            filter_match = re.search(r"FILTER\s*\([^,]+,\s*([^)]+)\)", dax_query)
            if filter_match:
                context.append(f"- Filter condition: `{filter_match.group(1)}`")
        
        # Check if it's counting failed assets
        if "fail" in dax_lower:
            context.append("- The count represents **failed assets only**.")
        
        # Check if it's counting passed assets
        if "pass" in dax_lower:
            context.append("- The count represents **passed assets only**.")
        
        # If it's just a table query (no filter)
        if "evaluate 'assets'" in dax_lower or "evaluate assets" in dax_lower:
            context.append("- This shows **all assets** in the dataset.")
        
        if not context:
            context.append("- The results are from a data query.")
        
        return "\n".join(context)
    
    # ==================== LAYER 1: AI - Detect Intent and Select Skills ====================
    
    def detect_intent_and_select_skills(self, question: str, available_skills: List[Dict[str, Any]], 
                                    schema_info: Optional[str] = None,
                                    skill_documentation: Optional[str] = None,
                                    status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        AI Layer 1: Use LLM to detect intent AND determine which skill(s) to use.
        Passes BOTH schema_info and full SKILL.md to the LLM.
        """
        start_time = time.time()
        
        if status_callback:
            status_callback({
                'status': 'defining_intent',
                'message': '🎯 Defining user intent...',
                'stage': 1,
                'total_stages': 3,
                'stage_name': 'AI Call 1: Detect Intent & Select Skill'
            })
            logger.stage("📊 [STAGE 1/3] START: AI Call 1 - Detect Intent & Select Skill")
        
        logger.timing("⏱️ [AI Call 1] START: Define User Intent & Select Skill")
        logger.llm("🧠 [AI Call 1] Purpose: Analyzing user query to determine intent")
        
        skill_descriptions = []
        for skill in available_skills:
            skill_name = skill.get('name', '')
            skill_desc = skill.get('description', '')
            skill_descriptions.append(f"- {skill_name}: {skill_desc}")
        
        skill_descriptions_text = "\n".join(skill_descriptions) if skill_descriptions else "No skills available"
        
        if available_skills and available_skills[0].get('name') == 'dax_query':
            doc_text = skill_documentation if skill_documentation else "No documentation available"
            
            system_content = f"""You are an AI assistant that generates DAX queries for Power BI.

    ## SKILL DOCUMENTATION (Full SKILL.md):
    {doc_text}

    ## Database Schema Information:
    {schema_info if schema_info else "No schema available"}

    ## User Question:
    {question}

    ## CRITICAL - CORRECT FILTER VALUES:
    The Validation Result column in the Assets table has these exact values:
    - **"Validation Failed"** (for failed assets)
    - **"Validation Pass"** (for passed assets)

    **IMPORTANT:** Use the EXACT values above. Do NOT use "Fail", "Pass", "Validation Passed", or any other variations.

    ## CRITICAL CONTEXT UNDERSTANDING:
    When a user asks "how many assets failed?" or similar filtered questions:
    1. The DAX query filters for specific conditions (e.g., Validation Result = "Validation Failed")
    2. The result count is the NUMBER OF FAILED ASSETS ONLY
    3. This is NOT the total number of all assets in the system

    ## Task:
    Generate the appropriate DAX query to answer the user's question.

    **CRITICAL RULES:**
    1. All DAX queries MUST start with EVALUATE
    2. Table names MUST be in single quotes: 'Assets'
    3. Column names MUST be in square brackets: [Validation Result]
    4. String values MUST be in double quotes: "Validation Failed" or "Validation Pass"
    5. For scalar values, use ROW() or curly braces: {{COUNTROWS('Assets')}}
    6. For rate calculations, use DIVIDE function

    ## Response Format (JSON only):
    {{"query_type":"question","confidence":0.95,"skills_to_use":["dax_query"],"skill_parameters":{{"dax_query":"YOUR_DAX_QUERY_HERE"}},"entities":{{"topics":[],"subjects":[]}},"reasoning":"brief explanation"}}"""
            
            user_content = "Return the JSON only. No other text."
            
        elif available_skills and available_skills[0].get('name') == 'echo':
            doc_text = skill_documentation if skill_documentation else "No documentation available"
            
            system_content = f"""You are an AI assistant that handles echo requests.

    ## SKILL DOCUMENTATION (Full SKILL.md):
    {doc_text}

    ## User Request:
    {question}

    ## Task:
    Generate the appropriate parameters for the echo skill.

    ## Response Format (JSON only):
    {{"query_type":"testing","skills_to_use":["echo"],"skill_parameters":{{"input_text":"the text to echo"}},"reasoning":"brief explanation"}}"""
            
            user_content = "Return JSON only."
        else:
            system_content = "You analyze user queries. Return JSON for general conversation."
            user_content = f'User: "{question}"\nReturn JSON: {{"query_type":"general","confidence":0.9,"skills_to_use":[],"skill_parameters":{{}},"entities":{{"topics":["general"],"subjects":[]}},"reasoning":"General conversation"}}'
        
        total_chars = len(system_content) + len(user_content)
        logger.char("=" * 80)
        logger.char(f"📊 AI CALL 1 - PROMPT ANALYSIS")
        logger.char("=" * 80)
        logger.char(f"📋 System prompt: {len(system_content):,} chars")
        logger.char(f"📋 User prompt: {len(user_content):,} chars")
        logger.char(f"📋 Total prompt: {total_chars:,} chars")
        logger.char("-" * 40)
        logger.char("📝 FULL SYSTEM PROMPT:")
        logger.char("-" * 40)
        if len(system_content) > 1000:
            logger.char(f"{system_content[:1000]}...")
            logger.char(f"... (truncated, total {len(system_content):,} chars)")
        else:
            logger.char(system_content)
        logger.char("-" * 40)
        logger.char(f"📝 USER PROMPT: {user_content}")
        logger.char("=" * 80)
        
        try:
            url = f"{self.base_url}/api/chat"
            
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
            
            log_file = self._log_llm_messages(messages, "AI Call 1 - Detect Intent & Select Skills")
            logger.llm(f"💾 AI Call 1 messages logged to: {log_file}")
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 600
                }
            }
            
            logger.char(f"📤 Sending request to Ollama...")
            logger.char(f"   URL: {url}")
            logger.char(f"   Model: {self.model}")
            logger.char(f"   Messages: {len(messages)}")
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            raw_response = result.get("message", {}).get("content", "").strip()
            
            elapsed = time.time() - start_time
            
            logger.llm("=" * 80)
            logger.llm("📥 RAW AI RESPONSE - AI CALL 1")
            logger.llm("=" * 80)
            logger.llm(f"⏱️ Response time: {elapsed:.2f}s")
            logger.llm(f"📏 Raw response length: {len(raw_response):,} characters")
            logger.llm("-" * 40)
            logger.llm("📝 FULL RAW RESPONSE:")
            logger.llm("-" * 40)
            if raw_response:
                logger.llm(raw_response)
            else:
                logger.llm("⚠️ EMPTY RESPONSE RECEIVED!")
            logger.llm("-" * 40)
            logger.llm("=" * 80)
            
            try:
                debug_dir = Path(__file__).parent / "debug"
                debug_dir.mkdir(exist_ok=True)
                debug_file = debug_dir / f"llm_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== LLM RESPONSE ===\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Question: {question}\n")
                    f.write(f"Response length: {len(raw_response)}\n")
                    f.write(f"=== FULL RESPONSE ===\n")
                    f.write(raw_response)
                    f.write(f"\n=== END ===\n")
                logger.llm(f"💾 Raw response saved to: {debug_file}")
            except Exception as e:
                logger.warning(f"Could not save debug file: {e}")
            
            if not raw_response:
                logger.warning("⚠️ Empty response from LLM, using fallback")
                dax_query = self._generate_fallback_dax_query(question, schema_info)
                if dax_query:
                    return {
                        'query_type': 'question',
                        'confidence': 0.8,
                        'skills_to_use': ['dax_query'],
                        'skill_parameters': {'dax_query': dax_query},
                        'entities': {'topics': ['data'], 'subjects': []},
                        'reasoning': 'Generated DAX query from question (LLM returned empty)'
                    }
                else:
                    return self._fallback_detection(question, available_skills)
            
            # ============================================================
            # STEP 1: Extract JSON from the raw response
            # ============================================================
            logger.llm("🔄 Attempting to extract JSON from response...")
            intent_data = self._extract_json_from_response(raw_response)
            
            # Try to find DAX query in response if JSON extraction failed
            dax_query_in_response = None
            if not intent_data:
                logger.llm("🔍 JSON extraction failed, trying to find DAX query in raw response...")
                try:
                    # Look for EVALUATE pattern
                    dax_pattern = r'EVALUATE\s+[^"]+'
                    dax_matches = re.findall(dax_pattern, raw_response)
                    if dax_matches:
                        dax_query_in_response = dax_matches[0].strip()
                        # Clean up the DAX query - remove extra spaces and newlines
                        dax_query_in_response = ' '.join(dax_query_in_response.split())
                        logger.llm(f"🔍 Found DAX query in response: {dax_query_in_response}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not find DAX query in response: {e}")
            
            if intent_data:
                # ============================================================
                # STEP 2: Process the extracted JSON
                # ============================================================
                skills_to_use = intent_data.get('skills_to_use', [])
                logger.llm(f"🎯 Skills to use: {skills_to_use}")
                
                # Get the DAX query from skill_parameters
                dax_query = intent_data.get('skill_parameters', {}).get('dax_query')
                
                # ============================================================
                # STEP 3: Fix skills_to_use if empty but DAX query exists
                # ============================================================
                if dax_query and not skills_to_use:
                    logger.warning("⚠️ DAX query found but skills_to_use empty. Auto-fixing...")
                    intent_data['skills_to_use'] = ['dax_query']
                    skills_to_use = ['dax_query']
                    logger.llm(f"✅ Fixed skills_to_use: {skills_to_use}")
                
                # ============================================================
                # STEP 4: Clean and validate DAX query
                # ============================================================
                if dax_query:
                    # Clean the DAX query - remove extra newlines and spaces
                    cleaned_dax = ' '.join(dax_query.split())
                    if cleaned_dax != dax_query:
                        intent_data['skill_parameters']['dax_query'] = cleaned_dax
                        logger.llm(f"📝 Cleaned DAX query: {cleaned_dax}")
                        dax_query = cleaned_dax
                    
                    # Auto-correct filter values
                    # "Validation Failed" is correct - keep it
                    if '"Validation Failed"' in dax_query:
                        logger.info("✅ DAX query uses correct value 'Validation Failed'")
                    
                    # "Validation Pass" is correct - keep it
                    if '"Validation Pass"' in dax_query:
                        logger.info("✅ DAX query uses correct value 'Validation Pass'")
                    
                    # "Fail" -> "Validation Failed"
                    if '"Fail"' in dax_query and 'Validation Result' in dax_query:
                        logger.info("⚠️ DAX query uses 'Fail' - correcting to 'Validation Failed'")
                        corrected_query = dax_query.replace('"Fail"', '"Validation Failed"')
                        if corrected_query != dax_query:
                            intent_data['skill_parameters']['dax_query'] = corrected_query
                            logger.llm(f"📝 Auto-corrected DAX query: {corrected_query}")
                            dax_query = corrected_query
                    
                    # "Pass" -> "Validation Pass"
                    if '"Pass"' in dax_query and 'Validation Result' in dax_query:
                        logger.info("⚠️ DAX query uses 'Pass' - correcting to 'Validation Pass'")
                        corrected_query = dax_query.replace('"Pass"', '"Validation Pass"')
                        if corrected_query != dax_query:
                            intent_data['skill_parameters']['dax_query'] = corrected_query
                            logger.llm(f"📝 Auto-corrected DAX query: {corrected_query}")
                            dax_query = corrected_query
                    
                    # "Validation Passed" -> "Validation Pass"
                    if '"Validation Passed"' in dax_query:
                        logger.info("⚠️ DAX query uses 'Validation Passed' - correcting to 'Validation Pass'")
                        corrected_query = dax_query.replace('"Validation Passed"', '"Validation Pass"')
                        if corrected_query != dax_query:
                            intent_data['skill_parameters']['dax_query'] = corrected_query
                            logger.llm(f"📝 Auto-corrected DAX query: {corrected_query}")
                            dax_query = corrected_query
                    
                    # Log the final DAX query
                    final_dax = intent_data.get('skill_parameters', {}).get('dax_query')
                    logger.llm(f"📝 Final DAX Query: {final_dax}")
                
                else:
                    # No DAX query in skill_parameters, try to find it in the raw response
                    if dax_query_in_response:
                        intent_data['skill_parameters'] = {'dax_query': dax_query_in_response}
                        intent_data['skills_to_use'] = ['dax_query']
                        logger.llm(f"📝 Extracted DAX from response: {dax_query_in_response}")
                    else:
                        # Try fallback
                        dax_query = self._generate_fallback_dax_query(question, schema_info)
                        if dax_query:
                            intent_data['skill_parameters'] = {'dax_query': dax_query}
                            intent_data['skills_to_use'] = ['dax_query']
                            logger.llm(f"📝 Fallback DAX: {dax_query}")
                
                return intent_data
            else:
                # JSON extraction failed
                if dax_query_in_response:
                    logger.info(f"✅ Using DAX from response: {dax_query_in_response}")
                    return {
                        'query_type': 'question',
                        'confidence': 0.8,
                        'skills_to_use': ['dax_query'],
                        'skill_parameters': {'dax_query': dax_query_in_response},
                        'entities': {'topics': ['data'], 'subjects': []},
                        'reasoning': 'Extracted DAX query from LLM response'
                    }
                
                logger.info("🔄 Attempting to generate DAX query from question...")
                dax_query = self._generate_fallback_dax_query(question, schema_info)
                
                if dax_query:
                    return {
                        'query_type': 'question',
                        'confidence': 0.8,
                        'skills_to_use': ['dax_query'],
                        'skill_parameters': {'dax_query': dax_query},
                        'entities': {'topics': ['data'], 'subjects': []},
                        'reasoning': 'Generated DAX query from question'
                    }
                else:
                    return self._fallback_detection(question, available_skills)
                        
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Intent detection failed after {elapsed:.2f}s: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_detection(question, available_skills)
    
    def _fallback_detection(self, question: str, available_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback intent detection."""
        question_lower = question.lower()
        
        skills_to_use = []
        skill_params = {}
        
        if question_lower.startswith('echo'):
            skills_to_use = ['echo']
            parts = question.split(' ', 1)
            if len(parts) > 1:
                skill_params['input_text'] = parts[1]
            else:
                skill_params['input_text'] = 'echo'
        elif available_skills and available_skills[0].get('name') == 'dax_query':
            dax_query = self._generate_fallback_dax_query(question, None)
            if dax_query:
                skills_to_use = ['dax_query']
                skill_params = {'dax_query': dax_query}
                logger.info(f"🔍 Fallback generated DAX query: {dax_query}")
            else:
                skills_to_use = ['dax_query']
                skill_params = {'get_schema': True}
                logger.info("🔍 Fallback: Using dax_query for schema")
        
        return {
            'query_type': 'question',
            'confidence': 0.7,
            'skills_to_use': skills_to_use,
            'skill_parameters': skill_params,
            'entities': {'topics': [], 'subjects': []},
            'reasoning': 'Fallback detection'
        }
    
    # ==================== LAYER 5: AI - Format Final Answer ====================
    
    def format_final_answer(self, question: str, skill_results: List[Dict[str, Any]], 
                        intent: Dict[str, Any], system_prompt: str,
                        conversation_history: List[Dict],
                        status_callback: Optional[Callable] = None) -> str:
        """
        AI Layer 3: Use LLM to format the final answer based on skill results.
        Passes ONLY a SAMPLE (first 5 rows) to the LLM for context.
        """
        start_time = time.time()
        
        if status_callback:
            status_callback({
                'status': 'formatting_answer',
                'message': '✍️ Formatting your answer...',
                'stage': 3,
                'total_stages': 3,
                'stage_name': 'AI Call 3: Format Final Answer'
            })
            logger.stage("📊 [STAGE 3/3] START: AI Call 3 - Format Final Answer")
        
        logger.timing("⏱️ [AI Call 3] START: Formatting Final Answer")
        logger.format("🧠 [AI Call 3] Purpose: Generating conversational response")
        
        messages = []
        enhanced_prompt = system_prompt
        
        if skill_results:
            result_texts = []
            dax_query_used = None
            all_rows_data = []
            is_aggregate = False
            aggregate_label = None
            aggregate_value = None
            
            for r in skill_results:
                if r.get('success'):
                    resp = r.get('response', '')
                    if resp:
                        result_texts.append(resp)
                    if r.get('dax_query'):
                        dax_query_used = r.get('dax_query')
                    
                    # Extract data
                    data = r.get('data', {})
                    if isinstance(data, dict):
                        if data.get('is_aggregate', False):
                            is_aggregate = True
                            aggregate_label = data.get('aggregate_label', 'Result')
                            aggregate_value = data.get('aggregate_value', 'N/A')
                            logger.info(f"📊 Detected aggregate result: {aggregate_label} = {aggregate_value}")
                        
                        rows = data.get('rows', [])
                        if rows:
                            all_rows_data.extend(rows)
                            logger.info(f"📊 Found {len(rows)} rows in result")
            
            # Build result text based on query type with REDUCED sample size
            if is_aggregate:
                full_result_text = self._build_aggregate_result(aggregate_label, aggregate_value, dax_query_used)
            else:
                # Only pass 5 rows to LLM for context
                full_result_text = self._build_comprehensive_result(skill_results, all_rows_data, dax_query_used, max_sample_rows=5)
            
            if full_result_text:
                enhanced_prompt += f"""
    CRITICAL INSTRUCTION:

    The skill(s) have been executed and returned the following result(s):

    RESULT(S):
    {full_result_text}

    **IMPORTANT CONTEXT ABOUT THE RESULTS:**
    {self._get_result_context(skill_results, dax_query_used)}

    YOUR TASK:
    1. Use the EXACT RESULT(S) above to answer the user.
    2. Format the response to be conversational and helpful.
    3. Do NOT make up new information. Use ONLY the provided result(s).
    4. Be clear about what the numbers represent.
    5. Provide a summary and key insights from the data.

    The user asked: "{question}"

    Your response MUST be based on the result(s) above. Keep it friendly and concise."""
        
        messages.append({"role": "system", "content": enhanced_prompt})
        
        context = f"User question: {question}"
        if skill_results:
            context += f"\n\nSkill Results:"
            for i, result in enumerate(skill_results, 1):
                if result.get('success'):
                    response_text = result.get('response', 'No response')
                    context += f"\n{i}. Skill '{result.get('skill', 'unknown')}' returned:\n   {response_text}"
                else:
                    context += f"\n{i}. Skill '{result.get('skill', 'unknown')}' failed: {result.get('error', 'Unknown error')}"
        
        messages.append({"role": "user", "content": context})
        
        logger.char("=" * 80)
        logger.char("📊 AI CALL 3 - MESSAGES ANALYSIS")
        logger.char("=" * 80)
        
        total_chars = 0
        for i, msg in enumerate(messages):
            content = msg.get('content', '')
            char_count = len(content)
            total_chars += char_count
            logger.char(f"   [{i}] {msg.get('role')}: {char_count:,} chars")
        
        logger.char(f"   Total messages: {len(messages)}")
        logger.char(f"   Total characters: {total_chars:,}")
        logger.char("=" * 80)
        
        llm_response = self.chat(messages, temperature=0.7, label="AI Call 3 - Format Final Answer")
        
        elapsed = time.time() - start_time
        logger.timing(f"⏱️ [AI Call 3] COMPLETED: {elapsed:.2f}s")
        logger.stage(f"✅ [STAGE 3/3] COMPLETE: AI Call 3 - Format Final Answer ({elapsed:.2f}s)")
        
        if llm_response['success']:
            response = llm_response['response']
            logger.char(f"📝 Final response length: {len(response):,} chars")
            
            if status_callback:
                status_callback({
                    'status': 'complete',
                    'message': '✅ Response ready!',
                    'stage': 3,
                    'total_stages': 3,
                    'stage_name': 'AI Call 3: Format Final Answer'
                })
            return response
        else:
            if status_callback:
                status_callback({
                    'status': 'error',
                    'message': f'❌ Error formatting answer: {llm_response.get("error")}',
                    'stage': 3,
                    'total_stages': 3,
                    'stage_name': 'AI Call 3: Format Final Answer'
                })
            
            if skill_results:
                responses = []
                for r in skill_results:
                    if r.get('success'):
                        resp = r.get('response', str(r))
                        if resp:
                            responses.append(resp)
                return "\n".join(responses) if responses else "No response from skills."
            return f"I received: '{question}'. How can I help you?"
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, label: str = "Chat") -> Dict[str, Any]:
        """Send messages to LLM with full logging."""
        try:
            log_file = self._log_llm_messages(messages, f"{label} - Temp {temperature}")
            
            url = f"{self.base_url}/api/chat"
            
            logger.format("=" * 80)
            logger.format("📤 LLM FORMATTING REQUEST")
            logger.format("=" * 80)
            logger.format(f"Label: {label}")
            logger.format(f"Model: {self.model}")
            logger.format(f"Temperature: {temperature}")
            logger.format(f"Messages: {len(messages)}")
            logger.format(f"💾 Messages logged to: {log_file}")
            
            total_chars = 0
            for i, msg in enumerate(messages):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                char_count = len(content)
                total_chars += char_count
                if content and isinstance(content, str):
                    display_content = content[:300] if len(content) > 300 else content
                else:
                    display_content = str(content) if content else ''
                logger.format(f"  [{i}] {role}: {char_count:,} chars - {display_content}")
            
            logger.format(f"   Total characters: {total_chars:,}")
            logger.format("=" * 80)
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature}
            }
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            llm_response = result.get("message", {}).get("content", "")
            
            try:
                debug_dir = Path(__file__).parent / "debug"
                debug_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                response_file = debug_dir / f"llm_response_{timestamp}.txt"
                with open(response_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write(f"LLM RESPONSE - {datetime.now().isoformat()}\n")
                    f.write(f"LABEL: {label}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(f"Response length: {len(llm_response):,} characters\n")
                    f.write("-" * 40 + "\n")
                    f.write(llm_response + "\n")
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("END OF RESPONSE\n")
                    f.write("=" * 80 + "\n")
                logger.llm(f"💾 Response saved to: {response_file}")
            except Exception as e:
                logger.warning(f"Could not save response log: {e}")
            
            logger.format("=" * 80)
            logger.format("📥 LLM FORMATTED RESPONSE")
            logger.format("=" * 80)
            logger.format(f"Response length: {len(llm_response):,} chars")
            if llm_response and isinstance(llm_response, str):
                logger.format(f"Response preview: {llm_response[:500]}{'...' if len(llm_response) > 500 else ''}")
            else:
                logger.format(f"Response: {str(llm_response)}")
            logger.format("=" * 80)
            
            return {
                "success": True,
                "response": llm_response,
                "model": self.model
            }
        except Exception as e:
            logger.error(f"❌ LLM chat failed: {e}")
            return {
                "success": False,
                "error": f"LLM chat failed: {str(e)}"
            }

# ==================== Chatbot Core ====================

class Chatbot:
    def __init__(self, name: str = "Chatbot", use_llm: bool = True):
        self.name = name
        self.conversation_history: List[Dict] = []
        self.use_llm = use_llm
        self.llm_client = None
        self.request_counter = 0
        self._status_callback = None
        
        self.skill_kit = SkillKitWrapper()
        
        logger.info(f"🤖 Initializing Chatbot: {name}")
        logger.info(f"   LLM Enabled: {use_llm}")
        logger.info(f"   SkillKit Enabled: {self.skill_kit.is_available()}")
        
        if self.skill_kit.is_available():
            skills = self.skill_kit.get_skill_list()
            logger.info(f"   Skills Found: {len(skills)}")
            if skills:
                logger.info("📋 Skill Details:")
                for skill in skills:
                    logger.info(f"   📦 {skill['name']} (v{skill.get('version', 'unknown')})")
                    logger.info(f"      📝 {skill['description'][:80] if skill['description'] else ''}...")
            else:
                logger.warning("⚠️ No skills were discovered!")
        else:
            logger.warning("⚠️ SkillKit is not available")
        
        if use_llm:
            try:
                self.llm_client = LLMClient()
                logger.info("✅ LLM client initialized successfully")
            except Exception as e:
                logger.error(f"⚠️ Failed to initialize LLM client: {e}")
                self.use_llm = False
        
        self.system_prompt = """You are an intelligent assistant that helps users with their questions.

Your capabilities include:
1. Answering general questions
2. Providing helpful information
3. Assisting with various topics
4. Having natural conversations

Always provide clear, concise, and helpful responses. Be friendly and professional."""
    
    def set_status_callback(self, callback: Callable):
        self._status_callback = callback
        logger.status(f"✅ Status callback set in Chatbot: {callback is not None}")
    
    @property
    def status_callback(self):
        return self._status_callback
    
    # ==================== LAYER 2: Select Skills ====================
    
    def _get_schema_and_documentation(self) -> Dict[str, Optional[str]]:
        """Get both schema and skill documentation from the dax_query skill."""
        result = {'schema': None, 'documentation': None}
        
        try:
            dax_skill = self.skill_kit.get_skill_by_name('dax_query')
            if dax_skill:
                if hasattr(dax_skill, '_get_schema_for_llm'):
                    logger.schema("=" * 80)
                    logger.schema("📊 FETCHING SCHEMA FROM POWER BI")
                    logger.schema("=" * 80)
                    
                    schema_data = dax_skill._get_schema_for_llm()
                    if schema_data.get('success'):
                        result['schema'] = schema_data.get('schema_text', '')
                        logger.char(f"📊 Schema size: {len(result['schema']):,} characters")
                    else:
                        logger.warning(f"⚠️ Schema retrieval failed: {schema_data.get('error')}")
                
                if hasattr(dax_skill, 'get_skill_documentation'):
                    result['documentation'] = dax_skill.get_skill_documentation()
                    if result['documentation']:
                        logger.char(f"📄 SKILL.md size: {len(result['documentation']):,} characters")
                    else:
                        logger.warning("⚠️ No documentation available")
        except Exception as e:
            logger.warning(f"⚠️ Error getting schema and documentation: {e}")
        
        return result
    
    def _select_skills(self, question: str, user_specified_skill: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Layer 2: Select which skill(s) to use based on query type."""
        logger.select("=" * 80)
        logger.select("🎯 LAYER 2: SELECTING SKILLS")
        logger.select("=" * 80)
        
        callback = self.status_callback
        question_lower = question.lower().strip()
        available_skills = []
        schema_info = None
        skill_documentation = None
        
        if question_lower.startswith('echo'):
            logger.info("🔊 Echo skill selected (query starts with 'echo')")
            echo_skill = self.skill_kit.get_skill_by_name('echo')
            if echo_skill:
                available_skills.append({
                    'name': 'echo',
                    'description': echo_skill.description if hasattr(echo_skill, 'description') else 'Echo back the input'
                })
                skill_documentation = self.skill_kit.get_skill_documentation('echo')
                logger.info("📋 Available skills: ['echo']")
            else:
                logger.warning("⚠️ Echo skill not found")
        else:
            logger.info("📊 Data query detected (not echo)")
            dax_skill = self.skill_kit.get_skill_by_name('dax_query')
            if dax_skill:
                logger.info("🔍 Fetching schema and documentation for DAX Query skill...")
                info = self._get_schema_and_documentation()
                schema_info = info.get('schema')
                skill_documentation = info.get('documentation')
                
                if schema_info:
                    logger.schema("✅ Schema will be passed to LLM")
                    logger.char(f"📊 Schema size: {len(schema_info):,} characters")
                else:
                    logger.warning("⚠️ Could not retrieve schema information")
                
                if skill_documentation:
                    logger.schema("✅ SKILL.md will be passed to LLM")
                    logger.char(f"📄 SKILL.md size: {len(skill_documentation):,} characters")
                else:
                    logger.warning("⚠️ Could not retrieve SKILL.md documentation")
                
                available_skills.append({
                    'name': 'dax_query',
                    'description': dax_skill.description if hasattr(dax_skill, 'description') else 'Execute DAX queries on Power BI'
                })
                logger.info("📋 Available skills: ['dax_query']")
            else:
                logger.warning("⚠️ DAX Query skill not found")
                available_skills = []
        
        if user_specified_skill:
            logger.select(f"📌 User specified skill: {user_specified_skill}")
            for skill in self.skill_kit.get_skill_list():
                if skill.get('name') == user_specified_skill:
                    available_skills = [skill]
                    skill_documentation = self.skill_kit.get_skill_documentation(user_specified_skill)
                    break
        
        logger.select("-" * 80)
        logger.select("📤 SENDING TO LLM:")
        logger.select(f"   Question: {question}")
        logger.select(f"   Available Skills: {[s.get('name') for s in available_skills]}")
        if schema_info:
            logger.select(f"   Schema: {len(schema_info):,} characters")
        if skill_documentation:
            logger.select(f"   SKILL.md: {len(skill_documentation):,} characters")
        logger.select("-" * 80)
        
        if self.use_llm and self.llm_client and available_skills:
            logger.select(f"🧠 [AI Call 1] Calling LLM to analyze intent...")
            logger.select(f"   Available skills: {[s.get('name') for s in available_skills]}")
            
            intent = self.llm_client.detect_intent_and_select_skills(
                question=question,
                available_skills=available_skills,
                schema_info=schema_info,
                skill_documentation=skill_documentation,
                status_callback=callback
            )
            
            skills_to_use = intent.get('skills_to_use', [])
            
            logger.select(f"🔍 LLM returned skills_to_use: {skills_to_use}")
            logger.select(f"🔍 LLM returned skill_parameters: {intent.get('skill_parameters', {})}")
            
            dax_query = intent.get('skill_parameters', {}).get('dax_query')
            if dax_query and not skills_to_use:
                logger.select(f"⚠️ DAX query found but skills_to_use is empty. Auto-fixing...")
                intent['skills_to_use'] = ['dax_query']
                skills_to_use = ['dax_query']
                logger.select(f"✅ Auto-fixed skills_to_use: {skills_to_use}")
            
            if skills_to_use and 'dax_query' in skills_to_use:
                logger.select(f"✅ LLM selected dax_query skill")
                if 'skill_parameters' not in intent:
                    intent['skill_parameters'] = {}
                
                dax_query = intent.get('skill_parameters', {}).get('dax_query')
                if dax_query:
                    logger.select(f"📝 LLM generated DAX query: {dax_query}")
                    logger.char(f"📝 DAX query length: {len(dax_query):,} chars")
                else:
                    if 'dax_query' in available_skills[0].get('name', ''):
                        fallback_dax = self.llm_client._generate_fallback_dax_query(question, schema_info)
                        if fallback_dax:
                            intent['skill_parameters']['dax_query'] = fallback_dax
                            logger.select(f"📝 Using fallback DAX query: {fallback_dax}")
                
                if callback:
                    callback({
                        'status': 'selecting_skills',
                        'message': f'🔍 Selected skill: {", ".join(skills_to_use)}',
                        'stage': 1,
                        'total_stages': 3,
                        'stage_name': 'AI Call 1: Detect Intent & Select Skill',
                        'skills_selected': skills_to_use
                    })
            else:
                logger.select("ℹ️ No skill selected by LLM")
                if available_skills and available_skills[0].get('name') == 'dax_query':
                    fallback_dax = self.llm_client._generate_fallback_dax_query(question, schema_info)
                    if fallback_dax:
                        logger.select(f"📝 Generated fallback DAX query: {fallback_dax}")
                        intent['skills_to_use'] = ['dax_query']
                        intent['skill_parameters'] = {'dax_query': fallback_dax}
                        logger.select(f"✅ Using fallback with dax_query")
                        if callback:
                            callback({
                                'status': 'selecting_skills',
                                'message': f'🔍 Using fallback skill: dax_query',
                                'stage': 1,
                                'total_stages': 3,
                                'stage_name': 'AI Call 1: Detect Intent & Select Skill',
                                'skills_selected': ['dax_query']
                            })
                    else:
                        if callback:
                            callback({
                                'status': 'selecting_skills',
                                'message': 'ℹ️ No skill needed',
                                'stage': 1,
                                'total_stages': 3,
                                'stage_name': 'AI Call 1: Detect Intent & Select Skill'
                            })
            
            logger.select(f"📝 Reasoning: {intent.get('reasoning', 'N/A')}")
            return intent
        
        logger.select("ℹ️ No skill selection (LLM not available or no skills)")
        return {
            'query_type': 'general',
            'confidence': 0.3,
            'skills_to_use': [],
            'skill_parameters': {},
            'entities': {'topics': [], 'subjects': []},
            'reasoning': 'No skill selection available'
        }
    
    # ==================== LAYER 4: Execute Skill Function ====================
    
    def _execute_skill(self, skill_name: str, input_text: str, **kwargs) -> Dict[str, Any]:
        """Layer 4: Execute a skill by name using SkillKit. (Stage 2/3)"""
        logger.execute("=" * 80)
        logger.execute("⚡ LAYER 4: EXECUTING SKILL (Stage 2/3)")
        logger.execute("=" * 80)
        logger.execute(f"🎯 Skill: {skill_name}")
        logger.execute(f"📝 Input: {input_text[:100] if input_text else ''}...")
        logger.execute(f"📋 Parameters: {kwargs}")
        
        callback = self.status_callback
        
        if callback:
            callback({
                'status': 'executing_skill',
                'message': f'⚡ Executing skill: {skill_name}...',
                'stage': 2,
                'total_stages': 3,
                'stage_name': 'AI Call 2: Execute Skill'
            })
            logger.stage("📊 [STAGE 2/3] START: AI Call 2 - Execute Skill")
        
        if self.skill_kit.is_available():
            start_time = time.time()
            logger.timing(f"⏱️ [Skill Execution] START: {skill_name}")
            
            result = self.skill_kit.execute_skill(skill_name, input_text, **kwargs)
            
            elapsed = time.time() - start_time
            logger.timing(f"⏱️ [Skill Execution] COMPLETED: {elapsed:.3f}s - {skill_name}")
            
            if result.get('success', False):
                logger.execute(f"✅ Skill '{skill_name}' executed successfully")
                result_value = result.get('result', 'No result')
                if isinstance(result_value, dict):
                    response_text = result_value.get('response', str(result_value))
                    dax_query_used = result_value.get('dax_query', '')
                    logger.execute(f"📤 Result length: {len(response_text):,} chars")
                    logger.execute(f"📤 DAX Query: {dax_query_used[:100] if dax_query_used else 'N/A'}...")
                    logger.execute(f"📤 Result preview: {response_text[:100]}...")
                else:
                    logger.execute(f"📤 Result: {str(result_value)[:100]}...")
                
                if callback:
                    callback({
                        'status': 'executing_skill',
                        'message': f'✅ Skill "{skill_name}" completed',
                        'stage': 2,
                        'total_stages': 3,
                        'stage_name': 'AI Call 2: Execute Skill',
                        'skill': skill_name,
                        'skill_result': result.get('result', {})
                    })
                    logger.stage(f"📊 [STAGE 2/3] Skill '{skill_name}' completed")
            else:
                logger.execute(f"❌ Skill '{skill_name}' failed: {result.get('error', 'Unknown error')}")
                logger.stage(f"❌ [STAGE 2/3] FAILED: Skill '{skill_name}'")
                
                if callback:
                    callback({
                        'status': 'error',
                        'message': f'❌ Skill "{skill_name}" failed: {result.get("error", "Unknown error")}',
                        'stage': 2,
                        'total_stages': 3,
                        'stage_name': 'AI Call 2: Execute Skill'
                    })
            
            return result
        else:
            logger.execute("❌ SkillKit not available")
            return {
                'success': False,
                'error': 'SkillKit not available',
                'skill': skill_name
            }
    
    def _execute_multiple_skills(self, skills_to_use: List[str], question: str, skill_params: Dict) -> List[Dict[str, Any]]:
        """Execute multiple skills and collect results. (Stage 2/3)"""
        results = []
        
        for skill_name in skills_to_use:
            if skill_name and skill_name != 'null':
                logger.execute(f"🎯 Executing skill: {skill_name}")
                result = self._execute_skill(skill_name, question, **skill_params)
                
                if result.get('success', False):
                    result_data = result.get('result', {})
                    if isinstance(result_data, dict):
                        response_text = result_data.get('response', str(result_data))
                        data = result_data.get('data')
                        dax_query = result_data.get('dax_query', '')
                    else:
                        response_text = str(result_data)
                        data = None
                        dax_query = ''
                    
                    results.append({
                        'skill': skill_name,
                        'success': True,
                        'response': response_text,
                        'data': data,
                        'dax_query': dax_query,
                        'source': result.get('source', 'unknown')
                    })
                    logger.execute(f"✅ Skill '{skill_name}' executed successfully")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    results.append({
                        'skill': skill_name,
                        'success': False,
                        'response': None,
                        'error': error_msg
                    })
                    logger.execute(f"❌ Skill '{skill_name}' failed: {error_msg}")
        
        return results
    
    # ==================== Main Ask Method ====================
    
    def ask(self, question: str, skill_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Main method to process a user question."""
        self.request_counter += 1
        request_id = self.request_counter
        
        self._add_to_history("user", question)
        
        logger.info("=" * 80)
        logger.info(f"📨 REQUEST #{request_id}")
        logger.info("=" * 80)
        logger.info(f"❓ Question: {question}")
        logger.info(f"📏 Question length: {len(question):,} chars")
        logger.info("=" * 80)
        logger.info("📊 Stage Flow: [1/3] Intent & Skill Selection → [2/3] Execute Skill → [3/3] Format Answer")
        logger.info("=" * 80)
        
        callback = self.status_callback
        
        if callback:
            callback({
                'status': 'thinking',
                'message': '🧠 Processing your question...',
                'stage': 0,
                'total_stages': 3,
                'stage_name': 'Starting...'
            })
        
        logger.info("🔍 [Stage 1/3] Defining User Intent & Selecting Skills...")
        
        intent = self._select_skills(question, skill_name, **kwargs)
        
        query_type = intent.get('query_type', 'general')
        confidence = intent.get('confidence', 0.5)
        skills_to_use = intent.get('skills_to_use', [])
        skill_params = intent.get('skill_parameters', {})
        
        logger.info(f"📊 Query Type: {query_type} (confidence: {confidence})")
        logger.info(f"🎯 Skills to use: {skills_to_use}")
        if intent.get('reasoning'):
            logger.info(f"💭 Reasoning: {intent['reasoning']}")
        
        # STAGE 2/3: AI Call 2 - Execute Skill
        skill_results = []
        tools_used = []
        skip_llm_formatting = False
        
        if skills_to_use:
            logger.info("⚡ [Stage 2/3] Executing Skill Calls...")
            
            skill_results = self._execute_multiple_skills(skills_to_use, question, skill_params)
            
            for result in skill_results:
                if result.get('success'):
                    tools_used.append(result.get('skill'))
            
            if 'echo' in skills_to_use and skill_results and skill_results[0].get('success'):
                skip_llm_formatting = True
                logger.info("🎯 Echo skill executed - skipping LLM formatting")
        else:
            logger.info("ℹ️ No skills selected for execution")
        
        # STAGE 3/3: Format Final Answer
        if skip_llm_formatting and skill_results:
            logger.info("🎨 [Stage 3/3] Using skill result directly (skipping LLM)")
            
            if callback:
                callback({
                    'status': 'formatting_answer',
                    'message': '✍️ Formatting your answer...',
                    'stage': 3,
                    'total_stages': 3,
                    'stage_name': 'AI Call 3: Format Final Answer'
                })
            
            if skill_results and skill_results[0].get('success'):
                response = skill_results[0].get('response', 'No response from echo skill.')
                logger.info(f"✅ Using skill result: {response[:100]}...")
            else:
                response = "No response from echo skill."
            
            if callback:
                callback({
                    'status': 'complete',
                    'message': '✅ Response ready!',
                    'stage': 3,
                    'total_stages': 3,
                    'stage_name': 'Complete'
                })
        
        elif self.use_llm and self.llm_client:
            logger.info("🎨 [Stage 3/3] Formatting Final Answer with LLM...")
            
            response = self.llm_client.format_final_answer(
                question=question,
                skill_results=skill_results,
                intent=intent,
                system_prompt=self.system_prompt,
                conversation_history=self.conversation_history,
                status_callback=callback
            )
            logger.info(f"✅ Response generated (length: {len(response) if response else 0:,} chars)")
        else:
            logger.info("ℹ️ Using fallback response (LLM disabled)")
            if skill_results:
                responses = [r.get('response', '') for r in skill_results if r.get('success')]
                response = "\n".join(responses) if responses else "No skill results available."
            else:
                response = f"I received: '{question}'. How can I help you?"
            
            if callback:
                callback({
                    'status': 'complete',
                    'message': '✅ Response ready!',
                    'stage': 3,
                    'total_stages': 3,
                    'stage_name': 'Complete'
                })
        
        self._add_to_history("assistant", response)
        
        if callback:
            callback({
                'status': 'complete',
                'message': '✅ Done!',
                'stage': 3,
                'total_stages': 3,
                'stage_name': 'Complete'
            })
        
        logger.info("=" * 80)
        logger.info(f"✅ REQUEST COMPLETE - Response length: {len(response):,} chars")
        logger.info("=" * 80)
        
        return {
            'response': response,
            'query_type': query_type,
            'tools_used': tools_used,
            'history_count': len(self.conversation_history),
            'skill_used': tools_used[0] if tools_used else None,
            'skill_results': skill_results,
            'is_error': response.startswith("❌") if response else True,
            'intent': intent,
            'skillkit_available': self.skill_kit.is_available()
        }
    
    # ==================== Helper Methods ====================
    
    def _add_to_history(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history
    
    def clear_history(self):
        self.conversation_history = []
    
    def get_skills(self) -> List[Dict[str, Any]]:
        if self.skill_kit.is_available():
            return self.skill_kit.get_skill_list()
        return []
    
    def get_skill_details(self) -> List[Dict[str, Any]]:
        if self.skill_kit.is_available():
            return self.skill_kit.get_discovery_details()
        return []
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "skills": self.get_skills(),
            "history_count": len(self.conversation_history),
            "timestamp": datetime.now().isoformat(),
            "llm_enabled": self.use_llm,
            "llm_model": "qwen3.5:35b" if self.use_llm else None,
            "skillkit_available": self.skill_kit.is_available(),
            "skillkit_skills_count": len(self.get_skills()),
            "skill_details": self.get_skill_details()
        }

# ==================== Main ====================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🤖 Chatbot with LLM and SkillKit")
    print("=" * 80)
    print("Architecture:")
    print("  [1/3] AI Call 1 - Detect Intent & Select Skills")
    print("  [2/3] AI Call 2 - Execute Skill")
    print("  [3/3] AI Call 3 - Format Final Answer")
    print("=" * 80)
    
    bot = Chatbot("Chatbot", use_llm=True)
    
    print(f"\n✅ Chatbot ready: {bot.name}")
    print(f"🧠 LLM Enabled: {bot.use_llm}")
    print(f"🎯 SkillKit Enabled: {bot.skill_kit.is_available()}")
    
    skills = bot.get_skills()
    print(f"📋 Skills registered: {len(skills)}")
    
    if skills:
        print("\n📦 Available Skills:")
        for skill in skills:
            version = skill.get('version', '')
            category = skill.get('category', 'general')
            source = skill.get('source', 'unknown')
            print(f"   • {skill['name']} v{version} [{category}] ({source})")
            print(f"     Description: {skill['description']}")
    else:
        print("\n⚠️ No skills found!")
    
    print("\n" + "=" * 80)
    print("💬 Try asking:")
    print("   • echo Hello World (uses echo skill)")
    print("   • What tables are available? (uses DAX Query skill)")
    print("   • Show me project data (uses DAX Query skill)")
    print("   • /skills - List all available skills")
    print("=" * 80 + "\n")
    
    while True:
        try:
            user_input = input("❓ You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['/exit', 'exit', 'quit']:
                print("👋 Goodbye!")
                break
            if user_input.lower() in ['/skills', 'list skills']:
                skills = bot.get_skills()
                if skills:
                    print("\n📦 Available Skills:")
                    for skill in skills:
                        version = skill.get('version', '')
                        category = skill.get('category', 'general')
                        source = skill.get('source', 'unknown')
                        print(f"   • {skill['name']} v{version} [{category}] ({source})")
                        print(f"     Description: {skill['description']}")
                else:
                    print("\nℹ️ No skills available")
                print()
                continue
            
            result = bot.ask(user_input)
            
            print(f"\n🤖 Bot: {result['response']}\n")
            print(f"📊 Query Type: {result['query_type']}")
            if result.get('tools_used'):
                print(f"🔧 Tools Used: {', '.join(result['tools_used'])}")
            if result.get('skill_used'):
                print(f"🎯 Skill Used: {result['skill_used']}")
            if result.get('skill_results'):
                print(f"📊 Skill Results: {len(result['skill_results'])}")
            if result.get('skillkit_available'):
                print(f"🎯 SkillKit: Available")
            print(f"📝 History: {result['history_count']} messages")
            print("-" * 80)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Error in main loop: {e}", exc_info=True)