import httpx
import logging
import base64
import time
from typing import Dict, Any

logger = logging.getLogger("novade_api")

# ==========================================
# HARDCODED CREDENTIALS FOR TESTING
# ==========================================
NOVADE_USERNAME = "spa_demohk1@novade.net" 
NOVADE_PASSWORD = "charlie01" 
# ==========================================

TOKEN_URL = "https://s3api.novade.net/token"
BASE_URL = "https://s3api.novade.net"

_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0}

async def get_novade_token(client: httpx.AsyncClient) -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    auth_str = f"{NOVADE_USERNAME}:{NOVADE_PASSWORD}"
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    
    headers = {"Authorization": f"Basic {auth_b64}", "Accept": "application/json"}
    logger.info("[NOVADE] Requesting new token...")
    
    try:
        response = await client.get(TOKEN_URL, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        
        token = data.get("token") or data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        
        if not token: raise ValueError("Token not found in response")

        _token_cache["token"] = token
        _token_cache["expires_at"] = now + expires_in
        return token
    except Exception as e:
        logger.error(f"[NOVADE] Auth error: {str(e)}")
        raise

async def get_safety_actions(project_id: str, since_timestamp: int) -> list:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            token = await get_novade_token(client)
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            url = f"{BASE_URL}/safety/since/actions/{since_timestamp}"
            
            # Format the project ID with single quotes explicitly
            quoted_project_id = f"'{project_id}'"
            params = {"projectid": quoted_project_id}
            
            logger.info(f"[NOVADE] Fetching actions for {quoted_project_id}")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[NOVADE] Fetch error: {str(e)}")
            raise