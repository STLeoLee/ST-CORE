// src/App.jsx
import React, { useState, useRef, useEffect } from 'react';
import './App.css';
import Sidebar from './components/Layout/Sidebar';
import TopBar from './components/Layout/TopBar';
import ContentPanel from './components/Layout/ContentPanel';
import { SessionProvider, useSession } from './context/SessionContext';
import ChatOverlay from './components/Chat/ChatOverlay';
import { ChatProvider } from './context/ChatContext';

const AppContent = () => {
  const [activeSection, setActiveSection] = useState('bim');
  const [status, setStatus] = useState({ text: 'Ready', type: 'idle' });
  const [isChatOpen, setIsChatOpen] = useState(false);
  const contentPanelRef = useRef(null);
  const smartDocsRef = useRef(null);
  
  // Guard to prevent multiple connection attempts
  const hasInitializedRef = useRef(false);

  const { 
    sessionId, isInitialized, initializeSession, 
    connectWebSocket, connectDataWebSocket, wsConnected, wsDataConnected
  } = useSession();

  useEffect(() => {
    const init = async () => {
      if (!isInitialized) {
        try { await initializeSession(); } catch (err) { return; }
      }
      
      if (sessionId && !hasInitializedRef.current) {
        hasInitializedRef.current = true; 
        if (!wsConnected) connectWebSocket(sessionId);
        if (!wsDataConnected) connectDataWebSocket(sessionId);
      }
    };
    init();
  }, [isInitialized, sessionId, wsConnected, wsDataConnected, initializeSession, connectWebSocket, connectDataWebSocket]);

  const handleSectionChange = (section) => {
    setActiveSection(section);
    setStatus({ text: 'Ready', type: 'idle' });
  };

  const handleRefresh = () => {
    if (activeSection === 'bim') {
      if (contentPanelRef.current) {
        const embedElement = contentPanelRef.current.querySelector('.powerbi-embed-container');
        if (embedElement) {
          setStatus({ text: 'Refreshing...', type: 'loading' });
          setTimeout(() => { setStatus({ text: 'Connected', type: 'connected' }); }, 2000);
        }
      }
    } else if (activeSection === 'docs-workflow') {
      if (smartDocsRef.current) smartDocsRef.current.refresh();
    }
  };

  return (
    <div className="app">
      <Sidebar activeSection={activeSection} onSectionChange={handleSectionChange} />
      <div className="main-content">
        <TopBar activeSection={activeSection} status={status} onRefresh={handleRefresh} />
        <div ref={contentPanelRef} style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          <ContentPanel 
            activeSection={activeSection} 
            onStatusChange={setStatus}
            smartDocsRef={smartDocsRef}
          />
        </div>
      </div>
      
      {!isChatOpen && (
        <button 
          className="chat-toggle-btn"
          onClick={() => setIsChatOpen(true)}
          style={{
            position: 'fixed', bottom: '24px', right: '24px',
            background: 'rgba(0, 255, 136, 0.1)', border: '1px solid rgba(0, 255, 136, 0.2)',
            borderRadius: '50%', width: '56px', height: '56px', color: '#00ff88',
            fontSize: '24px', cursor: 'pointer', zIndex: 100,
            transition: 'all 0.3s ease', display: 'flex',
            alignItems: 'center', justifyContent: 'center'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(0, 255, 136, 0.2)';
            e.currentTarget.style.transform = 'scale(1.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(0, 255, 136, 0.1)';
            e.currentTarget.style.transform = 'scale(1)';
          }}
        >
          <img src="/STCORE_ICON.svg" alt="ST-CORE" className="chat-header-icon" style={{ width: '40px', height: '40px' }} />
        </button>
      )}
      
      {/* The key prop forces a full reset of the ChatOverlay when changing pages */}
      <ChatOverlay 
        key={activeSection}
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
        activeSection={activeSection}
      />
    </div>
  );
};

function App() {
  return (
    <SessionProvider>
      <ChatProvider>
        <AppContent />
      </ChatProvider>
    </SessionProvider>
  );
}

export default App;