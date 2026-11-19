// src/components/Layout/Sidebar.jsx
import React, { useState, useEffect } from 'react';
import { FaCubes, FaCube, FaFileSignature, FaFolderOpen, FaMicrochip, FaChevronDown, FaChevronRight, FaListAlt, FaTasks } from 'react-icons/fa';
import './Sidebar.css';

const Sidebar = ({ activeSection, onSectionChange }) => {
  // State to track which sub-menu is open
  const [openSubMenu, setOpenSubMenu] = useState(null);

  // Automatically open the sub-menu if a child is active
  useEffect(() => {
    if (activeSection === 'docs-overview' || activeSection === 'docs-workflow') {
      setOpenSubMenu('document');
    }
  }, [activeSection]);

  const sections = [
    { id: 'bim', label: 'Smart BIM', icon: FaCube },
    { id: 'form', label: 'Smart Form', icon: FaFileSignature },
    { id: 'docs-workflow', label: 'Smart Docs', icon: FaTasks },
    // { 
    //   id: 'document', 
    //   label: 'Smart Docs', 
    //   icon: FaFolderOpen,
    //   subItems: [
    //     { id: 'docs-overview', label: 'Overview', icon: FaListAlt },
    //     { id: 'docs-workflow', label: 'Workflow', icon: FaTasks }
    //   ]
    // },
    // { id: 'iot', label: 'Smart IoT', icon: FaMicrochip },
  ];

  const handleItemClick = (section) => {
    if (section.subItems) {
      // Toggle sub-menu
      setOpenSubMenu(prev => prev === section.id ? null : section.id);
      // If no sub-item is currently active, default to the first one
      if (activeSection !== 'docs-overview' && activeSection !== 'docs-workflow') {
        onSectionChange(section.subItems[0].id);
      }
    } else {
      setOpenSubMenu(null);
      onSectionChange(section.id);
    }
  };

  return (
    <nav className="nav-sidebar">
      <div className="nav-brand">
        <div className="logo">
          <FaCubes className="logo-icon" />
          <h1>ST-CORE<span>SMART BIM</span></h1>
        </div>
      </div>
      
      {sections.map((section) => {
        const isActive = activeSection === section.id || 
        (section.subItems && section.subItems.some(sub => sub.id === activeSection));
        const isExpanded = openSubMenu === section.id;

        return (
          <div key={section.id} className="nav-group">
            <button
              type="button"
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => handleItemClick(section)}
            >
              <section.icon />
              <span>{section.label}</span>
              {section.subItems && (
                <span className="nav-chevron">
                  {isExpanded ? <FaChevronDown /> : <FaChevronRight />}
                </span>
              )}
            </button>

            {/* Sub-menu Items */}
            {section.subItems && isExpanded && (
              <div className="nav-sub-menu">
                {section.subItems.map(sub => (
                  <button
                    key={sub.id}
                    type="button"
                    className={`nav-sub-item ${activeSection === sub.id ? 'active' : ''}`}
                    onClick={() => onSectionChange(sub.id)}
                  >
                    <sub.icon />
                    <span>{sub.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
};

export default Sidebar;