// src/components/Layout/ContentPanel.jsx
import React, { useState, useEffect, useRef } from 'react';
import PowerBIEmbed from '../PowerBI/PowerBIEmbed';
import PlaceholderContent from '../Common/PlaceholderContent';
import SmartFormDashboard from '../Dashboard/SmartFormDashboard';
import SmartDocsWorkflow from '../Dashboard/SmartDocsWorkflow';
import SmartDocsOverview from '../Dashboard/SmartDocsOverview';
import SmartBIMDashboard from '../Dashboard/SmartBIMDashboard';
import './ContentPanel.css';

const ContentPanel = ({ activeSection, onStatusChange, smartDocsRef }) => {
  const [isLoading, setIsLoading] = useState(true);
  const embedRef = useRef(null);

  const reportIds = {
    bim: '2dbc78a5-e402-4ebb-b744-4eee3d0bcb58',
  };

  useEffect(() => {
    if (activeSection === 'bim') {
      setIsLoading(true);
      onStatusChange({ text: 'Loading Power BI...', type: 'loading' });
    } else {
      setIsLoading(false);
      onStatusChange({ text: 'Ready', type: 'idle' });
    }
  }, [activeSection, onStatusChange]);

  const handleLoad = () => {
    setIsLoading(false);
    onStatusChange({ text: 'Connected', type: 'connected' });
  };

  const handleError = (error) => {
    setIsLoading(false);
    onStatusChange({ text: 'Error', type: 'error' });
  };

  const showBIM = activeSection === 'bim';
  const showDocsOverview = activeSection === 'docs-overview';
  const showDocsWorkflow = activeSection === 'docs-workflow';
  const showSmartForm = activeSection === 'form';
  const showSmartBIM = activeSection === 'iot';
  const showPlaceholder = [''].includes(activeSection);

  return (
    <div className="content-panel" id="contentPanel">
      {showBIM && (
        <PowerBIEmbed
          ref={embedRef}
          reportId={reportIds.bim}
          onLoad={handleLoad}
          onError={handleError}
          filterPaneEnabled={false}
          navContentPaneEnabled={false}
          showLoading={true}
          autoRefresh={false}
        />
      )}
      
      {/* Smart Docs Overview (Existing Dashboard) */}
      {showDocsOverview && (
        <SmartDocsOverview onStatusChange={onStatusChange} 
        />
      )}

      {showDocsWorkflow && (
        <SmartDocsWorkflow ref={smartDocsRef}  onStatusChange={onStatusChange} />
      )}

      {showSmartForm && (
        <SmartFormDashboard onStatusChange={onStatusChange} />
      )}

      {showSmartBIM && (
          <SmartBIMDashboard
          accessToken={import.meta.env.VITE_APS_TOKEN}
          modelUrn={import.meta.env.VITE_APS_MODEL_URN}
        />
      )}

      {showPlaceholder && (
        <PlaceholderContent section={activeSection} />
      )}


    </div>
  );
};

export default ContentPanel;