const API_BASE = "/api";
const TOKEN_KEY = "compedu_token";

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401 && !endpoint.startsWith("/auth/")) {
    setToken(null);
    window.dispatchEvent(new CustomEvent("compedu:unauthorized"));
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const detail = Array.isArray(errorData.detail)
      ? errorData.detail.map(e => e.msg || JSON.stringify(e)).join("; ")
      : (errorData.detail || `Erro na requisição (${response.status})`);
    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }

  if (response.status === 204) return null;
  return await response.json();
}

function toQuery(params = {}) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== "all") {
      sp.set(k, String(v));
    }
  });
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

const api = {
  getToken,
  setToken,
  getHealth: () => apiRequest("/health"),
  login: (email, password) => apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  }),
  getMe: () => apiRequest("/auth/me"),

  // Painel e auditoria
  getDashboard: () => apiRequest("/dashboard"),
  getAudit: (limit = 100) => apiRequest(`/audit?limit=${limit}`),

  // Anos letivos e turmas
  getAcademicYears: () => apiRequest("/academic-years"),
  createAcademicYear: (data) => apiRequest("/academic-years", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  updateAcademicYear: (yearId, data) => apiRequest(`/academic-years/${yearId}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  getClasses: (params = {}) => apiRequest(`/classes${toQuery(params)}`),
  createClass: (data) => apiRequest("/classes", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  updateClass: (classId, data) => apiRequest(`/classes/${classId}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  getClassReport: (classId) => apiRequest(`/classes/${classId}/report`),

  // Alunos e matrículas
  getStudents: (params = {}) => apiRequest(`/students${toQuery(params)}`),
  getStudent: (studentId) => apiRequest(`/students/${studentId}`),
  createStudent: (data) => apiRequest("/students", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  updateStudent: (studentId, data) => apiRequest(`/students/${studentId}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  enrollStudent: (studentId, classId) => apiRequest(`/students/${studentId}/enrollments`, {
    method: "POST",
    body: JSON.stringify({ class_id: classId })
  }),

  // Registros pedagógicos
  getRecords: (params = {}) => apiRequest(`/records${toQuery(params)}`),
  createRecord: (data) => apiRequest("/records", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  updateRecord: (recordId, data) => apiRequest(`/records/${recordId}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  deleteRecord: (recordId) => apiRequest(`/records/${recordId}`, {
    method: "DELETE"
  }),

  // Mural de comunicados
  getAnnouncements: (params = {}) => apiRequest(`/announcements${toQuery(params)}`),
  createAnnouncement: (data) => apiRequest("/announcements", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  updateAnnouncement: (id, data) => apiRequest(`/announcements/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  deleteAnnouncement: (id) => apiRequest(`/announcements/${id}`, {
    method: "DELETE"
  }),

  // Administração de usuários
  getUsers: () => apiRequest("/admin/users"),
  createUser: (data) => apiRequest("/admin/users", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  updateUser: (userId, data) => apiRequest(`/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  setUserAssignments: (userId, classIds, academicYearId = null) => apiRequest(
    `/admin/users/${userId}/assignments${toQuery({ academic_year_id: academicYearId })}`,
    {
      method: "PUT",
      body: JSON.stringify({ class_ids: classIds })
    }
  )
};
