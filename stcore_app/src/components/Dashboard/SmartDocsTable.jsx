// src/components/Dashboard/SmartDocsTable.jsx
import React, { useState, useEffect, useMemo } from 'react';
import {
  FaSearch, FaChevronLeft, FaChevronRight,
  FaSort, FaSortUp, FaSortDown, FaExclamationTriangle, FaHourglassHalf, FaEye
} from 'react-icons/fa';
import './SmartDocsTable.css';

const SmartDocsTable = ({ documents }) => {
  const [searchTerm, setSearchTerm]   = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [sortConfig, setSortConfig]   = useState({ key: null, direction: 'asc' });

  useEffect(() => { setCurrentPage(1); }, [documents, searchTerm, sortConfig]);

  const filteredData = useMemo(() => {
    if (!searchTerm) return documents;
    const q = searchTerm.toLowerCase();
    return documents.filter(c =>
      (c.name || '').toLowerCase().includes(q) ||
      (String(c.userDefinedId ?? '')).toLowerCase().includes(q) ||
      (c.stageName || '').toLowerCase().includes(q)
    );
  }, [documents, searchTerm]);

  const sortedData = useMemo(() => {
    const items = [...filteredData];
    if (!sortConfig.key) return items;
    items.sort((a, b) => {
      let av = a[sortConfig.key];
      let bv = b[sortConfig.key];
      if (av == null) return 1;
      if (bv == null) return -1;
      if (sortConfig.key.endsWith('Date')) {
        av = new Date(av).getTime();
        bv = new Date(bv).getTime();
      } else if (typeof av === 'string') {
        av = av.toLowerCase(); bv = bv.toLowerCase();
      }
      if (av < bv) return sortConfig.direction === 'asc' ? -1 : 1;
      if (av > bv) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return items;
  }, [filteredData, sortConfig]);

  const totalPages  = Math.ceil(sortedData.length / rowsPerPage);
  const startIndex  = (currentPage - 1) * rowsPerPage;
  const endIndex    = startIndex + rowsPerPage;
  const currentData = sortedData.slice(startIndex, endIndex);

  const requestSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const sortIcon = (key) => {
    if (sortConfig.key !== key) return <FaSort className="sort-icon" />;
    return sortConfig.direction === 'asc'
      ? <FaSortUp className="sort-icon active" />
      : <FaSortDown className="sort-icon active" />;
  };

  const formatDate = (v) =>
    v ? new Date(v).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '-';

  // Helper to open the document preview in a new tab (bypasses iframe restrictions)
  const handlePreview = (docId) => {
    const url = `https://spatial-technology.isetia.eu/DocumentPreview/ShowPreview?documentId=${docId}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="table-card">
      <div className="table-header">
        <h3>Cards ({sortedData.length})</h3>
        <div className="table-search">
          <FaSearch className="search-icon" />
          <input
            type="text"
            placeholder="Search by name, ID, or stage..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="table-wrapper">
        <table className="docs-table">
          <thead>
            <tr>
              <th onClick={() => requestSort('userDefinedId')} className="sortable-header">
                <div>ID {sortIcon('userDefinedId')}</div>
              </th>
              <th onClick={() => requestSort('name')} className="sortable-header">
                <div>Name {sortIcon('name')}</div>
              </th>
              <th onClick={() => requestSort('stageName')} className="sortable-header">
                <div>Stage {sortIcon('stageName')}</div>
              </th>
              <th>Status</th>
              <th onClick={() => requestSort('plannedStartDate')} className="sortable-header">
                <div>Start Date {sortIcon('plannedStartDate')}</div>
              </th>
              <th onClick={() => requestSort('plannedFinishDate')} className="sortable-header">
                <div>Due Date {sortIcon('plannedFinishDate')}</div>
              </th>
              <th onClick={() => requestSort('completedPercent')} className="sortable-header">
                <div>% Complete {sortIcon('completedPercent')}</div>
              </th>
              <th>Preview</th>
            </tr>
          </thead>
          <tbody>
            {currentData.length > 0 ? (
              currentData.map((card) => (
                <tr key={card.id}>
                  <td className="text-mono">{card.userDefinedId ?? card.id}</td>
                  <td className="text-name">{card.name ?? '-'}</td>
                  <td>
                    <span
                      className="badge-stage"
                      style={{
                        background: `${card.stageColor || '#8899bb'}22`,
                        color: card.stageColor || '#8899bb',
                        border: `1px solid ${card.stageColor || '#8899bb'}55`,
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {card.stageName || 'Unknown'}
                    </span>
                  </td>
                  <td>
                    {card.isOverdue ? (
                      <span className="indicator-badge overdue" title="Overdue">
                        <FaExclamationTriangle /> Overdue
                      </span>
                    ) : card.isPending ? (
                      <span className="indicator-badge pending" title="Pending">
                        <FaHourglassHalf /> Pending
                      </span>
                    ) : (
                      <span className="indicator-badge complete" title="Complete">
                        ✅ Complete
                      </span>
                    )}
                  </td>
                  <td>{formatDate(card.plannedStartDate)}</td>
                  <td>{formatDate(card.plannedFinishDate)}</td>
                  <td>{card.completedPercent != null ? `${card.completedPercent}%` : '-'}</td>
                  <td>
                    {card.documentId ? (
                      <button 
                        onClick={() => handlePreview(card.documentId)}
                        className="preview-btn"
                        title="Open Document in New Tab"
                      >
                        <FaEye />
                      </button>
                    ) : (
                      <button 
                        className="preview-btn disabled"
                        title="No document attached"
                        disabled
                        style={{ opacity: 0.3, cursor: 'not-allowed' }}
                      >
                        <FaEye />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan="8" className="text-center">No cards found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="table-pagination">
        <div className="pagination-info">
          Showing {sortedData.length > 0 ? startIndex + 1 : 0} to{' '}
          {Math.min(endIndex, sortedData.length)} of {sortedData.length}
        </div>
        <div className="pagination-actions">
          <select value={rowsPerPage} onChange={(e) => { setRowsPerPage(Number(e.target.value)); setCurrentPage(1); }}>
            <option value={10}>10 / page</option>
            <option value={25}>25 / page</option>
            <option value={50}>50 / page</option>
          </select>
          <button onClick={() => setCurrentPage(p => Math.max(p - 1, 1))} disabled={currentPage === 1}>
            <FaChevronLeft />
          </button>
          <span className="page-indicator">Page {currentPage} of {totalPages || 1}</span>
          <button
            onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
            disabled={currentPage === totalPages || totalPages === 0}
          >
            <FaChevronRight />
          </button>
        </div>
      </div>
    </div>
  );
};

export default SmartDocsTable;