import React, { useState } from 'react';

interface FeedbackButtonsProps {
  traceId?: string;
  spanId?: string;
  onFeedbackSubmitted?: (feedback: 'thumbs_up' | 'thumbs_down', reason?: string) => void;
}

const FeedbackButtons: React.FC<FeedbackButtonsProps> = ({ 
  traceId, 
  spanId, 
  onFeedbackSubmitted 
}) => {
  const [selectedFeedback, setSelectedFeedback] = useState<'thumbs_up' | 'thumbs_down' | null>(null);
  const [showReasonInput, setShowReasonInput] = useState(false);
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Debug logging for testing
  console.log('FeedbackButtons rendered:', { traceId, spanId, selectedFeedback, showReasonInput });

  const handleFeedbackClick = (feedbackType: 'thumbs_up' | 'thumbs_down') => {
    console.log('Feedback button clicked:', feedbackType, 'current:', selectedFeedback);
    
    if (selectedFeedback === feedbackType) {
      // If already selected, toggle off and hide reason input
      setSelectedFeedback(null);
      setShowReasonInput(false);
      setReason('');
      console.log('Toggled off feedback');
    } else {
      setSelectedFeedback(feedbackType);
      setShowReasonInput(true);
      console.log('Selected feedback:', feedbackType, 'showing reason input');
    }
  };

  const submitFeedback = async () => {
    console.log('submitFeedback called:', { selectedFeedback, traceId, spanId });
    
    if (!selectedFeedback) {
      console.log('No feedback selected');
      return;
    }

    setIsSubmitting(true);
    try {
      // If we have a real trace ID, submit to API
      if (traceId && !traceId.startsWith('test-')) {
        const { submitFeedback: submitFeedbackAPI } = await import('../services/api');
        
        await submitFeedbackAPI({
          trace_id: traceId,
          span_id: spanId,
          feedback_type: selectedFeedback,
          reason: reason.trim() || undefined,
        });
        console.log('Feedback submitted to API');
      } else {
        // For testing with mock trace IDs, just log
        console.log('Test mode: Feedback would be submitted:', {
          trace_id: traceId,
          span_id: spanId,
          feedback_type: selectedFeedback,
          reason: reason.trim() || undefined,
        });
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // Notify parent component
      onFeedbackSubmitted?.(selectedFeedback, reason.trim() || undefined);

      // Hide the reason input after successful submission
      setShowReasonInput(false);
      console.log('Feedback submission completed');
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      // Show user-friendly error message
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReasonSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitFeedback();
  };

  // Temporarily show buttons for testing even without trace ID
  // TODO: Restore this check for final production
  // if (!traceId) {
  //   // Don't show feedback buttons if we don't have a trace ID
  //   return null;
  // }

  return (
    <div className="feedback-container">
      <div className="feedback-buttons">
        <button
          className={`feedback-btn thumbs-up ${selectedFeedback === 'thumbs_up' ? 'selected' : ''}`}
          onClick={() => handleFeedbackClick('thumbs_up')}
          disabled={isSubmitting}
          title="This response was helpful"
        >
          <span style={{ fontSize: '18px' }}>👍</span>
          <span style={{ marginLeft: '4px', fontSize: '12px' }}>Good</span>
        </button>
        <button
          className={`feedback-btn thumbs-down ${selectedFeedback === 'thumbs_down' ? 'selected' : ''}`}
          onClick={() => handleFeedbackClick('thumbs_down')}
          disabled={isSubmitting}
          title="This response was not helpful"
        >
          <span style={{ fontSize: '18px' }}>👎</span>
          <span style={{ marginLeft: '4px', fontSize: '12px' }}>Bad</span>
        </button>
      </div>

      {showReasonInput && (
        <div className="reason-input-container">
          <form onSubmit={handleReasonSubmit}>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                selectedFeedback === 'thumbs_up' 
                  ? "What did you like about this response? (optional)"
                  : "What could be improved? (optional)"
              }
              className="reason-textarea"
              rows={2}
              disabled={isSubmitting}
            />
            <div className="reason-buttons">
              <button
                type="submit"
                className="submit-btn"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit'}
              </button>
              <button
                type="button"
                className="cancel-btn"
                onClick={() => {
                  setShowReasonInput(false);
                  setReason('');
                }}
                disabled={isSubmitting}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default FeedbackButtons;