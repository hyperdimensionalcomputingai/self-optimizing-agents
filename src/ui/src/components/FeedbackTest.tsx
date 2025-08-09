import React from 'react';
import FeedbackButtons from './FeedbackButtons';

const FeedbackTest: React.FC = () => {
  const handleFeedbackSubmitted = (feedback: 'thumbs_up' | 'thumbs_down', reason?: string) => {
    console.log('Test feedback submitted:', { feedback, reason });
    alert(`Feedback submitted: ${feedback}${reason ? ` with reason: ${reason}` : ''}`);
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#000', color: '#fff', minHeight: '100vh' }}>
      <h2>Feedback Buttons Test</h2>
      
      <div style={{ margin: '20px 0', padding: '20px', border: '1px solid #fff', borderRadius: '8px' }}>
        <h3>Test 1: With Trace ID</h3>
        <div style={{ backgroundColor: '#1a1a1a', padding: '15px', borderRadius: '8px', marginBottom: '10px' }}>
          This is a test bot message with trace ID
        </div>
        <FeedbackButtons
          traceId="test-trace-123"
          spanId="test-span-456"
          onFeedbackSubmitted={handleFeedbackSubmitted}
        />
      </div>

      <div style={{ margin: '20px 0', padding: '20px', border: '1px solid #fff', borderRadius: '8px' }}>
        <h3>Test 2: Without Trace ID</h3>
        <div style={{ backgroundColor: '#1a1a1a', padding: '15px', borderRadius: '8px', marginBottom: '10px' }}>
          This is a test bot message without trace ID
        </div>
        <FeedbackButtons
          onFeedbackSubmitted={handleFeedbackSubmitted}
        />
      </div>

      <div style={{ margin: '20px 0', padding: '20px', border: '1px solid #fff', borderRadius: '8px' }}>
        <h3>Test 3: Buttons Only</h3>
        <div style={{ backgroundColor: '#1a1a1a', padding: '15px', borderRadius: '8px', marginBottom: '10px' }}>
          This should show buttons even without trace ID (development mode)
        </div>
        <div className="feedback-container">
          <div className="feedback-buttons">
            <button className="feedback-btn thumbs-up" onClick={() => alert('Thumbs up!')}>
              👍
            </button>
            <button className="feedback-btn thumbs-down" onClick={() => alert('Thumbs down!')}>
              👎
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FeedbackTest;