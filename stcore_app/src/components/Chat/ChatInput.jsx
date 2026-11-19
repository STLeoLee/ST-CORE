import React, { useState } from 'react';
import { FaPaperPlane } from 'react-icons/fa';
import './Chat.css';

const ChatInput = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');

  const handleSend = () => {
    const text = input.trim();
    if (text && !disabled) {
      onSend(text);
      setInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-area">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Ask about fail items, totals, dates..."
        disabled={disabled}
      />
      <button onClick={handleSend} disabled={disabled || !input.trim()}>
        <FaPaperPlane /> SEND
      </button>
    </div>
  );
};

export default ChatInput;