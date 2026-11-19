# authentication.py - Authentication for Power BI
import requests
from config import config

def get_access_token() -> str:
    """
    Get Power BI access token using Client Credentials flow.
    
    Returns:
        str: Access token for Power BI API
        
    Raises:
        Exception: If authentication fails
    """
    try:
        token_endpoint = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default',
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        
        return response.json()['access_token']
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get access token: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        raise Exception(f"Authentication failed: {e}")

def validate_connection() -> dict:
    """
    Validate the connection to Power BI.
    
    Returns:
        dict: Connection status
    """
    try:
        token = get_access_token()
        return {
            'success': True,
            'message': 'Successfully connected to Power BI',
            'token_received': bool(token)
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Connection failed: {str(e)}'
        }