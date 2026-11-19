# config.py - Configuration for Power BI
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("chatbot")

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"✅ Loaded .env from: {env_path}")
else:
    logger.warning(f"⚠️ .env file not found at: {env_path}")

class PowerBIConfig:
    """Power BI configuration settings"""
    
    def __init__(self):
        self.tenant_id = os.getenv('POWERBI_TENANT_ID')
        self.client_id = os.getenv('POWERBI_CLIENT_ID')
        self.client_secret = os.getenv('POWERBI_CLIENT_SECRET')
        self.semantic_model_id = os.getenv('POWERBI_MODEL_ID')
        self.workspace_id = os.getenv('POWERBI_WORKSPACE_ID')
        self.username = os.getenv('POWERBI_USERNAME')
        self.password = os.getenv('POWERBI_PASSWORD')
        self.power_bi_api = 'https://api.powerbi.com/v1.0/myorg'
    
    def validate(self):
        """Validate that all required configuration is present"""
        required = {
            'tenant_id': self.tenant_id,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'workspace_id': self.workspace_id
        }
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            raise Exception(f"Missing required configuration: {', '.join(missing)}")
        
        return True
    
    def to_dict(self):
        """Return config as dictionary (excluding sensitive data)"""
        return {
            'tenant_id': self.tenant_id,
            'workspace_id': self.workspace_id,
            'model_id': self.semantic_model_id,
            'power_bi_api': self.power_bi_api
        }
    
    def is_configured(self):
        """Check if Power BI credentials are configured."""
        return all([self.workspace_id, self.semantic_model_id, self.client_id, self.client_secret, self.tenant_id])

# Singleton instance
config = PowerBIConfig()

# Log configuration status
if config.is_configured():
    logger.info("✅ Power BI configuration loaded")
    logger.info(f"   Workspace ID: {config.workspace_id[:8] if config.workspace_id else 'Not set'}...")
    logger.info(f"   Dataset ID: {config.semantic_model_id[:8] if config.semantic_model_id else 'Not set'}...")
else:
    logger.warning("⚠️ Power BI configuration incomplete. Please set in .env:")
    logger.warning("   POWERBI_TENANT_ID")
    logger.warning("   POWERBI_CLIENT_ID")
    logger.warning("   POWERBI_CLIENT_SECRET")
    logger.warning("   POWERBI_WORKSPACE_ID")
    logger.warning("   POWERBI_MODEL_ID (optional)")