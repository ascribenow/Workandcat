"""
JSON Safe Utilities
Helper functions for safely handling JSONB data from PostgreSQL
"""

import json
from typing import Union, List, Dict, Any

def as_json(val: Union[str, dict, list, None]) -> Union[List, Dict]:
    """
    Safely convert JSONB/JSON data to Python object
    
    Args:
        val: Value from database (could be already parsed dict/list or JSON string)
        
    Returns:
        Parsed Python object (dict or list)
    """
    # If DB driver already parsed JSONB, it's a dict/list; if it's a string, parse it.
    if isinstance(val, (dict, list)):
        return val
    if val is None:
        return []
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return []
    
    # Fallback for unexpected types
    return []

def safe_json_parse(json_data: Any) -> Union[Dict, List]:
    """
    Legacy alias for as_json for backwards compatibility
    """
    return as_json(json_data)