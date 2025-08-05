import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import MessageInput from './MessageInput';
import { Message } from '../types';
import { queryAPI } from '../services/api';

interface ChatContainerProps {
  onDebugDataUpdate?: (ontologyContext: any, graphContext: any, graphData?: any) => void;
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
        onDebugDataUpdate(response.ontology_context, response.graph_context_str, response.graph_data);
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.response,
        isUser: false,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, there was an error processing your request.',
        isUser: false,
        timestamp: new Date(),
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
