import React from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  return (
    <div className={`message ${message.isUser ? 'message-user' : 'message-bot'}`}>
      <div className="message-content">
        {message.text}
      </div>
      <div className="message-timestamp">
        {message.timestamp.toLocaleTimeString()}
      </div>
    </div>
  );
};

export default ChatMessage;
