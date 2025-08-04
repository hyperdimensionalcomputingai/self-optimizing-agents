"""
Opik tracking utilities for conditional tracking based on environment variables.

This module provides utilities for conditionally enabling/disabling Opik tracking
across the entire application based on environment configuration.
"""

import os
import functools
from typing import Callable, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global setting for Opik tracking
OPIK_TRACKING_ENABLED = os.environ.get("OPIK_TRACKING_ENABLED", "true").lower() == "true"


def conditional_opik_track(func: Optional[Callable] = None, **opik_kwargs):
    """
    Conditionally apply opik.track decorator based on OPIK_TRACKING_ENABLED setting.
    
    Args:
        func: The function to decorate (when used as a decorator)
        **opik_kwargs: Additional arguments to pass to opik.track
        
    Returns:
        The decorated function or a decorator function
    """
    def decorator(f: Callable) -> Callable:
        if OPIK_TRACKING_ENABLED:
            # Import opik here to avoid circular imports
            import opik
            return opik.track(**opik_kwargs)(f)
        return f
    
    if func is None:
        return decorator
    return decorator(func)


def is_opik_tracking_enabled() -> bool:
    """
    Check if Opik tracking is currently enabled.
    
    Returns:
        True if Opik tracking is enabled, False otherwise
    """
    return OPIK_TRACKING_ENABLED


def set_opik_tracking_enabled(enabled: bool) -> None:
    """
    Set the Opik tracking enabled state.
    
    Args:
        enabled: Whether to enable Opik tracking
    """
    global OPIK_TRACKING_ENABLED
    OPIK_TRACKING_ENABLED = enabled


def get_opik_tracking_status() -> dict:
    """
    Get the current Opik tracking configuration status.
    
    Returns:
        Dictionary with tracking status information
    """
    return {
        "enabled": OPIK_TRACKING_ENABLED,
        "environment_variable": os.environ.get("OPIK_TRACKING_ENABLED", "true"),
        "api_key_set": bool(os.environ.get("OPIK_API_KEY")),
        "workspace_set": bool(os.environ.get("OPIK_WORKSPACE")),
    } 