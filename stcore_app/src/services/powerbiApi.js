// Use port 8000 for FastAPI backend
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

// Simple cache for embed configs
const embedConfigCache = new Map();
const pendingRequests = new Map();

export const powerbiApi = {
  /**
   * Fetch embed configuration for Power BI report
   * Matches your FastAPI endpoint: /api/powerbi/embed-config
   * @param {string} reportId - Optional specific report ID
   * @param {boolean} forceRefresh - Force refresh the cache
   * @returns {Promise<Object>} Embed config with token, URL, and report ID
   */
  async getEmbedConfig(reportId = null, forceRefresh = false) {
    const cacheKey = reportId || 'default';
    
    // Check if we have a pending request for this report
    if (pendingRequests.has(cacheKey)) {
      console.log('⏳ Waiting for pending request for:', cacheKey);
      return pendingRequests.get(cacheKey);
    }
    
    // Check cache
    if (!forceRefresh && embedConfigCache.has(cacheKey)) {
      const cached = embedConfigCache.get(cacheKey);
      // Check if token is still valid (within 50 minutes of 1 hour expiry)
      if (cached && cached._timestamp && (Date.now() - cached._timestamp) < 50 * 60 * 1000) {
        console.log('✅ Using cached embed config for:', cacheKey);
        return cached;
      }
    }
    
    // Create a new request
    const requestPromise = (async () => {
      try {
        // Use your FastAPI endpoint on port 8000
        let url = `${API_BASE}/api/powerbi/embed-config`;
        if (reportId) {
          url += `?report_id=${reportId}`;
        }
        
        console.log('📡 Fetching embed config from:', url);
        
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}: Failed to fetch embed config`);
        }

        const data = await response.json();
        
        // Validate response - matches your FastAPI response structure
        if (!data.embedToken) {
          throw new Error('Valid Embed Token was missing from API response');
        }
        if (!data.embedUrl) {
          throw new Error('Embed URL was missing from API response');
        }
        if (!data.reportId) {
          throw new Error('Report ID was missing from API response');
        }

        // Add timestamp to cache
        data._timestamp = Date.now();
        
        // Store in cache
        embedConfigCache.set(cacheKey, data);
        
        console.log('✅ Embed config received and cached:', {
          reportId: data.reportId,
          hasToken: !!data.embedToken,
          embedUrl: data.embedUrl.substring(0, 100) + '...'
        });
        
        return data;
      } catch (error) {
        console.error('❌ Failed to fetch embed config:', error);
        throw error;
      } finally {
        // Remove from pending requests
        pendingRequests.delete(cacheKey);
      }
    })();
    
    // Store the pending request
    pendingRequests.set(cacheKey, requestPromise);
    
    return requestPromise;
  },

  /**
   * Clear the embed config cache
   * @param {string} reportId - Specific report ID to clear, or null for all
   */
  clearCache(reportId = null) {
    if (reportId) {
      const cacheKey = reportId;
      embedConfigCache.delete(cacheKey);
      console.log('🗑️ Cleared cache for:', cacheKey);
    } else {
      embedConfigCache.clear();
      console.log('🗑️ Cleared all embed config cache');
    }
  },

  /**
   * Refresh embed token - calls your FastAPI endpoint again
   * @param {string} reportId - Report ID
   * @returns {Promise<Object>} New embed config
   */
  async refreshEmbedToken(reportId) {
    try {
      // Clear cache for this report to force refresh
      const cacheKey = reportId || 'default';
      embedConfigCache.delete(cacheKey);
      
      // Fetch fresh config
      return await this.getEmbedConfig(reportId, true);
    } catch (error) {
      console.error('❌ Failed to refresh embed token:', error);
      throw error;
    }
  }
};