// src/components/Dashboard/SmartDocsOverview.jsx
import React, { useState } from 'react';
import {
  FaSearch, FaFilePdf, FaFileExcel, FaBell, FaEye
} from 'react-icons/fa';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend
} from 'recharts';
import './SmartDocsOverview.css';

// Hardcoded Data for the Table
const TABLE_DATA = [
  { id: '02', name: 'Fire Test Report', trade: 'Fire Safety', priority: 'HIGH', stage: 'Review', status: 'OVERDUE', aging: '+4 Days', ballInCourt: 'Architect', dueDate: 'Oct 13, 2026', comp: 50 },
  { id: '05', name: 'Concrete Report', trade: 'Structural', priority: 'HIGH', stage: 'Review', status: 'OVERDUE', aging: '+11 Days', ballInCourt: 'RE Engineer', dueDate: 'Nov 06, 2026', comp: 50 },
  { id: '09', name: 'Roof Waterproofing', trade: 'Architectural', priority: 'MED', stage: 'Draft', status: 'OVERDUE', aging: '+5 Days', ballInCourt: 'Sub-Contractor', dueDate: 'Nov 12, 2026', comp: 0 },
  { id: '03', name: 'Fire Res. Report', trade: 'Fire Safety', priority: 'HIGH', stage: 'Review', status: 'PENDING', aging: 'In Time', ballInCourt: 'Fire Dept', dueDate: 'Jan 08, 2027', comp: 50 },
  { id: '06', name: 'Rebar Grade 500B', trade: 'Materials', priority: 'LOW', stage: 'Draft', status: 'PENDING', aging: 'In Time', ballInCourt: 'Main Con', dueDate: 'Nov 23, 2026', comp: 0 },
];

// Data for the S-Curve (planned vs actual progress over time)
const S_CURVE_DATA = [
  { month: 'Oct 2026', planned: 0,   actual: 0   },
  { month: '',         planned: 35,  actual: 18  },
  { month: 'Nov 2026', planned: 65,  actual: 50  },
  { month: '',         planned: 88,  actual: 66  },
  { month: 'Dec 2026', planned: 100, actual: 82  },
];

const SmartDocsOverview = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');

  const filteredData = TABLE_DATA.filter(row =>
    row.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    row.id.includes(searchTerm) ||
    row.trade.toLowerCase().includes(searchTerm.toLowerCase()) ||
    row.ballInCourt.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="smart-docs-overview">

      {/* 1. Header & Global Controls */}
      <div className="sdo-header">
        <div>
          <h1>SMART DOCS OVERVIEW</h1>
          <p>Real-time submittal progress, risk tracking, and action bottlenecks</p>
        </div>
        <div className="sdo-global-controls">
          <div className="filter-presets">
            {['All', 'High Risk / Overdue'].map(f => (
              <button
                key={f}
                className={`filter-btn ${activeFilter === f ? 'active' : ''}`}
                onClick={() => setActiveFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="export-controls">
            <button className="export-btn"><FaFilePdf /> Export PDF</button>
            <button className="export-btn"><FaFileExcel /> Export XLS</button>
          </div>
        </div>
      </div>

      {/* 2. High-Level KPI Summary Deck */}
      <div className="sdo-kpi-grid">
        <div className="sdo-kpi-card total">
          <div className="kpi-title">TOTAL SUBMITTALS</div>
          <div className="kpi-value">9 Cards</div>
          <div className="kpi-subtext">4 Pending | 5 Closed</div>
        </div>
        <div className="sdo-kpi-card risk">
          <div className="kpi-title">OVERDUE / BLOCKED</div>
          <div className="kpi-value">3 Cards</div>
          <div className="kpi-subtext critical"></div>
        </div>
        <div className="sdo-kpi-card turnaround">
          <div className="kpi-title">AVG TURNAROUND TIME</div>
          <div className="kpi-value">14.2 Days</div>
          <div className="kpi-subtext warning"></div>
        </div>
        <div className="sdo-kpi-card progress">
          <div className="kpi-title">SUBMITTAL PROGRESS</div>
          <div className="kpi-value">55% Actual</div>
          <div className="kpi-subtext">Target: 65%</div>
          <div className="progress-bar-container">
            <div className="progress-bar-fill" style={{ width: '55%' }}></div>
          </div>
        </div>
      </div>

      {/* 3. Analytical Charts & Bottleneck Tracking */}
      <div className="sdo-charts-grid">

        {/* Left Chart: S-Curve (Recharts) */}
        <div className="sdo-chart-card">
          <h3>SUBMITTAL PROGRESS (PLANNED VS ACTUAL S-CURVE)</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={S_CURVE_DATA}
                margin={{ top: 8, right: 16, bottom: 0, left: -16 }}
              >
                <CartesianGrid stroke="#333" strokeDasharray="2 2" vertical={false} />
                <XAxis
                  dataKey="month"
                  tick={{ fill: '#8899bb', fontSize: 10 }}
                  stroke="#333"
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 50, 100]}
                  tickFormatter={(v) => `${v}%`}
                  tick={{ fill: '#8899bb', fontSize: 10 }}
                  stroke="#333"
                />
                <Tooltip
                  contentStyle={{
                    background: '#0f1223',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 4,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: '#e0e4f0' }}
                  itemStyle={{ color: '#e0e4f0' }}
                  formatter={(value) => `${value}%`}
                />
                <Legend
                  wrapperStyle={{ fontSize: 12, color: '#8899bb' }}
                  iconType="circle"
                  iconSize={8}
                />
                <Line
                  type="monotone"
                  dataKey="planned"
                  name="Planned Target"
                  stroke="#6bcbff"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                  dot={false}
                  activeDot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual Progress"
                  stroke="#00ff88"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Chart: Bottleneck Breakdown */}
        <div className="sdo-chart-card">
          <h3>BOTTLENECK & RESPONSIBLE PARTY BREAKDOWN</h3>
          <div className="bottleneck-list">
            <div className="bottleneck-item">
              <div className="bottleneck-label">Main Contractor</div>
              <div className="bottleneck-bar-bg"><div className="bottleneck-bar-fill" style={{ width: '80%' }}></div></div>
              <div className="bottleneck-count">4 Pending</div>
            </div>
            <div className="bottleneck-item">
              <div className="bottleneck-label">Structural Eng.</div>
              <div className="bottleneck-bar-bg"><div className="bottleneck-bar-fill risk" style={{ width: '60%' }}></div></div>
              <div className="bottleneck-count">2 Overdue</div>
            </div>
            <div className="bottleneck-item">
              <div className="bottleneck-label">MEP Consultant</div>
              <div className="bottleneck-bar-bg"><div className="bottleneck-bar-fill risk" style={{ width: '40%' }}></div></div>
              <div className="bottleneck-count">1 Overdue</div>
            </div>
            <div className="bottleneck-item">
              <div className="bottleneck-label">Fire Specialist</div>
              <div className="bottleneck-bar-bg"><div className="bottleneck-bar-fill" style={{ width: '25%' }}></div></div>
              <div className="bottleneck-count">1 Draft</div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. PM Management Data Table */}
      <div className="sdo-table-card">
        <div className="sdo-table-header">
          <h3>MANAGEMENT ACTION TABLE</h3>
          <div className="table-search">
            <FaSearch />
            <input
              type="text"
              placeholder="Search by Name, ID, Assignee, Trade..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="table-wrapper">
          <table className="sdo-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Document Name</th>
                <th>Trade / Group</th>
                <th>Priority</th>
                <th>Stage</th>
                <th>Status / Aging</th>
                <th>Ball in Court</th>
                <th>Due Date</th>
                <th>% Comp.</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((row, idx) => (
                <tr key={idx}>
                  <td className="text-mono">{row.id}</td>
                  <td className="text-name">{row.name}</td>
                  <td>{row.trade}</td>
                  <td>
                    <span className={`badge-priority ${row.priority.toLowerCase()}`}>{row.priority}</span>
                  </td>
                  <td>{row.stage}</td>
                  <td>
                    <span className={`status-text ${row.status.toLowerCase()}`}>{row.status}</span>
                    {row.status === 'OVERDUE' && <span className="aging-text">{row.aging}</span>}
                  </td>
                  <td>{row.ballInCourt}</td>
                  <td>{row.dueDate}</td>
                  <td>
                    <div className="mini-progress">
                      <div className="mini-progress-fill" style={{ width: `${row.comp}%` }}></div>
                    </div>
                    <span className="comp-text">{row.comp}%</span>
                  </td>
                  <td>
                    {row.status === 'OVERDUE' ? (
                      <button className="action-btn remind"><FaBell /> Remind</button>
                    ) : (
                      <button className="action-btn view"><FaEye /> View</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="sdo-table-footer">
          <span>Showing 1 to {filteredData.length} of 9 critical items</span>
        </div>
      </div>

    </div>
  );
};

export default SmartDocsOverview;