// Estado da aplicação sincronizado com a API FastAPI
let currentUser = null;
let classes = [];
let students = [];
let records = [];
let announcements = [];
let usersList = [];
let academicYears = [];
let dashboardData = null;

let selectedClass = null;
let selectedStudent = null;
let currentView = "comunicados";

const ROLE_LABELS = {
  admin: "Administrador",
  coordination: "Coordenação",
  teacher: "Professor(a)",
  secretary: "Secretaria",
  support: "Suporte técnico"
};

const ROLE_DEFAULT_LEVEL = {
  admin: 1,
  coordination: 2,
  teacher: 3,
  secretary: 4,
  support: 5
};

const RECORD_TYPE_LABELS = {
  positive: "Positivo",
  attention: "Atenção",
  follow_up: "Acompanhamento"
};

const LEVEL_DESCRIPTIONS = {
  1: "Nível 1 — Direção / Administração",
  2: "Nível 2 — Coordenação e encaminhamentos",
  3: "Nível 3 — Padrão docente",
  4: "Nível 4 — Administrativo e operacional",
  5: "Nível 5 — Geral / todas as equipes"
};

const viewInfo = {
  inicio: ["Painel", "Visão geral", "O que precisa de atenção agora no seu escopo."],
  turmas: ["Turmas", "Turmas", "Acesse uma turma e depois o histórico de cada aluno."],
  registros: ["Registros", "Lista de registros", "Filtre por turma, tipo de registro ou aluno."],
  comunicados: ["Mural", "Mural interno", "Informações compartilhadas com as equipes da escola."],
  administracao: ["Cadastros", "Cadastros da escola", "Gerencie alunos, matrículas, profissionais, turmas e anos letivos."],
  auditoria: ["Auditoria", "Trilha de auditoria", "Histórico técnico de operações realizadas no sistema."]
};

// ---------- Utilitários ----------
function initials(name) {
  return (name || "?")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(p => p[0])
    .join("")
    .toUpperCase();
}

function badgeClass(recordType) {
  if (recordType === "positive") return "good";
  if (recordType === "attention") return "warn";
  return "neutral";
}

function recordTypeLabel(recordType) {
  return RECORD_TYPE_LABELS[recordType] || recordType;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

function formatDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}

function formatCouncilDate(value) {
  if (!value) return "Data não definida";
  const [y, m, d] = value.split("-").map(Number);
  const months = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
  ];
  return `${d} de ${months[m - 1]} de ${y}`;
}

function showFeedback(message, isError = false) {
  const box = document.getElementById("global-feedback");
  if (!message) {
    box.classList.add("hidden");
    box.textContent = "";
    return;
  }
  box.textContent = message;
  box.classList.toggle("error", isError);
  box.classList.remove("hidden");
  setTimeout(() => {
    if (box.textContent === message) box.classList.add("hidden");
  }, 5000);
}

// ---------- Permissões de interface (a segurança real está no backend) ----------
function canReadRecords() {
  return currentUser && ["admin", "coordination", "teacher"].includes(currentUser.role);
}
function canWriteRecords() {
  return currentUser && ["admin", "coordination", "teacher"].includes(currentUser.role);
}
function canWriteAnnouncements() {
  return Boolean(currentUser);
}
function canViewClassesAndStudents() {
  return currentUser && ["admin", "coordination", "teacher", "secretary"].includes(currentUser.role);
}
function canManageEnrollments() {
  return currentUser && ["admin", "secretary"].includes(currentUser.role);
}
function isAdmin() {
  return currentUser && currentUser.role === "admin";
}
function canEditCouncilDate() {
  return currentUser && ["admin", "coordination"].includes(currentUser.role);
}
function canViewAudit() {
  return currentUser && ["admin", "support"].includes(currentUser.role);
}

// ---------- Autenticação e inicialização ----------
async function setupLoginScreen() {
  document.getElementById("login-screen").classList.remove("hidden");
  document.getElementById("app-shell").classList.add("hidden");
  document.getElementById("profile-popover").classList.add("hidden");

  try {
    const cfg = await api.getAuthConfig();
    const devForm = document.getElementById("dev-login-form");
    const googleSec = document.getElementById("google-login-section");

    devForm.classList.toggle("hidden", !cfg.dev_login_enabled);
    document.getElementById("dev-login-divider").classList.toggle("hidden", !cfg.dev_login_enabled);

    if (cfg.google_client_id) {
      googleSec.classList.remove("hidden");
      if (cfg.allowed_domain) {
        document.getElementById("google-domain-hint").textContent =
          `Use seu e-mail institucional @${cfg.allowed_domain}`;
      }
      loadGoogleIdentityScript(cfg.google_client_id);
    } else {
      googleSec.classList.add("hidden");
    }
  } catch (err) {
    document.getElementById("dev-login-form").classList.add("hidden");
    document.getElementById("dev-login-divider").classList.add("hidden");
    document.getElementById("google-login-section").classList.add("hidden");
    showLoginError("Não foi possível carregar as opções de login.");
  }
}

function loadGoogleIdentityScript(clientId) {
  if (window.google?.accounts?.id) {
    renderGoogleButton(clientId);
    return;
  }
  const existing = document.getElementById("gsi-client-script");
  if (existing) return;
  const script = document.createElement("script");
  script.id = "gsi-client-script";
  script.src = "https://accounts.google.com/gsi/client";
  script.async = true;
  script.defer = true;
  script.onload = () => renderGoogleButton(clientId);
  document.head.appendChild(script);
}

function renderGoogleButton(clientId) {
  if (!window.google?.accounts?.id) return;
  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: async (response) => {
      hideLoginError();
      try {
        const res = await api.loginGoogle(response.credential);
        api.setToken(res.access_token);
        await enterAuthenticatedApp();
      } catch (err) {
        showLoginError(err.message);
      }
    }
  });
  const container = document.getElementById("google-button-container");
  container.innerHTML = "";
  window.google.accounts.id.renderButton(container, {
    theme: "outline",
    size: "large",
    width: 340,
    text: "signin_with"
  });
}

function showLoginError(msg) {
  const el = document.getElementById("login-error");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideLoginError() {
  const el = document.getElementById("login-error");
  el.textContent = "";
  el.classList.add("hidden");
}

document.getElementById("dev-login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideLoginError();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const btn = document.getElementById("login-submit-btn");
  btn.disabled = true;
  try {
    const res = await api.login(email, password);
    api.setToken(res.access_token);
    document.getElementById("login-password").value = "";
    await enterAuthenticatedApp();
  } catch (err) {
    showLoginError(err.message || "Não foi possível entrar.");
  } finally {
    btn.disabled = false;
  }
});

document.querySelectorAll("[data-demo-email]").forEach(chip => {
  chip.addEventListener("click", () => {
    document.getElementById("login-email").value = chip.dataset.demoEmail;
    document.getElementById("login-password").value = chip.dataset.demoPw;
  });
});

window.addEventListener("compedu:unauthorized", () => {
  currentUser = null;
  setupLoginScreen();
});

async function bootstrap() {
  if (!api.getToken()) {
    await setupLoginScreen();
    return;
  }
  try {
    await enterAuthenticatedApp();
  } catch (err) {
    api.setToken(null);
    await setupLoginScreen();
  }
}

async function enterAuthenticatedApp() {
  currentUser = await api.getMe();
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app-shell").classList.remove("hidden");

  configureProfileSidebar();
  configureRoleVisibility();
  populateAccessLevelSelects();

  await refreshAllData();
  showView("comunicados");
}

function configureProfileSidebar() {
  const roleLabel = ROLE_LABELS[currentUser.role] || currentUser.role;
  document.getElementById("user-avatar").textContent = initials(currentUser.name);
  document.getElementById("user-name").textContent = currentUser.name;
  document.getElementById("user-role-badge").textContent =
    `${roleLabel} · Nível ${currentUser.access_level}`;

  document.getElementById("profile-email").textContent = currentUser.email;
  document.getElementById("profile-role-level").textContent =
    `${roleLabel} (Nível ${currentUser.access_level})`;

  const classNames = (currentUser.classes || []).map(c => c.name);
  const classesBlock = document.getElementById("profile-classes-block");
  if (currentUser.role === "teacher") {
    classesBlock.classList.remove("hidden");
    document.getElementById("profile-classes").textContent =
      classNames.length ? classNames.join(", ") : "Nenhuma turma vinculada no ano ativo";
  } else {
    classesBlock.classList.add("hidden");
  }

  document.getElementById("sidebar-year-label").textContent =
    currentUser.active_year ? `Ano letivo ${currentUser.active_year}` : "Acompanhamento escolar";
}

function configureRoleVisibility() {
  document.getElementById("nav-registros").classList.toggle("hidden", !canReadRecords());
  document.getElementById("nav-turmas").classList.toggle("hidden", !canViewClassesAndStudents());
  document.getElementById("nav-administracao").classList.toggle("hidden", !canManageEnrollments());
  document.getElementById("nav-auditoria").classList.toggle("hidden", !canViewAudit());

  document.getElementById("home-pedagogical-grid").classList.toggle("hidden", !canReadRecords());
  document.getElementById("student-records-panel").classList.toggle("hidden", !canReadRecords());
  document.getElementById("class-report").classList.toggle("hidden", !canReadRecords());
  document.getElementById("student-new-record").classList.toggle("hidden", !canWriteRecords());
  document.getElementById("student-transfer-btn").classList.toggle("hidden", !canManageEnrollments());
  document.getElementById("council-actions").classList.toggle("hidden", !canEditCouncilDate());

  // Abas administrativas restritas a admin (secretaria vê apenas Alunos e matrículas)
  document.getElementById("tab-btn-profissionais").classList.toggle("hidden", !isAdmin());
  document.getElementById("tab-btn-turmas").classList.toggle("hidden", !isAdmin());
  document.getElementById("tab-btn-anos").classList.toggle("hidden", !isAdmin());
}

function populateAccessLevelSelects() {
  // Um usuário não pode publicar em nível mais alto (numericamente menor) que o próprio
  const minLevel = currentUser ? currentUser.access_level : 3;
  const defaultLevel = Math.max(3, minLevel);
  ["record-access-level", "announcement-access-level"].forEach(selectId => {
    const sel = document.getElementById(selectId);
    const options = [];
    for (let lvl = minLevel; lvl <= 5; lvl++) {
      const selected = lvl === defaultLevel ? "selected" : "";
      options.push(`<option value="${lvl}" ${selected}>${escapeHtml(LEVEL_DESCRIPTIONS[lvl])}</option>`);
    }
    sel.innerHTML = options.join("");
  });
}

async function refreshAllData() {
  const tasks = [
    api.getAnnouncements(),
    api.getDashboard(),
    api.getAcademicYears()
  ];
  if (canViewClassesAndStudents()) {
    tasks.push(api.getClasses(), api.getStudents());
  } else {
    tasks.push(Promise.resolve([]), Promise.resolve([]));
  }
  if (canReadRecords()) {
    tasks.push(api.getRecords());
  } else {
    tasks.push(Promise.resolve([]));
  }

  const [annData, dashData, yearsData, classesData, studentsData, recordsData] =
    await Promise.all(tasks);

  announcements = annData;
  dashboardData = dashData;
  academicYears = yearsData;
  classes = classesData;
  students = studentsData;
  records = recordsData;

  populateFilters();
  renderDashboard();
  renderClasses();
  renderAllRecords();
  renderAnnouncements();
  populateAdminClassOptions();
}

// ---------- Popover de perfil e Logout ----------
document.getElementById("profile-toggle").addEventListener("click", () => {
  const pop = document.getElementById("profile-popover");
  const open = pop.classList.toggle("hidden");
  document.getElementById("profile-toggle").setAttribute("aria-expanded", String(!open));
});

document.getElementById("logout-btn").addEventListener("click", () => {
  api.setToken(null);
  currentUser = null;
  setupLoginScreen();
});

// ---------- Navegação entre views ----------
function updateTopbarActionButtons(view) {
  const showNewAnnouncement = view === "comunicados" && canWriteAnnouncements();
  const showNewRecord = (view === "inicio" || view === "registros" || view === "turmas") && canWriteRecords();
  document.getElementById("new-announcement").classList.toggle("hidden", !showNewAnnouncement);
  document.getElementById("new-record").classList.toggle("hidden", !showNewRecord);
}

async function showView(view) {
  if (!viewInfo[view]) view = "comunicados";
  currentView = view;
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active-view"));
  document.getElementById(view).classList.add("active-view");
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  document.getElementById("breadcrumb").textContent = viewInfo[view][0];
  document.getElementById("page-title").textContent = viewInfo[view][1];
  document.getElementById("page-description").textContent = viewInfo[view][2];
  updateTopbarActionButtons(view);

  if (view === "inicio") renderDashboard();
  if (view === "turmas") showClassesHome();
  if (view === "registros") renderAllRecords();
  if (view === "comunicados") renderAnnouncements();
  if (view === "administracao") await loadAndRenderAdmin();
  if (view === "auditoria") await loadAndRenderAudit();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => showView(btn.dataset.view));
});
document.querySelectorAll("[data-go]").forEach(btn => {
  btn.addEventListener("click", () => showView(btn.dataset.go));
});

// ---------- Painel (Dashboard) ----------
function renderDashboard() {
  if (!dashboardData) return;
  document.getElementById("overview-year-label").textContent =
    dashboardData.active_year ? `Ano letivo ${dashboardData.active_year}` : "sem ano ativo";
  document.getElementById("stat-students").textContent = String(dashboardData.student_count ?? 0);
  document.getElementById("stat-classes").textContent = String(dashboardData.class_count ?? 0);
  document.getElementById("stat-records-month").textContent = String(dashboardData.records_this_month ?? 0);

  document.getElementById("council-date-label").textContent =
    formatCouncilDate(dashboardData.council_date);
  document.getElementById("council-date").value = dashboardData.council_date || "";

  const recent = dashboardData.recent_records || [];
  document.getElementById("recent-records").innerHTML = recent.length
    ? recent.map(r => `
      <div class="timeline-item">
        <span class="dot"></span>
        <div>
          <strong>${escapeHtml(r.student_name)}<span class="badge ${badgeClass(r.record_type)}">${escapeHtml(recordTypeLabel(r.record_type))}</span></strong>
          <p>${escapeHtml(r.text_content)}</p>
        </div>
        <time>${escapeHtml(formatDateTime(r.created_at))}</time>
      </div>
    `).join("")
    : `<p class="empty-state">Nenhum registro recente no seu escopo.</p>`;

  const watch = dashboardData.watch_students || [];
  document.getElementById("watch-students").innerHTML = watch.length
    ? watch.map(item => `
      <div class="watch-item" onclick="openStudentById('${item.student_id}')">
        <div class="student-mini-avatar">${escapeHtml(initials(item.student_name))}</div>
        <div>
          <strong>${escapeHtml(item.student_name)}</strong>
          <span>${escapeHtml(item.class_name || "Sem turma")} · acompanhamento recente</span>
        </div>
        <div class="record-count">${item.attention_count} ${item.attention_count === 1 ? "registro" : "registros"}</div>
      </div>
    `).join("")
    : `<p class="empty-state">Nenhum ponto de atenção recorrente no momento.</p>`;
}

document.getElementById("save-council-date").addEventListener("click", async () => {
  const val = document.getElementById("council-date").value || null;
  const active = academicYears.find(y => y.is_active);
  if (!active) {
    showFeedback("Não há ano letivo ativo.", true);
    return;
  }
  try {
    await api.updateAcademicYear(active.id, { council_date: val });
    dashboardData = await api.getDashboard();
    academicYears = await api.getAcademicYears();
    renderDashboard();
    showFeedback("Data do conselho de classe atualizada.");
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// ---------- Turmas e Alunos ----------
function renderClasses() {
  const grid = document.getElementById("class-grid");
  if (!classes.length) {
    grid.innerHTML = `<p class="empty-state">Nenhuma turma vinculada ou cadastrada no ano letivo ativo.</p>`;
    return;
  }
  grid.innerHTML = classes.map(c => `
    <article class="class-card" onclick="openClass('${c.id}')">
      <div class="class-card-top">
        <div>
          <h3>${escapeHtml(c.name)}</h3>
          <p>${escapeHtml(c.grade_level)} · ${escapeHtml(c.year_label)}</p>
        </div>
        <span class="class-arrow">→</span>
      </div>
      <div class="class-stats">
        <div><strong>${c.student_count}</strong><span>alunos</span></div>
        <div><strong>${c.record_count ?? 0}</strong><span>registros visíveis</span></div>
      </div>
    </article>
  `).join("");
}

function showClassesHome() {
  selectedClass = null;
  selectedStudent = null;
  document.getElementById("classes-home").classList.remove("hidden");
  document.getElementById("class-detail").classList.add("hidden");
  document.getElementById("student-detail").classList.add("hidden");
  document.getElementById("breadcrumb").textContent = "Turmas";
  document.getElementById("page-title").textContent = "Turmas";
  document.getElementById("page-description").textContent = "Acesse uma turma e depois o histórico de cada aluno.";
  renderClasses();
}

window.openClass = function(id, scroll = true) {
  selectedClass = classes.find(c => c.id === id);
  if (!selectedClass) return;
  document.getElementById("classes-home").classList.add("hidden");
  document.getElementById("student-detail").classList.add("hidden");
  document.getElementById("class-detail").classList.remove("hidden");
  document.getElementById("class-title").textContent = selectedClass.name;
  document.getElementById("class-subtitle").textContent =
    `${selectedClass.student_count} alunos · ${selectedClass.grade_level} · ${selectedClass.year_label}`;
  document.getElementById("breadcrumb").textContent = `Turmas / ${selectedClass.name}`;
  document.getElementById("page-title").textContent = selectedClass.name;
  document.getElementById("page-description").textContent = "Selecione um aluno ou gere o relatório consolidado da turma.";
  document.getElementById("class-student-search").value = "";
  renderClassStudents();
  if (scroll) window.scrollTo({ top: 0, behavior: "smooth" });
};

function countStudentRecordsById(studentId) {
  return records.filter(r => r.student_id === studentId).length;
}

function renderClassStudents(filter = "") {
  if (!selectedClass) return;
  const q = filter.trim().toLowerCase();
  const list = students.filter(s =>
    s.current_class_id === selectedClass.id &&
    (s.full_name.toLowerCase().includes(q) || s.school_identifier.toLowerCase().includes(q))
  );
  document.getElementById("class-student-list").innerHTML = list.length
    ? list.map(s => `
      <div class="student-row" onclick="openStudentById('${s.id}')">
        <div class="student-mini-avatar">${escapeHtml(initials(s.full_name))}</div>
        <div>
          <strong>${escapeHtml(s.full_name)}</strong>
          <span class="meta">ID: ${escapeHtml(s.school_identifier)} · ${escapeHtml(s.current_class_name || "")}</span>
        </div>
        ${canReadRecords() ? `<span class="records-pill">${countStudentRecordsById(s.id)} registros</span>` : `<span></span>`}
        <span class="row-arrow">→</span>
      </div>
    `).join("")
    : `<p class="empty-state">Nenhum aluno encontrado nesta turma.</p>`;
}

document.getElementById("class-student-search").addEventListener("input", e => renderClassStudents(e.target.value));
document.getElementById("back-to-classes").addEventListener("click", showClassesHome);

window.openStudentById = async function(studentId) {
  try {
    const detail = await api.getStudent(studentId);
    selectedStudent = detail;
    if (!selectedClass || selectedClass.id !== detail.current_class_id) {
      selectedClass = classes.find(c => c.id === detail.current_class_id) || selectedClass;
    }
    showView("turmas");
    document.getElementById("classes-home").classList.add("hidden");
    document.getElementById("class-detail").classList.add("hidden");
    document.getElementById("student-detail").classList.remove("hidden");

    document.getElementById("student-name").textContent = detail.full_name;
    document.getElementById("student-identifier").textContent = `ID ${detail.school_identifier}`;
    document.getElementById("student-class").textContent =
      detail.current_class_name ? `Turma atual: ${detail.current_class_name}` : "Sem matrícula ativa";
    document.getElementById("student-avatar").textContent = initials(detail.full_name);
    document.getElementById("breadcrumb").textContent =
      `Turmas / ${detail.current_class_name || "Aluno"} / ${detail.full_name}`;
    document.getElementById("page-title").textContent = detail.full_name;
    document.getElementById("page-description").textContent = "Histórico de matrículas e registros pedagógicos do aluno.";

    renderStudentEnrollments(detail.enrollments || []);
    renderStudentRecords();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    showFeedback(err.message, true);
  }
};

function renderStudentEnrollments(enrollments) {
  const container = document.getElementById("student-enrollments");
  if (!enrollments.length) {
    container.innerHTML = `<p class="empty-state">Nenhum vínculo registrado.</p>`;
    return;
  }
  container.innerHTML = enrollments.map(e => {
    const active = !e.ended_at;
    const period = e.ended_at
      ? `${e.started_at} até ${e.ended_at} (encerrado)`
      : `desde ${e.started_at} (vigente)`;
    return `
      <div class="enrollment-chip ${active ? "active" : ""}">
        <strong>${escapeHtml(e.class_name)} · Ano ${escapeHtml(e.year_label)}</strong>
        <span>${escapeHtml(period)}</span>
      </div>
    `;
  }).join("");
}

function renderStudentRecords() {
  if (!selectedStudent || !canReadRecords()) return;
  const list = records.filter(r => r.student_id === selectedStudent.id);
  document.getElementById("student-records").innerHTML = list.length
    ? list.map(recordCard).join("")
    : `<p class="empty-state">Este aluno ainda não possui registros visíveis para o seu perfil.</p>`;
}

document.getElementById("back-to-class").addEventListener("click", () => {
  if (selectedClass) openClass(selectedClass.id);
  else showClassesHome();
});

document.getElementById("student-transfer-btn").addEventListener("click", async () => {
  if (!selectedStudent) return;
  await showView("administracao");
  activateAdminTab("alunos");
  const modeSel = document.getElementById("student-mode");
  modeSel.value = "existing";
  modeSel.dispatchEvent(new Event("change"));
  document.getElementById("admin-existing-student").value = selectedStudent.id;
});

// ---------- Registros pedagógicos ----------
function populateFilters() {
  const classSelect = document.getElementById("filter-class");
  classSelect.innerHTML = `<option value="all">Todas as turmas</option>` +
    classes.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");

  const sortedStudents = students.slice().sort((a, b) => a.full_name.localeCompare(b.full_name));

  const studentSelect = document.getElementById("filter-student");
  studentSelect.innerHTML = `<option value="all">Todos os alunos</option>` +
    sortedStudents.map(s => `<option value="${s.id}">${escapeHtml(s.full_name)} (${escapeHtml(s.school_identifier)})</option>`).join("");

  const recordStudent = document.getElementById("record-student");
  recordStudent.innerHTML = sortedStudents
    .filter(s => s.current_class_id)
    .map(s => `<option value="${s.id}">${escapeHtml(s.full_name)} — ${escapeHtml(s.current_class_name || "")} (${escapeHtml(s.school_identifier)})</option>`)
    .join("");
}

function recordCard(r) {
  const canEdit = currentUser && r.author_id === currentUser.id;
  const canDelete = currentUser && (r.author_id === currentUser.id || currentUser.role === "admin");
  const actions = (canEdit || canDelete) ? `
    <div class="card-inline-actions">
      ${canEdit ? `<button class="link-btn" type="button" onclick="openEditRecord('${r.id}')">Editar</button>` : ""}
      ${canDelete ? `<button class="link-btn danger-text" type="button" onclick="confirmDeleteRecord('${r.id}')">Remover</button>` : ""}
    </div>
  ` : "";

  return `
    <article class="record-card">
      <div class="record-top">
        <div>
          <span class="record-student">${escapeHtml(r.student_name)}</span>
          <span class="record-class">${escapeHtml(r.class_name)}</span>
          <span class="badge ${badgeClass(r.record_type)}">${escapeHtml(recordTypeLabel(r.record_type))}</span>
        </div>
        <span class="record-meta">${escapeHtml(formatDateTime(r.created_at))}${r.updated_at ? " (editado)" : ""} · ${escapeHtml(r.author_name)}</span>
      </div>
      <p>${escapeHtml(r.text_content)}</p>
      <div class="record-footer">
        <div class="record-access">Nível de acesso: ${r.access_level} · visível para contas de nível 1 até ${r.access_level}</div>
        ${actions}
      </div>
    </article>
  `;
}

function renderAllRecords() {
  if (!canReadRecords()) return;
  const cls = document.getElementById("filter-class").value;
  const type = document.getElementById("filter-type").value;
  const studentId = document.getElementById("filter-student").value;

  const list = records.filter(r => {
    return (cls === "all" || r.class_id === cls) &&
           (type === "all" || r.record_type === type) &&
           (studentId === "all" || r.student_id === studentId);
  });

  document.getElementById("all-records").innerHTML = list.length
    ? list.map(recordCard).join("")
    : `<p class="empty-state">Nenhum registro encontrado para esses filtros no seu escopo.</p>`;
  document.getElementById("result-count").textContent =
    `${list.length} ${list.length === 1 ? "registro" : "registros"}`;

  const parts = [];
  if (cls !== "all") parts.push(classes.find(c => c.id === cls)?.name);
  if (type !== "all") parts.push(recordTypeLabel(type));
  if (studentId !== "all") parts.push(students.find(s => s.id === studentId)?.full_name);
  document.getElementById("active-filter-text").textContent =
    parts.length ? `Filtros: ${parts.join(" · ")}` : "Mostrando todos do seu escopo";
}

["filter-class", "filter-type", "filter-student"].forEach(id => {
  document.getElementById(id).addEventListener("change", renderAllRecords);
});
document.getElementById("clear-filters").addEventListener("click", () => {
  document.getElementById("filter-class").value = "all";
  document.getElementById("filter-type").value = "all";
  document.getElementById("filter-student").value = "all";
  renderAllRecords();
});

// Modal de registro (criar / editar)
const recordModal = document.getElementById("record-modal");
function openRecordModal(studentId = null) {
  document.getElementById("record-edit-id").value = "";
  document.getElementById("record-modal-title").textContent = "Novo registro";
  document.getElementById("record-student-field").classList.remove("hidden");
  document.getElementById("record-text").value = "";
  document.getElementById("record-type").value =
    currentUser?.role === "coordination" ? "follow_up" : "positive";
  populateAccessLevelSelects();
  if (studentId) document.getElementById("record-student").value = studentId;
  recordModal.classList.remove("hidden");
}

window.openEditRecord = function(recordId) {
  const rec = records.find(r => r.id === recordId);
  if (!rec) return;
  document.getElementById("record-edit-id").value = rec.id;
  document.getElementById("record-modal-title").textContent = `Editar registro — ${rec.student_name}`;
  document.getElementById("record-student-field").classList.add("hidden");
  document.getElementById("record-type").value = rec.record_type;
  populateAccessLevelSelects();
  document.getElementById("record-access-level").value = String(rec.access_level);
  document.getElementById("record-text").value = rec.text_content;
  recordModal.classList.remove("hidden");
};

window.confirmDeleteRecord = async function(recordId) {
  if (!confirm("Remover este registro pedagógico?")) return;
  try {
    await api.deleteRecord(recordId);
    await refreshAllData();
    if (selectedStudent) renderStudentRecords();
    showFeedback("Registro removido.");
  } catch (err) {
    showFeedback(err.message, true);
  }
};

function closeRecordModal() { recordModal.classList.add("hidden"); }
document.getElementById("new-record").addEventListener("click", () => openRecordModal());
document.getElementById("student-new-record").addEventListener("click", () => openRecordModal(selectedStudent?.id));
document.getElementById("close-record-modal").addEventListener("click", closeRecordModal);
document.getElementById("cancel-record").addEventListener("click", closeRecordModal);
recordModal.addEventListener("click", e => { if (e.target === recordModal) closeRecordModal(); });

document.getElementById("record-form").addEventListener("submit", async e => {
  e.preventDefault();
  const editId = document.getElementById("record-edit-id").value;
  try {
    if (editId) {
      await api.updateRecord(editId, {
        record_type: document.getElementById("record-type").value,
        access_level: Number(document.getElementById("record-access-level").value),
        text_content: document.getElementById("record-text").value.trim()
      });
      showFeedback("Registro atualizado.");
    } else {
      await api.createRecord({
        student_id: document.getElementById("record-student").value,
        record_type: document.getElementById("record-type").value,
        access_level: Number(document.getElementById("record-access-level").value),
        text_content: document.getElementById("record-text").value.trim()
      });
      showFeedback("Registro salvo com sucesso.");
    }
    closeRecordModal();
    await refreshAllData();
    if (selectedStudent) renderStudentRecords();
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// ---------- Mural de comunicados ----------
function renderAnnouncements() {
  const list = document.getElementById("announcement-list");
  if (!announcements.length) {
    list.innerHTML = `<p class="empty-state">Nenhum comunicado publicado para o seu nível de acesso.</p>`;
    return;
  }
  list.innerHTML = announcements.map(item => {
    const canManage = currentUser && (item.author_id === currentUser.id || currentUser.role === "admin");
    return `
      <article class="announcement-item">
        <div class="announcement-top">
          <div>
            <h3>${escapeHtml(item.title)}</h3>
            <span class="access-level-badge">Nível ${item.access_level}</span>
          </div>
          <time>${escapeHtml(formatDateTime(item.published_at))}${item.updated_at ? " (editado)" : ""}</time>
        </div>
        <p>${escapeHtml(item.content)}</p>
        <div class="record-footer">
          <div class="announcement-author">Publicado por ${escapeHtml(item.author_name)}</div>
          ${canManage ? `
            <div class="card-inline-actions">
              <button class="link-btn" type="button" onclick="openEditAnnouncement('${item.id}')">Editar</button>
              <button class="link-btn danger-text" type="button" onclick="confirmDeleteAnnouncement('${item.id}')">Remover</button>
            </div>
          ` : ""}
        </div>
      </article>
    `;
  }).join("");
}

const announcementModal = document.getElementById("announcement-modal");
function openAnnouncementModal() {
  document.getElementById("announcement-edit-id").value = "";
  document.getElementById("announcement-modal-title").textContent = "Novo comunicado";
  document.getElementById("announcement-title").value = "";
  document.getElementById("announcement-text").value = "";
  populateAccessLevelSelects();
  announcementModal.classList.remove("hidden");
}

window.openEditAnnouncement = function(id) {
  const item = announcements.find(a => a.id === id);
  if (!item) return;
  document.getElementById("announcement-edit-id").value = item.id;
  document.getElementById("announcement-modal-title").textContent = "Editar comunicado";
  document.getElementById("announcement-title").value = item.title;
  document.getElementById("announcement-text").value = item.content;
  populateAccessLevelSelects();
  document.getElementById("announcement-access-level").value = String(item.access_level);
  announcementModal.classList.remove("hidden");
};

window.confirmDeleteAnnouncement = async function(id) {
  if (!confirm("Remover este comunicado do mural?")) return;
  try {
    await api.deleteAnnouncement(id);
    announcements = await api.getAnnouncements();
    renderAnnouncements();
    showFeedback("Comunicado removido.");
  } catch (err) {
    showFeedback(err.message, true);
  }
};

function closeAnnouncementModal() { announcementModal.classList.add("hidden"); }
document.getElementById("new-announcement").addEventListener("click", openAnnouncementModal);
document.getElementById("close-announcement-modal").addEventListener("click", closeAnnouncementModal);
document.getElementById("cancel-announcement").addEventListener("click", closeAnnouncementModal);
announcementModal.addEventListener("click", e => { if (e.target === announcementModal) closeAnnouncementModal(); });

document.getElementById("announcement-form").addEventListener("submit", async e => {
  e.preventDefault();
  const editId = document.getElementById("announcement-edit-id").value;
  const payload = {
    title: document.getElementById("announcement-title").value.trim(),
    access_level: Number(document.getElementById("announcement-access-level").value),
    content: document.getElementById("announcement-text").value.trim()
  };
  try {
    if (editId) {
      await api.updateAnnouncement(editId, payload);
      showFeedback("Comunicado atualizado.");
    } else {
      await api.createAnnouncement(payload);
      showFeedback("Comunicado publicado.");
    }
    closeAnnouncementModal();
    announcements = await api.getAnnouncements();
    renderAnnouncements();
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// ---------- Relatório da turma (via endpoint agregado do backend) ----------
const reportModal = document.getElementById("report-modal");
async function openReport() {
  if (!selectedClass) return;
  try {
    const rep = await api.getClassReport(selectedClass.id);
    const positive = rep.by_type?.positive ?? 0;
    const attention = rep.by_type?.attention ?? 0;
    const follow = rep.by_type?.follow_up ?? 0;

    document.getElementById("report-title").textContent =
      `Relatório — ${rep.class_name} (${rep.year_label})`;
    document.getElementById("report-content").innerHTML = `
      <div class="report-numbers">
        <div class="report-stat"><strong>${rep.total}</strong><span>registros no período</span></div>
        <div class="report-stat"><strong>${positive}</strong><span>registros positivos</span></div>
        <div class="report-stat"><strong>${attention + follow}</strong><span>pontos de acompanhamento</span></div>
      </div>
      <div class="report-block">
        <h3>Leitura rápida da turma (${rep.student_count} alunos matriculados)</h3>
        <p>Este relatório consolida os registros pedagógicos da turma para apoiar o conselho de classe. O objetivo é organizar fatos registrados sem produzir rótulos sobre os estudantes.</p>
      </div>
      <div class="report-block">
        <h3>Distribuição por tipo</h3>
        <p>Positivos: <strong>${positive}</strong> · Atenção: <strong>${attention}</strong> · Acompanhamento / encaminhamento: <strong>${follow}</strong>.</p>
      </div>
    `;
    reportModal.classList.remove("hidden");
  } catch (err) {
    showFeedback(err.message, true);
  }
}
document.getElementById("class-report").addEventListener("click", openReport);
function closeReport() { reportModal.classList.add("hidden"); }
document.getElementById("close-report-modal").addEventListener("click", closeReport);
document.getElementById("close-report-bottom").addEventListener("click", closeReport);
reportModal.addEventListener("click", e => { if (e.target === reportModal) closeReport(); });

// ---------- Administração / Cadastros ----------
function activateAdminTab(tabName) {
  document.querySelectorAll("[data-admin-tab]").forEach(item => {
    const selected = item.dataset.adminTab === tabName;
    item.classList.toggle("active", selected);
    item.setAttribute("aria-selected", String(selected));
  });
  document.querySelectorAll(".admin-panel").forEach(panel => {
    panel.classList.toggle("hidden", panel.id !== `admin-${tabName}`);
  });
}

document.querySelectorAll("[data-admin-tab]").forEach(tab => {
  tab.addEventListener("click", () => activateAdminTab(tab.dataset.adminTab));
});

document.getElementById("student-mode").addEventListener("change", e => {
  const isNew = e.target.value === "new";
  document.getElementById("student-new-fields").classList.toggle("hidden", !isNew);
  document.getElementById("student-existing-fields").classList.toggle("hidden", isNew);
});

document.getElementById("user-form-role").addEventListener("change", e => {
  const def = ROLE_DEFAULT_LEVEL[e.target.value] || 3;
  document.getElementById("user-form-level").value = String(def);
});

function populateAdminClassOptions() {
  const options = classes.map(item =>
    `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${escapeHtml(item.grade_level)}</option>`
  ).join("");
  document.getElementById("user-form-classes").innerHTML = options;
  document.getElementById("admin-student-class").innerHTML = options;
  document.getElementById("assign-classes-select").innerHTML = options;

  const studentOpts = students
    .slice()
    .sort((a, b) => a.full_name.localeCompare(b.full_name))
    .map(s => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.full_name)} (${escapeHtml(s.school_identifier)}) — atual: ${escapeHtml(s.current_class_name || "sem turma")}</option>`)
    .join("");
  document.getElementById("admin-existing-student").innerHTML = studentOpts;
}

async function loadAndRenderAdmin() {
  if (isAdmin()) {
    usersList = await api.getUsers();
  }
  academicYears = await api.getAcademicYears();
  renderAdminLists();
}

function renderAdminLists() {
  populateAdminClassOptions();

  // Alunos
  document.getElementById("admin-student-list").innerHTML = students.length
    ? students.map(s => `
      <article class="admin-list-item">
        <div class="admin-item-row">
          <div>
            <strong>${escapeHtml(s.full_name)}</strong>
            <span>ID: ${escapeHtml(s.school_identifier)} · Turma atual: ${escapeHtml(s.current_class_name || "Nenhuma")}</span>
          </div>
          <button class="link-btn" type="button" onclick="openStudentById('${s.id}')">Ver histórico</button>
        </div>
      </article>
    `).join("")
    : `<p class="empty-state">Nenhum aluno cadastrado.</p>`;

  if (!isAdmin()) return;

  // Profissionais
  document.getElementById("user-list").innerHTML = usersList.length
    ? usersList.map(u => {
      const classNames = (u.classes || []).map(c => c.name).join(", ") || "Nenhuma turma";
      const roleLabel = ROLE_LABELS[u.role] || u.role;
      return `
        <article class="admin-list-item">
          <div class="admin-item-row">
            <div>
              <strong>${escapeHtml(u.name)} ${u.active ? "" : "(Inativo)"}</strong>
              <span>${escapeHtml(u.email)} · ${escapeHtml(roleLabel)} · Nível ${u.access_level}</span>
              <small>Turmas no ano ativo: ${escapeHtml(classNames)}</small>
            </div>
            <div class="card-inline-actions">
              <button class="link-btn" type="button" onclick="openAssignModal('${u.id}')">Vínculos</button>
              ${u.id !== currentUser.id ? `<button class="link-btn" type="button" onclick="toggleUserActive('${u.id}', ${!u.active})">${u.active ? "Desativar" : "Ativar"}</button>` : ""}
            </div>
          </div>
        </article>
      `;
    }).join("")
    : `<p class="empty-state">Nenhum profissional cadastrado.</p>`;

  // Turmas
  document.getElementById("admin-class-list").innerHTML = classes.length
    ? classes.map(item => `
      <article class="admin-list-item">
        <strong>${escapeHtml(item.name)} (${escapeHtml(item.year_label)})</strong>
        <span>${escapeHtml(item.grade_level)}</span>
        <small>${item.student_count} aluno(s) matriculado(s)</small>
      </article>
    `).join("")
    : `<p class="empty-state">Nenhuma turma no ano letivo ativo.</p>`;

  // Anos letivos
  document.getElementById("admin-year-list").innerHTML = academicYears.length
    ? academicYears.map(y => `
      <article class="admin-list-item">
        <div class="admin-item-row">
          <div>
            <strong>Ano letivo ${escapeHtml(y.year_label)} ${y.is_active ? "· ATIVO" : ""}</strong>
            <span>Conselho: ${escapeHtml(formatCouncilDate(y.council_date))}</span>
          </div>
          ${!y.is_active ? `<button class="link-btn" type="button" onclick="activateYear('${y.id}')">Tornar ativo</button>` : ""}
        </div>
      </article>
    `).join("")
    : `<p class="empty-state">Nenhum ano letivo cadastrado.</p>`;
}

// Submissão: Alunos (criar novo ou vincular/transferir existente)
document.getElementById("student-form").addEventListener("submit", async event => {
  event.preventDefault();
  const mode = document.getElementById("student-mode").value;
  const classId = document.getElementById("admin-student-class").value;
  try {
    if (mode === "new") {
      const fullName = document.getElementById("admin-student-name").value.trim();
      const identifier = document.getElementById("admin-student-identifier").value.trim();
      if (!fullName || !identifier) {
        showFeedback("Informe o nome completo e o identificador escolar do aluno.", true);
        return;
      }
      await api.createStudent({
        full_name: fullName,
        school_identifier: identifier,
        class_id: classId
      });
      showFeedback("Aluno cadastrado e matriculado na turma.");
    } else {
      const studentId = document.getElementById("admin-existing-student").value;
      await api.enrollStudent(studentId, classId);
      showFeedback("Vínculo de turma atualizado (histórico preservado).");
    }
    event.currentTarget.reset();
    document.getElementById("student-mode").dispatchEvent(new Event("change"));
    await refreshAllData();
    renderAdminLists();
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// Submissão: Novo profissional
document.getElementById("user-form").addEventListener("submit", async event => {
  event.preventDefault();
  const pw = document.getElementById("user-form-password").value;
  const payload = {
    name: document.getElementById("user-form-name").value.trim(),
    email: document.getElementById("user-form-email").value.trim(),
    role: document.getElementById("user-form-role").value,
    access_level: Number(document.getElementById("user-form-level").value),
    class_ids: [...document.getElementById("user-form-classes").selectedOptions].map(o => o.value),
    ...(pw ? { password: pw } : {})
  };
  try {
    await api.createUser(payload);
    event.currentTarget.reset();
    document.getElementById("user-form-level").value = "3";
    usersList = await api.getUsers();
    renderAdminLists();
    showFeedback("Profissional cadastrado.");
  } catch (err) {
    showFeedback(err.message, true);
  }
});

window.toggleUserActive = async function(userId, active) {
  try {
    await api.updateUser(userId, { active });
    usersList = await api.getUsers();
    renderAdminLists();
    showFeedback(active ? "Conta reativada." : "Conta desativada.");
  } catch (err) {
    showFeedback(err.message, true);
  }
};

// Modal de vínculos de turmas do profissional
const assignModal = document.getElementById("assign-modal");
window.openAssignModal = function(userId) {
  const u = usersList.find(item => item.id === userId);
  if (!u) return;
  document.getElementById("assign-user-id").value = u.id;
  document.getElementById("assign-modal-title").textContent = `Turmas vinculadas — ${u.name}`;
  const currentIds = new Set((u.classes || []).map(c => c.id));
  [...document.getElementById("assign-classes-select").options].forEach(opt => {
    opt.selected = currentIds.has(opt.value);
  });
  assignModal.classList.remove("hidden");
};
function closeAssignModal() { assignModal.classList.add("hidden"); }
document.getElementById("close-assign-modal").addEventListener("click", closeAssignModal);
document.getElementById("cancel-assign").addEventListener("click", closeAssignModal);
assignModal.addEventListener("click", e => { if (e.target === assignModal) closeAssignModal(); });

document.getElementById("assign-form").addEventListener("submit", async e => {
  e.preventDefault();
  const userId = document.getElementById("assign-user-id").value;
  const classIds = [...document.getElementById("assign-classes-select").selectedOptions].map(o => o.value);
  try {
    await api.setUserAssignments(userId, classIds);
    closeAssignModal();
    usersList = await api.getUsers();
    if (userId === currentUser.id) {
      currentUser = await api.getMe();
      configureProfileSidebar();
    }
    await refreshAllData();
    renderAdminLists();
    showFeedback("Vínculos de turma atualizados.");
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// Submissão: Nova turma
document.getElementById("class-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await api.createClass({
      name: document.getElementById("admin-class-name").value.trim(),
      grade_level: document.getElementById("admin-class-year").value
    });
    event.currentTarget.reset();
    await refreshAllData();
    renderAdminLists();
    showFeedback("Turma criada no ano letivo ativo.");
  } catch (err) {
    showFeedback(err.message, true);
  }
});

// Submissão: Novo ano letivo
document.getElementById("year-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await api.createAcademicYear({
      year_label: document.getElementById("admin-year-label").value.trim(),
      is_active: document.getElementById("admin-year-active").checked
    });
    event.currentTarget.reset();
    currentUser = await api.getMe();
    configureProfileSidebar();
    await refreshAllData();
    renderAdminLists();
    showFeedback("Ano letivo cadastrado.");
  } catch (err) {
    showFeedback(err.message, true);
  }
});

window.activateYear = async function(yearId) {
  try {
    await api.updateAcademicYear(yearId, { is_active: true });
    currentUser = await api.getMe();
    configureProfileSidebar();
    await refreshAllData();
    await loadAndRenderAdmin();
    showFeedback("Ano letivo ativo alterado.");
  } catch (err) {
    showFeedback(err.message, true);
  }
};

// ---------- Auditoria ----------
async function loadAndRenderAudit() {
  if (!canViewAudit()) return;
  try {
    const items = await api.getAudit(100);
    document.getElementById("audit-list").innerHTML = items.length
      ? items.map(a => `
        <article class="admin-list-item">
          <div class="admin-item-row">
            <div>
              <strong>${escapeHtml(a.action.toUpperCase())} · ${escapeHtml(a.entity)}</strong>
              <span>Autor: ${escapeHtml(a.actor_name || "Sistema")} ${a.detail ? `· ${escapeHtml(a.detail)}` : ""}</span>
            </div>
            <small>${escapeHtml(formatDateTime(a.created_at))}</small>
          </div>
        </article>
      `).join("")
      : `<p class="empty-state">Nenhum evento de auditoria registrado.</p>`;
  } catch (err) {
    showFeedback(err.message, true);
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);
