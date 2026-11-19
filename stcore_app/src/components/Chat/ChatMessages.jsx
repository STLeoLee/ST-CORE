// src/components/Chat/ChatMessages.jsx
import React, { useRef, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FaCheckCircle, FaTimesCircle } from 'react-icons/fa';
import ReactECharts from 'echarts-for-react';
import { useSession } from '../../context/SessionContext';
import './Chat.css';

const ChatMessages = ({ messages, isLoading, status }) => {
  const { sendActionUpdate } = useSession();
  const messagesEndRef = useRef(null);
  const [tableData, setTableData] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [actionLoading, setActionLoading] = useState(null);
  
  const pageSizeOptions = [10, 20, 50, 100];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  useEffect(() => {
    const lastMsg = messages.filter(m => m.type === 'assistant' && !m.isThinking).pop();
    if (lastMsg && lastMsg.tableData) {
      setTableData(lastMsg.tableData);
      setCurrentPage(1);
    } else {
      setTableData(null);
    }
  }, [messages]);

  const formatTimestamp = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusIcon = (statusKey) => ({ 'thinking': '🧠', 'defining_intent': '🎯', 'selecting_skills': '🔍', 'executing_skill': '⚡', 'formatting_answer': '✍️', 'complete': '✅', 'error': '❌', 'idle': '💤' }[statusKey] || '🔄');
  const getStatusColor = (statusKey) => ({ 'thinking': '#ffd93d', 'defining_intent': '#6bcbff', 'selecting_skills': '#00ff88', 'executing_skill': '#ff9a76', 'formatting_answer': '#a66cff', 'complete': '#00ff88', 'error': '#ff6b6b', 'idle': '#8899bb' }[statusKey] || '#8899bb');
  const getStatusDisplay = (statusKey) => ({
    'thinking': { icon: '🧠', label: 'Processing...', color: '#ffd93d' },
    'defining_intent': { icon: '🎯', label: 'Defining User Intent', color: '#6bcbff' },
    'selecting_skills': { icon: '🔍', label: 'Selecting Skill', color: '#00ff88' },
    'executing_skill': { icon: '⚡', label: 'Executing Skill', color: '#ff9a76' },
    'formatting_answer': { icon: '✍️', label: 'Formatting Answer', color: '#a66cff' },
    'complete': { icon: '✅', label: 'Complete!', color: '#00ff88' },
    'error': { icon: '❌', label: 'Error', color: '#ff6b6b' },
    'idle': { icon: '💤', label: 'Ready', color: '#8899bb' }
  }[statusKey] || { icon: '💤', label: 'Ready', color: '#8899bb' });

  const totalRows = tableData?.total_rows || 0;
  const totalPages = Math.ceil(totalRows / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalRows);
  const currentRows = tableData?.rows?.slice(startIndex, endIndex) || [];
  const handlePageChange = (page) => setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  const handlePageSizeChange = (size) => { setPageSize(size); setCurrentPage(1); };

  const renderTable = () => {
    if (!tableData || !tableData.rows || tableData.rows.length === 0) return null;
    const displayFields = tableData.display_fields || [];
    return (
      <div className="table-pagination-container">
        <div className="table-wrapper">
          <table className="markdown-table">
            <thead><tr><th>#</th>{displayFields.map((field, idx) => <th key={idx}>{field}</th>)}</tr></thead>
            <tbody>
              {currentRows.map((row, idx) => (
                <tr key={idx}><td>{startIndex + idx + 1}</td>{displayFields.map((field, fidx) => <td key={fidx}>{row[field] || '-'}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalRows > pageSize && (
          <div className="pagination-controls">
            <div className="pagination-info">Showing {startIndex + 1} - {endIndex} of {totalRows} rows</div>
            <div className="pagination-buttons">
              <button onClick={() => handlePageChange(1)} disabled={currentPage === 1}>⟪</button>
              <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1}>◀</button>
              <span className="pagination-current">{currentPage} / {totalPages}</span>
              <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages}>▶</button>
              <button onClick={() => handlePageChange(totalPages)} disabled={currentPage === totalPages}>⟫</button>
            </div>
          </div>
        )}
      </div>
    );
  };

  const parseMessageContent = (content) => {
    const instructionRegex = /---INSTRUCTION-BLOCK-START---([\s\S]*?)---INSTRUCTION-BLOCK-END---/;
    const match = content.match(instructionRegex);
    
    if (match) {
      let cleanContent = content.replace(instructionRegex, '').trim();
      let instructions = null;
      try { 
        instructions = JSON.parse(match[1].trim()); 
      } catch (e) { 
        console.error("Failed to parse instruction JSON", e); 
      }
      return { cleanContent, instructions };
    }
    return { cleanContent: content, instructions: null };
  };

  const handleActionClick = async (action, userDefinedId) => {
    setActionLoading(`${action}-${userDefinedId}`);
    try {
      await sendActionUpdate(action, userDefinedId);
      alert(`Card ${userDefinedId} updated successfully!`);
    } catch (error) {
      console.error("Action failed", error);
      alert(`Failed to execute action: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="chat-messages">
      {messages.map((msg) => {
        const { cleanContent, instructions } = msg.type === 'assistant' 
          ? parseMessageContent(msg.content) 
          : { cleanContent: msg.content, instructions: null };

        return (
          <div key={msg.id} className={`msg ${msg.type} ${msg.isThinking ? 'thinking' : ''} ${msg.isError ? 'error' : ''}`}>
            {msg.type === 'assistant' && !msg.isThinking && <span className="msg-icon">🤖</span>}
            
            {msg.isMarkdown ? (
              <>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Intercept the code block renderer
                    code({node, inline, className, children, ...props}) {
                      const match = /language-(\w+)/.exec(className || '');
                      const language = match ? match[1] : '';
                      
                      // 1. If it's an echarts block, render the chart inline
                      if (!inline && language === 'echarts') {
                        try {
                          const chartJson = String(children).replace(/\n$/, '');
                          // Clean up common AI json issues (like trailing commas)
                          const cleanedJson = chartJson.replace(/,\s*([\]}])/g, '$1');
                          const chartOptions = JSON.parse(cleanedJson);
                          
                          return (
                            <div className="chat-chart-container" style={{ 
                              margin: '15px 0', 
                              background: 'rgba(0,0,0,0.2)', 
                              padding: '10px', 
                              borderRadius: '8px', 
                              border: '1px solid rgba(255,255,255,0.05)' 
                            }}>
                              <ReactECharts 
                                option={{
                                  ...chartOptions,
                                  textStyle: { color: '#e0e4f0' },
                                  backgroundColor: 'transparent',
                                }} 
                                style={{ height: '300px', width: '100%' }}
                                theme="dark"
                              />
                            </div>
                          );
                        } catch (e) {
                          console.error("Failed to parse ECharts JSON", e);
                          return (
                            <div style={{ color: '#ff6b6b', fontSize: '0.8rem' }}>
                              ⚠️ Failed to render chart: Invalid JSON format.
                            </div>
                          );
                        }
                      }

                      // 2. Standard Syntax Highlighter for other code blocks
                      return !inline && match ? (
                        <SyntaxHighlighter style={vscDarkPlus} language={language} PreTag="div" {...props}>
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className="markdown-code" {...props}>{children}</code>
                      );
                    },
                    table({children}) { return msg.tableData ? null : <div className="table-wrapper"><table className="markdown-table">{children}</table></div>; },
                    th({children}) { return <th>{children}</th>; },
                    td({children}) { return <td>{children}</td>; },
                    blockquote({children}) { return <blockquote className="markdown-blockquote">{children}</blockquote>; },
                    h1({children}) { return <h1 className="markdown-h1">{children}</h1>; },
                    h2({children}) { return <h2 className="markdown-h2">{children}</h2>; },
                    h3({children}) { return <h3 className="markdown-h3">{children}</h3>; },
                    h4({children}) { return <h4 className="markdown-h4">{children}</h4>; },
                    p({children}) { return <p className="markdown-p">{children}</p>; },
                    ul({children}) { return <ul className="markdown-ul">{children}</ul>; },
                    ol({children}) { return <ol className="markdown-ol">{children}</ol>; },
                    li({children}) { return <li className="markdown-li">{children}</li>; },
                    strong({children}) { return <strong className="markdown-strong">{children}</strong>; },
                    em({children}) { return <em className="markdown-em">{children}</em>; },
                    hr() { return <hr className="markdown-hr" />; }
                  }}
                >
                  {cleanContent}
                </ReactMarkdown>
                
                {msg.tableData && renderTable()}

                {instructions && instructions.action === "render_buttons" && (
                  <div className="instruction-buttons" style={{ marginTop: '15px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    {instructions.buttons.map((btn, idx) => {
                      const isLoading = actionLoading === `${btn.action}-${btn.payload}`;
                      const isInvalid = btn.action === 'updateStageInvalid';
                      
                      return (
                        <button
                          key={idx}
                          onClick={() => handleActionClick(btn.action, btn.payload)}
                          disabled={isLoading}
                          className={`action-btn ${isInvalid ? 'invalid' : 'valid'}`}
                          style={{
                            padding: '8px 16px', borderRadius: '6px', border: 'none',
                            cursor: isLoading ? 'not-allowed' : 'pointer',
                            display: 'flex', alignItems: 'center', gap: '8px',
                            fontWeight: 600, fontSize: '0.85rem',
                            opacity: isLoading ? 0.7 : 1,
                            transition: 'all 0.2s ease',
                            background: isInvalid ? 'rgba(255, 107, 107, 0.15)' : 'rgba(0, 255, 136, 0.15)',
                            color: isInvalid ? '#ff6b6b' : '#00ff88',
                            border: isInvalid ? '1px solid rgba(255, 107, 107, 0.3)' : '1px solid rgba(0, 255, 136, 0.3)'
                          }}
                          onMouseEnter={(e) => !isLoading && (e.currentTarget.style.transform = 'translateY(-2px)')}
                          onMouseLeave={(e) => !isLoading && (e.currentTarget.style.transform = 'translateY(0)')}
                        >
                          {isLoading ? '⏳ Processing...' : (
                            <>
                              {isInvalid ? <FaTimesCircle /> : <FaCheckCircle />}
                              {btn.label}
                            </>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </>
            ) : (
              <span className="msg-text">{cleanContent}</span>
            )}
            
            <div className="msg-timestamp">{formatTimestamp(msg.timestamp)}</div>
          </div>
        );
      })}
      
      {status && status.status && status.status !== 'idle' && status.status !== 'complete' && (
        <div className="msg status-msg">
          <span className="msg-icon">{getStatusIcon(status.status)}</span>
          <div className="status-content">
            <span className="status-text" style={{ color: getStatusColor(status.status) }}>
              {status.message || getStatusDisplay(status.status)?.label || 'Processing...'}
            </span>
            {status.stage > 0 && status.totalStages > 0 && (
              <span className="status-progress-info">({status.stage}/{status.totalStages})</span>
            )}
            {status.stageName && <span className="status-stage-name">— {status.stageName}</span>}
            <div className="status-progress-bar">
              <div 
                className="status-progress-fill" 
                style={{ 
                  width: status.totalStages > 0 ? `${(status.stage / status.totalStages) * 100}%` : '0%',
                  background: getStatusColor(status.status)
                }}
              />
            </div>
          </div>
        </div>
      )}
      
      {isLoading && !status && (
        <div className="msg assistant typing">
          <span className="typing-dots"><span>.</span><span>.</span><span>.</span></span>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;