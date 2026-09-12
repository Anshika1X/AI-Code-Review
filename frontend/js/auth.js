/**
 * Authentication management module
 */

const Auth = {
  isAuthenticated() {
    return !!localStorage.getItem('auth_token');
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem('user_info') || '{}');
    } catch {
      return {};
    }
  },

  saveAuth(token, user) {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('user_info', JSON.stringify(user));
  },

  logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
    window.location.href = 'login.html';
  },

  requireAuth() {
    if (!this.isAuthenticated()) {
      window.location.href = 'login.html';
    }
  },

  requireGuest() {
    if (this.isAuthenticated()) {
      window.location.href = 'dashboard.html';
    }
  },

  updateUserUI() {
    const user = this.getUser();
    const nameEls = document.querySelectorAll('.user-name-display');
    const emailEls = document.querySelectorAll('.user-email-display');
    
    nameEls.forEach(el => { el.textContent = user.name || 'Developer'; });
    emailEls.forEach(el => { el.textContent = user.email || ''; });
  }
};

window.Auth = Auth;

// Setup generic logout listeners
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.btn-logout').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      Auth.logout();
    });
  });

  // Mobile sidebar toggler if present
  const sidebarToggleBtn = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.app-sidebar');
  if (sidebarToggleBtn && sidebar) {
    sidebarToggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('show');
    });
  }

  Auth.updateUserUI();
});
