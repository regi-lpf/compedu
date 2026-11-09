const API_BASE = "/api";

async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("compedu_token");
  
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Erro na requisição: ${response.status}`);
    }

    // Se a resposta for 204 No Content
    if (response.status === 204) return null;
    
    return await response.json();
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

// Funções de consumo específicas
const api = {
  getHealth: () => apiRequest("/health"),
  login: (email, password) => apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  }),
  getMe: () => apiRequest("/auth/me"),
  getClasses: () => apiRequest("/classes"),
  getStudents: () => apiRequest("/students"),
  getRecords: () => apiRequest("/records"),
  createRecord: (data) => apiRequest("/records", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  getAnnouncements: () => apiRequest("/announcements", {
    method: "GET"
  }),
  createAnnouncement: (data) => apiRequest("/announcements", {
    method: "POST",
    body: JSON.stringify(data)
  })
};