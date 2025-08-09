# Feedback Implementation for Self-Optimizing Agents

This document describes the implementation of thumbs-up/thumbs-down feedback functionality for the RAG system.

## Overview

The implementation allows users to provide binary feedback (thumbs up/down) on AI responses with optional text reasons. The feedback is stored in Opik using the `overall_quality` metric with values:
- Thumbs up = 1.0 (good)
- Thumbs down = 0.0 (bad)

## Components Added/Modified

### Frontend Components

1. **FeedbackButtons.tsx** - New component
   - Renders thumbs up/down buttons
   - Shows optional reason input dialog
   - Handles submission to backend API
   - Only shows if trace ID is available

2. **ChatMessage.tsx** - Modified
   - Added FeedbackButtons for bot messages only
   - Passes trace/span IDs to feedback component

3. **ChatContainer.tsx** - Modified
   - Extracts trace/span IDs from API response
   - Passes them to Message objects

### Backend API

4. **api_server.py** - Modified
   - Added `get_current_trace_and_span_ids()` helper function
   - Modified query endpoint to return trace/span IDs
   - Added `/feedback` endpoint for recording feedback
   - Uses Opik client to log feedback scores

### Types and Services

5. **types/index.ts** - Modified
   - Added trace_id/span_id to Message and QueryResponse interfaces
   - Added FeedbackRequest interface

6. **services/api.ts** - Modified
   - Added submitFeedback function for API calls

7. **App.css** - Modified
   - Added comprehensive styling for feedback buttons and reason input

## API Endpoints

### POST /feedback
Records user feedback for traces/spans in Opik.

**Request Body:**
```json
{
  "trace_id": "optional-trace-id",
  "span_id": "optional-span-id", 
  "feedback_type": "thumbs_up" | "thumbs_down",
  "reason": "optional text reason"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Feedback recorded successfully"
}
```

## User Flow

1. User asks a question
2. System generates response with trace/span tracking
3. Response includes trace_id and span_id
4. UI shows thumbs up/down buttons below bot responses
5. User clicks button (optional reason dialog appears)
6. User submits feedback
7. Feedback sent to `/feedback` endpoint
8. Backend logs feedback to Opik with binary score

## Opik Integration

The feedback is recorded using Opik's feedback scoring system:
- `log_traces_feedback_scores()` for trace-level feedback
- `log_spans_feedback_scores()` for span-level feedback
- Metric name: "overall_quality"
- Score: 1.0 (thumbs up) or 0.0 (thumbs down)
- Optional reason text included

## Error Handling

- Graceful fallback if trace IDs unavailable
- Network error handling in UI
- Backend validation of feedback types
- Fallback to logging warnings if Opik calls fail

## Future Enhancements

- Success/error toast notifications
- Feedback analytics dashboard
- More granular feedback categories
- Bulk feedback operations
- Feedback history per user session