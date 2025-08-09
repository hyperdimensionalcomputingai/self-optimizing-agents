import React from 'react';
import { Message } from '../types';
import FeedbackButtons from './FeedbackButtons';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const handleFeedbackSubmitted = (feedback: 'thumbs_up' | 'thumbs_down', reason?: string) => {
    // Log feedback submission for monitoring
    console.log(`Feedback submitted: ${feedback}`, { messageId: message.id, reason });
  };

  return (
    <div className={`message ${message.isUser ? 'message-user' : 'message-bot'}`}>
      <div className="message-content">
        {message.text}
      </div>
      <div className="message-timestamp">
        {message.timestamp.toLocaleTimeString()}
      </div>
      {!message.isUser && (
        <FeedbackButtons
          traceId={message.traceId}
          spanId={message.spanId}
          onFeedbackSubmitted={handleFeedbackSubmitted}
        />
      )}
    </div>
  );
};

export default ChatMessage;
