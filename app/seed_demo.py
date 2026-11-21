"""Cria dados INTEIRAMENTE FICTÍCIOS para desenvolvimento local.

Uso: python -m app.seed_demo   (aplica as migrações antes de inserir)
"""
from datetime import date

from sqlalchemy import select

from app.database import SessionLocal
from app.migrate import upgrade_head
from app.models import (
    AcademicYear, Announcement, Enrollment, PedagogicalRecord, RecordType, Role, SchoolClass, Student,
    TeachingAssignment, User,
)
from app.security import hash_password

ACCOUNTS = [
    ("Admin Demonstração", "admin@example.com", "DemoAdmin2026!", Role.admin, 1),
    ("Coordenação Demonstração", "coord@example.com", "DemoCoord2026!", Role.coordination, 2),
    ("Professora Demonstração", "prof@example.com", "DemoProf2026!", Role.teacher, 3),
    ("Professor Demonstração B", "prof2@example.com", "DemoProf2026!", Role.teacher, 3),
    ("Secretaria Demonstração", "secretaria@example.com", "DemoSecre2026!", Role.secretary, 4),
    ("Suporte Demonstração", "suporte@example.com", "DemoSuporte2026!", Role.support, 5),
]

STUDENTS = {
    "2º A": ["Ana Exemplo", "Bruno Fictício", "Carla Modelo", "Diego Teste"],
    "2º B": ["Elisa Exemplo", "Fábio Fictício", "Gabi Modelo"],
    "3º A": ["Heitor Exemplo", "Íris Fictícia", "João Modelo"],
}


def main() -> None:
    upgrade_head()
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            print("O banco já contém contas; nenhuma alteração foi feita.")
            return

        past = AcademicYear(year_label="2025", is_active=False)
        year = AcademicYear(year_label="2026", is_active=True, council_date=date(2026, 12, 4))
        db.add_all([past, year])
        db.flush()

        users = {email: User(name=n, email=email, password_hash=hash_password(pw), role=r, access_level=lvl)
                 for n, email, pw, r, lvl in ACCOUNTS}
        db.add_all(users.values())

        old_class = SchoolClass(name="1º A", grade_level="Ensino Médio", academic_year_id=past.id)
        classes = {name: SchoolClass(name=name, grade_level="Ensino Médio", academic_year_id=year.id) for name in STUDENTS}
        db.add_all([old_class, *classes.values()])
        db.flush()

        prof, prof2 = users["prof@example.com"], users["prof2@example.com"]
        db.add_all([
            TeachingAssignment(user_id=prof.id, class_id=classes["2º A"].id),
            TeachingAssignment(user_id=prof.id, class_id=classes["3º A"].id),
            TeachingAssignment(user_id=prof2.id, class_id=classes["2º B"].id),
            TeachingAssignment(user_id=prof.id, class_id=old_class.id),
        ])

        seq = 1
        students: dict[str, Student] = {}
        for cls_name, names in STUDENTS.items():
            for name in names:
                s = Student(full_name=name, school_identifier=f"DEMO-{seq:04d}")
                seq += 1
                db.add(s)
                db.flush()
                db.add(Enrollment(student_id=s.id, class_id=classes[cls_name].id, academic_year_id=year.id,
                                  started_at=date(2026, 2, 9)))
                students[name] = s
        # Histórico: Ana estava no 1º A em 2025.
        db.add(Enrollment(student_id=students["Ana Exemplo"].id, class_id=old_class.id, academic_year_id=past.id,
                          started_at=date(2025, 2, 10), ended_at=date(2025, 12, 15)))
        db.flush()

        def rec(student, cls, author, kind, level, text):
            db.add(PedagogicalRecord(student_id=students[student].id, class_id=classes[cls].id, author_id=author.id,
                                     record_type=kind, access_level=level, text_content=text))

        rec("Ana Exemplo", "2º A", prof, RecordType.positive, 3, "Exemplo fictício: apresentou o trabalho em grupo com clareza.")
        rec("Bruno Fictício", "2º A", prof, RecordType.attention, 3, "Exemplo fictício: não entregou as duas últimas atividades.")
        rec("Bruno Fictício", "2º A", prof, RecordType.attention, 3, "Exemplo fictício: chegou atrasado três vezes na semana.")
        rec("Carla Modelo", "2º A", prof, RecordType.follow_up, 3, "Exemplo fictício: combinar conversa com a família sobre frequência.")
        rec("Elisa Exemplo", "2º B", prof2, RecordType.positive, 3, "Exemplo fictício: ajudou colegas na atividade prática.")
        rec("Fábio Fictício", "2º B", prof2, RecordType.attention, 3, "Exemplo fictício: dificuldade recorrente em leitura de enunciados.")
        rec("Heitor Exemplo", "3º A", users["coord@example.com"], RecordType.follow_up, 2,
            "Exemplo fictício: encaminhado para orientação educacional.")
        db.add(PedagogicalRecord(student_id=students["Ana Exemplo"].id, class_id=old_class.id, author_id=prof.id,
                                 record_type=RecordType.positive, access_level=3,
                                 text_content="Exemplo fictício (2025): ótima evolução no segundo semestre."))

        admin, coord, secre = users["admin@example.com"], users["coord@example.com"], users["secretaria@example.com"]
        db.add_all([
            Announcement(author_id=admin.id, title="Reunião de planejamento", access_level=3,
                         content="Exemplo fictício: reunião geral na sexta-feira às 14h na sala dos professores."),
            Announcement(author_id=coord.id, title="Pauta do conselho de classe", access_level=2,
                         content="Exemplo fictício: pauta restrita à coordenação e à direção."),
            Announcement(author_id=secre.id, title="Calendário de matrículas", access_level=5,
                         content="Exemplo fictício: rematrículas abertas até o fim do mês."),
        ])
        db.commit()

    print("Banco demo criado com dados fictícios. Contas:")
    for _, email, pw, role, lvl in ACCOUNTS:
        print(f"  {role.value:<13} nível {lvl}  {email} / {pw}")


if __name__ == "__main__":
    main()
