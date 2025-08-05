# Conditional Opik Tracking

This document describes the conditional Opik tracking feature that allows you to globally enable or disable Opik tracking across the entire application.

## Overview

The conditional Opik tracking system provides a way to control whether Opik tracking is active without modifying code. This is useful for:

- Development environments where you don't want to send data to Opik
- Testing scenarios where tracking might interfere with results
- Production environments where you want to temporarily disable tracking
- Cost control by reducing the number of tracked calls

## How It Works

The system uses a global environment variable `OPIK_TRACKING_ENABLED` to control whether Opik tracking is active. When disabled, all `@conditional_opik_track` decorators become no-ops, effectively removing tracking without code changes.

## Configuration

### Environment Variable

Set the `OPIK_TRACKING_ENABLED` environment variable in your `.env` file:

```bash
# Enable Opik tracking (default)
OPIK_TRACKING_ENABLED=true

# Disable Opik tracking
OPIK_TRACKING_ENABLED=false
```

### Default Behavior

If `OPIK_TRACKING_ENABLED` is not set, tracking is **enabled by default** (`true`).

## Usage

### Decorator Usage

Replace `@opik.track(flush=True)` with `@conditional_opik_track(flush=True)`:

```python
from opik_utils import conditional_opik_track

@conditional_opik_track(flush=True)
async def my_function():
    # This function will only be tracked if OPIK_TRACKING_ENABLED=true
    return "result"
```

### Utility Functions

The `opik_utils` module provides several utility functions:

```python
from opik_utils import (
    is_opik_tracking_enabled,
    get_opik_tracking_status,
    set_opik_tracking_enabled
)

# Check if tracking is enabled
if is_opik_tracking_enabled():
    print("Opik tracking is active")

# Get detailed status information
status = get_opik_tracking_status()
print(f"Tracking enabled: {status['enabled']}")
print(f"API key set: {status['api_key_set']}")
print(f"Workspace set: {status['workspace_set']}")

# Programmatically enable/disable tracking
set_opik_tracking_enabled(False)  # Disable
set_opik_tracking_enabled(True)   # Enable
```

## Files Updated

The following files have been updated to use conditional tracking:

### Core Files
- `src/opik_utils.py` - New utility module for conditional tracking
- `src/self_optimizing_agents.py` - Updated all `@opik.track` decorators
- `src/rag_obs_eval.py` - Updated all `@opik.track` decorators
- `src/prompt_optimization.py` - Updated to respect conditional tracking

### Test Files
- `src/test_conditional_tracking.py` - Test script for the feature

## Testing

Run the test script to verify the conditional tracking works:

```bash
cd src
python test_conditional_tracking.py
```

The test script will:
1. Check the initial tracking status
2. Run functions with tracking enabled
3. Disable tracking and test again
4. Re-enable tracking
5. Test environment variable override

## Migration Guide

To migrate existing code to use conditional tracking:

1. **Import the utility**: Add `from opik_utils import conditional_opik_track` to your imports
2. **Replace decorators**: Change `@opik.track(flush=True)` to `@conditional_opik_track(flush=True)`
3. **Test**: Run your code with `OPIK_TRACKING_ENABLED=false` to verify tracking is disabled
4. **Verify**: Run with `OPIK_TRACKING_ENABLED=true` to verify tracking works normally

## Benefits

- **No Code Changes**: Disable tracking without modifying function decorators
- **Environment Control**: Different settings for different environments
- **Cost Control**: Reduce Opik usage when needed
- **Development Friendly**: Easier local development without tracking overhead
- **Backward Compatible**: Existing code continues to work unchanged

## Troubleshooting

### Tracking Not Working

1. Check if `OPIK_TRACKING_ENABLED` is set to `true`
2. Verify Opik credentials are configured
3. Check the status output when the application starts

### Functions Still Being Tracked

1. Ensure you're using `@conditional_opik_track` instead of `@opik.track`
2. Check that the environment variable is being loaded correctly
3. Verify the import statement includes the conditional decorator

### Environment Variable Not Working

1. Make sure the `.env` file is in the correct location
2. Verify the variable name is exactly `OPIK_TRACKING_ENABLED`
3. Check that `python-dotenv` is loading the file correctly 