import React from 'react';
import './Chat.css';

const ChatStatus = ({ status, stage, totalStages, stageName }) => {
  if (!status) return null;

  const getStatusIcon = (status) => {
    const icons = {
      'thinking': '🧠',
      'defining_intent': '🎯',
      'selecting_skills': '🔍',
      'executing_skill': '⚡',
      'formatting_answer': '✍️',
      'complete': '✅',
      'error': '❌',
      'idle': '💤'
    };
    return icons[status] || '🔄';
  };

  const getStatusColor = (status) => {
    const colors = {
      'thinking': '#ffd93d',
      'defining_intent': '#6bcbff',
      'selecting_skills': '#00ff88',
      'executing_skill': '#ff9a76',
      'formatting_answer': '#a66cff',
      'complete': '#00ff88',
      'error': '#ff6b6b',
      'idle': '#8899bb'
    };
    return colors[status] || '#8899bb';
  };

  const getStatusLabel = (status) => {
    const labels = {
      'thinking': 'Processing...',
      'defining_intent': 'Defining User Intent',
      'selecting_skills': 'Selecting Skill',
      'executing_skill': 'Executing Skill',
      'formatting_answer': 'Formatting Answer',
      'complete': 'Complete!',
      'error': 'Error',
      'idle': 'Ready'
    };
    return labels[status] || status;
  };

  const progress = totalStages > 0 ? (stage / totalStages) * 100 : 0;

  return (
    <div className="chat-status-container">
      <div className="chat-status-bar">
        <div className="chat-status-icon" style={{ color: getStatusColor(status) }}>
          {getStatusIcon(status)}
        </div>
        <div className="chat-status-info">
          <div className="chat-status-label">
            <span className="status-name">{getStatusLabel(status)}</span>
            {stage > 0 && (
              <span className="status-stage">
                {stage}/{totalStages}
              </span>
            )}
          </div>
          <div className="chat-status-progress">
            <div 
              className="chat-status-progress-fill" 
              style={{ 
                width: `${progress}%`,
                background: getStatusColor(status)
              }}
            />
          </div>
        </div>
      </div>
      {stageName && (
        <div className="chat-status-stage-name">
          {stageName}
        </div>
      )}
    </div>
  );
};

export default ChatStatus;