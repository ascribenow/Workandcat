"""
UUID validation utilities for canonical format enforcement
Canonical format: lowercase, dashed, 36 characters
Example: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
"""

import re
from typing import Optional
from fastapi import HTTPException

UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def validate_canonical_uuid(value: str, field_name: str = "id") -> str:
    """
    Validate UUID is in canonical format
    
    Args:
        value: UUID string to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated and normalized UUID string
        
    Raises:
        HTTPException: If UUID format is invalid (400 Bad Request)
    """
    if not value:
        raise HTTPException(400, f"Missing required field: {field_name}")
    
    value_lower = value.lower().strip()
    
    if not UUID_PATTERN.match(value_lower):
        raise HTTPException(
            400,
            f"Invalid {field_name} format. Must be lowercase UUID with dashes (e.g., 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11')"
        )
    
    return value_lower


def normalize_uuid(value: Optional[str]) -> Optional[str]:
    """
    Normalize UUID to canonical format (lowercase with dashes)
    
    Args:
        value: UUID string to normalize (may be uppercase or missing dashes)
        
    Returns:
        Normalized UUID string or None if invalid
    """
    if not value:
        return None
    
    # Remove non-hex characters except dashes
    cleaned = ''.join(c for c in value.lower() if c in '0123456789abcdef-')
    
    # Add dashes if missing (32 hex chars without dashes)
    if '-' not in cleaned and len(cleaned) == 32:
        cleaned = f"{cleaned[0:8]}-{cleaned[8:12]}-{cleaned[12:16]}-{cleaned[16:20]}-{cleaned[20:32]}"
    
    # Validate the normalized UUID
    return cleaned if UUID_PATTERN.match(cleaned) else None


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID without raising exceptions
    
    Args:
        value: String to check
        
    Returns:
        True if valid UUID, False otherwise
    """
    if not value:
        return False
    
    value_lower = value.lower().strip()
    return bool(UUID_PATTERN.match(value_lower))


def validate_uuid_list(values: list[str], field_name: str = "ids") -> list[str]:
    """
    Validate a list of UUIDs
    
    Args:
        values: List of UUID strings to validate
        field_name: Name of the field for error messages
        
    Returns:
        List of validated and normalized UUID strings
        
    Raises:
        HTTPException: If any UUID format is invalid (400 Bad Request)
    """
    if not values:
        return []
    
    validated = []
    for idx, value in enumerate(values):
        try:
            validated.append(validate_canonical_uuid(value, f"{field_name}[{idx}]"))
        except HTTPException as e:
            # Re-raise with more context
            raise HTTPException(
                400,
                f"Invalid UUID at index {idx} in {field_name}: {e.detail}"
            )
    
    return validated
