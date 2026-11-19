// src/components/Chat/ChatOverlay.jsx
import React, { useState, useRef, useEffect } from 'react';
import { FaTimes, FaRobot, FaFileAlt } from 'react-icons/fa';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import { useSession } from '../../context/SessionContext';
import './Chat.css';

const STATUS_STAGES = {
  'thinking': { icon: '⏳', label: 'Processing...', color: '#ffd93d' },
  'complete': { icon: '✅', label: 'Complete!', color: '#00ff88' },
  'error': { icon: '❌', label: 'Error', color: '#ff6b6b' },
  'idle': { icon: '💤', label: 'Ready', color: '#8899bb' }
};

const LoadingDots = () => (
  <span className="loading-dots"><span>.</span><span>.</span><span>.</span></span>
);

const ChatOverlay = ({ isOpen, onClose, activeSection }) => {
  const { 
    sessionId, sessionInfo, isInitialized, isLoading: sessionLoading,
    sendQuery, getHistory, clearHistory, deleteSession,
    wsConnected, wsStatus, sendWsQuery, sendSmartDocsQuery, connectWebSocket, disconnectWebSocket,
    initializeSession, refreshSessionInfo
  } = useSession();
  
  const [chatMode, setChatMode] = useState(activeSection === 'document' ? 'smartdocs' : 'powerbi');
  const [messages, setMessages] = useState([{
    id: 1, type: 'assistant',
    content: chatMode === 'smartdocs' 
      ? `### Smart Docs AI Assistant\n- Ask me anything about your project documents.`
      : `### Welcome to ST-CORE, I am Smart BIM Assistant\n- I can help you with your BIM data queries.`,
    timestamp: new Date(), isMarkdown: true
  }]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [showSessionMenu, setShowSessionMenu] = useState(false);
  const [currentStatus, setCurrentStatus] = useState(null);
  const [currentStage, setCurrentStage] = useState(0);
  const [totalStages, setTotalStages] = useState(3);
  const [stageName, setStageName] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusQueue, setStatusQueue] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [displayedStages, setDisplayedStages] = useState(new Set());
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);
  const statusTimeoutRef = useRef(null);
  const processingTimeoutRef = useRef(null);

  // Sync chat mode and welcome message when the page changes (via key remount)
  useEffect(() => {
    setMessages([{
      id: 1, type: 'assistant',
      content: chatMode === 'smartdocs' 
        ? `### Smart Docs AI Assistant\n- Ask me anything about your project documents.`
        : `### Welcome to ST-CORE, I am Smart BIM Assistant\n- I can help you with your BIM data queries.`,
      timestamp: new Date(), isMarkdown: true
    }]);
  }, [chatMode]);

  // Initialize session
  useEffect(() => {
    if (isOpen && !isInitialized) initializeSession();
  }, [isOpen, isInitialized, initializeSession]);

  // Connect Chat WebSocket
  useEffect(() => {
    if (isOpen && sessionId) connectWebSocket(sessionId);
    return () => { if (isOpen) disconnectWebSocket(); };
  }, [isOpen, sessionId, connectWebSocket, disconnectWebSocket]);

  // Handle WebSocket status updates (from Dify)
  useEffect(() => {
    if (!wsStatus) return;
    const statusType = wsStatus.status || 'idle';
    
    if (statusType === 'thinking') {
      setCurrentStatus('thinking');
      setStatusMessage(wsStatus.message || 'Processing...');
      setStageName(wsStatus.stage_name || '');
    } else if (statusType === 'idle') {
      setCurrentStatus(null);
      setStatusMessage('');
    }
  }, [wsStatus]);

  // Scroll to bottom
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, currentStatus]);

  // Click outside session menu
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowSessionMenu(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleModeSwitch = (mode) => {
    setChatMode(mode);
    setMessages([{
      id: Date.now(), type: 'assistant',
      content: mode === 'smartdocs' 
        ? `### Smart Docs AI Assistant\n- Ask me anything about your project documents.`
        : `### Welcome to ST-CORE, I am Smart BIM Assistant\n- I can help you with your BIM data queries.`,
      timestamp: new Date(), isMarkdown: true
    }]);
  };

  const handleClearHistory = async () => {
    if (window.confirm('Are you sure you want to clear all conversation history?')) {
      await clearHistory();
      setMessages([{
        id: 1, type: 'assistant',
        content: chatMode === 'smartdocs' 
          ? `### Smart Docs AI Assistant\n- Ask me anything about your project documents.`
          : `### Welcome to ST-CORE, I am Smart BIM Assistant\n- I can help you with your BIM data queries.`,
        timestamp: new Date(), isMarkdown: true
      }]);
      await refreshSessionInfo();
      setShowSessionMenu(false);
    }
  };

  const handleResetSession = async () => {
    if (window.confirm('This will create a new session and clear all conversation history. Continue?')) {
      await deleteSession();
      setMessages([{
        id: 1, type: 'assistant',
        content: `### Welcome to ST-CORE, I am Smart BIM Assistant\n- I can help you with your BIM data queries.`,
        timestamp: new Date(), isMarkdown: true
      }]);
      await refreshSessionInfo();
      setShowSessionMenu(false);
    }
  };

  const handleSendMessage = async (text) => {
    setCurrentStatus('thinking');
    setStatusMessage('🧠 Thinking...');
    
    const userMessage = { id: Date.now(), type: 'user', content: text, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let response;
      if (chatMode === 'smartdocs') {
        response = await sendSmartDocsQuery(text);
      } else {
        response = await sendWsQuery(text);
      }
      
      setMessages(prev => [...prev, {
        id: Date.now() + 2, type: 'assistant',
        content: response.answer || response.response || 'No response.',
        timestamp: new Date(), isMarkdown: true
      }]);

      setTimeout(() => {
        setCurrentStatus(null);
        setStatusMessage('');
        setStageName('');
      }, 2000);

    } catch (error) {
      setCurrentStatus('error');
      setStatusMessage(`❌ ${error.message}`);
      setTimeout(() => setCurrentStatus(null), 3000);
    }
    setIsLoading(false);
  };

  if (!isOpen) return null;

  return (
    <div className={`chat-overlay ${isOpen ? 'open' : ''}`}>
      {/* Header */}
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <img src="/STCORE_ICON.svg" alt="ST-CORE" className="chat-header-icon" style={{ width: '20px', height: '20px' }} />
          
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '2px' }}>
            <button 
              onClick={() => handleModeSwitch('powerbi')}
              style={{
                background: chatMode === 'powerbi' ? 'rgba(0,255,136,0.2)' : 'transparent',
                color: chatMode === 'powerbi' ? '#00ff88' : '#8899bb',
                border: 'none', padding: '4px 12px', borderRadius: '6px',
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem'
              }}
            >
              <FaRobot /> Power BI
            </button>
            <button 
              onClick={() => handleModeSwitch('smartdocs')}
              style={{
                background: chatMode === 'smartdocs' ? 'rgba(107,203,255,0.2)' : 'transparent',
                color: chatMode === 'smartdocs' ? '#6bcbff' : '#8899bb',
                border: 'none', padding: '4px 12px', borderRadius: '6px',
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem'
              }}
            >
              <FaFileAlt /> Smart Docs
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '12px', fontSize: '0.7rem', opacity: 0.7 }}>
            <span style={{ 
              display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%',
              background: wsConnected ? '#00ff88' : '#ff6b6b', animation: sessionLoading ? 'pulse 1s infinite' : 'none'
            }} />
            <span style={{ color: wsConnected ? '#00ff88' : '#ff6b6b', fontWeight: wsConnected ? '600' : '400' }}>
              {wsConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button 
            className="chat-session-btn"
            onClick={() => setShowSessionMenu(!showSessionMenu)}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              background: 'rgba(0,255,136,0.05)', border: '1px solid rgba(0,255,136,0.2)',
              color: '#8899bb', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem'
            }}
          >
            ⚙️ Session
          </button>
          <button className="chat-close" onClick={onClose}>
            <FaTimes />
          </button>
        </div>
      </div>

      {/* Status Bar */}
      {currentStatus && currentStatus !== 'idle' && (
        <div className="chat-status-bar-container">
          <div className="chat-status-bar">
            <div className="chat-status-icon" style={{ color: STATUS_STAGES[currentStatus]?.color }}>
              {currentStatus === 'thinking' ? <LoadingDots /> : STATUS_STAGES[currentStatus]?.icon}
            </div>
            <div className="chat-status-info">
              <div className="chat-status-label">
                <span className="status-name" style={{ color: STATUS_STAGES[currentStatus]?.color }}>
                  {currentStatus === 'thinking' ? (
                    <>{statusMessage}<LoadingDots /></>
                  ) : (
                    STATUS_STAGES[currentStatus]?.label
                  )}
                </span>
              </div>
              <div className="chat-status-progress">
                <div 
                  className="chat-status-progress-fill" 
                  style={{ width: '100%', background: STATUS_STAGES[currentStatus]?.color }}
                />
              </div>
            </div>
          </div>
          {stageName && <div className="chat-status-stage-name">{stageName}</div>}
        </div>
      )}

      {/* Session Menu */}
      {showSessionMenu && (
        <div 
          ref={menuRef}
          style={{
            position: 'absolute', top: '58px', right: '16px',
            background: 'rgba(10, 10, 30, 0.98)', backdropFilter: 'blur(14px)',
            border: '1px solid rgba(0,255,136,0.15)', borderRadius: '12px',
            padding: '14px 18px', minWidth: '220px', zIndex: 100, boxShadow: '0 8px 30px rgba(0,0,0,0.5)'
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
            <button
              onClick={handleClearHistory}
              style={{
                background: 'rgba(255,107,107,0.05)', border: '1px solid rgba(255,107,107,0.1)',
                color: '#ff6b6b', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer',
                fontSize: '0.75rem', textAlign: 'left'
              }}
            >
              🗑️ Clear History
            </button>
            <button
              onClick={handleResetSession}
              style={{
                background: 'rgba(0,255,136,0.03)', border: '1px solid rgba(0,255,136,0.08)',
                color: '#00ff88', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer',
                fontSize: '0.75rem', textAlign: 'left'
              }}
            >
              🔄 New Session
            </button>
          </div>
        </div>
      )}
      
      <ChatMessages 
        messages={messages} 
        isLoading={isLoading} 
        status={currentStatus ? {
          status: currentStatus,
          stage: currentStage,
          totalStages: totalStages,
          stageName: stageName,
          message: statusMessage
        } : null}
      />
      
      <ChatInput onSend={handleSendMessage} disabled={isLoading || !isInitialized} />
    </div>
  );
};

export default ChatOverlay;