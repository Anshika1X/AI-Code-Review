/**
 * API Client module for AI Code Review
 * Handles HTTP requests, JWT injection, response parsing, and error toasts.
 */

// Toast notification display helper
function showToast(message, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast-custom ${type === 'error' ? 'error' : ''}`;
  
  const icon = type === 'error' ? '⚠️' : '✅';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.4s ease';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

const apiClient = {
  async request(endpoint, options = {}) {
    const baseUrl = window.AppConfig ? window.AppConfig.getApiBaseUrl() : 'http://localhost:5000';
    const url = `${baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = localStorage.getItem('auth_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json().catch(() => ({}));

      // Handle 401 Unauthorized globally
      if (response.status === 401) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        
        const currentPath = window.location.pathname;
        if (!currentPath.includes('login.html') && !currentPath.includes('register.html') && !currentPath.endsWith('/') && !currentPath.includes('index.html')) {
          showToast('Session expired. Please log in again.', 'error');
          setTimeout(() => {
            window.location.href = 'login.html';
          }, 1200);
        }
        throw new Error(data.error || 'Authentication required');
      }

      if (!response.ok) {
        throw new Error(data.error || `HTTP error ${response.status}`);
      }

      return data;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        const errorMsg = `Cannot connect to backend at ${baseUrl}. Please check if the server is running.`;
        showToast(errorMsg, 'error');
        throw new Error(errorMsg);
      }
      throw err;
    }
  },

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
};

window.apiClient = apiClient;
window.showToast = showToast;
