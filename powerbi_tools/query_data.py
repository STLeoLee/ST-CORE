# query_data.py - Execute DAX queries on Power BI
import json
import requests
from typing import Dict, Any, Optional
from config import config
from authentication import get_access_token

def query_data(dax_query: str, dataset_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a DAX query on a Power BI dataset.
    
    Args:
        dax_query: DAX query to execute (required)
        dataset_id: Dataset ID (uses default from config if not provided)
        workspace_id: Optional workspace ID (uses default from config if not provided)
    
    Returns:
        Dictionary containing query results and summary
        
    Example:
        >>> dax = "EVALUATE SUMMARIZECOLUMNS('Sales'[Category], 'Total Sales', SUM('Sales'[Amount]))"
        >>> result = query_data(dax, dataset_id='your-dataset-id')
        >>> if result['success']:
        ...     for row in result['result']['rows']:
        ...         print(row)
    """
    try:
        # Validate config
        config.validate()
        
        # Use provided IDs or defaults from config
        ws_id = workspace_id or config.workspace_id
        ds_id = dataset_id or config.semantic_model_id
        
        # Validate required parameters
        if not ds_id:
            return {
                'success': False,
                'tool': 'query_data',
                'error': 'Dataset ID is required. Please provide dataset_id or set POWERBI_MODEL_ID in .env'
            }
        
        if not dax_query:
            return {
                'success': False,
                'tool': 'query_data',
                'error': 'DAX query is required. Please provide a DAX query to execute.'
            }
        
        if not ws_id:
            return {
                'success': False,
                'tool': 'query_data',
                'error': 'Workspace ID is required. Please provide workspace_id or set POWERBI_WORKSPACE_ID in .env'
            }
        
        print(f"🔍 Executing DAX query on dataset: {ds_id}")
        print(f"   Workspace: {ws_id}")
        print(f"   Query: {dax_query[:100]}{'...' if len(dax_query) > 100 else ''}")
        
        # Get access token
        access_token = get_access_token()
        
        # Execute query
        url = f"{config.power_bi_api}/groups/{ws_id}/datasets/{ds_id}/executeQueries"
        
        payload = {
            'queries': [{'query': dax_query}],
            'serializeAs': 'Dataset'
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [{}])[0]
        
        # Parse results
        columns = []
        formatted_rows = []
        row_count = 0
        
        if results and results.get('tables') and len(results['tables']) > 0:
            table = results['tables'][0]
            
            # Extract columns
            if table.get('columns'):
                columns = [
                    {'name': col.get('name'), 'dataType': col.get('dataType', 'Unknown')}
                    for col in table['columns']
                ]
            
            # Extract rows
            rows = table.get('rows', [])
            row_count = len(rows)
            
            # Format rows as dictionaries
            if columns and rows:
                formatted_rows = []
                for row in rows:
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        row_dict[col['name']] = row[idx] if idx < len(row) else None
                    formatted_rows.append(row_dict)
            elif rows and not columns:
                # Fallback: if we have rows but no columns defined
                formatted_rows = rows
        
        # Get dataset name (optional)
        dataset_name = ds_id
        try:
            dataset_url = f"{config.power_bi_api}/groups/{ws_id}/datasets/{ds_id}"
            headers_get = {'Authorization': f'Bearer {access_token}'}
            ds_response = requests.get(dataset_url, headers=headers_get)
            if ds_response.status_code == 200:
                dataset_name = ds_response.json().get('name', ds_id)
        except:
            pass
        
        # Generate summary
        summary_lines = [
            f"✅ Query executed successfully",
            "",
            f"📊 Dataset: {dataset_name}",
            f"📝 Query: {dax_query}",
            "",
            "📈 Results:",
            f"   • Rows: {row_count}",
            f"   • Columns: {len(columns)}",
        ]
        
        if columns:
            column_names = [c['name'] for c in columns]
            summary_lines.append(f"   • Column Names: {', '.join(column_names)}")
        
        summary_lines.append("")
        
        # Add sample data
        if formatted_rows and columns:
            sample_size = min(3, len(formatted_rows))
            summary_lines.append(f"📋 Sample Data ({sample_size} rows):")
            for idx, row in enumerate(formatted_rows[:sample_size], 1):
                summary_lines.append(f"   Row {idx}: {json.dumps(row)}")
            if row_count > sample_size:
                summary_lines.append(f"   ... and {row_count - sample_size} more rows")
        elif formatted_rows and not columns:
            # Raw data fallback
            sample_size = min(3, len(formatted_rows))
            summary_lines.append(f"📋 Sample Data ({sample_size} rows):")
            for idx, row in enumerate(formatted_rows[:sample_size], 1):
                summary_lines.append(f"   Row {idx}: {json.dumps(row)}")
            if row_count > sample_size:
                summary_lines.append(f"   ... and {row_count - sample_size} more rows")
        
        return {
            'success': True,
            'tool': 'query_data',
            'result': {
                'dataset_id': ds_id,
                'dataset_name': dataset_name,
                'workspace_id': ws_id,
                'query': dax_query,
                'columns': columns,
                'rows': formatted_rows,
                'row_count': row_count,
                'summary': '\n'.join(summary_lines)
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
            
            if status_code == 400:
                suggestions = [
                    'The DAX query may have syntax errors',
                    'Check for missing quotes or parentheses',
                    'Ensure table names are spelled correctly and enclosed in single quotes',
                    'The dataset may be in a processing state',
                    'Check if the query references existing tables and columns'
                ]
            elif status_code == 403:
                suggestions = [
                    'Service principal may not have permission to query this dataset',
                    'Check that the service principal has access to the dataset',
                    'Verify the workspace ID is correct'
                ]
            elif status_code == 404:
                suggestions = [
                    'Dataset not found',
                    'Check the dataset ID is correct',
                    'Use get_datasets() to get a list of available datasets'
                ]
            elif status_code == 401:
                suggestions = [
                    'Authentication failed',
                    'Check your tenant ID, client ID, and client secret',
                    'Verify the service principal has the required permissions'
                ]
        
        print(f"❌ query_data error: {error_message}")
        return {
            'success': False,
            'tool': 'query_data',
            'error': error_message,
            'status': status_code,
            'suggestions': suggestions
        }
    
    except Exception as e:
        print(f"❌ Unexpected error in query_data: {e}")
        return {
            'success': False,
            'tool': 'query_data',
            'error': str(e)
        }

# ============================================================
# Helper Functions
# ============================================================

def query_tables(workspace_id: Optional[str] = None, dataset_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get list of all tables in a dataset.
    
    Args:
        workspace_id: Optional workspace ID
        dataset_id: Optional dataset ID
    
    Returns:
        Dictionary with table information
    """
    dax = """
    EVALUATE
    SELECTCOLUMNS(
        FILTER(
            INFO.VIEW.TABLES(),
            [IsHidden] = FALSE
        ),
        "Name", [Name],
        "Description", [Description]
    )
    ORDER BY [Name]
    """
    return query_data(dax, dataset_id, workspace_id)

def query_columns(table_name: str, workspace_id: Optional[str] = None, dataset_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get list of columns for a specific table.
    
    Args:
        table_name: Name of the table
        workspace_id: Optional workspace ID
        dataset_id: Optional dataset ID
    
    Returns:
        Dictionary with column information
    """
    dax = f"""
    EVALUATE
    SELECTCOLUMNS(
        FILTER(
            INFO.VIEW.COLUMNS(),
            [TableName] = "{table_name}" &&
            NOT ISBLANK([Description])
        ),
        "Name", [Name],
        "Description", [Description]
    )
    ORDER BY [Name]
    """
    return query_data(dax, dataset_id, workspace_id)

# ============================================================
# Command Line Usage
# ============================================================
if __name__ == '__main__':
    import sys
    
    print("=" * 50)
    print("QUERY DATA - Example")
    print("=" * 50)
    
    # Example DAX query - Get tables with descriptions
    dax_query = """
    EVALUATE
    SELECTCOLUMNS(
        FILTER(
            INFO.VIEW.TABLES(),
            [IsHidden] = FALSE
        ),
        "Name", [Name],
        "Description", [Description]
    )
    ORDER BY [Name]
    """
    
    result = query_data(dax_query)
    
    if result['success']:
        print(result['result']['summary'])
        print("\n📊 Results as JSON:")
        print(json.dumps(result['result']['rows'], indent=2))
    else:
        print(f"❌ Error: {result.get('error')}")
        if result.get('suggestions'):
            print("\n💡 Suggestions:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion}")