(function () {
  function isAuthed() {
    return Boolean(localStorage.getItem('authToken') || sessionStorage.getItem('authToken'));
  }

  function getStoredUser() {
    try {
      const raw = localStorage.getItem('authUser') || sessionStorage.getItem('authUser');
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function clearAuth() {
    ['authToken', 'authUser', 'userLoggedIn', 'profileImageUrl'].forEach(function (key) {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    });
  }

  function logout() {
    clearAuth();
    window.location.href = resolvePath('login.html');
  }

  function resolvePath(target) {
    // Pages at the repo root (item-detail.html, claim.html) point inside frontend/.
    const path = (window.location.pathname || '').toLowerCase();
    const insideFrontend = path.indexOf('/frontend/') !== -1
      || /\/(index|lost|found|post|login|signup|profile|help|contact|forgot-password|claim)\.html$/.test(path);
    return insideFrontend ? target : 'frontend/' + target;
  }

  function renderNavAuth() {
    const right = document.querySelector('.navbar-right');
    if (!right) return;

    const filename = (window.location.pathname.split('/').pop() || '').toLowerCase();
    if (filename === 'login.html' || filename === 'signup.html' || filename === 'forgot-password.html') {
      return;
    }

    const lost = resolvePath('post.html?type=lost');
    const found = resolvePath('post.html?type=found');
    const profile = resolvePath('profile.html');
    const login = resolvePath('login.html');

    if (isAuthed()) {
      right.innerHTML =
        '<a href="' + lost + '" class="btn-report"><i data-lucide="clipboard-list" class="icon"></i><span>Report Lost</span></a>' +
        '<a href="' + found + '" class="btn-report"><i data-lucide="check-circle-2" class="icon"></i><span>Report Found</span></a>' +
        '<a href="' + profile + '" class="btn-auth"><i data-lucide="user" class="icon"></i><span>Profile</span></a>' +
        '<button type="button" class="btn-logout" data-action="logout"><i data-lucide="log-out" class="icon"></i><span>Logout</span></button>';
    } else {
      right.innerHTML =
        '<a href="' + lost + '" class="btn-report"><i data-lucide="clipboard-list" class="icon"></i><span>Report Lost</span></a>' +
        '<a href="' + found + '" class="btn-report"><i data-lucide="check-circle-2" class="icon"></i><span>Report Found</span></a>' +
        '<a href="' + login + '" class="btn-auth"><i data-lucide="log-in" class="icon"></i><span>Login / Register</span></a>';
    }

    const logoutBtn = right.querySelector('[data-action="logout"]');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', logout);
    }
  }

  function refreshIcons(root) {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons({ icons: window.lucide.icons, attrs: {}, nameAttr: 'data-lucide' });
    }
  }

  window.__lfRefreshIcons = refreshIcons;
  window.__lfLogout = logout;

  document.addEventListener('DOMContentLoaded', function () {
    renderNavAuth();
    refreshIcons();
  });
})();
