(function () {
  const ADMIN_TOKEN_KEY = 'adminAuthToken';
  const IS_FLASK_ADMIN_ROUTE = window.location.pathname.toLowerCase().startsWith('/admin/');
  const DASHBOARD_URL = IS_FLASK_ADMIN_ROUTE ? '/admin/dashboard' : 'admin-dashboard.html';
  const LOGIN_URL = IS_FLASK_ADMIN_ROUTE ? '/admin/login' : 'admin-login.html';

  function getAdminToken() {
    return localStorage.getItem(ADMIN_TOKEN_KEY) || sessionStorage.getItem(ADMIN_TOKEN_KEY) || '';
  }

  function setAdminToken(token, remember) {
    if (remember) {
      localStorage.setItem(ADMIN_TOKEN_KEY, token);
      sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    } else {
      sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
      localStorage.removeItem(ADMIN_TOKEN_KEY);
    }
  }

  function clearAdminToken() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  }

  function redirectToLogin() {
    if (window.location.pathname.toLowerCase().indexOf('admin-login.html') === -1) {
      window.location.href = LOGIN_URL;
    }
  }

  function redirectToDashboard() {
    if (window.location.pathname.toLowerCase().indexOf('admin-dashboard.html') === -1) {
      window.location.href = DASHBOARD_URL;
    }
  }

  async function api(path, options = {}) {
    const headers = Object.assign({}, options.headers || {});
    const token = getAdminToken();

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    if (typeof apiRequest === 'function') {
      return apiRequest(path.replace(/^\/api/, ''), Object.assign({}, options, { headers }));
    }

    return fetch(`${getApiBaseUrl().replace(/\/api$/, '')}${path}`, Object.assign({}, options, { headers }));
  }

  async function readApiJson(response) {
    try {
      return await response.json();
    } catch (error) {
      return { success: false, message: 'Invalid API response format' };
    }
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function refreshIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function setFormMessage(target, message, type) {
    if (!target) return;
    target.textContent = message;
    target.className = type ? `form-note ${type}` : 'form-note';
  }

  function setDashboardStatus(message, type = 'info') {
    const dashboard = document.querySelector('.admin-dashboard-page');
    if (!dashboard) return;

    let statusEl = document.getElementById('adminDashboardStatus');
    if (!statusEl) {
      const topbar = document.querySelector('.topbar');
      if (!topbar) return;
      statusEl = document.createElement('div');
      statusEl.id = 'adminDashboardStatus';
      statusEl.style.marginTop = '10px';
      statusEl.style.fontSize = '0.92rem';
      topbar.appendChild(statusEl);
    }

    const palette = {
      info: '#c8d2ff',
      success: '#87f3c3',
      error: '#ffb3c2'
    };

    statusEl.textContent = message || '';
    statusEl.style.color = palette[type] || palette.info;
  }

  async function handleAdminLogin(form) {
    const emailInput = form.querySelector('#adminEmail');
    const passwordInput = form.querySelector('#adminPassword');
    const rememberInput = form.querySelector('#rememberAdmin');
    const statusEl = form.querySelector('#adminLoginError');
    const submitBtn = form.querySelector('#adminLoginBtn');
    const originalLabel = submitBtn ? submitBtn.innerHTML : '';

    if (passwordInput) {
      passwordInput.addEventListener('copy', (event) => event.preventDefault());
      passwordInput.addEventListener('cut', (event) => event.preventDefault());
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      const email = (emailInput?.value || '').trim();
      const password = passwordInput?.value || '';
      const remember = Boolean(rememberInput?.checked);

      if (!email || !password) {
        setFormMessage(statusEl, 'Please enter email and password.', 'error');
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>Signing in...</span>';
      }

      try {
        const response = await api('/api/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        const result = await readApiJson(response);

        if (!response.ok || !result.success) {
          setFormMessage(statusEl, result.message || 'Login failed.', 'error');
          return;
        }

        setAdminToken(result.data.token, remember);
        setFormMessage(statusEl, 'Login successful. Redirecting...', 'success');
        setTimeout(redirectToDashboard, 280);
      } catch (error) {
        setFormMessage(statusEl, 'Could not connect to backend. Please start the API server.', 'error');
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalLabel;
        }
      }
    });
  }

  function renderBadge(value) {
    const normalized = String(value || '').toLowerCase();
    return `<span class="badge ${normalized}">${escapeHtml(value || 'pending')}</span>`;
  }

  function getEffectiveItemStatus(item) {
    const raw = String(item?.status || '').toLowerCase();
    if (raw === 'pending' || raw === 'approved' || raw === 'rejected' || raw === 'resolved') {
      return raw;
    }
    return item?.is_approved ? 'approved' : 'pending';
  }

  function bindNav() {
    document.querySelectorAll('.nav-link').forEach((link) => {
      link.addEventListener('click', (event) => {
        event.preventDefault();
        const target = link.getAttribute('href') || '#dashboard';

        document.querySelectorAll('.nav-link').forEach((item) => item.classList.remove('active'));
        link.classList.add('active');

        document.querySelectorAll('.content-section').forEach((section) => section.classList.add('hidden'));
        const activeSection = document.querySelector(target);
        if (activeSection) activeSection.classList.remove('hidden');
      });
    });
  }

  function wireItemFilter() {
    const filter = document.getElementById('filterApproval');
    if (!filter) return;

    const applyFilter = () => {
      const value = filter.value;
      document.querySelectorAll('#itemsTable tbody tr').forEach((row) => {
        const badge = row.querySelector('.badge');
        const statusText = badge ? badge.textContent.trim().toLowerCase() : '';

        if (value === 'all') {
          row.style.display = '';
          return;
        }

        row.style.display = value === '0'
          ? (statusText === 'pending' ? '' : 'none')
          : (statusText === 'approved' ? '' : 'none');
      });
    };

    filter.addEventListener('change', applyFilter);
    document.addEventListener('admin:items-updated', applyFilter);
  }

  async function loadDashboardSummary() {
    const response = await api('/api/admin/dashboard', { method: 'GET' });
    if (response.status === 401 || response.status === 403) {
      clearAdminToken();
      redirectToLogin();
      return null;
    }

    const result = await readApiJson(response);
    if (!response.ok || !result.success) {
      throw new Error(result.message || 'Unable to load dashboard');
    }

    return result.data || {};
  }

  async function loadAdminSession() {
    const response = await api('/api/admin/me', { method: 'GET' });
    if (response.status === 401 || response.status === 403) {
      clearAdminToken();
      redirectToLogin();
      return null;
    }

    const result = await readApiJson(response);
    if (!response.ok || !result.success) {
      throw new Error(result.message || 'Unable to validate admin session');
    }

    return result.data || null;
  }

  function renderChart(container, values, labels) {
    if (!container) return;
    const maxValue = Math.max(...values, 1);
    container.innerHTML = values.map((value, index) => {
      const height = Math.max(20, Math.round((value / maxValue) * 100) + 18);
      return `<div class="chart-bar" style="height:${height}%"><span>${escapeHtml(labels[index] || '')}</span></div>`;
    }).join('');
  }

  function renderFeed(container, entries) {
    if (!container) return;
    container.innerHTML = entries.map((entry) => `
      <article class="activity-entry">
        <h4>${escapeHtml(entry.title)}</h4>
        <p>${escapeHtml(entry.body)}</p>
      </article>
    `).join('');
  }

  async function loadItemsTable() {
    const response = await api('/api/admin/items', { method: 'GET' });
    if (response.status === 401 || response.status === 403) {
      clearAdminToken();
      redirectToLogin();
      return;
    }

    const result = await readApiJson(response);
    if (!response.ok || !result.success) return;

    const rows = Array.isArray(result.data?.items) ? result.data.items : [];
    const tbody = document.querySelector('#itemsTable tbody');
    if (!tbody) return;

    tbody.innerHTML = rows.map((item) => `
      <tr>
        <td>${item.id}</td>
        <td>${escapeHtml(item.item_type)}</td>
        <td>${escapeHtml(item.item_name)}</td>
        <td>${escapeHtml(item.reporter_email || '')}</td>
        <td>${renderBadge(getEffectiveItemStatus(item))}</td>
        <td>
          <div class="action-row">
            <button class="table-btn primary" data-action="approve-item" data-id="${item.id}">Approve</button>
            <button class="table-btn danger" data-action="reject-item" data-id="${item.id}">Reject</button>
            <button class="table-btn danger" data-action="delete-item" data-id="${item.id}">Delete</button>
            <button class="table-btn" data-action="resolve-item" data-id="${item.id}">Resolve</button>
          </div>
        </td>
      </tr>
    `).join('');

    document.dispatchEvent(new CustomEvent('admin:items-updated'));
  }

  async function loadClaimsTable() {
    const response = await api('/api/admin/claims', { method: 'GET' });
    if (response.status === 401 || response.status === 403) {
      clearAdminToken();
      redirectToLogin();
      return;
    }

    const result = await readApiJson(response);
    if (!response.ok || !result.success) return;

    const rows = Array.isArray(result.data) ? result.data : [];
    const tbody = document.querySelector('#claimsTable tbody');
    if (!tbody) return;

    tbody.innerHTML = rows.map((claim) => `
      <tr>
        <td>${claim.id}</td>
        <td>${claim.item_id}</td>
        <td>${escapeHtml(claim.claimant_name || 'Unknown')}</td>
        <td>${escapeHtml(claim.contact_number || '')}</td>
        <td>${renderBadge(claim.status)}</td>
        <td>
          <div class="action-row">
            <button class="table-btn primary" data-action="approve-claim" data-id="${claim.id}">Approve</button>
            <button class="table-btn danger" data-action="reject-claim" data-id="${claim.id}">Reject</button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  async function loadUsersTable() {
    const response = await api('/api/admin/users', { method: 'GET' });
    if (response.status === 401 || response.status === 403) {
      clearAdminToken();
      redirectToLogin();
      return;
    }

    const result = await readApiJson(response);
    if (!response.ok || !result.success) return;

    const rows = Array.isArray(result.data) ? result.data : [];
    const tbody = document.querySelector('#usersTable tbody');
    if (!tbody) return;

    tbody.innerHTML = rows.map((user) => `
      <tr>
        <td>${user.id}</td>
        <td>${escapeHtml(user.name)}</td>
        <td>${escapeHtml(user.email)}</td>
        <td>${escapeHtml(user.student_id || '')}</td>
        <td>${escapeHtml((user.role || (user.is_admin ? 'admin' : 'student')).toString())}</td>
        <td>${renderBadge(user.is_banned ? 'rejected' : 'approved')}</td>
        <td>
          <div class="action-row">
            <button class="table-btn" data-action="ban-user" data-id="${user.id}">Ban</button>
            <button class="table-btn danger" data-action="delete-user" data-id="${user.id}">Delete</button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  function wireTableActions() {
    document.addEventListener('click', async (event) => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;

      const action = button.getAttribute('data-action');
      const id = button.getAttribute('data-id');
      if (!action || !id) return;

      const methodMap = {
        'approve-item': {
          method: 'POST',
          paths: [`/api/admin/items/${id}/approve`, '/api/admin/approve-item'],
          bodyByPath: {
            '/api/admin/approve-item': { item_id: Number(id) }
          }
        },
        'reject-item': {
          method: 'POST',
          paths: [`/api/admin/items/${id}/reject`, '/api/admin/reject-item'],
          bodyByPath: {
            [`/api/admin/items/${id}/reject`]: { reason: 'Removed by moderation' },
            '/api/admin/reject-item': { item_id: Number(id), reason: 'Removed by moderation' }
          }
        },
        'delete-item': { method: 'DELETE', path: '/api/admin/delete-item', body: { item_id: Number(id) } },
        'resolve-item': { method: 'POST', path: `/api/admin/items/${id}/resolve` },
        'approve-claim': { method: 'POST', path: `/api/admin/claims/${id}/approve` },
        'reject-claim': { method: 'POST', path: `/api/admin/claims/${id}/reject`, body: { reason: 'Rejected by admin' } },
        'ban-user': { method: 'POST', path: `/api/admin/users/${id}/ban` },
        'delete-user': { method: 'DELETE', path: `/api/admin/users/${id}` }
      };

      const config = methodMap[action];
      if (!config) return;

      button.disabled = true;
      try {
        const paths = config.paths || [config.path];
        let lastError = null;
        let success = false;

        for (const path of paths) {
          const body = (config.bodyByPath && config.bodyByPath[path]) || config.body;
          const response = await api(path, {
            method: config.method,
            headers: body ? { 'Content-Type': 'application/json' } : {},
            body: body ? JSON.stringify(body) : undefined
          });

          const result = await readApiJson(response);
          if (response.ok && result.success) {
            success = true;
            break;
          }

          lastError = new Error(result.message || 'Action failed');
          if (response.status !== 404) {
            break;
          }
        }

        if (!success) {
          throw (lastError || new Error('Action failed'));
        }

        await bootstrapDashboard();
        setDashboardStatus('Action completed successfully.', 'success');
      } catch (error) {
        setDashboardStatus(error.message || 'Could not complete admin action.', 'error');
        window.alert(error.message || 'Could not complete admin action.');
      } finally {
        button.disabled = false;
      }
    });
  }

  function wireGlobalSearch() {
    const searchInput = document.getElementById('globalSearch');
    if (!searchInput) return;

    const filterVisibleRows = () => {
      const query = (searchInput.value || '').trim().toLowerCase();
      document.querySelectorAll('.data-table tbody tr').forEach((row) => {
        const haystack = row.textContent.toLowerCase();
        row.style.display = haystack.includes(query) ? '' : 'none';
      });
    };

    searchInput.addEventListener('input', filterVisibleRows);
  }

  function wireSidebarLogout() {
    const logoutBtn = document.getElementById('btnLogout');
    if (!logoutBtn) return;

    logoutBtn.addEventListener('click', () => {
      clearAdminToken();
      redirectToLogin();
    });
  }

  function wireRefreshButtons() {
    const refreshItems = document.getElementById('refreshItems');
    const refreshClaims = document.getElementById('refreshClaims');
    const refreshUsers = document.getElementById('refreshUsers');
    const reload = document.getElementById('btnReload');

    const refreshAll = async () => {
      await bootstrapDashboard();
    };

    if (refreshItems) refreshItems.addEventListener('click', refreshAll);
    if (refreshClaims) refreshClaims.addEventListener('click', refreshAll);
    if (refreshUsers) refreshUsers.addEventListener('click', refreshAll);
    if (reload) reload.addEventListener('click', refreshAll);
  }

  function wireAuthPage() {
    const form = document.getElementById('adminLoginForm');
    if (!form) return;

    handleAdminLogin(form);
  }

  async function bootstrapDashboard() {
    const dashboard = document.querySelector('.admin-dashboard-page');
    if (!dashboard) return;

    const token = getAdminToken();
    if (!token) {
      redirectToLogin();
      return;
    }

    try {
      const session = await loadAdminSession();
      if (!session) return;
      const summary = await loadDashboardSummary();
      if (!summary) return;

      const stats = {
        totalItems: summary.totalItems ?? 0,
        users: summary.totalUsers || 0,
        pendingItems: summary.pendingItems ?? 0,
        approvedItems: summary.approvedItems ?? 0,
        rejectedItems: summary.rejectedItems ?? 0,
        pendingClaims: summary.pendingClaims ?? 0,
        resolvedItems: summary.resolvedItems ?? 0
      };

      const statTotalItems = document.getElementById('statTotalItems');
      const statUsers = document.getElementById('statUsers');
      const statPendingItems = document.getElementById('statPendingItems');
      const statApprovedItems = document.getElementById('statApprovedItems');
      const statRejectedItems = document.getElementById('statRejectedItems');
      const statPendingClaims = document.getElementById('statPendingClaims');
      const statResolvedItems = document.getElementById('statResolvedItems');

      if (statTotalItems) statTotalItems.textContent = String(stats.totalItems);
      if (statUsers) statUsers.textContent = String(stats.users);
      if (statPendingItems) statPendingItems.textContent = String(stats.pendingItems);
      if (statApprovedItems) statApprovedItems.textContent = String(stats.approvedItems);
      if (statRejectedItems) statRejectedItems.textContent = String(stats.rejectedItems);
      if (statPendingClaims) statPendingClaims.textContent = String(stats.pendingClaims);
      if (statResolvedItems) statResolvedItems.textContent = String(stats.resolvedItems);

      const trendRows = Array.isArray(summary.moderationTrend) ? summary.moderationTrend : [];
      const trendValues = trendRows.map((row) => Number(row.items || 0) + Number(row.claims || 0));
      const trendLabels = trendRows.map((row) => {
        const day = new Date(row.day);
        return Number.isNaN(day.getTime()) ? String(row.day || '') : day.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      });

      if (trendValues.length > 0) {
        renderChart(document.getElementById('miniChart'), trendValues, trendLabels);
      } else {
        renderChart(document.getElementById('miniChart'), [0], ['No data']);
      }

      const recentActivity = Array.isArray(summary.recentActivity) ? summary.recentActivity : [];
      renderFeed(
        document.getElementById('activityFeed'),
        recentActivity.length > 0
          ? recentActivity.map((entry) => ({ title: entry.title || 'Activity', body: entry.body || 'Update recorded.' }))
          : [{ title: 'No recent moderation events', body: 'New moderation actions will appear here as soon as they happen.' }]
      );

      renderFeed(document.getElementById('reportsList'), [
        { title: 'Spam / duplicate posts', body: 'Review items flagged by staff or users.' },
        { title: 'Policy violations', body: 'Handle reports of inappropriate or fake submissions.' }
      ]);

      renderFeed(document.getElementById('notificationList'), [
        { title: 'Claim approval notifications', body: 'Users receive updates when their claim is approved or rejected.' },
        { title: 'Item removal alerts', body: 'Users are notified when a post is removed by moderation.' }
      ]);

      setDashboardStatus('Live data loaded from database.', 'success');
    } catch (error) {
      console.error('Admin dashboard load error:', error);
      setDashboardStatus(error.message || 'Could not load dashboard data from backend.', 'error');
    }

    await Promise.allSettled([
      loadItemsTable(),
      loadClaimsTable(),
      loadUsersTable()
    ]);

    refreshIcons();
  }

  document.addEventListener('DOMContentLoaded', async () => {
    refreshIcons();
    wireAuthPage();
    bindNav();
    wireItemFilter();
    wireTableActions();
    wireGlobalSearch();
    wireSidebarLogout();
    wireRefreshButtons();

    if (document.querySelector('.admin-dashboard-page')) {
      await bootstrapDashboard();
    }
  });
})();