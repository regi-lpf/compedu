import csv
import io

from openpyxl import Workbook
import xlwt

from app.database import SessionLocal
from app.models import AuditLog, Enrollment, Student
from app.student_imports import normalize_student_name


def _csv_upload(rows):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerows(rows)
    return {"file": ("lista.csv", output.getvalue().encode("utf-8"), "text/csv")}


def test_import_preview_normalizes_names_without_writing(client, world):
    response = client.post(
        "/api/students/import/preview",
        data={"class_id": str(world.classes["B"])},
        files=_csv_upload([
            ["Nome do aluno", "Nota"],
            ["Aluno A", "10"],
            ["José Silva", "9"],
            ["JOSE SILVA", "8"],
            ["", "7"],
        ]),
        headers=world.h("secre"),
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["new_count"], result["confirmation_count"]) == (1, 1)
    assert (result["ignored_count"], result["duplicate_count"]) == (1, 1)
    transfer = next(row for row in result["rows"] if row["status"] == "needs_confirmation")
    assert transfer["current_class_name"] == "A"
    assert transfer["student_id"] == str(world.students["A"])
    with SessionLocal() as db:
        assert db.query(Student).count() == 2
        assert db.query(AuditLog).count() == 0
        assert db.query(Enrollment).filter(Enrollment.student_id == world.students["A"],
                                           Enrollment.ended_at.is_(None)).one().class_id == world.classes["A"]


def test_import_confirmation_creates_and_transfers_only_approved_students(client, world):
    upload = _csv_upload([["Nome"], ["Aluno A"], ["Maria Silva"]])
    response = client.post(
        "/api/students/import/confirm",
        data={
            "class_id": str(world.classes["B"]),
            "confirmed_student_ids": str(world.students["A"]),
            "expected_class_ids": str(world.classes["A"]),
        },
        files=upload,
        headers=world.h("secre"),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "created_count": 1,
        "enrolled_count": 1,
        "transferred_count": 1,
        "ignored_count": 0,
        "duplicate_count": 0,
    }
    with SessionLocal() as db:
        current = db.query(Enrollment).filter(Enrollment.student_id == world.students["A"],
                                              Enrollment.ended_at.is_(None)).one()
        assert current.class_id == world.classes["B"]
        created = db.query(Student).filter(Student.full_name == "Maria Silva").one()
        assert created.school_identifier.startswith("AUTO-")
        assert db.query(Enrollment).filter(Enrollment.student_id == created.id,
                                           Enrollment.ended_at.is_(None)).one().class_id == world.classes["B"]
        logs = db.query(AuditLog).all()
        assert len(logs) == 3
        assert all("Maria Silva" not in (entry.detail or "") for entry in logs)


def test_import_confirmation_skips_unapproved_transfer(client, world):
    response = client.post(
        "/api/students/import/confirm",
        data={"class_id": str(world.classes["B"])},
        files=_csv_upload([["Nome"], ["Aluno A"]]),
        headers=world.h("admin"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["ignored_count"] == 1
    with SessionLocal() as db:
        current = db.query(Enrollment).filter(Enrollment.student_id == world.students["A"],
                                              Enrollment.ended_at.is_(None)).one()
        assert current.class_id == world.classes["A"]


def test_import_confirmation_rejects_stale_transfer_preview(client, world):
    preview = client.post(
        "/api/students/import/preview",
        data={"class_id": str(world.classes["B"])},
        files=_csv_upload([["Nome"], ["Aluno A"]]),
        headers=world.h("admin"),
    ).json()
    assert preview["rows"][0]["status"] == "needs_confirmation"

    moved = client.post(
        f"/api/students/{world.students['A']}/enrollments",
        json={"class_id": str(world.classes["B"])},
        headers=world.h("secre"),
    )
    assert moved.status_code == 201

    response = client.post(
        "/api/students/import/confirm",
        data={
            "class_id": str(world.classes["B"]),
            "confirmed_student_ids": str(world.students["A"]),
            "expected_class_ids": str(world.classes["A"]),
        },
        files=_csv_upload([["Nome"], ["Aluno A"]]),
        headers=world.h("admin"),
    )
    assert response.status_code == 409


def test_import_rejects_ambiguous_names_and_non_manager_roles(client, world):
    with SessionLocal() as db:
        db.add(Student(full_name="ÁLUNO A", school_identifier="ID-A-SECOND"))
        db.commit()

    preview = client.post(
        "/api/students/import/preview",
        data={"class_id": str(world.classes["B"])},
        files=_csv_upload([["Nome"], ["Aluno A"]]),
        headers=world.h("secre"),
    )
    assert preview.status_code == 200
    assert preview.json()["rows"][0]["status"] == "ambiguous"

    forbidden = client.post(
        "/api/students/import/preview",
        data={"class_id": str(world.classes["B"])},
        files=_csv_upload([["Nome"], ["Novo Aluno"]]),
        headers=world.h("t1"),
    )
    assert forbidden.status_code == 403


def test_xlsx_import_reads_name_column_and_ignores_other_columns(client, world):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Nota", "Nome completo", "Observação"])
    sheet.append([10, "João da Silva", "ignorada"])
    content = io.BytesIO()
    workbook.save(content)

    response = client.post(
        "/api/students/import/preview",
        data={"class_id": str(world.classes["A"])},
        files={"file": ("diario.xlsx", content.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=world.h("admin"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["rows"][0]["full_name"] == "João da Silva"
    assert response.json()["rows"][0]["status"] == "new"


def test_xls_import_reads_name_column_and_ignores_other_columns(client, world):
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("Diário")
    sheet.write(0, 0, "Nota")
    sheet.write(0, 1, "Aluno")
    sheet.write(1, 0, 10)
    sheet.write(1, 1, "Ana Souza")
    content = io.BytesIO()
    workbook.save(content)

    response = client.post(
        "/api/students/import/preview",
        data={"class_id": str(world.classes["A"])},
        files={"file": ("diario.xls", content.getvalue(), "application/vnd.ms-excel")},
        headers=world.h("admin"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["rows"][0]["full_name"] == "Ana Souza"


def test_import_limit_and_name_normalization(client, world):
    response = client.post(
        "/api/students/import/preview",
        data={"class_id": str(world.classes["A"])},
        files=_csv_upload([["Nome"], *[[f"Aluno {index}"] for index in range(61)]]),
        headers=world.h("admin"),
    )
    assert response.status_code == 422
    assert "60" in response.json()["detail"]
    assert normalize_student_name("  JOÃO   da Silva ") == normalize_student_name("Joao da Silva")
