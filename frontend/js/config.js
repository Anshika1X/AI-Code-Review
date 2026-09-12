/**
 * Centralized Application Configuration
 * Provides single point of truth for API endpoint URLs.
 */
const AppConfig = {
  // Check localStorage override first, then window config, then intelligent defaults
  getApiBaseUrl() {
    const customUrl = localStorage.getItem('api_base_url');
    if (customUrl) {
      return customUrl.replace(/\/+$/, '');
    }

    // If frontend is being served directly by Flask backend (same origin)
    if (window.location.port === '5000' || (!window.location.port && window.location.protocol.startsWith('http') && !window.location.hostname.includes('vercel.app'))) {
      return window.location.origin;
    }

    // Default for local development frontend (e.g., Live Server on 5500 / 3000)
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:5000';
    }

    // Production default: Replace this with your deployed Render backend URL or configure via Settings page
    return 'https://ai-code-review-backend.onrender.com';
  },

  setApiBaseUrl(url) {
    if (!url) {
      localStorage.removeItem('api_base_url');
    } else {
      localStorage.setItem('api_base_url', url.trim().replace(/\/+$/, ''));
    }
  }
};

window.AppConfig = AppConfig;
