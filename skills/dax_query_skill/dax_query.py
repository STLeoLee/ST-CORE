"""
DAX Query Skill - Execute DAX queries on Power BI datasets

This skill executes DAX queries and returns formatted results.
It also provides schema information to help the LLM generate accurate queries.
"""

import json
import logging
import sys
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from collections import Counter

# ==================== PATH SETUP ====================
current_file = Path(__file__).resolve()
skill_dir = current_file.parent
skills_dir = skill_dir.parent
project_root = skills_dir.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

powerbi_tools_path = project_root / "powerbi_tools"
if str(powerbi_tools_path) not in sys.path:
    sys.path.insert(0, str(powerbi_tools_path))

# ==================== LOGGING ====================
logger = logging.getLogger("chatbot")

# ==================== POWER BI IMPORTS ====================
POWERBI_AVAILABLE = False

try:
    from powerbi_tools.query_data import query_data
    from powerbi_tools.config import config as powerbi_config
    POWERBI_AVAILABLE = True
    logger.info("✅ Power BI functions imported successfully")
except ImportError as e:
    POWERBI_AVAILABLE = False
    logger.warning(f"⚠️ Could not import Power BI functions: {e}")
    try:
        import importlib.util
        query_data_path = powerbi_tools_path / "query_data.py"
        if query_data_path.exists():
            spec = importlib.util.spec_from_file_location("query_data", query_data_path)
            query_data_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(query_data_module)
            query_data = query_data_module.query_data
            
            config_path = powerbi_tools_path / "config.py"
            if config_path.exists():
                spec = importlib.util.spec_from_file_location("config", config_path)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                powerbi_config = config_module.config
            
            POWERBI_AVAILABLE = True
            logger.info("✅ Power BI functions imported successfully (via direct file)")
    except Exception as e2:
        logger.warning(f"⚠️ Alternative import also failed: {e2}")


class DAXQuerySkill:
    """
    Execute DAX queries on Power BI datasets with schema discovery.
    """
    
    def __init__(self):
        """Initialize the skill with metadata."""
        self.name = "dax_query"
        self.description = "Execute DAX queries on Power BI datasets. Use this skill to query BIM data, get schema information, analyze data, and retrieve filtered datasets."
        self.version = "1.0.0"
        self.author = "ST-CORE Team"
        self.category = "data_query"
        self.tags = ["bim", "powerbi", "dax", "query", "data", "schema"]
        
        # Default pagination settings
        self.default_page_size = 20
        self.max_page_size = 100
        
        try:
            if POWERBI_AVAILABLE:
                self.default_workspace_id = getattr(powerbi_config, 'workspace_id', None)
                self.default_dataset_id = getattr(powerbi_config, 'semantic_model_id', None)
            else:
                self.default_workspace_id = None
                self.default_dataset_id = None
        except:
            self.default_workspace_id = None
            self.default_dataset_id = None
        
        self.schema_cache = {}
        self.cache_duration = 300
    
    def get_skill_documentation(self) -> str:
        """Load and return the SKILL.md content for this skill."""
        try:
            skill_md_path = Path(__file__).parent / "SKILL.md"
            if skill_md_path.exists():
                with open(skill_md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return content
            return ""
        except Exception as e:
            logger.warning(f"⚠️ Error loading SKILL.md: {e}")
            return ""
    
    def _clean_key(self, key: str) -> str:
        """Remove brackets from key if present."""
        if key.startswith('[') and key.endswith(']'):
            return key[1:-1]
        # Remove Assets[field] pattern
        if key.startswith('Assets[') and key.endswith(']'):
            return key[7:-1]
        return key
    
    def _extract_from_row(self, row: Dict[str, Any], field: str, default: str = "") -> str:
        """
        Extract a value from a row. Handles both direct keys and attribute_json.
        """
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
    
    def _get_schema_for_llm(self, workspace_id: Optional[str] = None,
                           dataset_id: Optional[str] = None) -> Dict[str, Any]:
        """Get schema information formatted for LLM consumption."""
        if not POWERBI_AVAILABLE:
            return {
                'success': False,
                'error': 'Power BI functions not available',
                'schema_text': 'Power BI functions not available.'
            }
        
        ws_id = workspace_id or self.default_workspace_id
        ds_id = dataset_id or self.default_dataset_id
        
        if not ds_id or not ws_id:
            return {
                'success': False,
                'error': 'Workspace and Dataset IDs are required',
                'schema_text': 'Workspace and Dataset IDs are required.'
            }
        
        cache_key = f"schema_{ws_id}_{ds_id}"
        if cache_key in self.schema_cache:
            cache_time = self.schema_cache.get(f"{cache_key}_timestamp", 0)
            if time.time() - cache_time < self.cache_duration:
                logger.info("📦 Using cached schema")
                return self.schema_cache[cache_key]
        
        logger.info("🔍 Fetching schema from Power BI...")
        
        schema_data = {
            'tables': [],
            'columns': [],
            'attribute_definitions': [],
            'columns_by_table': {},
            'success': False
        }
        
        # ============================================================
        # 1. Get Tables
        # ============================================================
        tables_dax = """
        EVALUATE
        SELECTCOLUMNS(
            FILTER(
                INFO.VIEW.TABLES(),
                [IsHidden] = FALSE
            ),
            "Table Name", [Name],
            "Table Description", [Description]
        )
        ORDER BY [Table Name]
        """
        
        try:
            tables_result = query_data(tables_dax, ds_id, ws_id)
            if tables_result.get('success'):
                rows = tables_result.get('result', {}).get('rows', [])
                for row in rows:
                    table_name = self._extract_from_row(row, 'Table Name', 'Unknown')
                    table_desc = self._extract_from_row(row, 'Table Description', '')
                    
                    if table_name and table_name != 'Unknown':
                        schema_data['tables'].append({
                            'Table Name': table_name,
                            'Table Description': table_desc
                        })
                logger.info(f"✅ Found {len(schema_data['tables'])} tables")
            else:
                logger.warning(f"⚠️ Could not get tables: {tables_result.get('error')}")
        except Exception as e:
            logger.warning(f"⚠️ Error getting tables: {e}")
        
        # ============================================================
        # 2. Get Columns with descriptions
        # ============================================================
        columns_dax = """
        EVALUATE
        SELECTCOLUMNS(
            FILTER(
                INFO.VIEW.COLUMNS(),
                [Description]<> ""
            ),
            "Table Name", [Table],
            "Column Name", [Name],
            "Column Description", [Description]
        )
        ORDER BY [Table Name], [Column Name]
        """
        
        try:
            columns_result = query_data(columns_dax, ds_id, ws_id)
            if columns_result.get('success'):
                rows = columns_result.get('result', {}).get('rows', [])
                for row in rows:
                    table_name = self._extract_from_row(row, 'Table Name', '')
                    col_name = self._extract_from_row(row, 'Column Name', '')
                    col_desc = self._extract_from_row(row, 'Column Description', '')
                    
                    if table_name and col_name:
                        schema_data['columns'].append({
                            'Table Name': table_name,
                            'Column Name': col_name,
                            'Column Description': col_desc
                        })
                        
                        if table_name not in schema_data['columns_by_table']:
                            schema_data['columns_by_table'][table_name] = []
                        schema_data['columns_by_table'][table_name].append({
                            'name': col_name,
                            'description': col_desc
                        })
                
                logger.info(f"✅ Found {len(schema_data['columns'])} columns with descriptions")
            else:
                logger.warning(f"⚠️ Could not get columns: {columns_result.get('error')}")
        except Exception as e:
            logger.warning(f"⚠️ Error getting columns: {e}")
        
        # ============================================================
        # 3. Get Attribute Definitions from Assets_attributes table
        # ============================================================
        attribute_definitions_dax = """
        EVALUATE
        SELECTCOLUMNS(
            FILTER(
                'Assets_attributes',
                [Description]<> ""
            ),
            "Attribute Name", [display_name],
            "Attribute Description", [description]
        )
        ORDER BY [Attribute Name]
        """
        
        try:
            attr_result = query_data(attribute_definitions_dax, ds_id, ws_id)
            if attr_result.get('success'):
                rows = attr_result.get('result', {}).get('rows', [])
                for row in rows:
                    attr_name = self._extract_from_row(row, 'Attribute Name', '')
                    attr_desc = self._extract_from_row(row, 'Attribute Description', '')
                    
                    if attr_name:
                        schema_data['attribute_definitions'].append({
                            'Attribute Name': attr_name,
                            'Attribute Description': attr_desc
                        })
                
                logger.info(f"✅ Found {len(schema_data['attribute_definitions'])} attribute definitions from Assets_attributes table")
            else:
                logger.warning(f"⚠️ Could not get attribute definitions: {attr_result.get('error')}")
        except Exception as e:
            logger.warning(f"⚠️ Error getting attribute definitions: {e}")
        
        # ============================================================
        # 4. Format schema text
        # ============================================================
        schema_text = self._format_schema_for_llm(schema_data)
        schema_data['schema_text'] = schema_text
        schema_data['success'] = True
        
        # Cache
        self.schema_cache[cache_key] = schema_data
        self.schema_cache[f"{cache_key}_timestamp"] = time.time()
        
        return schema_data
    
    def _format_schema_for_llm(self, schema_data: Dict[str, Any]) -> str:
        """Format schema information in an AI-friendly way."""
        lines = []
        lines.append("=== Power BI Schema Information ===")
        lines.append("")
        
        tables = schema_data.get('tables', [])
        if tables:
            lines.append(f"## Tables ({len(tables)}):")
            for table in tables:
                table_name = table.get('Table Name', 'Unknown')
                description = table.get('Table Description', '')
                if table_name == 'Assets_attributes':
                    lines.append(f"- **{table_name}**: {description} *(Contains attribute definitions - see Attribute Definitions section below)*")
                else:
                    if description:
                        lines.append(f"- **{table_name}**: {description}")
                    else:
                        lines.append(f"- **{table_name}**")
            lines.append("")
        else:
            lines.append("## Tables: No tables found")
            lines.append("")
        
        columns_by_table = schema_data.get('columns_by_table', {})
        if columns_by_table:
            lines.append("## Columns with Descriptions:")
            for table_name, columns in columns_by_table.items():
                if table_name:
                    if table_name == 'Assets':
                        lines.append(f"\n### Table: {table_name} ({len(columns)} columns)")
                        lines.append(f"*(Note: The `attribute_json` column contains JSON data. See Attribute Definitions below for the JSON schema.)*")
                    else:
                        lines.append(f"\n### Table: {table_name} ({len(columns)} columns)")
                    
                    for col in columns:
                        name = col.get('name', '')
                        description = col.get('description', '')
                        if description:
                            lines.append(f"- `{name}`: {description}")
                        else:
                            lines.append(f"- `{name}`")
        else:
            lines.append("## Columns: No columns with descriptions found")
            lines.append("")
        
        attribute_definitions = schema_data.get('attribute_definitions', [])
        if attribute_definitions:
            lines.append("")
            lines.append("## Attribute Definitions (JSON Schema for Assets.attribute_json):")
            lines.append("")
            lines.append("The following attributes are stored as JSON in the `attribute_json` column of the **Assets** table:")
            lines.append("")
            lines.append("| Attribute Name | Description |")
            lines.append("|---------------|-------------|")
            for attr in attribute_definitions:
                name = attr.get('Attribute Name', '')
                description = attr.get('Attribute Description', '')
                lines.append(f"| `{name}` | {description} |")
        else:
            lines.append("")
            lines.append("## Attribute Definitions: No attribute definitions found")
        
        return "\n".join(lines)
    
    def _format_data_for_frontend(self, result: Dict[str, Any], page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Format data for frontend display with proper field extraction.
        Returns complete structured data for frontend rendering with pagination support.
        """
        data = result.get('result', {})
        rows = data.get('rows', [])
        total_rows = data.get('row_count', 0)
        
        # Validate pagination parameters
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        total_pages = max(1, (total_rows + page_size - 1) // page_size) if total_rows > 0 else 1
        page = min(page, total_pages)
        
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_rows)
        
        logger.info(f"📊 Formatting {total_rows} rows for frontend (page {page}/{total_pages}, showing {start_idx+1}-{end_idx})")
        
        if not rows:
            return {
                'total_rows': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 1,
                'start_row': 0,
                'end_row': 0,
                'display_fields': [],
                'field_keys': [],
                'rows': [],
                'sample_rows': [],
                'is_aggregate': False,
                'is_row_aggregate': False,
                'is_summarize_aggregate': False,
                'aggregate_value': None,
                'aggregate_label': None,
                'summary': {
                    'total': 0,
                    'validation': {'pass': 0, 'fail': 0, 'other': 0},
                    'top_validation_issues': [],
                    'cat_code_distribution': []
                },
                'pagination': {
                    'current_page': page,
                    'total_pages': 1,
                    'total_rows': 0,
                    'page_size': page_size,
                    'has_previous': False,
                    'has_next': False,
                    'start_row': 0,
                    'end_row': 0
                }
            }
        
        # Check if this is a ROW() result (single value aggregate)
        is_row_aggregate = False
        aggregate_value = None
        aggregate_label = None
        
        if total_rows == 1 and rows and isinstance(rows[0], dict):
            row_keys = list(rows[0].keys())
            if len(row_keys) == 1:
                key = row_keys[0]
                if key.startswith('[') and key.endswith(']'):
                    is_row_aggregate = True
                    aggregate_label = key[1:-1]
                    aggregate_value = rows[0].get(key)
                    logger.info(f"📊 Detected ROW() aggregate: {aggregate_label} = {aggregate_value}")
        
        # Check if this is a SUMMARIZE result (multiple rows with aggregates)
        is_summarize_aggregate = False
        if total_rows > 1 and rows and isinstance(rows[0], dict):
            row_keys = list(rows[0].keys())
            aggregate_keys = ['Count', 'Total', 'Sum', 'Average', 'Min', 'Max']
            has_aggregate = any(k in row_keys for k in aggregate_keys)
            if has_aggregate:
                is_summarize_aggregate = True
                logger.info(f"📊 Detected SUMMARIZE aggregate with {total_rows} rows, keys: {row_keys}")
        
        is_aggregate = is_row_aggregate or is_summarize_aggregate
        
        # Define display fields and their mapping
        field_mapping = {
            'CEDD_I_AssetID': 'Asset ID',
            'client_asset_id': 'Asset ID (Legacy)',
            'Family Name': 'Family Name',
            'Validation Result': 'Validation Result',
            'Validation Remarks': 'Validation Remarks',
            'CEDD_I_SpaceID': 'Space ID',
            'Space ID': 'Space ID',
            'CAT Code': 'CAT Code'
        }
        
        # Determine which fields exist in the data
        display_fields = []
        field_keys = []
        
        sample_row = rows[0] if rows else {}
        for key, display_name in field_mapping.items():
            exists = False
            for row_key in sample_row.keys():
                clean_row_key = self._clean_key(row_key)
                if clean_row_key == key or clean_row_key == self._clean_key(key):
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
                field_keys.append(key)
        
        # Also check for aggregate fields
        aggregate_fields = ['Count', 'Total', 'Sum', 'Average', 'Min', 'Max']
        for agg_field in aggregate_fields:
            if agg_field in sample_row or f"[{agg_field}]" in sample_row:
                if agg_field not in display_fields:
                    display_fields.append(agg_field)
        
        # If no fields found, use default fields
        if not display_fields:
            display_fields = ['Validation Result', 'Count']
            field_keys = ['Validation Result', 'Count']
        
        # Process ALL rows
        processed_rows = []
        for row in rows:
            processed_row = {}
            for i, field_key in enumerate(field_keys):
                display_name = display_fields[i] if i < len(display_fields) else field_key
                value = self._extract_from_row(row, field_key, '')
                processed_row[display_name] = str(value) if value else ''
            processed_rows.append(processed_row)
        
        # Get the current page rows
        page_rows = processed_rows[start_idx:end_idx]
        
        # Build summary statistics (using all rows)
        summary = self._build_summary(rows)
        
        return {
            'total_rows': total_rows,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'start_row': start_idx + 1 if total_rows > 0 else 0,
            'end_row': end_idx,
            'display_fields': display_fields,
            'field_keys': field_keys,
            'rows': page_rows,
            'all_rows': processed_rows,
            'sample_rows': processed_rows[:20],
            'is_aggregate': is_aggregate,
            'is_row_aggregate': is_row_aggregate,
            'is_summarize_aggregate': is_summarize_aggregate,
            'aggregate_label': aggregate_label,
            'aggregate_value': aggregate_value,
            'summary': summary,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_rows': total_rows,
                'page_size': page_size,
                'has_previous': page > 1,
                'has_next': page < total_pages,
                'start_row': start_idx + 1 if total_rows > 0 else 0,
                'end_row': end_idx
            }
        }
    
    def _build_summary(self, rows: List[Dict]) -> Dict[str, Any]:
        """Build summary statistics from the data."""
        summary = {
            'total': len(rows),
            'validation': {'pass': 0, 'fail': 0, 'other': 0},
            'top_validation_issues': [],
            'cat_code_distribution': []
        }
        
        remarks_counter = Counter()
        cat_code_counter = Counter()
        
        for row in rows:
            # Count pass/fail
            result_val = self._extract_from_row(row, 'Validation Result', '')
            if 'Pass' in result_val:
                summary['validation']['pass'] += 1
            elif 'Fail' in result_val or 'Validation Failed' in result_val:
                summary['validation']['fail'] += 1
            else:
                summary['validation']['other'] += 1
            
            # Extract validation remarks
            remark = self._extract_from_row(row, 'Validation Remarks', '')
            if remark:
                import re
                cat_match = re.search(r"CAT Code\s*'([^']+)'", remark)
                if cat_match:
                    cat_code = cat_match.group(1)
                    remarks_counter[f"CAT Code '{cat_code}' not found"] += 1
                    cat_code_counter[cat_code] += 1
                else:
                    remarks_counter[remark] += 1
        
        # Top validation issues
        for issue, count in remarks_counter.most_common(5):
            summary['top_validation_issues'].append({
                'issue': issue,
                'count': count
            })
        
        # CAT Code distribution
        for cat_code, count in cat_code_counter.most_common(5):
            summary['cat_code_distribution'].append({
                'cat_code': cat_code,
                'count': count
            })
        
        return summary
    
    def _format_markdown(self, result: Dict[str, Any], page: int = 1, page_size: int = 20) -> str:
        """
        Format results as markdown for display with pagination info.
        Handles both aggregate (ROW) results and regular table results.
        """
        data = result.get('result', {})
        rows = data.get('rows', [])
        row_count = data.get('row_count', 0)
        
        # Check if this is a ROW() aggregate result
        is_row_aggregate = False
        aggregate_label = None
        aggregate_value = None
        
        if row_count == 1 and rows and isinstance(rows[0], dict):
            row_keys = list(rows[0].keys())
            if len(row_keys) == 1:
                key = row_keys[0]
                if key.startswith('[') and key.endswith(']'):
                    is_row_aggregate = True
                    aggregate_label = key[1:-1]
                    aggregate_value = rows[0].get(key)
        
        # If it's a ROW() aggregate result, show it as a single value
        if is_row_aggregate:
            lines = []
            lines.append(f"## 📊 Query Result\n")
            lines.append("")
            lines.append(f"### {aggregate_label}: **{aggregate_value}**")
            lines.append("")
            lines.append(f"*This is a single value result from an aggregate query.*")
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("**DAX Query:** `EVALUATE ROW(...)`")
            return "\n".join(lines)
        
        # Check if this is a SUMMARIZE aggregate result
        is_summarize_aggregate = False
        if row_count > 1 and rows and isinstance(rows[0], dict):
            row_keys = list(rows[0].keys())
            aggregate_keys = ['Count', 'Total', 'Sum', 'Average', 'Min', 'Max']
            has_aggregate = any(k in row_keys for k in aggregate_keys)
            if has_aggregate:
                is_summarize_aggregate = True
        
        # Regular table results
        # Calculate pagination
        total_pages = max(1, (row_count + page_size - 1) // page_size) if row_count > 0 else 1
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, row_count)
        page_rows = rows[start_idx:end_idx] if rows else []
        
        lines = []
        
        # Add note if this is a SUMMARIZE result
        if is_summarize_aggregate:
            lines.append(f"## 📊 Aggregate Query Results\n")
        else:
            lines.append(f"## 📊 Query Results\n")
        
        lines.append(f"**Total Rows:** {row_count}")
        lines.append(f"**Showing:** {start_idx + 1 if row_count > 0 else 0} - {end_idx} of {row_count}")
        lines.append(f"**Page:** {page}/{total_pages}\n")
        
        if row_count == 0:
            lines.append("### ℹ️ No data found")
            lines.append("")
            lines.append("The query returned 0 rows. This means no records matched the criteria.")
            return "\n".join(lines)
        
        if not page_rows:
            return "\n".join(lines)
        
        # Get display fields
        sample_row = rows[0] if rows else {}
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
        
        display_fields = []
        # Also check for aggregate fields like Count, Total, etc.
        aggregate_fields = ['Count', 'Total', 'Sum', 'Average', 'Min', 'Max']
        
        for key in sample_row.keys():
            clean_key = self._clean_key(key)
            # Check if it's a known display field
            display_name = field_mapping.get(clean_key, None)
            if display_name:
                if display_name not in display_fields:
                    display_fields.append(display_name)
            # Check if it's an aggregate field
            elif clean_key in aggregate_fields:
                display_fields.append(clean_key)
        
        # If no fields found, use default fields
        if not display_fields:
            display_fields = ['Validation Result', 'Count']
        
        # Build table with current page rows
        lines.append("### Asset Details\n")
        lines.append("| # | " + " | ".join(display_fields) + " |")
        lines.append("| " + " | ".join(["---"] * (len(display_fields) + 1)) + " |")
        
        for idx, row in enumerate(page_rows, start_idx + 1):
            row_values = [str(idx)]
            for field in display_fields:
                # Find the key for this field
                key = None
                clean_field = field
                for k, v in field_mapping.items():
                    if v == field:
                        key = k
                        break
                if not key:
                    # Check if it's an aggregate field directly
                    if field in row:
                        key = field
                    elif field in row.keys():
                        key = field
                
                if key:
                    val = self._extract_from_row(row, key, '')
                    row_values.append(str(val) if val else '')
                else:
                    # Try to find by clean key
                    found = False
                    for row_key, row_val in row.items():
                        if self._clean_key(row_key) == field:
                            row_values.append(str(row_val) if row_val else '')
                            found = True
                            break
                    if not found:
                        row_values.append('')
            lines.append("| " + " | ".join(row_values) + " |")
        
        if row_count > page_size:
            lines.append("")
            lines.append(f"*... and {row_count - end_idx} more rows*")
        
        # Add pagination controls
        lines.append("")
        lines.append("### 📄 Pagination")
        lines.append(f"**Page {page} of {total_pages}** | **Total: {row_count} rows**")
        
        nav_links = []
        if page > 1:
            nav_links.append(f"[⬅️ Previous](?page={page-1})")
        if page < total_pages:
            nav_links.append(f"[Next ➡️](?page={page+1})")
        if nav_links:
            lines.append(" | ".join(nav_links))
        
        # Add summary
        summary = self._build_summary(rows)
        if summary['validation']['fail'] > 0 or summary['validation']['pass'] > 0:
            lines.append("")
            lines.append("### Summary")
            lines.append(f"- **Total:** {summary['total']}")
            lines.append(f"- **Passed:** {summary['validation']['pass']}")
            lines.append(f"- **Failed:** {summary['validation']['fail']}")
        
        if summary['top_validation_issues']:
            lines.append("")
            lines.append("### Top Validation Issues")
            for issue in summary['top_validation_issues']:
                lines.append(f"- {issue['issue']}: {issue['count']} assets")
        
        return "\n".join(lines)
    
    def execute(self, input_text: str = "", **kwargs) -> Dict[str, Any]:
        """Execute the skill."""
        logger.info(f"🔧 DAXQuerySkill executing")
        logger.info(f"   Input: {input_text[:100] if input_text else 'No input'}...")
        
        dax_query = kwargs.get('dax_query')
        workspace_id = kwargs.get('workspace_id') or self.default_workspace_id
        dataset_id = kwargs.get('dataset_id') or self.default_dataset_id
        output_format = kwargs.get('format', 'markdown')
        get_schema = kwargs.get('get_schema', False)
        page = kwargs.get('page', 1)
        page_size = kwargs.get('page_size', 20)
        
        # If user wants schema or no query provided
        if get_schema or not dax_query:
            logger.info("📋 Fetching schema for LLM")
            schema_data = self._get_schema_for_llm(workspace_id, dataset_id)
            
            if schema_data.get('success'):
                return {
                    'success': True,
                    'response': schema_data.get('schema_text', 'No schema available'),
                    'data': schema_data,
                    'is_schema': True
                }
            else:
                return {
                    'success': False,
                    'error': schema_data.get('error', 'Could not fetch schema'),
                    'is_schema': True,
                    'response': schema_data.get('schema_text', 'Could not fetch schema.')
                }
        
        # Validate for data query
        if not POWERBI_AVAILABLE:
            return {
                'success': False,
                'error': 'Power BI functions not available.',
                'suggestions': ['Check powerbi_tools installation']
            }
        
        if not dataset_id:
            return {
                'success': False,
                'error': 'Dataset ID is required',
                'suggestions': ['Set POWERBI_MODEL_ID in .env']
            }
        
        logger.info(f"📝 DAX Query from LLM: {dax_query}")
        logger.info(f"📄 Page: {page}, Page Size: {page_size}")
        
        try:
            logger.info(f"⚡ Executing DAX query: {dax_query[:100] if dax_query else 'No query'}...")
            result = query_data(dax_query, dataset_id, workspace_id)
            
            logger.info(f"📊 Raw result success: {result.get('success')}")
            if result.get('success'):
                result_data = result.get('result', {})
                rows = result_data.get('rows', [])
                row_count = result_data.get('row_count', 0)
                logger.info(f"📊 Raw result - rows: {len(rows)}, row_count: {row_count}")
                if rows:
                    logger.info(f"📊 Raw result - first row sample: {str(rows[0])[:200]}...")
            
            if result.get('success'):
                if output_format == 'json':
                    response = json.dumps(result, indent=2, default=str)
                    return {
                        'success': True,
                        'response': response,
                        'data': result.get('result', {}),
                        'dax_query': dax_query
                    }
                else:
                    # Format for frontend display with pagination
                    frontend_data = self._format_data_for_frontend(result, page, page_size)
                    markdown_response = self._format_markdown(result, page, page_size)
                    
                    return {
                        'success': True,
                        'response': markdown_response,
                        'data': frontend_data,
                        'dax_query': dax_query,
                        'total_rows': frontend_data.get('total_rows', 0),
                        'display_fields': frontend_data.get('display_fields', []),
                        'summary': frontend_data.get('summary', {}),
                        'pagination': frontend_data.get('pagination', {})
                    }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'suggestions': result.get('suggestions', []),
                    'dax_query': dax_query
                }
                
        except Exception as e:
            logger.error(f"❌ DAX query execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'suggestions': ['Check DAX syntax and try again'],
                'dax_query': dax_query
            }
    
    def get_info(self) -> Dict[str, Any]:
        """Get skill information."""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'category': self.category,
            'tags': self.tags,
            'type': 'SkillKit',
            'source': 'skillkit',
            'powerbi_available': POWERBI_AVAILABLE,
            'default_workspace_id': self.default_workspace_id,
            'default_dataset_id': self.default_dataset_id,
            'default_page_size': self.default_page_size,
            'max_page_size': self.max_page_size,
            'documentation': self.get_skill_documentation()
        }


def create_skill():
    """Factory function for SkillKit discovery."""
    logger.info("🏭 Creating DAXQuerySkill instance")
    return DAXQuerySkill()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 Testing DAXQuerySkill")
    print("=" * 60)
    
    skill = DAXQuerySkill()
    print(f"Power BI Available: {POWERBI_AVAILABLE}")
    print(f"Skill Name: {skill.name}")
    print(f"Default Page Size: {skill.default_page_size}")
    print(f"Max Page Size: {skill.max_page_size}")
    
    if POWERBI_AVAILABLE:
        print("\n📊 Testing schema retrieval...")
        result = skill.execute(get_schema=True)
        if result.get('success'):
            print("✅ Schema retrieved successfully")
            print("\n" + result['response'])
        else:
            print(f"❌ Error: {result.get('error')}")
    else:
        print("\n⚠️ Power BI not available")
    
    print("\n" + "=" * 60)