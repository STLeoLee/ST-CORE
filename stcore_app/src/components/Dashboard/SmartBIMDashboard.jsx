// src/components/SmartBIMDashboard/SmartBIMDashboard.jsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
import './SmartBIMDashboard.css';

/**
 * Loads the APS Viewer SDK from the CDN and resolves when window.Autodesk is ready.
 */
function loadViewerSdk() {
  return new Promise((resolve, reject) => {
    if (window.Autodesk?.Viewing) {
      resolve();
      return;
    }

    const VERSION = '7.*';
    const BASE = `https://developer.api.autodesk.com/modelderivative/v2/viewers/${VERSION}`;

    if (!document.querySelector('link[data-aps-viewer]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = `${BASE}/style.min.css`;
      link.setAttribute('data-aps-viewer', 'true');
      document.head.appendChild(link);
    }

    if (!document.querySelector('script[data-aps-viewer]')) {
      const script = document.createElement('script');
      script.src = `${BASE}/viewer3D.min.js`;
      script.setAttribute('data-aps-viewer', 'true');
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load APS Viewer SDK'));
      document.head.appendChild(script);
    } else {
      // Script tag exists but may still be loading — poll briefly
      const poll = setInterval(() => {
        if (window.Autodesk?.Viewing) {
          clearInterval(poll);
          resolve();
        }
      }, 50);
    }
  });
}

/**
 * Convert "#rrggbb" -> THREE.Vector4(r, g, b, 1) with 0..1 components.
 * Uses the global THREE bundled with the APS Viewer (no npm three import needed).
 */
function hexToVector4(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return new window.THREE.Vector4(r, g, b, 1.0);
}

const SmartBIMDashboard = ({
  accessToken,   // string: short-lived APS access token
  modelUrn,      // string: Data Exchange URN (no "urn:" prefix)
}) => {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const selectionRef = useRef([]);

  const [selectedCount, setSelectedCount] = useState(0);
  const [color, setColor] = useState('#ff5722');
  const [status, setStatus] = useState('Loading viewer…');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let disposed = false;

    const init = async () => {
      try {
        await loadViewerSdk();
        if (disposed || !containerRef.current) return;

        const Autodesk = window.Autodesk;

        // SVF2 config — use AutodeskProduction2 + streamingV2 for SVF2 models.
        // If your Data Exchange is legacy SVF, switch to:
        //   env: 'AutodeskProduction', api: 'derivativeV2'
        const options = {
          env: 'AutodeskProduction2',
          api: 'streamingV2',
          getAccessToken: (onTokenReady) => {
            onTokenReady(accessToken, 3600);
          },
        };

        Autodesk.Viewing.Initializer(options, () => {
          if (disposed) return;

          const viewer = new Autodesk.Viewing.GuiViewer3D(containerRef.current, {
            extensions: ['Autodesk.DocumentBrowser'],
          });
          viewer.start();
          viewerRef.current = viewer;

          // Track selection
          const onSelection = (event) => {
            selectionRef.current = event.dbIdArray || [];
            setSelectedCount(selectionRef.current.length);
          };
          viewer.addEventListener(
            Autodesk.Viewing.SELECTION_CHANGED_EVENT,
            onSelection
          );

          // Enable recolor controls only after geometry is fully loaded.
          const onGeometryLoaded = () => {
            setStatus('Model loaded — select features to recolor');
            setReady(true);
          };
          viewer.addEventListener(
            Autodesk.Viewing.GEOMETRY_LOADED_EVENT,
            onGeometryLoaded
          );

          // Load the model
          Autodesk.Viewing.Document.load(
            `urn:${modelUrn}`,
            (doc) => {
              const viewable = doc.getRoot().getDefaultGeometry();
              viewer
                .loadDocumentNode(doc, viewable)
                .catch((err) => {
                  console.error(err);
                  setStatus('Failed to load model geometry');
                });
            },
            (code, msg) => {
              console.error('Document.load failed', code, msg);
              setStatus(`Model load error (${code})`);
            }
          );
        });
      } catch (err) {
        console.error(err);
        setStatus('Failed to initialize viewer');
      }
    };

    init();

    return () => {
      disposed = true;
      if (viewerRef.current) {
        try {
          viewerRef.current.finish();
        } catch {
          /* ignore */
        }
        viewerRef.current = null;
      }
    };
    // Re-init only if credentials change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, modelUrn]);

  const applyColor = useCallback(() => {
    const viewer = viewerRef.current;
    if (!viewer || selectionRef.current.length === 0) return;
    const vec = hexToVector4(color);
    selectionRef.current.forEach((dbId) => viewer.setThemingColor(dbId, vec));
    setStatus(`Applied ${color} to ${selectionRef.current.length} feature(s)`);
  }, [color]);

  const clearColor = useCallback(() => {
    const viewer = viewerRef.current;
    if (!viewer || selectionRef.current.length === 0) return;
    selectionRef.current.forEach((dbId) => viewer.setThemingColor(dbId, null));
    setStatus(`Cleared color on ${selectionRef.current.length} feature(s)`);
  }, []);

  const clearAll = useCallback(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.clearThemingColors();
    setStatus('Cleared all color overrides');
  }, []);

  return (
    <div className="smart-bim-dashboard">
      <div ref={containerRef} className="sbd-canvas" />

      <div className="sbd-panel">
        <h3>Feature Color</h3>
        <label htmlFor="sbd-color">Color</label>
        <input
          id="sbd-color"
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
        />

        <button onClick={applyColor} disabled={!ready || selectedCount === 0}>
          Apply to Selected ({selectedCount})
        </button>
        <button
          onClick={clearColor}
          className="sbd-secondary"
          disabled={!ready || selectedCount === 0}
        >
          Clear Selected
        </button>
        <button onClick={clearAll} className="sbd-secondary" disabled={!ready}>
          Clear All Colors
        </button>

        <p className="sbd-status">{status}</p>
      </div>
    </div>
  );
};

export default SmartBIMDashboard;