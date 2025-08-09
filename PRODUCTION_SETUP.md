# Production Setup Guide for Feedback System

## Environment Variables Required

Set these environment variables for production deployment:

```bash
# Required for Opik Integration
export OPIK_API_KEY="your-opik-api-key"
export OPIK_WORKSPACE="your-opik-workspace"
export OPIK_PROJECT_NAME="your-project-name"  # Optional, defaults to "ODSC-RAG"

# Required for LLM calls
export OPENROUTER_API_KEY="your-openrouter-api-key"

# Optional: Adjust metrics sampling rate (default: 5%)
export METRICS_SAMPLE_RATE="0.05"

# Optional: Enable/disable guardrails (default: true)
export GUARDRAILS_ENABLED="true"
```

## Production Changes Made

### ✅ Frontend Changes
1. **Removed mock data** - No more test bot message on startup
2. **Restored trace ID validation** - Feedback buttons only show with valid trace IDs
3. **Cleaned up debug logging** - Minimal logging for production
4. **Enhanced error handling** - User-friendly error messages

### ✅ Backend Changes
1. **UUID validation** - Handles both real and mock IDs gracefully
2. **Development mode detection** - Skips Opik logging for non-UUID IDs
3. **Production Opik integration** - Full feedback logging with real trace/span IDs

## Deployment Steps

### 1. Set Environment Variables
```bash
# In your production environment
export OPIK_API_KEY="your-actual-opik-api-key"
export OPIK_WORKSPACE="your-actual-workspace"
export OPENROUTER_API_KEY="your-actual-openrouter-key"
```

### 2. Build Frontend
```bash
cd src/ui
npm run build
```

### 3. Start Backend
```bash
cd src
python api_server.py
```

### 4. Verify Configuration
Check logs for:
```
INFO: Opik configured for cloud tracking
```

## How It Works in Production

### Real Trace Flow
1. User asks question → RAG system generates response
2. `generate_ui_response_with_details()` creates Opik trace/span
3. `get_current_trace_and_span_ids()` extracts real UUIDs
4. API returns response with trace_id and span_id
5. UI shows feedback buttons below bot message
6. User feedback is logged to Opik with "overall_quality" metric

### Feedback Recording
- **Metric name**: "overall_quality"
- **Score values**: 0 = thumbs up (good), 1 = thumbs down (bad)
- **Optional reason**: User-provided text explanation
- **Logged to**: Both trace and span in Opik

## Monitoring & Analytics

### Opik Dashboard
View feedback in your Opik dashboard by:
1. Filtering traces by feedback scores
2. Searching for "overall_quality" metric
3. Analyzing user satisfaction trends
4. Identifying problematic responses

### Example Opik Query
```
traces.feedback_scores.overall_quality < 0.5  # Good feedback (thumbs up)
traces.feedback_scores.overall_quality > 0.5  # Bad feedback (thumbs down)
```

## Troubleshooting

### No Feedback Buttons Appearing
- Check that trace IDs are being generated (look for @opik.track decorators)
- Verify Opik is configured properly (check logs)
- Ensure real questions are being asked (not just loading the page)

### Feedback Not Logging to Opik
- Verify environment variables are set
- Check network connectivity to Opik
- Look for UUID validation errors in logs

### Error Messages
- "Failed to submit feedback" - Network or API issue
- UUID validation errors - Check trace/span ID format

## Rollback Plan

If issues occur, you can quickly revert to development mode by:
1. Commenting out production environment variables
2. The system will fall back to local mode automatically
3. Feedback will still work but won't log to Opik

The system is now production-ready with full Opik integration!