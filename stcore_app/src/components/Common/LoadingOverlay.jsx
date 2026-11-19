import React, { useState, useEffect } from 'react';
import './LoadingOverlay.css';

const LoadingOverlay = ({ 
  moduleName = 'Power BI', 
  subText = 'ST-CORE · SMART BIM',
  loadingTip = null, // <-- Added this prop
  isLoading = true,
  onComplete 
}) => {
  const [progress, setProgress] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);

  const defaultTips = [
    'Preparing your construction data...',
    'Loading BIM models...',
    'Connecting to Power BI...',
    'Rendering visualizations...',
    'Almost ready...'
  ];

  // If a custom loadingTip is passed, use it as the only tip
  const tips = loadingTip ? [loadingTip] : defaultTips;

  useEffect(() => {
    if (!isLoading) {
      setProgress(100);
      const timer = setTimeout(() => {
        if (onComplete) onComplete();
      }, 500); 
      return () => clearTimeout(timer);
    }

    setProgress(0);

    // Only rotate tips if we are using the default array
    let tipInterval;
    if (!loadingTip && tips.length > 1) {
      tipInterval = setInterval(() => {
        setTipIndex(prev => (prev + 1) % tips.length);
      }, 2500);
    }

    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) return prev; 
        return prev + 1.5;
      });
    }, 100);

    return () => {
      if (tipInterval) clearInterval(tipInterval);
      clearInterval(progressInterval);
    };
  }, [isLoading, onComplete, loadingTip, tips.length]);

  const isComplete = !isLoading && progress === 100;

  return (
    <div className={`loading-overlay ${isComplete ? 'fade-out' : ''}`}>
      <div className="spinner-container">
        <div className="spinner-ring"></div>
        <div className="spinner-ring inner"></div>
        <div className="spinner"></div>
      </div>
      
      <div className="loading-text">
        Loading <span className="highlight">{moduleName}</span> Module
      </div>
      
      <div className="loading-subtext">{subText}</div>
      
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
      </div>
      
      <div className="loading-tips">{tips[tipIndex]}</div>
    </div>
  );
};

export default LoadingOverlay;