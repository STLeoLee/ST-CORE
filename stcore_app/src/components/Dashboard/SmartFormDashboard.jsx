// src/components/Dashboard/SmartFormDashboard.jsx
import React, { useState, useEffect } from 'react';
import { 
  FaShieldAlt, FaExclamationTriangle, FaCloudSun, 
  FaUsers, FaBoxOpen, FaBullhorn, FaNewspaper, FaTimes,
  FaHardHat, FaTools, FaBoxes, FaLeaf, FaClock, FaFileSignature, FaChartLine
} from 'react-icons/fa';
import {
  ResponsiveContainer, ComposedChart, BarChart, Bar, Line, XAxis, YAxis,
  Tooltip, PieChart, Pie, Cell
} from 'recharts';
import { useSession } from '../../context/SessionContext';
import './SmartFormDashboard.css';

const COLOR_PALETTE = [
  '#ffd93d', '#ff6b6b', '#6bcbff', '#00ff88', '#a66cff', '#ff9a76', '#8899bb', '#e83e8c', '#6610f2'
];

const EPTW_DATA = [
  { zone: "Main Construction Area", applied: 8, approved: 5, inProgress: 3, expired: 0, totalActive: 8 },
  { zone: "North Wing", applied: 4, approved: 3, inProgress: 1, expired: 0, totalActive: 4 },
  { zone: "Equipment Storage", applied: 3, approved: 3, inProgress: 0, expired: 0, totalActive: 3 },
  { zone: "Site Office", applied: 2, approved: 2, inProgress: 0, expired: 0, totalActive: 2 },
  { zone: "Material Staging", applied: 5, approved: 2, inProgress: 2, expired: 0, totalActive: 4 },
  { zone: "Stairwell / Lift Core", applied: 3, approved: 1, inProgress: 1, expired: 1, totalActive: 2 },
];

const SCORE_BREAKDOWN = [
  { category: "Worker", deduction: -5, reason: "PPE Compliance (89%) & 2 Safety Violations" },
  { category: "Asset", deduction: -3, reason: "1 Expired Equipment Certificate & 2 Uninspected Scaffolds" },
  { category: "Material", deduction: -3, reason: "Improper Material Staging in Zone B" },
  { category: "Environment", deduction: 0, reason: "All parameters within normal limits" },
];

const ASSET_CERT_DATA = [
  { name: 'Valid Certificates', count: 12, color: '#00ff88' },
  { name: 'Expired Certificates', count: 3, color: '#ff6b6b' },
];

const ISSUES_CHART_DATA = [
  { month: 'Jun', completed: 120, pending: 20, avgTime: 14.2 },
  { month: 'Jul', completed: 150, pending: 35, avgTime: 18.4 },
  { month: 'Aug', completed: 90, pending: 10, avgTime: 2.48 },
  { month: 'Sep', completed: 180, pending: 15, avgTime: 16.81 },
  { month: 'Oct', completed: 160, pending: 25, avgTime: 22.38 },
  { month: 'Nov', completed: 200, pending: 10, avgTime: 17.94 },
];

const PTW_TREND_DATA = [
  { month: 'Jun', approvalRate: 0.52, expiredPtw: 0.08, avgApprovalTime: 257 },
  { month: 'Jul', approvalRate: 1.00, expiredPtw: 0.10, avgApprovalTime: 1 },
  { month: 'Aug', approvalRate: 0.99, expiredPtw: 0.02, avgApprovalTime: 274 },
  { month: 'Sep', approvalRate: 0.92, expiredPtw: 0.01, avgApprovalTime: 166 },
  { month: 'Oct', approvalRate: 0.72, expiredPtw: 0.15, avgApprovalTime: 178 },
  { month: 'Nov', approvalRate: 0.98, expiredPtw: 0.03, avgApprovalTime: 178 },
  { month: 'Dec', approvalRate: 0.65, expiredPtw: 0.12, avgApprovalTime: 211 },
];

const ALERT_CATEGORY_DATA = [
  { name: 'Machine Proximity', count: 2490, color: '#ff4d4d' }, 
  { name: 'Non-Auth Entry', count: 1490, color: '#b30000' },    
  { name: 'PPE', count: 1040, color: '#ff9999' },               
  { name: 'Other', count: 250, color: '#666666' },              
];

const PERMIT_METRICS = {
  avgApprovalTime: '4.2 Days',
  rejectionRate: '8%',
  expiredPermits: 3
};

const CERT_MONTH_DATA = [
  { month: 'Jan', valid: 10, expired: 1 }, { month: 'Feb', valid: 10, expired: 1 },
  { month: 'Mar', valid: 10, expired: 1 }, { month: 'Apr', valid: 10, expired: 1 },
  { month: 'May', valid: 10, expired: 1 }, { month: 'Jun', valid: 10, expired: 1 },
  { month: 'Jul', valid: 10, expired: 1 }, { month: 'Aug', valid: 10, expired: 1 },
  { month: 'Sep', valid: 12, expired: 2 }, { month: 'Oct', valid: 14, expired: 3 },
  { month: 'Nov', valid: 12, expired: 3 },
];

const calculateScore = () => {
  const baseScore = 100;
  const totalDeductions = SCORE_BREAKDOWN.reduce((sum, item) => sum + item.deduction, 0);
  return baseScore + totalDeductions;
};

const getCategoryScore = (category) => {
  const deduction = SCORE_BREAKDOWN.find(item => item.category === category)?.deduction || 0;
  return 100 + deduction;
};

/* Custom Tooltips */
const CustomIssuesTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div style={{ background: '#0f1223', border: '1px solid rgba(255,255,255,0.2)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.7rem', color: '#e0e4f0' }}>
        <div style={{ fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px', marginBottom: '4px' }}>{label} Alerts</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
          <span><span style={{ color: '#00ff88' }}>●</span> Completed:</span> <strong>{data.completed}</strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
          <span><span style={{ color: '#ff6b6b' }}>●</span> Pending:</span> <strong>{data.pending}</strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '4px', marginTop: '2px' }}>
          <span><span style={{ color: '#fff' }}>●</span> Avg Time:</span> <strong style={{ color: '#6bcbff' }}>{data.avgTime}m</strong>
        </div>
      </div>
    );
  }
  return null;
};

const CustomPtwTrendTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div style={{ background: '#0f1223', border: '1px solid rgba(255,255,255,0.2)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.7rem', color: '#e0e4f0' }}>
        <div style={{ fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px', marginBottom: '4px' }}>{label} PTW Metrics</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
          <span><span style={{ color: '#00ff88' }}>●</span> Approval Rate:</span> <strong>{(data.approvalRate * 100).toFixed(0)}%</strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
          <span><span style={{ color: '#ff6b6b' }}>●</span> Expired Rate:</span> <strong>{(data.expiredPtw * 100).toFixed(0)}%</strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '4px', marginTop: '2px' }}>
          <span><span style={{ color: '#6bcbff' }}>●</span> Avg Time:</span> <strong style={{ color: '#6bcbff' }}>{data.avgApprovalTime} Mins</strong>
        </div>
      </div>
    );
  }
  return null;
};

const CustomCertTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div style={{ background: '#0f1223', border: '1px solid rgba(255,255,255,0.2)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.7rem', color: '#e0e4f0' }}>
        <div style={{ fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px', marginBottom: '4px' }}>{label} Total: {data.valid + data.expired}</div>
        <div style={{ color: '#00ff88' }}>Valid: {data.valid}</div>
        <div style={{ color: '#ff6b6b' }}>Expired: {data.expired}</div>
      </div>
    );
  }
  return null;
};

const SmartFormDashboard = () => {
  const { requestNovadeData, novadeData, novadeLoading, wsDataConnected } = useSession();

  const [weather, setWeather] = useState({ temp: '25', humidity: '78', warning: 'No active signals' });
  
  const [isEptwModalOpen, setIsEptwModalOpen] = useState(false);
  const [isScoreModalOpen, setIsScoreModalOpen] = useState(false);
  const [isIssueModalOpen, setIsIssueModalOpen] = useState(false);
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);

  const currentScore = calculateScore();

  const issueStatusData = (novadeData?.statusPieData || []).map((item, idx) => ({
    ...item,
    color: COLOR_PALETTE[idx % COLOR_PALETTE.length]
  }));

  const newsItems = [
    { title: "Strong wind warning issued", detail: "Secure loose materials by 18:00.", time: "10 min ago", type: "warning" },
    { title: "Scaffolding Inspection", detail: "West Wing scheduled at 14:00.", time: "1 hr ago", type: "info" },
    { title: "Concrete Delivery", detail: "Arriving at Zone B at 10:30 AM.", time: "2 hrs ago", type: "info" },
    { title: "PPE Reminder", detail: "High-vis vests mandatory in all zones.", time: "3 hrs ago", type: "info" },
    { title: "Fire Drill Scheduled", detail: "Friday at 15:00. Assembly point is Car Park A.", type: "warning" },
  ];

  useEffect(() => {
    const fetchHKOWeather = async () => {
      try {
        const res = await fetch('https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en');
        if (!res.ok) throw new Error('HKO API error');
        const data = await res.json();
        const tempData = data.temperature?.data?.[0];
        const humidityData = data.humidity?.data?.[0];
        if (tempData && humidityData) {
          setWeather({
            temp: tempData.value.toString(),
            humidity: humidityData.value.toString(),
            warning: data.warningMessage ? 'Warning active' : 'No active signals'
          });
        }
      } catch (err) { console.warn('HKO fetch failed:', err); }
    };
    fetchHKOWeather();
  }, []);

  useEffect(() => {
    if (wsDataConnected) {
      requestNovadeData('IZ2L4', 1520234658834);
    }
  }, [wsDataConnected, requestNovadeData]);

  const importantNews = newsItems.filter(n => n.type === 'warning');
  const tickerText = importantNews.length > 0 
    ? importantNews.map(n => `${n.title}: ${n.detail}`).join('  •  ') 
    : "No critical alerts at this time.";

  const totalAlerts = ALERT_CATEGORY_DATA.reduce((sum, item) => sum + item.count, 0);
  const totalModalIssues = issueStatusData.reduce((sum, item) => sum + item.count, 0);
  const totalAssetCerts = ASSET_CERT_DATA.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="smart-docs-dashboard">
      
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h2>Safety Overview</h2>
          <p>Real-time site performance</p>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '4px 10px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FaCloudSun style={{ fontSize: '1rem', color: '#6bcbff' }} />
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#e0e4f0' }}>
              {weather.temp}°C <span style={{fontSize: '0.65rem', color: '#8899bb'}}>RH {weather.humidity}%</span>
            </div>
            <div style={{ fontSize: '0.6rem', color: '#00ff88' }}>HKO: {weather.warning}</div>
          </div>
        </div>
      </div>

      {/* Top Single Row KPI Grid */}
      <div className="kpi-grid">
        <div className="kpi-card total" onClick={() => setIsScoreModalOpen(true)}>
          <div style={{ color: '#00ff88', fontSize: '1.2rem' }}><FaShieldAlt /></div>
          <div className="kpi-content">
            <span className="kpi-label">Overall Score</span>
            <span className="kpi-value" style={{ color: '#00ff88' }}>{currentScore}</span>
            <span style={{ fontSize: '0.55rem', color: '#00ff88' }}>↗ +2</span>
          </div>
        </div>
        
        <div className="kpi-card" onClick={() => setIsScoreModalOpen(true)}>
          <div style={{ color: '#ffd93d', fontSize: '1.2rem' }}><FaHardHat /></div>
          <div className="kpi-content">
            <span className="kpi-label">Worker Score</span>
            <span className="kpi-value">{getCategoryScore('Worker')}</span>
            <span style={{ fontSize: '0.55rem', color: '#8899bb' }}>Deduction: -5</span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => setIsAssetModalOpen(true)}>
          <div style={{ color: '#6bcbff', fontSize: '1.2rem' }}><FaTools /></div>
          <div className="kpi-content">
            <span className="kpi-label">Asset Score</span>
            <span className="kpi-value">{getCategoryScore('Asset')}</span>
            <span style={{ fontSize: '0.55rem', color: '#8899bb' }}>Deduction: -3</span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => setIsScoreModalOpen(true)}>
          <div style={{ color: '#a66cff', fontSize: '1.2rem' }}><FaBoxes /></div>
          <div className="kpi-content">
            <span className="kpi-label">Material Score</span>
            <span className="kpi-value">{getCategoryScore('Material')}</span>
            <span style={{ fontSize: '0.55rem', color: '#8899bb' }}>Deduction: -3</span>
          </div>
        </div>

        <div className="kpi-card" onClick={() => setIsScoreModalOpen(true)}>
          <div style={{ color: '#ff9a76', fontSize: '1.2rem' }}><FaLeaf /></div>
          <div className="kpi-content">
            <span className="kpi-label">Env. Score</span>
            <span className="kpi-value">{getCategoryScore('Environment')}</span>
            <span style={{ fontSize: '0.55rem', color: '#00ff88' }}>Excellent</span>
          </div>
        </div>
      </div>

      <div className="main-layout-grid">
        
        {/* LEFT SIDE: Rolling News -> Site News -> Site Model */}
        <div className="dashboard-col">
          
          {/* 1. Rolling News */}
          <div className="news-ticker-container">
            <FaBullhorn style={{ color: '#ff6b6b', flexShrink: 0 }} />
            <div style={{ flex: 1, overflow: 'hidden', whiteSpace: 'nowrap', position: 'relative' }}>
              <div className="news-ticker-text">{tickerText}</div>
            </div>
          </div>

          {/* 2. Site News (Fixed Height to avoid huge empty gap) */}
          <div className="chart-card">
            <div className="chart-card-header">
              <h3 className="chart-card-title"><FaNewspaper style={{marginRight: '6px'}}/> Site News</h3>
            </div>
            <div style={{ padding: '8px', minHeight: '140px', maxHeight: '160px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {newsItems.map((news, idx) => (
                <div key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: news.type === 'warning' ? '#ffd93d' : '#e0e4f0' }}>{news.title}</span>
                    <span style={{ fontSize: '0.6rem', color: '#8899bb' }}>{news.time}</span>
                  </div>
                  <div style={{ fontSize: '0.65rem', color: '#8899bb' }}>{news.detail}</div>
                </div>
              ))}
            </div>
          </div>

          {/* 3. Site Model (Fills remaining left column space) */}
          <div className="chart-card site-model-card">
            <div className="chart-card-header">
              <h3 className="chart-card-title">Site Model</h3>
              <button className="filter-pill" style={{ padding: '2px 6px', fontSize: '0.6rem', background: 'rgba(107, 203, 255, 0.15)', color: '#6bcbff', border: 'none', borderRadius: '3px' }}>3D Scan</button>
            </div>
            <div className="iframe-container">
              <iframe 
                src="https://my.matterport.com/show/?m=FGwxABB6QX9&play=1&ts=2&lp=1" 
                title="Site Model 3D" frameBorder="0" allowFullScreen
              ></iframe>
            </div>
          </div>

        </div>

        {/* RIGHT SIDE */}
        <div className="dashboard-col">
          
          {/* 1. Permit to Work Summary */}
          <div className="chart-card" onClick={() => setIsEptwModalOpen(true)} style={{ cursor: 'pointer' }}>
            <div className="chart-card-header">
              <h3 className="chart-card-title"><FaFileSignature style={{marginRight: '4px'}}/> Permit to Work Summary</h3>
            </div>
            <div style={{ padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <FaClock style={{ color: '#6bcbff', fontSize: '1.2rem' }} />
                <span style={{ fontSize: '0.6rem', color: '#8899bb' }}>Avg Approval</span>
                <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#fff' }}>{PERMIT_METRICS.avgApprovalTime}</span>
              </div>
              <div style={{ width: '1px', height: '30px', background: 'rgba(255,255,255,0.1)' }}></div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <FaExclamationTriangle style={{ color: '#ffd93d', fontSize: '1.2rem' }} />
                <span style={{ fontSize: '0.6rem', color: '#8899bb' }}>Rejection Rate</span>
                <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#fff' }}>{PERMIT_METRICS.rejectionRate}</span>
              </div>
              <div style={{ width: '1px', height: '30px', background: 'rgba(255,255,255,0.1)' }}></div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <FaTimes style={{ color: '#ff6b6b', fontSize: '1.2rem' }} />
                <span style={{ fontSize: '0.6rem', color: '#8899bb' }}>Expired</span>
                <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#fff' }}>{PERMIT_METRICS.expiredPermits}</span>
              </div>
            </div>
          </div>

          {/* 2. PT Performance Trend (Fixed Recharts container height) */}
          <div className="chart-card" onClick={() => setIsEptwModalOpen(true)} style={{ cursor: 'pointer' }}>
            <div className="chart-card-header">
              <h3 className="chart-card-title"><FaChartLine style={{ marginRight: '6px' }} /> PT Performance Trend</h3>
              <div style={{ display: 'flex', gap: '6px', fontSize: '0.5rem', color: '#8899bb' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}><span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#00ff88' }}></span> Appr. Rate</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}><span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#ff6b6b' }}></span> Expired</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}><span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#6bcbff' }}></span> Avg Time</span>
              </div>
            </div>

            <div style={{ width: '100%', height: 160, padding: '10px 6px 4px 0' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={PTW_TREND_DATA} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                  <XAxis dataKey="month" tick={{ fill: '#8899bb', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="left" domain={[0, 1.0]} tick={{ fill: '#8899bb', fontSize: 9 }} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fill: '#8899bb', fontSize: 9 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomPtwTrendTooltip />} />
                  <Bar yAxisId="left" dataKey="approvalRate" fill="#00ff88" barSize={12} radius={[2, 2, 0, 0]} />
                  <Bar yAxisId="left" dataKey="expiredPtw" fill="#ff6b6b" barSize={12} radius={[2, 2, 0, 0]} />
                  <Line yAxisId="right" type="monotone" dataKey="avgApprovalTime" stroke="#6bcbff" strokeWidth={2} dot={{ fill: '#6bcbff', r: 3 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 3. Issues & Alerts Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', alignItems: 'stretch' }}>
            
            <div className="chart-card" onClick={() => setIsIssueModalOpen(true)} style={{ cursor: 'pointer' }}>
              <div className="chart-card-header">
                <h3 className="chart-card-title">Issues & Response</h3>
                <div style={{ display: 'flex', gap: '4px', fontSize: '0.5rem', color: '#8899bb' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}><span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#00ff88' }}></span> Done</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}><span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#ff6b6b' }}></span> Pending</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}><span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#fff' }}></span> Avg</span>
                </div>
              </div>
              
              <div style={{ width: '100%', height: 160, padding: '8px 4px 0 0' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={ISSUES_CHART_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="month" tick={{ fill: '#8899bb', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="left" tick={{ fill: '#8899bb', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fill: '#8899bb', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomIssuesTooltip />} />
                    <Bar yAxisId="left" dataKey="completed" stackId="a" fill="#00ff88" barSize={14} />
                    <Bar yAxisId="left" dataKey="pending" stackId="a" fill="#ff6b6b" barSize={14} radius={[3, 3, 0, 0]} />
                    <Line yAxisId="right" type="monotone" dataKey="avgTime" stroke="#ffffff" strokeWidth={2} dot={{ fill: '#ffffff', r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="chart-card">
              <div className="chart-card-header">
                <h3 className="chart-card-title">Alerts By Category</h3>
              </div>
              
              <div style={{ padding: '4px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'space-between', flex: 1 }}>
                <div style={{ width: '100%', height: 100, position: 'relative' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={ALERT_CATEGORY_DATA}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={30}
                        outerRadius={45}
                        stroke="none"
                      >
                        {ALERT_CATEGORY_DATA.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                    textAlign: 'center', pointerEvents: 'none'
                  }}>
                    <div style={{ fontSize: '0.45rem', color: '#8899bb', textTransform: 'uppercase' }}>Total</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#fff' }}>{totalAlerts.toLocaleString()}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', width: '100%', padding: '0 8px 4px 8px' }}>
                  {ALERT_CATEGORY_DATA.map((item, idx) => {
                    const pct = ((item.count / totalAlerts) * 100).toFixed(1);
                    return (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.6rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#e0e4f0' }}>
                          <div style={{ width: '6px', height: '6px', borderRadius: '2px', background: item.color }}></div>
                          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '85px' }}>{item.name}</span>
                        </div>
                        <div style={{ color: '#8899bb', fontWeight: 'bold', textAlign: 'right' }}>
                          {item.count.toLocaleString()} <span style={{ fontWeight: 'normal', fontSize: '0.5rem' }}>({pct}%)</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

          </div>

          {/* 4. Certificates by Month */}
          <div className="chart-card">
            <div className="chart-card-header">
              <h3 className="chart-card-title">Certificates by Month</h3>
              <div style={{ display: 'flex', gap: '8px', fontSize: '0.55rem', color: '#8899bb' }}>
                <span><span style={{ display: 'inline-block', width: '6px', height: '6px', background: '#00ff88', marginRight: '3px', borderRadius: '2px' }}></span>Valid</span>
                <span><span style={{ display: 'inline-block', width: '6px', height: '6px', background: '#ff6b6b', marginRight: '3px', borderRadius: '2px' }}></span>Expired</span>
              </div>
            </div>
            
            <div style={{ width: '100%', height: 120, padding: '6px 4px 0 0' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={CERT_MONTH_DATA} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <XAxis dataKey="month" tick={{ fill: '#8899bb', fontSize: 9 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#8899bb', fontSize: 9 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomCertTooltip />} />
                  <Bar dataKey="valid" stackId="a" fill="#00ff88" barSize={10} />
                  <Bar dataKey="expired" stackId="a" fill="#ff6b6b" barSize={10} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>

      {/* Modals */}
      {isEptwModalOpen && (<div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '20px' }}><div style={{ width: '80vw', maxWidth: '1000px', backgroundColor: '#0a0a1e', borderRadius: '12px', border: '1px solid rgba(0, 255, 136, 0.3)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}><div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#0f1223' }}><div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#00ff88', fontWeight: 600, fontSize: '1rem' }}><FaUsers /> EPTW NOS. BY ZONE</div><button onClick={() => setIsEptwModalOpen(false)} style={{ background: 'transparent', border: 'none', color: '#ff6b6b', fontSize: '1.2rem', cursor: 'pointer' }}><FaTimes /></button></div><div style={{ flex: 1, overflowY: 'auto', maxHeight: '70vh' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', color: '#e0e4f0' }}><thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textTransform: 'uppercase', color: '#8899bb', fontSize: '0.7rem' }}><th style={{ padding: '12px 20px', textAlign: 'left' }}>Zone</th><th style={{ padding: '12px 20px', textAlign: 'center', color: '#6bcbff' }}>Applied</th><th style={{ padding: '12px 20px', textAlign: 'center', color: '#00ff88' }}>Approved</th><th style={{ padding: '12px 20px', textAlign: 'center', color: '#ffd93d' }}>In Progress</th><th style={{ padding: '12px 20px', textAlign: 'center', color: '#ff6b6b' }}>Expired</th><th style={{ padding: '12px 20px', textAlign: 'center' }}>Total Active</th></tr></thead><tbody>{EPTW_DATA.map((row, idx) => (<tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}><td style={{ padding: '12px 20px', fontWeight: 500 }}>{row.zone}</td><td style={{ padding: '12px 20px', textAlign: 'center' }}><span style={{ background: 'rgba(107,203,255,0.1)', color: '#6bcbff', padding: '2px 10px', borderRadius: '4px' }}>{row.applied}</span></td><td style={{ padding: '12px 20px', textAlign: 'center' }}><span style={{ background: 'rgba(0,255,136,0.1)', color: '#00ff88', padding: '2px 10px', borderRadius: '4px' }}>{row.approved}</span></td><td style={{ padding: '12px 20px', textAlign: 'center' }}><span style={{ background: 'rgba(255,217,61,0.1)', color: '#ffd93d', padding: '2px 10px', borderRadius: '4px' }}>{row.inProgress}</span></td><td style={{ padding: '12px 20px', textAlign: 'center' }}><span style={{ background: 'rgba(255,107,107,0.1)', color: '#ff6b6b', padding: '2px 10px', borderRadius: '4px' }}>{row.expired}</span></td><td style={{ padding: '12px 20px', textAlign: 'center', fontWeight: 600 }}>{row.totalActive}</td></tr>))}</tbody></table></div></div></div>)}

      {isScoreModalOpen && (<div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '20px' }}><div style={{ width: '60vw', maxWidth: '700px', backgroundColor: '#0a0a1e', borderRadius: '12px', border: '1px solid rgba(0, 255, 136, 0.3)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}><div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#0f1223' }}><div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#00ff88', fontWeight: 600, fontSize: '1rem' }}><FaShieldAlt /> SAFETY SCORE BREAKDOWN</div><button onClick={() => setIsScoreModalOpen(false)} style={{ background: 'transparent', border: 'none', color: '#ff6b6b', fontSize: '1.2rem', cursor: 'pointer' }}><FaTimes /></button></div><div style={{ padding: '20px' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', color: '#e0e4f0' }}><thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textTransform: 'uppercase', color: '#8899bb', fontSize: '0.7rem' }}><th style={{ padding: '10px', textAlign: 'left' }}>Category</th><th style={{ padding: '10px', textAlign: 'center' }}>Deduction</th><th style={{ padding: '10px', textAlign: 'left' }}>Reason</th></tr></thead><tbody>{SCORE_BREAKDOWN.map((item, idx) => (<tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}><td style={{ padding: '12px 10px', fontWeight: 500 }}>{item.category}</td><td style={{ padding: '12px 10px', textAlign: 'center' }}><span style={{ background: 'rgba(255,107,107,0.1)', color: '#ff6b6b', padding: '2px 8px', borderRadius: '4px', fontWeight: 'bold' }}>{item.deduction}</span></td><td style={{ padding: '12px 10px', color: '#8899bb' }}>{item.reason}</td></tr>))}</tbody></table></div></div></div>)}

      {isIssueModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '20px' }}>
          <div style={{ width: '60vw', maxWidth: '800px', backgroundColor: '#0a0a1e', borderRadius: '12px', border: '1px solid rgba(0, 255, 136, 0.3)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#0f1223' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#ff6b6b', fontWeight: 600, fontSize: '1rem' }}>
                <FaExclamationTriangle /> TOTAL ISSUES BY STATUS
              </div>
              <button onClick={() => setIsIssueModalOpen(false)} style={{ background: 'transparent', border: 'none', color: '#ff6b6b', fontSize: '1.2rem', cursor: 'pointer' }}>
                <FaTimes />
              </button>
            </div>
            <div style={{ padding: '40px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '40px' }}>
              {novadeLoading ? (
                <div style={{ color: '#8899bb' }}>Loading chart data...</div>
              ) : issueStatusData.length > 0 ? (
                <>
                  <div style={{ width: 220, height: 220, position: 'relative' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={issueStatusData}
                          dataKey="count"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={65}
                          outerRadius={95}
                          stroke="none"
                        >
                          {issueStatusData.map((entry, idx) => (
                            <Cell key={`modal-cell-${idx}`} fill={entry.color} />
                          ))}
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                    <div style={{
                      position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                      textAlign: 'center', pointerEvents: 'none'
                    }}>
                      <div style={{ fontSize: '0.7rem', color: '#8899bb', textTransform: 'uppercase' }}>Total</div>
                      <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#fff' }}>{totalModalIssues}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {issueStatusData.map((item, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.9rem' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: item.color }}></div>
                        <div style={{ color: '#e0e4f0', width: '90px' }}>{item.name}</div>
                        <div style={{ color: '#8899bb', fontWeight: 'bold' }}>{item.count}</div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div style={{ color: '#8899bb' }}>No issue data available</div>
              )}
            </div>
          </div>
        </div>
      )}

      {isAssetModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '20px' }}>
          <div style={{ width: '50vw', maxWidth: '600px', backgroundColor: '#0a0a1e', borderRadius: '12px', border: '1px solid rgba(0, 255, 136, 0.3)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#0f1223' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#6bcbff', fontWeight: 600, fontSize: '1rem' }}>
                <FaBoxOpen /> ASSET CERTIFICATE STATUS
              </div>
              <button onClick={() => setIsAssetModalOpen(false)} style={{ background: 'transparent', border: 'none', color: '#ff6b6b', fontSize: '1.2rem', cursor: 'pointer' }}>
                <FaTimes />
              </button>
            </div>
            <div style={{ padding: '40px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '40px' }}>
              <div style={{ width: 200, height: 200, position: 'relative' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={ASSET_CERT_DATA}
                      dataKey="count"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      stroke="none"
                    >
                      {ASSET_CERT_DATA.map((entry, idx) => (
                        <Cell key={`asset-cell-${idx}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div style={{
                  position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                  textAlign: 'center', pointerEvents: 'none'
                }}>
                  <div style={{ fontSize: '0.65rem', color: '#8899bb', textTransform: 'uppercase' }}>Total</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#fff' }}>{totalAssetCerts}</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {ASSET_CERT_DATA.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.95rem' }}>
                    <div style={{ width: '14px', height: '14px', borderRadius: '3px', background: item.color }}></div>
                    <div style={{ color: '#e0e4f0', width: '150px' }}>{item.name}</div>
                    <div style={{ color: '#8899bb', fontWeight: 'bold' }}>{item.count}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default SmartFormDashboard;