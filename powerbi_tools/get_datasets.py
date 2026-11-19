# get_datasets.py - Get Power BI datasets
import requests
from typing import Dict, Any, Optional
from config import config
from authentication import get_access_token

def get_datasets(workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all datasets in a Power BI workspace.
    
    Args:
        workspace_id: Optional workspace ID (uses default from config if not provided)
    
    Returns:
        Dictionary containing datasets list and summary
        
    Example:
        >>> result = get_datasets()
        >>> if result['success']:
        ...     for ds in result['result']['datasets']:
        ...         print(f"{ds['name']}: {ds['id']}")
    """
    try:
        # Validate config
        config.validate()
        
        # Use provided workspace_id or default from config
        ws_id = workspace_id or config.workspace_id
        
        if not ws_id:
            return {
                'success': False,
                'tool': 'get_datasets',
                'error': 'Workspace ID is required. Please provide workspace_id or set POWERBI_WORKSPACE_ID in .env'
            }
        
        print(f"🔍 Getting datasets from workspace: {ws_id}")
        
        # Get access token
        access_token = get_access_token()
        
        # Make API request
        url = f"{config.power_bi_api}/groups/{ws_id}/datasets"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        datasets = response.json().get('value', [])
        
        # Simplify dataset information
        simplified_datasets = []
        for dataset in datasets:
            simplified_datasets.append({
                'id': dataset.get('id'),
                'name': dataset.get('name'),
                'description': dataset.get('description') or 'No description provided'
            })
        
        # Find selected/default dataset
        default_model_id = config.semantic_model_id
        selected_dataset = None
        
        if default_model_id:
            for ds in datasets:
                if ds.get('id') == default_model_id:
                    selected_dataset = {
                        'id': ds.get('id'),
                        'name': ds.get('name')
                    }
                    break
        
        # Generate summary
        summary_lines = [
            f"Found {len(simplified_datasets)} datasets in workspace:",
            ""
        ]
        
        for idx, ds in enumerate(simplified_datasets, 1):
            summary_lines.append(f"{idx}. {ds['name']}")
            summary_lines.append(f"   ID: {ds['id']}")
            summary_lines.append(f"   Description: {ds['description']}")
            summary_lines.append("")
        
        return {
            'success': True,
            'tool': 'get_datasets',
            'result': {
                'datasets': simplified_datasets,
                'dataset_count': len(simplified_datasets),
                'summary': '\n'.join(summary_lines),
                'workspace_id': ws_id,
                'default_model_id': default_model_id,
                'selected_dataset': selected_dataset
            }
        }
    
    except requests.exceptions.RequestException as e:
        error_message = str(e)
        suggestions = []
        status_code = None
        
        if hasattr(e, 'response') and e.response:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
                error_message = error_data.get('error', {}).get('message', str(e))
            except:
                error_message = e.response.text or str(e)
            
            if status_code == 403:
                suggestions = [
                    'Service principal may not have permission to access this workspace',
                    'Check that the service principal is added as a member or admin to the workspace',
                    'Verify the workspace ID is correct'
                ]
            elif status_code == 404:
                suggestions = [
                    'Workspace not found',
                    'Check the workspace ID is correct'
                ]
            elif status_code == 401:
                suggestions = [
                    'Authentication failed',
                    'Check your tenant ID, client ID, and client secret',
                    'Verify the service principal has the required permissions'
                ]
        
        print(f"❌ get_datasets error: {error_message}")
        return {
            'success': False,
            'tool': 'get_datasets',
            'error': error_message,
            'status': status_code,
            'suggestions': suggestions
        }
    
    except Exception as e:
        print(f"❌ Unexpected error in get_datasets: {e}")
        return {
            'success': False,
            'tool': 'get_datasets',
            'error': str(e)
        }

# ============================================================
# Helper Functions
# ============================================================

def get_dataset_id_by_name(dataset_name: str, workspace_id: Optional[str] = None) -> Optional[str]:
    """
    Get dataset ID by its name.
    
    Args:
        dataset_name: Name of the dataset to find
        workspace_id: Optional workspace ID
    
    Returns:
        Dataset ID if found, None otherwise
    """
    result = get_datasets(workspace_id)
    
    if not result['success']:
        return None
    
    for dataset in result['result']['datasets']:
        if dataset['name'].lower() == dataset_name.lower():
            return dataset['id']
    
    return None

def get_default_dataset_id() -> Optional[str]:
    """
    Get the default dataset ID from configuration.
    
    Returns:
        Dataset ID if configured, None otherwise
    """
    return config.semantic_model_id

# ============================================================
# Command Line Usage
# ============================================================
if __name__ == '__main__':
    # Example usage
    print("=" * 50)
    print("GET DATASETS - Example")
    print("=" * 50)
    
    result = get_datasets()
    
    if result['success']:
        print(result['result']['summary'])
        print("\n📊 Datasets as JSON:")
        import json
        print(json.dumps(result['result']['datasets'], indent=2))
    else:
        print(f"❌ Error: {result.get('error')}")
        if result.get('suggestions'):
            print("\n💡 Suggestions:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion}")