// src/components/Dashboard/SmartDocsWorkflow.jsx
import React, { useState, useEffect, useMemo, forwardRef, useImperativeHandle, useRef } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { FaLayerGroup, FaExclamationTriangle, FaTasks, FaTimes } from 'react-icons/fa';
import Select from 'react-select';
import { useSession } from '../../context/SessionContext';
import SmartDocsTable from './SmartDocsTable';
import LoadingOverlay from '../Common/LoadingOverlay';
import './SmartDocsWorkflow.css';

const FALLBACK_COLORS = [
  '#00ff88', '#6bcbff', '#ff9a76', '#ffd93d', '#ff6b6b',
  '#a66cff', '#17a2b8', '#e83e8c', '#6610f2', '#fd7e14',
];

const customSelectStyles = {
  control: (base, state) => ({
    ...base,
    backgroundColor: '#0a0a1e',
    borderColor: state.isFocused ? '#00ff88' : 'rgba(0, 255, 136, 0.3)',
    boxShadow: state.isFocused ? '0 0 15px rgba(0, 255, 136, 0.15)' : 'none',
    borderRadius: '8px',
    padding: '2px',
    cursor: 'pointer',
    '&:hover': { borderColor: '#00ff88' },
  }),
  singleValue: (base) => ({ ...base, color: '#00ff88', fontWeight: '500' }),
  menu: (base) => ({ ...base, backgroundColor: '#1a1a3a', border: '1px solid rgba(0, 255, 136, 0.2)', borderRadius: '8px', zIndex: 9999 }),
  option: (base, state) => ({
    ...base,
    backgroundColor: state.isFocused ? 'rgba(0, 255, 136, 0.1)' : 'transparent',
    color: state.isSelected ? '#00ff88' : '#e0e4f0',
    cursor: 'pointer',
  }),
  input: (base) => ({ ...base, color: '#e0e4f0' }),
  placeholder: (base) => ({ ...base, color: '#8899bb' }),
  indicatorSeparator: () => ({ display: 'none' }),
  dropdownIndicator: (base) => ({ ...base, color: '#00ff88' }),
};

const SmartDocsWorkflow = forwardRef(({ onStatusChange }, ref) => {
  const {
    requestProjects, projectsList,
    sendCardsRequest, cardsData, cardsLoading, cardsError,
    wsDataConnected
  } = useSession();

  const [selectedProject, setSelectedProject] = useState('all');
  const [selectedMonth, setSelectedMonth]     = useState(null);
  const [selectedStage, setSelectedStage]     = useState(null);
  const [selectedKpiFilter, setSelectedKpiFilter] = useState(null);
  
  // Guard to prevent duplicate fetch calls on mount
  const hasFetchedRef = useRef(false);

  useImperativeHandle(ref, () => ({
    refresh: () => {
      if (wsDataConnected) sendCardsRequest(selectedProject);
    }
  }), [sendCardsRequest, selectedProject, wsDataConnected]);

  useEffect(() => {
    if (wsDataConnected && !hasFetchedRef.current) {
      hasFetchedRef.current = true;
      requestProjects();
      sendCardsRequest(selectedProject);
    }
  }, [wsDataConnected, requestProjects, sendCardsRequest, selectedProject]);

  useEffect(() => {
    if (wsDataConnected) {
      sendCardsRequest(selectedProject);
      setSelectedMonth(null);
      setSelectedStage(null);
      setSelectedKpiFilter(null);
    }
  }, [selectedProject, sendCardsRequest, wsDataConnected]);

  useEffect(() => {
    if (!wsDataConnected) {
      onStatusChange?.({ text: 'Connecting...', type: 'loading' });
    } else if (cardsLoading) {
      onStatusChange?.({ text: 'Loading Cards...', type: 'loading' });
    } else if (cardsError) {
      onStatusChange?.({ text: 'Cards Error', type: 'error' });
    } else if (cardsData) {
      onStatusChange?.({ text: 'Connected', type: 'connected' });
    }
  }, [cardsLoading, cardsError, cardsData, onStatusChange, wsDataConnected]);

  const allCards   = cardsData?.cards || [];
  const stageNames = cardsData?.stageNames || [];
  const stageColors = cardsData?.stageColors || {};

  const colorFor = (name, idx = 0) =>
    stageColors[name] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];

  const matchesMonth = (card, month) => {
    if (!month) return true;
    if (!card.plannedFinishDate) return false;
    return card.plannedFinishDate.slice(0, 7) === month;
  };
  const matchesStage = (card, stage) => !stage || card.stageName === stage;
  
  const matchesKpi = (card, kpi) => {
    if (!kpi) return true;
    if (kpi === 'overdue') return card.isOverdue;
    if (kpi === 'pending') return card.isPending && !card.isOverdue; 
    return true;
  };

  const finalTableData = useMemo(
    () => allCards.filter(c => 
      matchesMonth(c, selectedMonth) && 
      matchesStage(c, selectedStage) &&
      matchesKpi(c, selectedKpiFilter)
    ),
    [allCards, selectedMonth, selectedStage, selectedKpiFilter]
  );

  const displayKpi = useMemo(() => {
    if (!selectedMonth && !selectedStage && !selectedKpiFilter) {
      return {
        total:   cardsData?.totalCards         ?? 0,
        overdue: cardsData?.overdueCards       ?? 0,
        pending: cardsData?.pendingActionCards ?? 0,
      };
    }
    
    const filteredByChart = allCards.filter(c => matchesMonth(c, selectedMonth) && matchesStage(c, selectedStage));
    return {
      total:   filteredByChart.length,
      overdue: filteredByChart.filter(c => c.isOverdue).length,
      pending: filteredByChart.filter(c => c.isPending).length,
    };
  }, [cardsData, allCards, selectedMonth, selectedStage, selectedKpiFilter]);

  const pieData = useMemo(() => {
    if (!selectedMonth && !selectedStage && !selectedKpiFilter && cardsData?.stagePie?.length) {
      return cardsData.stagePie.map((s, i) => ({ ...s, color: colorFor(s.name, i) }));
    }
    const counts = {};
    allCards.forEach(c => {
      if (matchesMonth(c, selectedMonth) && matchesKpi(c, selectedKpiFilter)) {
        counts[c.stageName] = (counts[c.stageName] || 0) + 1;
      }
    });
    return Object.entries(counts).map(([name, value], i) => ({
      name, value, color: colorFor(name, i),
    }));
  }, [cardsData, allCards, selectedMonth, selectedStage, selectedKpiFilter, stageColors]);

  const barRows = useMemo(() => {
    if (!selectedStage && !selectedKpiFilter && cardsData?.timelineBars?.length) return cardsData.timelineBars;
    const counts = {};
    allCards.forEach(c => {
      if (!matchesStage(c, selectedStage) || !matchesKpi(c, selectedKpiFilter) || !c.plannedFinishDate) return;
      const m = c.plannedFinishDate.slice(0, 7);
      if (!counts[m]) counts[m] = {};
      counts[m][c.stageName] = (counts[m][c.stageName] || 0) + 1;
    });
    return Object.keys(counts).sort().map(m => ({ month: m, ...counts[m] }));
  }, [cardsData, allCards, selectedStage, selectedKpiFilter]);

  const projectOptions = useMemo(() => [
    { value: 'all', label: 'All Projects' },
    ...projectsList.map(p => ({ value: p.id, label: p.name })),
  ], [projectsList]);

  const selectedOption =
    projectOptions.find(o => o.value === selectedProject) || projectOptions[0];

  return (
    <div className={`smart-docs-dashboard ${cardsLoading ? 'loading-blur' : ''}`}>
      {cardsLoading && (
        <LoadingOverlay
          moduleName="Smart Docs"
          subText="ST-CORE · DOCS CONTROL"
          loadingTip="Fetching cards and stages..."
          isLoading={cardsLoading}
        />
      )}

      <div className="dashboard-header">
        <div>
          <h2>Smart Docs Overview</h2>
          <p>Real-time analytics by stage</p>
        </div>
        <div className="header-controls">
          {selectedKpiFilter && (
            <button onClick={() => setSelectedKpiFilter(null)} className="filter-pill kpi-pill">
              <FaTimes /> {selectedKpiFilter === 'overdue' ? 'Overdue' : 'Pending'}
            </button>
          )}
          {selectedMonth && (
            <button onClick={() => setSelectedMonth(null)} className="filter-pill">
              <FaTimes /> Month: {selectedMonth}
            </button>
          )}
          {selectedStage && (
            <button onClick={() => setSelectedStage(null)} className="filter-pill">
              <FaTimes /> Stage: {selectedStage}
            </button>
          )}
          <div style={{ width: '280px', zIndex: 100 }}>
            <Select
              value={selectedOption}
              onChange={(opt) => setSelectedProject(opt.value)}
              options={projectOptions}
              isSearchable
              placeholder="Search projects..."
              styles={customSelectStyles}
            />
          </div>
        </div>
      </div>

      {cardsError && wsDataConnected && (
        <div className="dashboard-error">
          ⚠️ {cardsError}
          <button onClick={() => sendCardsRequest(selectedProject)}>Retry</button>
        </div>
      )}

      {cardsData && (
        <>
          <div className="kpi-grid">
            <div className="kpi-card total">
              <div className="kpi-icon"><FaLayerGroup /></div>
              <div className="kpi-content">
                <span className="kpi-label">Total Cards</span>
                <span className="kpi-value">{displayKpi.total.toLocaleString()}</span>
              </div>
            </div>
            
            <div 
              className={`kpi-card outstanding clickable ${selectedKpiFilter === 'overdue' ? 'active-kpi' : ''}`}
              onClick={() => setSelectedKpiFilter(prev => prev === 'overdue' ? null : 'overdue')}
            >
              <div className="kpi-icon"><FaExclamationTriangle /></div>
              <div className="kpi-content">
                <span className="kpi-label">Overdue Cards</span>
                <span className="kpi-value">{displayKpi.overdue}</span>
              </div>
            </div>

            <div 
              className={`kpi-card pending clickable ${selectedKpiFilter === 'pending' ? 'active-kpi' : ''}`}
              onClick={() => setSelectedKpiFilter(prev => prev === 'pending' ? null : 'pending')}
            >
              <div className="kpi-icon"><FaTasks /></div>
              <div className="kpi-content">
                <span className="kpi-label">Pending Action Cards</span>
                <span className="kpi-value">{displayKpi.pending}</span>
              </div>
            </div>
          </div>

          <div className="dashboard-grid">
            <div className="chart-card">
              <h3>
                Cards by Stage {selectedMonth ? `(Finish month: ${selectedMonth})` : ''}
                {' '}— click a slice
              </h3>
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%" cy="50%" innerRadius={45} outerRadius={65}
                      paddingAngle={2} dataKey="value" stroke="none"
                      onClick={(d) => setSelectedStage(prev => prev === d.name ? null : d.name)}
                      cursor="pointer"
                    >
                      {pieData.map((entry, i) => (
                        <Cell
                          key={i}
                          fill={entry.color}
                          opacity={selectedStage && selectedStage !== entry.name ? 0.3 : 1}
                        />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: '#1a1a3a',
                        border: '1px solid rgba(0,255,136,0.2)',
                        borderRadius: '8px', color: '#fff',
                      }}
                    />
                    <Legend
                      verticalAlign="bottom" height={70} iconType="circle"
                      wrapperStyle={{ fontSize: '11px', paddingTop: '10px', maxHeight: '70px', overflowY: 'auto' }}
                      onClick={(p) => setSelectedStage(prev => prev === p.value ? null : p.value)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="chart-card">
              <h3>
                Card Timeline by Stage
                {selectedStage ? ` — ${selectedStage}` : ''}
                {' '}— click a month
              </h3>
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={barRows}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    onClick={(s) => {
                      if (s?.activeLabel) {
                        setSelectedMonth(prev => prev === s.activeLabel ? null : s.activeLabel);
                      }
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis
                      dataKey="month" stroke="#8899bb"
                      tick={{ fill: '#8899bb', fontSize: 10 }}
                      angle={-45} textAnchor="end" height={60}
                    />
                    <YAxis stroke="#8899bb" tick={{ fill: '#8899bb', fontSize: 10 }} />
                    <RechartsTooltip
                      cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                      contentStyle={{
                        backgroundColor: '#1a1a3a',
                        border: '1px solid rgba(0,255,136,0.2)',
                        borderRadius: '8px', color: '#fff',
                      }}
                    />
                    {stageNames.map((sname, i) => (
                      <Bar
                        key={sname}
                        dataKey={sname}
                        stackId="stages"
                        fill={colorFor(sname, i)}
                        radius={i === stageNames.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <SmartDocsTable documents={finalTableData} />
        </>
      )}
    </div>
  );
});

SmartDocsWorkflow.displayName = 'SmartDocsWorkflow';
export default SmartDocsWorkflow;