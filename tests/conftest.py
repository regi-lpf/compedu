import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="compedu-test-"))
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"

from dataclasses import dataclass, field  # noqa: E402
from datetime import date  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    AcademicYear, Announcement, Enrollment, PedagogicalRecord, RecordType, Role, SchoolClass, Student,
    TeachingAssignment, User,
)
from app.security import create_access_token, hash_password  # noqa: E402


@dataclass
class World:
    users: dict = field(default_factory=dict)
    classes: dict = field(default_factory=dict)
    students: dict = field(default_factory=dict)
    records: dict = field(default_factory=dict)
    years: dict = field(default_factory=dict)

    def h(self, who: str) -> dict:
        return {"Authorization": f"Bearer {create_access_token(self.users[who])}"}


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def world(client) -> World:
    w = World()
    with SessionLocal() as db:
        past = AcademicYear(year_label="2025", is_active=False)
        cur = AcademicYear(year_label="2026", is_active=True)
        db.add_all([past, cur])
        db.flush()
        w.years = {"past": past.id, "cur": cur.id}

        specs = {
            "admin": (Role.admin, 1), "coord": (Role.coordination, 2), "t1": (Role.teacher, 3),
            "t2": (Role.teacher, 3), "secre": (Role.secretary, 4), "support": (Role.support, 5),
        }
        users = {}
        for key, (role, lvl) in specs.items():
            users[key] = User(name=key.upper(), email=f"{key}@example.com", role=role, access_level=lvl,
                              password_hash=hash_password("SenhaTeste12345") if key == "admin" else None)
        db.add_all(users.values())
        cA = SchoolClass(name="A", grade_level="EM", academic_year_id=cur.id)
        cB = SchoolClass(name="B", grade_level="EM", academic_year_id=cur.id)
        cOld = SchoolClass(name="Old", grade_level="EM", academic_year_id=past.id)
        db.add_all([cA, cB, cOld])
        db.flush()
        db.add_all([TeachingAssignment(user_id=users["t1"].id, class_id=cA.id),
                    TeachingAssignment(user_id=users["t1"].id, class_id=cOld.id),
                    TeachingAssignment(user_id=users["t2"].id, class_id=cB.id)])
        sA = Student(full_name="Aluno A", school_identifier="ID-A")
        sB = Student(full_name="Aluno B", school_identifier="ID-B")
        db.add_all([sA, sB])
        db.flush()
        db.add_all([
            Enrollment(student_id=sA.id, class_id=cA.id, academic_year_id=cur.id, started_at=date(2026, 2, 1)),
            Enrollment(student_id=sB.id, class_id=cB.id, academic_year_id=cur.id, started_at=date(2026, 2, 1)),
            Enrollment(student_id=sA.id, class_id=cOld.id, academic_year_id=past.id, started_at=date(2025, 2, 1),
                       ended_at=date(2025, 12, 1)),
        ])

        def rec(key, student, cls, author, kind, level):
            r = PedagogicalRecord(student_id=student.id, class_id=cls.id, author_id=users[author].id,
                                  record_type=kind, access_level=level, text_content=f"texto {key}")
            db.add(r)
            return r

        recs = {
            "a_t1": rec("a_t1", sA, cA, "t1", RecordType.positive, 3),
            "a_admin": rec("a_admin", sA, cA, "admin", RecordType.attention, 3),
            "a_lvl1": rec("a_lvl1", sA, cA, "admin", RecordType.attention, 1),
            "a_follow": rec("a_follow", sA, cA, "coord", RecordType.follow_up, 2),
            "a_follow3": rec("a_follow3", sA, cA, "t1", RecordType.follow_up, 3),
            "b_t2": rec("b_t2", sB, cB, "t2", RecordType.attention, 3),
            "old": rec("old", sA, cOld, "admin", RecordType.positive, 3),
        }
        db.add_all([
            Announcement(author_id=users["admin"].id, title="L1", content="x", access_level=1),
            Announcement(author_id=users["coord"].id, title="L2", content="x", access_level=2),
            Announcement(author_id=users["admin"].id, title="L3", content="x", access_level=3),
            Announcement(author_id=users["secre"].id, title="L5", content="x", access_level=5),
        ])
        db.commit()
        w.users = {k: u.id for k, u in users.items()}
        w.classes = {"A": cA.id, "B": cB.id, "Old": cOld.id}
        w.students = {"A": sA.id, "B": sB.id}
        w.records = {k: r.id for k, r in recs.items()}
    return w
