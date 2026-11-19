// src/context/SessionContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || `ws://localhost:8000`;

const SessionContext = createContext(null);

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) throw new Error('useSession must be used within a SessionProvider');
  return context;
};

export const SessionProvider = ({ children }) => {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('stcore_session_id') || null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [wsConnected, setWsConnected] = useState(false);
  const [wsDataConnected, setWsDataConnected] = useState(false);
  const [wsStatus, setWsStatus] = useState(null);

  const wsRef = useRef(null);
  const wsDataRef = useRef(null);
  const wsReconnectTimerRef = useRef(null);
  const wsDataReconnectTimerRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const isReconnectingRef = useRef(false);

  const pendingQueryRef = useRef(null);
  const messageCallbacksRef = useRef({});

  const [projectsList, setProjectsList] = useState([]);
  const [cardsData, setCardsData] = useState(null);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [cardsError, setCardsError] = useState(null);
  const [difyConversationId, setDifyConversationId] = useState('');
  
  // Novade Data State
  const [novadeData, setNovadeData] = useState(null);
  const [novadeLoading, setNovadeLoading] = useState(false);

  // ============================================================
  // 1. CHAT WEBSOCKET
  // ============================================================
  const disconnectWebSocket = useCallback(() => {
    if (wsReconnectTimerRef.current) clearTimeout(wsReconnectTimerRef.current);
    if (wsRef.current) {
      try { wsRef.current.close(1000, 'Normal closure'); } catch (err) {}
      wsRef.current = null;
    }
    setWsConnected(false);
    setWsStatus({ status: 'disconnected', message: 'Disconnected' });
  }, []);

  const connectWebSocket = useCallback((sid) => {
    const sessionToUse = sid || sessionId;
    if (!sessionToUse || isReconnectingRef.current) return;
    if (wsRef.current) disconnectWebSocket();

    try {
      const ws = new WebSocket(`${WS_BASE_URL}/ws/chat/${sessionToUse}`);
      wsRef.current = ws;

      ws.onopen = () => {
        isReconnectingRef.current = false;
        setWsConnected(true);
        setWsStatus(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong' || data.type === 'ping') return;
          if (messageCallbacksRef.current[data.type]) {
             messageCallbacksRef.current[data.type](data);
             delete messageCallbacksRef.current[data.type];
             return;
          }
          if (data.type === 'status') {
            setWsStatus({
              status: data.data?.status || 'idle',
              stage: data.data?.stage || 0,
              total_stages: data.data?.total_stages || 3,
              stage_name: data.data?.stage_name || '',
              message: data.data?.message || '',
            });
          } else if (data.type === 'result') {
            if (pendingQueryRef.current) {
              pendingQueryRef.current.resolve({
                answer: data.data?.response || data.data?.answer || 'Done!',
                response: data.data?.response || data.data?.answer,
                data: data.data?.data || null,
                conversation_id: data.data?.conversation_id || null
              });
              pendingQueryRef.current = null;
            }
          } else if (data.type === 'error') {
            if (pendingQueryRef.current) {
              pendingQueryRef.current.reject(new Error(data.data?.error || 'Unknown error'));
              pendingQueryRef.current = null;
            }
          }
        } catch (err) {}
      };

      ws.onerror = () => setWsConnected(false);
      ws.onclose = (event) => {
        setWsConnected(false);
        if (pendingQueryRef.current) {
          pendingQueryRef.current.reject(new Error('WebSocket disconnected'));
          pendingQueryRef.current = null;
        }
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          if (wsReconnectTimerRef.current) clearTimeout(wsReconnectTimerRef.current);
          const delay = 2000 * Math.pow(2, reconnectAttempts.current - 1);
          wsReconnectTimerRef.current = setTimeout(() => {
            isReconnectingRef.current = false;
            connectWebSocket(sessionToUse);
          }, delay);
        }
      };
    } catch (err) {
      setWsConnected(false);
    }
  }, [sessionId, disconnectWebSocket]);

  // ============================================================
  // 2. DATA WEBSOCKET
  // ============================================================
  const disconnectDataWebSocket = useCallback(() => {
    if (wsDataReconnectTimerRef.current) clearTimeout(wsDataReconnectTimerRef.current);
    if (wsDataRef.current) {
      try { wsDataRef.current.close(1000, 'Normal closure'); } catch (err) {}
      wsDataRef.current = null;
    }
    setWsDataConnected(false);
  }, []);

  const connectDataWebSocket = useCallback((sid) => {
    const sessionToUse = sid || sessionId;
    if (!sessionToUse) return;
    if (wsDataRef.current) disconnectDataWebSocket();

    try {
      const ws = new WebSocket(`${WS_BASE_URL}/ws/data/${sessionToUse}`);
      wsDataRef.current = ws;

      ws.onopen = () => setWsDataConnected(true);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong' || data.type === 'ping') return;
          
          if (messageCallbacksRef.current[data.type]) {
             messageCallbacksRef.current[data.type](data);
             delete messageCallbacksRef.current[data.type];
          }
        } catch (err) {}
      };

      ws.onerror = () => setWsDataConnected(false);
      ws.onclose = () => {
        setWsDataConnected(false);
        if (wsDataReconnectTimerRef.current) clearTimeout(wsDataReconnectTimerRef.current);
        wsDataReconnectTimerRef.current = setTimeout(() => connectDataWebSocket(sessionToUse), 3000);
      };
    } catch (err) {
      setWsDataConnected(false);
    }
  }, [sessionId, disconnectDataWebSocket]);

  // ============================================================
  // 3. Session Management
  // ============================================================
  const createSession = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await axios.post(`${API_BASE_URL}/session/create`);
      if (response.data.success) {
        const newSessionId = response.data.session_id;
        setSessionId(newSessionId);
        localStorage.setItem('stcore_session_id', newSessionId);
        setSessionInfo(response.data.session_info);
        setIsInitialized(true);
        return newSessionId;
      }
    } catch (err) {
      setError(err.message || 'Failed to create session');
      throw err;
    } finally { setIsLoading(false); }
  }, []);

  const initializeSession = useCallback(async () => {
    if (isInitialized && sessionId) return sessionId;
    let sid = sessionId || localStorage.getItem('stcore_session_id');
    if (sid) {
      try {
        const res = await axios.get(`${API_BASE_URL}/session/${sid}`);
        if (res.data.success) { setSessionInfo(res.data.session_info); setIsInitialized(true); return sid; }
      } catch (e) { localStorage.removeItem('stcore_session_id'); setSessionId(null); }
    }
    return await createSession();
  }, [sessionId, isInitialized, createSession]);

  // ============================================================
  // 4. Data Fetchers
  // ============================================================
  const requestProjects = useCallback(() => {
    if (wsDataRef.current && wsDataRef.current.readyState === WebSocket.OPEN) {
      messageCallbacksRef.current['projects_list'] = (data) => {
        const projects = (data.data || []).map(p => ({ id: p.Id, name: p.Name }));
        setProjectsList(projects);
      };
      wsDataRef.current.send(JSON.stringify({ type: 'get_projects' }));
    }
  }, []);

  const sendCardsRequest = useCallback((projectId, boardId = 0) => {
    if (!wsDataRef.current || wsDataRef.current.readyState !== WebSocket.OPEN) {
      setCardsError('Data WebSocket disconnected. Cannot fetch data.');
      return;
    }

    setCardsLoading(true);
    setCardsError(null);
    
    messageCallbacksRef.current['cards_update'] = (data) => {
      setCardsData(data.data);
      setCardsLoading(false);
    };

    wsDataRef.current.send(JSON.stringify({
      type: 'get_cards_data',
      project_id: projectId === 'all' ? 0 : projectId,
      board_id: boardId
    }));
  }, []);

  // --- NEW: Request Novade Data via WS ---
  const requestNovadeData = useCallback((projectId = 'IZ2L4', since = 1520234658834) => {
    if (!wsDataRef.current || wsDataRef.current.readyState !== WebSocket.OPEN) {
      console.warn("Data WebSocket disconnected. Cannot fetch Novade data.");
      return;
    }

    setNovadeLoading(true);
    
    messageCallbacksRef.current['novade_data'] = (data) => {
      if (data.data.success) {
        setNovadeData(data.data);
      } else {
        console.error("Novade data fetch failed:", data.data.error);
      }
      setNovadeLoading(false);
    };

    wsDataRef.current.send(JSON.stringify({
      type: 'get_novade_data',
      project_id: projectId,
      since: since
    }));
  }, []);

  // ============================================================
  // 5. Queries
  // ============================================================
  const sendWsQueryInternal = useCallback((payload, resolve, reject) => {
    if (pendingQueryRef.current) {
      pendingQueryRef.current.reject(new Error('Superseded by new query'));
    }
    pendingQueryRef.current = { resolve, reject };
    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (err) {
      pendingQueryRef.current = null;
      reject(err);
    }
  }, []);

  const sendSmartDocsQuery = useCallback((question) => {
    return new Promise((resolve, reject) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        sendWsQueryInternal({ type: 'smart_docs_query', question, conversation_id: difyConversationId }, resolve, reject);
      } else {
        reject(new Error('Chat WebSocket disconnected'));
      }
    });
  }, [sendWsQueryInternal, difyConversationId]);

  // Cleanups
  useEffect(() => {
    return () => { disconnectWebSocket(); disconnectDataWebSocket(); };
  }, [disconnectWebSocket, disconnectDataWebSocket]);

  const value = useMemo(() => ({
    sessionId, sessionInfo, isInitialized, isLoading, error,
    createSession, initializeSession,
    wsConnected, wsStatus, connectWebSocket, disconnectWebSocket, sendSmartDocsQuery,
    wsDataConnected, connectDataWebSocket, disconnectDataWebSocket,
    projectsList, requestProjects,
    cardsData, sendCardsRequest, cardsLoading, cardsError,
    novadeData, novadeLoading, requestNovadeData
  }), [
    sessionId, sessionInfo, isInitialized, isLoading, error,
    createSession, initializeSession,
    wsConnected, wsStatus, connectWebSocket, disconnectWebSocket, sendSmartDocsQuery,
    wsDataConnected, connectDataWebSocket, disconnectDataWebSocket,
    projectsList, requestProjects,
    cardsData, sendCardsRequest, cardsLoading, cardsError,
    novadeData, novadeLoading, requestNovadeData
  ]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
};