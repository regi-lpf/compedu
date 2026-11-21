"""Matriz de autorização (docs/arq-decisoes-final.md §2) — cada papel × operação, incluindo casos negativos."""
import pytest


def _ids(resp) -> set[str]:
    assert resp.status_code == 200, resp.text
    return {r["id"] for r in resp.json()}


def _rec(w, *keys) -> set[str]:
    return {str(w.records[k]) for k in keys}


# ---------- Leitura de registros ----------
def test_admin_sees_all_active_records(client, world):
    assert _ids(client.get("/api/records", headers=world.h("admin"))) == _rec(
        world, "a_t1", "a_admin", "a_lvl1", "a_follow", "a_follow3", "b_t2", "old")


def test_teacher_sees_only_own_classes_in_active_year_and_level(client, world):
    # a_lvl1 (nível 1) e a_follow (nível 2) acima do nível 3; b_t2 é de outra turma; old é de ano anterior.
    assert _ids(client.get("/api/records", headers=world.h("t1"))) == _rec(world, "a_t1", "a_admin", "a_follow3")
    assert _ids(client.get("/api/records", headers=world.h("t2"))) == _rec(world, "b_t2")


def test_teacher_cannot_bypass_scope_with_filters(client, world):
    resp = client.get("/api/records", params={"class_id": str(world.classes["B"])}, headers=world.h("t1"))
    assert _ids(resp) == set()
    resp = client.get("/api/records", params={"student_id": str(world.students["B"])}, headers=world.h("t1"))
    assert _ids(resp) == set()


def test_coordination_sees_only_follow_up_or_level_le_2(client, world):
    assert _ids(client.get("/api/records", headers=world.h("coord"))) == _rec(world, "a_follow", "a_follow3")


@pytest.mark.parametrize("who", ["secre", "support"])
def test_secretary_and_support_have_no_pedagogical_access(client, world, who):
    assert _ids(client.get("/api/records", headers=world.h(who))) == set()
    payload = {"student_id": str(world.students["A"]), "record_type": "positive", "access_level": 5,
               "text_content": "x"}
    assert client.post("/api/records", json=payload, headers=world.h(who)).status_code == 403


def test_record_filters(client, world):
    resp = client.get("/api/records", params={"record_type": "attention"}, headers=world.h("admin"))
    assert _ids(resp) == _rec(world, "a_admin", "a_lvl1", "b_t2")


# ---------- Escrita de registros ----------
def _new(world, student="A", level=3, kind="positive"):
    return {"student_id": str(world.students[student]), "record_type": kind, "access_level": level,
            "text_content": "Participou da atividade."}


def test_teacher_creates_record_for_own_student_with_class_context(client, world):
    resp = client.post("/api/records", json=_new(world), headers=world.h("t1"))
    assert resp.status_code == 201, resp.text
    assert resp.json()["class_id"] == str(world.classes["A"])
    assert resp.json()["author_name"] == "T1"


def test_teacher_cannot_create_for_other_class(client, world):
    assert client.post("/api/records", json=_new(world, "B"), headers=world.h("t1")).status_code == 403


@pytest.mark.parametrize("who,level", [("t1", 2), ("t1", 1), ("coord", 1)])
def test_cannot_publish_above_own_level(client, world, who, level):
    assert client.post("/api/records", json=_new(world, level=level), headers=world.h(who)).status_code == 403


def test_coordination_can_create_follow_up(client, world):
    resp = client.post("/api/records", json=_new(world, "B", level=2, kind="follow_up"), headers=world.h("coord"))
    assert resp.status_code == 201


def test_only_author_edits_and_author_or_admin_deletes(client, world):
    rid = world.records["a_t1"]
    assert client.patch(f"/api/records/{rid}", json={"text_content": "x"}, headers=world.h("admin")).status_code == 403
    resp = client.patch(f"/api/records/{rid}", json={"text_content": "corrigido"}, headers=world.h("t1"))
    assert resp.status_code == 200 and resp.json()["text_content"] == "corrigido" and resp.json()["updated_at"]
    assert client.patch(f"/api/records/{rid}", json={"access_level": 1}, headers=world.h("t1")).status_code == 403
    # Professor não autor não remove registro de outro autor (a_admin).
    assert client.delete(f"/api/records/{world.records['a_admin']}", headers=world.h("t1")).status_code == 403
    assert client.delete(f"/api/records/{rid}", headers=world.h("admin")).status_code == 204
    assert str(rid) not in _ids(client.get("/api/records", headers=world.h("t1")))
    # Registro invisível ao usuário responde 404 (não revela existência).
    assert client.patch(f"/api/records/{world.records['b_t2']}", json={"text_content": "x"},
                        headers=world.h("t1")).status_code == 404


# ---------- Alunos, matrículas e transferências ----------
def test_student_visibility(client, world):
    names = lambda who: {s["full_name"] for s in client.get("/api/students", headers=world.h(who)).json()}  # noqa: E731
    assert names("t1") == {"Aluno A"}
    assert names("secre") == {"Aluno A", "Aluno B"}
    assert names("support") == set()
    assert client.get(f"/api/students/{world.students['B']}", headers=world.h("t1")).status_code == 404
    detail = client.get(f"/api/students/{world.students['A']}", headers=world.h("t1")).json()
    assert detail["current_class_name"] == "A" and len(detail["enrollments"]) == 2


def test_create_student_with_enrollment_and_unique_identifier(client, world):
    payload = {"full_name": "Aluno Novo", "school_identifier": "ID-NEW", "class_id": str(world.classes["A"])}
    assert client.post("/api/students", json=payload, headers=world.h("t1")).status_code == 403
    resp = client.post("/api/students", json=payload, headers=world.h("secre"))
    assert resp.status_code == 201 and resp.json()["current_class_name"] == "A"
    assert client.post("/api/students", json=payload, headers=world.h("admin")).status_code == 409
    # Homônimo com outro identificador é permitido.
    payload2 = {**payload, "school_identifier": "ID-NEW-2"}
    assert client.post("/api/students", json=payload2, headers=world.h("admin")).status_code == 201


def test_transfer_preserves_history_and_moves_access(client, world):
    sid = world.students["A"]
    resp = client.post(f"/api/students/{sid}/enrollments", json={"class_id": str(world.classes["B"])},
                       headers=world.h("secre"))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["current_class_name"] == "B"
    current_year = [e for e in body["enrollments"] if e["year_label"] == "2026"]
    assert len(current_year) == 2 and sum(e["ended_at"] is None for e in current_year) == 1
    # t1 perde o aluno, mas mantém acesso aos próprios registros; t2 passa a ver o histórico do ano.
    assert _ids(client.get("/api/records", headers=world.h("t1"))) == _rec(world, "a_t1", "a_follow3")
    assert _rec(world, "a_admin", "a_t1") <= _ids(client.get("/api/records", headers=world.h("t2")))
    # Matricular de novo na mesma turma é conflito.
    assert client.post(f"/api/students/{sid}/enrollments", json={"class_id": str(world.classes["B"])},
                       headers=world.h("secre")).status_code == 409


# ---------- Turmas, anos e relatórios ----------
def test_class_listing_scope(client, world):
    names = lambda who: {c["name"] for c in client.get("/api/classes", headers=world.h(who)).json()}  # noqa: E731
    assert names("t1") == {"A"}
    assert names("admin") == {"A", "B"}
    assert names("support") == set()
    past = client.get("/api/classes", params={"academic_year_id": str(world.years["past"])}, headers=world.h("admin"))
    assert {c["name"] for c in past.json()} == {"Old"}


def test_admin_only_structure_endpoints(client, world):
    assert client.post("/api/classes", json={"name": "C", "grade_level": "EM"}, headers=world.h("t1")).status_code == 403
    assert client.post("/api/classes", json={"name": "C", "grade_level": "EM"}, headers=world.h("admin")).status_code == 201
    assert client.post("/api/classes", json={"name": "C", "grade_level": "EM"}, headers=world.h("admin")).status_code == 409
    assert client.get("/api/admin/users", headers=world.h("coord")).status_code == 403


def test_council_date_by_coordination_only(client, world):
    yid = world.years["cur"]
    assert client.patch(f"/api/academic-years/{yid}", json={"council_date": "2026-12-01"},
                        headers=world.h("coord")).status_code == 200
    assert client.patch(f"/api/academic-years/{yid}", json={"is_active": False},
                        headers=world.h("coord")).status_code == 403
    assert client.patch(f"/api/academic-years/{yid}", json={"council_date": "2026-12-01"},
                        headers=world.h("t1")).status_code == 403


def test_activating_year_deactivates_others(client, world):
    resp = client.post("/api/academic-years", json={"year_label": "2027", "is_active": True}, headers=world.h("admin"))
    assert resp.status_code == 201
    actives = [y for y in client.get("/api/academic-years", headers=world.h("admin")).json() if y["is_active"]]
    assert [y["year_label"] for y in actives] == ["2027"]
    # Sem turmas atribuídas no novo ano, o professor deixa de ver registros de rotina.
    assert _ids(client.get("/api/records", headers=world.h("t1"))) == _rec(world, "a_t1", "a_follow3")


def test_class_report(client, world):
    cid = world.classes["A"]
    coord = client.get(f"/api/classes/{cid}/report", headers=world.h("coord"))
    assert coord.status_code == 200 and coord.json()["total"] == 5  # agregado de todos os registros da turma
    assert client.get(f"/api/classes/{cid}/report", headers=world.h("t1")).json()["total"] == 3
    assert client.get(f"/api/classes/{cid}/report", headers=world.h("t2")).status_code == 403
    assert client.get(f"/api/classes/{cid}/report", headers=world.h("secre")).status_code == 403


# ---------- Mural ----------
def test_announcement_levels_and_writers(client, world):
    titles = lambda who: {a["title"] for a in client.get("/api/announcements", headers=world.h(who)).json()}  # noqa: E731
    assert titles("admin") == {"L1", "L2", "L3", "L5"}
    assert titles("coord") == {"L2", "L3", "L5"}
    assert titles("t1") == {"L3", "L5"}
    assert titles("support") == {"L5"}
    body = {"title": "Novo", "content": "x", "access_level": 3}
    assert client.post("/api/announcements", json=body, headers=world.h("t1")).status_code == 403
    assert client.post("/api/announcements", json=body, headers=world.h("secre")).status_code == 403  # nível 4 < 3
    assert client.post("/api/announcements", json={**body, "access_level": 4},
                       headers=world.h("secre")).status_code == 201


def test_announcement_edit_delete(client, world):
    created = client.post("/api/announcements", json={"title": "T", "content": "x", "access_level": 3},
                          headers=world.h("coord")).json()
    aid = created["id"]
    assert client.patch(f"/api/announcements/{aid}", json={"title": "T2"}, headers=world.h("secre")).status_code == 404
    assert client.patch(f"/api/announcements/{aid}", json={"title": "T2"}, headers=world.h("coord")).json()["title"] == "T2"
    assert client.delete(f"/api/announcements/{aid}", headers=world.h("admin")).status_code == 204
    assert aid not in _ids(client.get("/api/announcements", headers=world.h("coord")))


# ---------- Painel e auditoria ----------
def test_dashboard_is_scoped(client, world):
    t1 = client.get("/api/dashboard", headers=world.h("t1")).json()
    assert t1["student_count"] == 1 and t1["class_count"] == 1 and t1["active_year"] == "2026"
    assert {r["id"] for r in t1["recent_records"]} <= _rec(world, "a_t1", "a_admin", "a_follow3")
    support = client.get("/api/dashboard", headers=world.h("support")).json()
    assert support["recent_records"] == [] and support["records_this_month"] == 0


def test_audit_access(client, world):
    client.post("/api/records", json=_new(world), headers=world.h("t1"))
    assert client.get("/api/audit", headers=world.h("t1")).status_code == 403
    entries = client.get("/api/audit", headers=world.h("support")).json()
    assert any(e["entity"] == "record" and e["action"] == "create" for e in entries)
    assert all("Participou" not in (e["detail"] or "") for e in entries)  # sem conteúdo pedagógico na auditoria


# ---------- Usuários e vínculos ----------
def test_user_management(client, world):
    resp = client.post("/api/admin/users", json={"name": "Nova Prof", "email": "Nova@Example.com", "role": "teacher",
                                                 "class_ids": [str(world.classes["B"])]}, headers=world.h("admin"))
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["email"] == "nova@example.com" and user["access_level"] == 3 and user["classes"][0]["name"] == "B"
    resp = client.put(f"/api/admin/users/{user['id']}/assignments", json={"class_ids": [str(world.classes["A"])]},
                      headers=world.h("admin"))
    assert [c["name"] for c in resp.json()["classes"]] == ["A"]
    # Turma de outro ano junto com o ano ativo é rejeitada.
    resp = client.put(f"/api/admin/users/{user['id']}/assignments",
                      json={"class_ids": [str(world.classes["Old"])]}, headers=world.h("admin"))
    assert resp.status_code == 422
    assert client.patch(f"/api/admin/users/{world.users['admin']}", json={"active": False},
                        headers=world.h("admin")).status_code == 422
