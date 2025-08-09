import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import MessageInput from './MessageInput';
import { Message } from '../types';
import { queryAPI } from '../services/api';

interface ChatContainerProps {
  onDebugDataUpdate?: (vectorAnswer: string, graphAnswer: string, graphData?: any) => void;
}

const ChatContainer: React.FC<ChatContainerProps> = ({ onDebugDataUpdate }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (messageText: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      text: messageText,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await queryAPI(messageText);

      if (onDebugDataUpdate) {
        onDebugDataUpdate(response.vector_answer || '', response.graph_answer || '', undefined);
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.response,
        isUser: false,
        timestamp: new Date(),
        traceId: response.trace_id,
        spanId: response.span_id,
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      // For debugging: Create an error message with mock trace ID to test feedback buttons
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, there was an error processing your request. (This is a test message to demonstrate feedback buttons - try clicking the thumbs up/down below!)',
        isUser: false,
        timestamp: new Date(),
        traceId: `test-trace-${Date.now()}`,
        spanId: `test-span-${Date.now()}`,
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages-container">
        {messages.map(message => (
          <ChatMessage key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <MessageInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
};

export default ChatContainer;
