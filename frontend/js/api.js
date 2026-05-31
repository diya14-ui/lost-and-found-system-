// Primary backend API base (development). Change if your backend runs elsewhere.
const BACKEND_API_BASE = 'http://127.0.0.1:5000/api';

window.API_CONFIG = {
  BASE_URL: BACKEND_API_BASE
};

function getApiBaseUrl() {
  // If the page is served from the backend origin, use same-origin API.
  try {
    if (window.location && window.location.origin && window.location.origin.indexOf(':5000') !== -1) {
      return `${window.location.origin}/api`;
    }
  } catch (e) {
    // ignore
  }

  // Otherwise prefer the configured backend base so Live Server pages call the real API.
  return window.API_CONFIG.BASE_URL;
}

function getCandidateApiBaseUrls() {
  const configured = getApiBaseUrl();
  const candidates = [configured];

  // Auto-fallback between localhost and 127.0.0.1 to avoid host mismatch issues.
  if (configured.includes("localhost")) {
    candidates.push(configured.replace("localhost", "127.0.0.1"));
  } else if (configured.includes("127.0.0.1")) {
    candidates.push(configured.replace("127.0.0.1", "localhost"));
  }

  return [...new Set(candidates)];
}

async function apiRequest(path, options = {}) {
  const bases = getCandidateApiBaseUrls();
  let lastError = null;

  for (const base of bases) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const response = await fetch(`${base}${path}`, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      lastError = error;
    }
  }

  throw lastError || new Error("Unable to connect to API");
}

function getAuthToken() {
  return localStorage.getItem("authToken") || "";
}

function setAuthSession(data) {
  if (!data || !data.token) {
    return;
  }

  localStorage.setItem("authToken", data.token);
  localStorage.setItem("authUser", JSON.stringify(data.user || {}));
}
