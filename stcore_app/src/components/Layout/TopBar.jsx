import React from 'react';
import { FaCube, FaFileSignature, FaFolderOpen, FaMicrochip, FaSyncAlt, FaExpand, FaCircle } from 'react-icons/fa';
import './TopBar.css';

const TopBar = ({ activeSection, status, onRefresh }) => {
  const sectionIcons = {
    bim: FaCube,
    form: FaFileSignature,
    document: FaFolderOpen,
    iot: FaMicrochip
  };

  const sectionTitles = {
    bim: 'Smart BIM',
    form: 'Smart Form',
    document: 'Smart Docs',
    iot: 'Smart IoT'
  };

  const Icon = sectionIcons[activeSection] || FaCube;
  const title = sectionTitles[activeSection] || 'Smart BIM';

  return (
    <div className="main-topbar">
      <div className="page-title">
        <Icon />
        <span>{title}</span>
      </div>
      
      <div className="topbar-actions">
        <div className="status-badge">
          <FaCircle className={`dot ${status.type}`} />
          <span className="status-text">{status.text}</span>
        </div>
        <FaSyncAlt 
          className="action-icon" 
          onClick={onRefresh} 
          title="Refresh" 
        />
        <FaExpand 
          className="action-icon" 
          onClick={() => {
            const panel = document.getElementById('contentPanel');
            if (panel) {
              if (!document.fullscreenElement) {
                panel.requestFullscreen?.();
              } else {
                document.exitFullscreen?.();
              }
            }
          }} 
          title="Fullscreen" 
        />
      </div>
    </div>
  );
};

export default TopBar;