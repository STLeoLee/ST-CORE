import React, { useRef, useEffect, useState, useCallback, forwardRef, useImperativeHandle } from 'react';
import { powerbiApi } from '../../services/powerbiApi';
import LoadingOverlay from '../Common/LoadingOverlay';
import './PowerBIEmbed.css';

// Load Power BI SDK from CDN
const loadPowerBISDK = () => {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if (window.powerbi && window.powerbi.embed) {
      console.log('✅ Power BI SDK already loaded');
      resolve(window.powerbi);
      return;
    }

    // Create script element
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/powerbi-client@2.18.0/dist/powerbi.min.js';
    script.async = true;

    script.onload = () => {
      // Wait a bit for the SDK to initialize
      setTimeout(() => {
        if (window.powerbi && window.powerbi.embed) {
          console.log('✅ Power BI SDK loaded from CDN');
          resolve(window.powerbi);
        } else {
          reject(new Error('Power BI SDK failed to initialize'));
        }
      }, 500);
    };

    script.onerror = () => {
      reject(new Error('Failed to load Power BI SDK from CDN'));
    };

    document.head.appendChild(script);
  });
};

const PowerBIEmbed = forwardRef(({ 
  reportId,
  onLoad,
  onError,
  filterPaneEnabled = false,
  navContentPaneEnabled = false,
  showLoading = true,
  autoRefresh = false,
  refreshInterval = 300000
}, ref) => {
  const containerRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isReady, setIsReady] = useState(false);
  const [sdkLoaded, setSdkLoaded] = useState(false);
  const reportInstance = useRef(null);
  const refreshTimer = useRef(null);
  const isMounted = useRef(true);
  const isEmbedding = useRef(false);
  const pbiRef = useRef(null);

  // Load SDK on mount
  useEffect(() => {
    const loadSDK = async () => {
      try {
        const pbi = await loadPowerBISDK();
        pbiRef.current = pbi;
        setSdkLoaded(true);
        console.log('✅ Power BI SDK ready');
      } catch (err) {
        console.error('❌ Failed to load Power BI SDK:', err);
        setError('Failed to load Power BI SDK. Please refresh the page.');
        setIsLoading(false);
      }
    };
    loadSDK();
  }, []);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (refreshTimer.current) {
      clearInterval(refreshTimer.current);
      refreshTimer.current = null;
    }
    
    if (reportInstance.current) {
      try {
        reportInstance.current.off('loaded');
        reportInstance.current.off('rendered');
        reportInstance.current.off('error');
        reportInstance.current.off('pageChanged');
        reportInstance.current.off('visualClicked');
        reportInstance.current = null;
      } catch (e) {
        console.warn('Cleanup error:', e);
      }
    }
    
    if (containerRef.current && isMounted.current) {
      try {
        while (containerRef.current.firstChild) {
          containerRef.current.removeChild(containerRef.current.firstChild);
        }
      } catch (e) {
        console.warn('Container clear error:', e);
      }
    }
  }, []);

  // Embed the report using SDK
  const embedReport = useCallback(async () => {
    if (!sdkLoaded || !pbiRef.current) {
      console.log('⏳ SDK not loaded yet, waiting...');
      setTimeout(() => {
        if (isMounted.current) {
          embedReport();
        }
      }, 1000);
      return;
    }
    
    if (isEmbedding.current) {
      console.log('⏳ Embed already in progress, skipping...');
      return;
    }
    
    if (!containerRef.current || !isMounted.current) {
      console.log('⚠️ Container not ready, skipping embed');
      return;
    }

    try {
      isEmbedding.current = true;
      setError(null);
      setIsLoading(true);
      setIsReady(false);

      console.log(`🚀 Fetching embed config...`);
      
      const config = await powerbiApi.getEmbedConfig(reportId);

      if (!isMounted.current) {
        isEmbedding.current = false;
        return;
      }

      console.log('📦 Embed config received, embedding report...');

      // Clear container
      while (containerRef.current.firstChild) {
        containerRef.current.removeChild(containerRef.current.firstChild);
      }

      const pbi = pbiRef.current;

      // Get TokenType and Permissions
      let tokenType = 0;
      let permissions = 0;
      
      if (pbi.models) {
        tokenType = pbi.models.TokenType?.Embed ?? 0;
        permissions = pbi.models.Permissions?.View ?? 0;
      }

      const embedConfig = {
        type: 'report',
        tokenType: 0,
        accessToken: config.embedToken,
        embedUrl: config.embedUrl,
        id: config.reportId,
        permissions: permissions,
        settings: {
          filterPaneEnabled: filterPaneEnabled,
          navContentPaneEnabled: navContentPaneEnabled,
          panes: {
            filters: {
              visible: filterPaneEnabled,
              expanded: false
            },
            pageNavigation: {
              visible: navContentPaneEnabled
            }
          },
          bars: {
            statusBar: {
              visible: false
            }
          }
        }
      };

      console.log('🎯 Embedding report...');

      // Embed the report
      const report = pbi.embed(containerRef.current, embedConfig);
      reportInstance.current = report;

      // Event handlers
      report.on('loaded', () => {
        console.log('✅ Power BI SDK: Report loaded');
        if (isMounted.current) {
          setIsReady(true);
          setIsLoading(false);
          isEmbedding.current = false;
          if (onLoad) onLoad();
        }
      });

      report.on('rendered', () => {
        console.log('✅ Power BI SDK: Report rendered');
        if (isMounted.current) {
          setIsReady(true);
          setIsLoading(false);
          isEmbedding.current = false;
          if (onLoad) onLoad();
        }
      });

      report.on('error', (event) => {
        console.error('❌ Power BI SDK Error:', event);
        const detail = event.detail || {};
        const errorMsg = detail.message || detail.error || 'Unknown error';
        if (isMounted.current) {
          setError(errorMsg);
          setIsLoading(false);
          setIsReady(false);
          isEmbedding.current = false;
          if (onError) onError(errorMsg);
        }
      });

      // Additional events
      report.on('pageChanged', (event) => {
        console.log('📄 Page changed:', event);
      });

      report.on('visualClicked', (event) => {
        console.log('👆 Visual clicked:', event);
      });

      // Auto-refresh
      if (autoRefresh && isMounted.current) {
        if (refreshTimer.current) {
          clearInterval(refreshTimer.current);
        }
        refreshTimer.current = setInterval(() => {
          refreshReport();
        }, refreshInterval);
      }

    } catch (err) {
      console.error('❌ Embed pipeline error:', err);
      if (isMounted.current) {
        setError(err.message || 'Failed to embed Power BI report');
        setIsLoading(false);
        setIsReady(false);
        isEmbedding.current = false;
        if (onError) onError(err.message);
      }
    }
  }, [reportId, filterPaneEnabled, navContentPaneEnabled, autoRefresh, refreshInterval, onLoad, onError, sdkLoaded]);

  // Refresh the report
  const refreshReport = useCallback(async () => {
    if (!reportInstance.current || !isMounted.current) return;

    try {
      await powerbiApi.refreshEmbedToken(reportId);
      await reportInstance.current.refresh();
      console.log('🔄 Report refreshed successfully');
    } catch (err) {
      console.warn('Refresh failed, reloading:', err);
      powerbiApi.clearCache(reportId);
      await embedReport();
    }
  }, [reportId, embedReport]);

  // Expose methods to parent
  useImperativeHandle(ref, () => ({
    refresh: refreshReport,
    reload: embedReport,
    getReport: () => reportInstance.current,
    isReady: () => isReady && !isLoading && !error
  }));

  // Initial embed
  useEffect(() => {
    isMounted.current = true;
    if (sdkLoaded) {
      const timer = setTimeout(() => {
        embedReport();
      }, 200);
      return () => {
        clearTimeout(timer);
      };
    }
  }, [sdkLoaded, embedReport]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMounted.current = false;
      cleanup();
    };
  }, [cleanup]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (reportInstance.current && isMounted.current) {
        try {
          reportInstance.current.resize();
        } catch (e) {
          // Ignore resize errors
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="powerbi-embed-container" style={{ width: '100%', height: '100%', position: 'relative' }}>
      {isLoading && showLoading && (
        <div className="powerbi-embed-loading">
          <LoadingOverlay moduleName="Power BI" onComplete={() => {}} />
        </div>
      )}

      {error && (
        <div className="powerbi-embed-error">
          <div className="error-icon">⚠️</div>
          <h3>Failed to Load Report</h3>
          <p>{error}</p>
          <button 
            onClick={() => {
              powerbiApi.clearCache(reportId);
              embedReport();
            }} 
            className="retry-btn"
          >
            🔄 Retry
          </button>
        </div>
      )}

      <div 
        ref={containerRef} 
        className="powerbi-container"
        style={{ 
          width: '100%', 
          height: '100%',
          minHeight: '500px',
          opacity: error ? 0.3 : 1,
          pointerEvents: error ? 'none' : 'auto'
        }}
      />
    </div>
  );
});

PowerBIEmbed.displayName = 'PowerBIEmbed';

export default PowerBIEmbed;