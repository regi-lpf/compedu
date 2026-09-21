const classes = [
  { id:"1A", name:"1º A", year:"1º ano", students:28, records:9 },
  { id:"1B", name:"1º B", year:"1º ano", students:30, records:11 },
  { id:"2A", name:"2º A", year:"2º ano", students:27, records:8 },
  { id:"2B", name:"2º B", year:"2º ano", students:29, records:5 },
  { id:"3A", name:"3º A", year:"3º ano", students:26, records:7 },
  { id:"3B", name:"3º B", year:"3º ano", students:25, records:6 }
];

const students = [
  { name:"Ana Souza", cls:"2º A", classId:"2A" },
  { name:"Bruno Martins", cls:"2º A", classId:"2A" },
  { name:"Gabriel Costa", cls:"2º A", classId:"2A" },
  { name:"Marina Lopes", cls:"2º A", classId:"2A" },

  { name:"Carla Lima", cls:"1º B", classId:"1B" },
  { name:"Henrique Melo", cls:"1º B", classId:"1B" },
  { name:"Julia Reis", cls:"1º B", classId:"1B" },

  { name:"Eduarda Alves", cls:"1º A", classId:"1A" },
  { name:"Felipe Ramos", cls:"1º A", classId:"1A" },

  { name:"Diego Rocha", cls:"3º A", classId:"3A" },
  { name:"Isabela Nunes", cls:"3º A", classId:"3A" },

  { name:"Lucas Vieira", cls:"2º B", classId:"2B" },
  { name:"Sofia Andrade", cls:"2º B", classId:"2B" },

  { name:"Rafael Gomes", cls:"3º B", classId:"3B" },
  { name:"Vitória Luz", cls:"3º B", classId:"3B" }
];

let records = [
  { student:"Ana Souza", cls:"2º A", classId:"2A", type:"Atenção", text:"Conversou repetidamente durante a explicação, mesmo após duas orientações.", date:"Hoje, 10:20", teacher:"Prof. William" },
  { student:"Bruno Martins", cls:"2º A", classId:"2A", type:"Positivo", text:"Participou da atividade em grupo e ajudou colegas na resolução dos exercícios.", date:"Ontem, 14:05", teacher:"Prof. Renan" },
  { student:"Carla Lima", cls:"1º B", classId:"1B", type:"Acompanhamento", text:"Apresentou melhora na entrega das atividades. Manter acompanhamento por mais duas semanas.", date:"14 ago., 09:15", teacher:"Prof. William" },
  { student:"Ana Souza", cls:"2º A", classId:"2A", type:"Positivo", text:"Concluiu a atividade proposta dentro do tempo e apresentou boa participação.", date:"12 ago., 10:40", teacher:"Prof. Renan" },
  { student:"Diego Rocha", cls:"3º A", classId:"3A", type:"Atenção", text:"Chegou atrasado em duas aulas na mesma semana. Conversado com o aluno sobre os horários.", date:"11 ago., 08:05", teacher:"Prof. William" },
  { student:"Ana Souza", cls:"2º A", classId:"2A", type:"Atenção", text:"Teve dificuldade em manter o foco durante a atividade individual.", date:"8 ago., 11:10", teacher:"Prof. Renan" },
  { student:"Carla Lima", cls:"1º B", classId:"1B", type:"Positivo", text:"Entregou todas as atividades pendentes e demonstrou organização.", date:"7 ago., 15:20", teacher:"Prof. William" },
  { student:"Eduarda Alves", cls:"1º A", classId:"1A", type:"Positivo", text:"Apresentou o trabalho com clareza e bom domínio do conteúdo.", date:"6 ago., 09:40", teacher:"Prof. Renan" }
];

let selectedClass = null;
let selectedStudent = null;

const viewInfo = {
  inicio:["Início","Visão geral","O que precisa de atenção agora."],
  turmas:["Turmas","Turmas","Acesse uma turma e depois o histórico de cada aluno."],
  registros:["Registros","Lista de registros","Filtre por turma, tipo de registro ou aluno."]
};

function initials(name){
  return name.split(" ").slice(0,2).map(p=>p[0]).join("").toUpperCase();
}
function badgeClass(type){
  if(type==="Positivo") return "good";
  if(type==="Atenção") return "warn";
  return "neutral";
}
function countStudentRecords(name){
  return records.filter(r=>r.student===name).length;
}
function escapeHtml(text){
  const div=document.createElement("div");
  div.textContent=text;
  return div.innerHTML;
}

function showView(view){
  document.querySelectorAll(".view").forEach(v=>v.classList.remove("active-view"));
  document.getElementById(view).classList.add("active-view");
  document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===view));
  document.getElementById("breadcrumb").textContent=viewInfo[view][0];
  document.getElementById("page-title").textContent=viewInfo[view][1];
  document.getElementById("page-description").textContent=viewInfo[view][2];

  if(view==="turmas") showClassesHome();
  if(view==="registros") renderAllRecords();
  window.scrollTo({top:0,behavior:"smooth"});
}

document.querySelectorAll(".nav-item").forEach(btn=>{
  btn.addEventListener("click",()=>showView(btn.dataset.view));
});
document.querySelectorAll("[data-go]").forEach(btn=>{
  btn.addEventListener("click",()=>showView(btn.dataset.go));
});

function renderRecent(){
  document.getElementById("recent-records").innerHTML=records.slice(0,4).map(r=>`
    <div class="timeline-item">
      <span class="dot"></span>
      <div>
        <strong>${r.student}<span class="badge ${badgeClass(r.type)}">${r.type}</span></strong>
        <p>${escapeHtml(r.text)}</p>
      </div>
      <time>${r.date}</time>
    </div>
  `).join("");
}

function renderWatch(){
  const attention = {};
  records.filter(r=>r.type==="Atenção").forEach(r=>{
    attention[r.student]=(attention[r.student]||0)+1;
  });
  const list = Object.entries(attention).sort((a,b)=>b[1]-a[1]).slice(0,4);
  document.getElementById("watch-students").innerHTML=list.map(([name,count])=>{
    const s=students.find(x=>x.name===name);
    return `
      <div class="watch-item" onclick="openStudentFromHome('${name}')">
        <div class="student-mini-avatar">${initials(name)}</div>
        <div>
          <strong>${name}</strong>
          <span>${s ? s.cls : ""} · acompanhamento recente</span>
        </div>
        <div class="record-count">${count} ${count===1?"registro":"registros"}</div>
      </div>
    `;
  }).join("");
}

window.openStudentFromHome = function(name){
  const s=students.find(x=>x.name===name);
  if(!s) return;
  showView("turmas");
  openClass(s.classId,false);
  openStudent(name);
}

function renderClasses(){
  document.getElementById("class-grid").innerHTML=classes.map(c=>`
    <article class="class-card" onclick="openClass('${c.id}')">
      <div class="class-card-top">
        <div>
          <h3>${c.name}</h3>
          <p>${c.year} · Ensino Médio</p>
        </div>
        <span class="class-arrow">→</span>
      </div>
      <div class="class-stats">
        <div><strong>${c.students}</strong><span>alunos</span></div>
        <div><strong>${records.filter(r=>r.classId===c.id).length}</strong><span>registros</span></div>
      </div>
    </article>
  `).join("");
}

function showClassesHome(){
  selectedClass=null;
  selectedStudent=null;
  document.getElementById("classes-home").classList.remove("hidden");
  document.getElementById("class-detail").classList.add("hidden");
  document.getElementById("student-detail").classList.add("hidden");
  document.getElementById("breadcrumb").textContent="Turmas";
  document.getElementById("page-title").textContent="Turmas";
  document.getElementById("page-description").textContent="Acesse uma turma e depois o histórico de cada aluno.";
  renderClasses();
}

window.openClass = function(id, scroll=true){
  selectedClass=classes.find(c=>c.id===id);
  if(!selectedClass) return;
  document.getElementById("classes-home").classList.add("hidden");
  document.getElementById("student-detail").classList.add("hidden");
  document.getElementById("class-detail").classList.remove("hidden");
  document.getElementById("class-title").textContent=selectedClass.name;
  document.getElementById("class-subtitle").textContent=`${selectedClass.students} alunos · ${selectedClass.year} · Ensino Médio`;
  document.getElementById("breadcrumb").textContent=`Turmas / ${selectedClass.name}`;
  document.getElementById("page-title").textContent=selectedClass.name;
  document.getElementById("page-description").textContent="Selecione um aluno ou gere o relatório da turma.";
  renderClassStudents();
  if(scroll) window.scrollTo({top:0,behavior:"smooth"});
}

function renderClassStudents(filter=""){
  const list=students.filter(s=>s.classId===selectedClass.id && s.name.toLowerCase().includes(filter.toLowerCase()));
  document.getElementById("class-student-list").innerHTML=list.length?list.map(s=>`
    <div class="student-row" onclick="openStudent('${s.name}')">
      <div class="student-mini-avatar">${initials(s.name)}</div>
      <div>
        <strong>${s.name}</strong>
        <span class="meta">${s.cls}</span>
      </div>
      <span class="records-pill">${countStudentRecords(s.name)} registros</span>
      <span class="row-arrow">→</span>
    </div>
  `).join(""):`<p style="color:#6f7b8f">Nenhum aluno encontrado.</p>`;
}

document.getElementById("class-student-search").addEventListener("input",e=>renderClassStudents(e.target.value));
document.getElementById("back-to-classes").addEventListener("click",showClassesHome);

window.openStudent = function(name){
  selectedStudent=students.find(s=>s.name===name);
  if(!selectedStudent) return;
  if(!selectedClass || selectedClass.id!==selectedStudent.classId) selectedClass=classes.find(c=>c.id===selectedStudent.classId);
  document.getElementById("classes-home").classList.add("hidden");
  document.getElementById("class-detail").classList.add("hidden");
  document.getElementById("student-detail").classList.remove("hidden");
  document.getElementById("student-name").textContent=selectedStudent.name;
  document.getElementById("student-class").textContent=selectedStudent.cls;
  document.getElementById("student-avatar").textContent=initials(selectedStudent.name);
  document.getElementById("breadcrumb").textContent=`Turmas / ${selectedStudent.cls} / ${selectedStudent.name}`;
  document.getElementById("page-title").textContent=selectedStudent.name;
  document.getElementById("page-description").textContent="Histórico de registros do aluno.";
  renderStudentRecords();
  window.scrollTo({top:0,behavior:"smooth"});
}

function renderStudentRecords(){
  const list=records.filter(r=>r.student===selectedStudent.name);
  document.getElementById("student-records").innerHTML=list.length?list.map(recordCard).join(""):`<p style="color:#6f7b8f">Este aluno ainda não possui registros.</p>`;
}

document.getElementById("back-to-class").addEventListener("click",()=>openClass(selectedClass.id));

function populateFilters(){
  const classSelect=document.getElementById("filter-class");
  classSelect.innerHTML=`<option value="all">Todas as turmas</option>`+classes.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");

  const studentSelect=document.getElementById("filter-student");
  studentSelect.innerHTML=`<option value="all">Todos os alunos</option>`+students
    .slice().sort((a,b)=>a.name.localeCompare(b.name))
    .map(s=>`<option value="${s.name}">${s.name}</option>`).join("");

  const recordStudent=document.getElementById("record-student");
  recordStudent.innerHTML=students.slice().sort((a,b)=>a.name.localeCompare(b.name))
    .map(s=>`<option value="${s.name}">${s.name} — ${s.cls}</option>`).join("");
}

function recordCard(r){
  return `
    <article class="record-card">
      <div class="record-top">
        <div>
          <span class="record-student">${r.student}</span>
          <span class="record-class">${r.cls}</span>
          <span class="badge ${badgeClass(r.type)}">${r.type}</span>
        </div>
        <span class="record-meta">${r.date} · ${r.teacher}</span>
      </div>
      <p>${escapeHtml(r.text)}</p>
    </article>
  `;
}

function renderAllRecords(){
  const cls=document.getElementById("filter-class").value;
  const type=document.getElementById("filter-type").value;
  const student=document.getElementById("filter-student").value;

  const list=records.filter(r=>{
    return (cls==="all"||r.classId===cls) &&
           (type==="all"||r.type===type) &&
           (student==="all"||r.student===student);
  });

  document.getElementById("all-records").innerHTML=list.length?list.map(recordCard).join(""):`<p style="color:#6f7b8f">Nenhum registro encontrado para esses filtros.</p>`;
  document.getElementById("result-count").textContent=`${list.length} ${list.length===1?"registro":"registros"}`;

  const parts=[];
  if(cls!=="all") parts.push(classes.find(c=>c.id===cls)?.name);
  if(type!=="all") parts.push(type);
  if(student!=="all") parts.push(student);
  document.getElementById("active-filter-text").textContent=parts.length?`Filtros: ${parts.join(" · ")}`:"Mostrando todos";
}

["filter-class","filter-type","filter-student"].forEach(id=>{
  document.getElementById(id).addEventListener("change",renderAllRecords);
});
document.getElementById("clear-filters").addEventListener("click",()=>{
  document.getElementById("filter-class").value="all";
  document.getElementById("filter-type").value="all";
  document.getElementById("filter-student").value="all";
  renderAllRecords();
});

function formatCouncilDate(value){
  if(!value) return "Data não definida";
  const [y,m,d]=value.split("-").map(Number);
  const months=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  return `${d} de ${months[m-1]} de ${y}`;
}
document.getElementById("save-council-date").addEventListener("click",()=>{
  const val=document.getElementById("council-date").value;
  document.getElementById("council-date-label").textContent=formatCouncilDate(val);
});

const recordModal=document.getElementById("record-modal");
function openRecordModal(studentName=null){
  if(studentName) document.getElementById("record-student").value=studentName;
  recordModal.classList.remove("hidden");
}
function closeRecordModal(){ recordModal.classList.add("hidden"); }
document.getElementById("new-record").addEventListener("click",()=>openRecordModal());
document.getElementById("student-new-record").addEventListener("click",()=>openRecordModal(selectedStudent?.name));
document.getElementById("close-record-modal").addEventListener("click",closeRecordModal);
document.getElementById("cancel-record").addEventListener("click",closeRecordModal);
recordModal.addEventListener("click",e=>{if(e.target===recordModal)closeRecordModal()});

document.getElementById("record-form").addEventListener("submit",e=>{
  e.preventDefault();
  const name=document.getElementById("record-student").value;
  const s=students.find(x=>x.name===name);
  records.unshift({
    student:name,
    cls:s.cls,
    classId:s.classId,
    type:document.getElementById("record-type").value,
    text:document.getElementById("record-text").value,
    date:"Agora",
    teacher:"Professor"
  });
  document.getElementById("record-text").value="";
  closeRecordModal();
  renderRecent();
  renderWatch();
  renderClasses();
  if(selectedStudent?.name===name) renderStudentRecords();
  renderAllRecords();
});

const reportModal=document.getElementById("report-modal");
function openReport(){
  if(!selectedClass) return;
  const classRecords=records.filter(r=>r.classId===selectedClass.id);
  const positive=classRecords.filter(r=>r.type==="Positivo").length;
  const attention=classRecords.filter(r=>r.type==="Atenção").length;
  const follow=classRecords.filter(r=>r.type==="Acompanhamento").length;

  document.getElementById("report-title").textContent=`Relatório — ${selectedClass.name}`;
  document.getElementById("report-content").innerHTML=`
    <div class="report-numbers">
      <div class="report-stat"><strong>${classRecords.length}</strong><span>registros no período</span></div>
      <div class="report-stat"><strong>${positive}</strong><span>registros positivos</span></div>
      <div class="report-stat"><strong>${attention+follow}</strong><span>pontos de acompanhamento</span></div>
    </div>
    <div class="report-block">
      <h3>Leitura rápida da turma</h3>
      <p>Este relatório reúne os registros pedagógicos já cadastrados e serve como apoio para o conselho de classe. O objetivo é organizar fatos registrados, não produzir rótulos sobre os alunos.</p>
    </div>
    <div class="report-block">
      <h3>Distribuição dos registros</h3>
      <p>Positivos: ${positive} · Atenção: ${attention} · Acompanhamento: ${follow}.</p>
    </div>
  `;
  reportModal.classList.remove("hidden");
}
document.getElementById("class-report").addEventListener("click",openReport);
function closeReport(){reportModal.classList.add("hidden")}
document.getElementById("close-report-modal").addEventListener("click",closeReport);
document.getElementById("close-report-bottom").addEventListener("click",closeReport);
reportModal.addEventListener("click",e=>{if(e.target===reportModal)closeReport()});

populateFilters();
renderRecent();
renderWatch();
renderClasses();
renderAllRecords();
