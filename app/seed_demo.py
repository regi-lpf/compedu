"""Cria dados inteiramente fictícios para desenvolvimento local."""
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Announcement, PedagogicalRecord, RecordType, Role, SchoolClass, Student, User
from app.security import hash_password


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            print("O banco já contém contas; nenhuma alteração foi feita.")
            return

        turma = SchoolClass(name="Turma Demo A", year="2º ano")
        db.add(turma)
        db.flush()

        admin = User(name="Admin Demonstração", email="admin@example.com", password_hash=hash_password("DemoAdmin2026!"), role=Role.admin, access_level=1)
        teacher = User(name="Professora Demonstração", email="prof@example.com", password_hash=hash_password("DemoProf2026!"), role=Role.teacher, access_level=3, classes=[turma])
        coord = User(name="Coordenação Demonstração", email="coord@example.com", password_hash=hash_password("DemoCoord2026!"), role=Role.coordination, access_level=2)
        student = Student(name="Estudante Exemplo", school_class=turma)
        db.add_all([admin, teacher, coord, student])
        db.flush()

        db.add_all([
            PedagogicalRecord(student_id=student.id, author_id=teacher.id, kind=RecordType.positive,
                              access_level=3,
                              body="Exemplo fictício: participou da atividade em grupo."),
            PedagogicalRecord(student_id=student.id, author_id=coord.id, kind=RecordType.follow_up,
                              access_level=2,
                              body="Exemplo fictício: combinar acompanhamento com a equipe."),
            Announcement(author_id=admin.id, title="Comunicado de demonstração", access_level=1,
                         body="Este comunicado contém somente dados fictícios.",
                         ),
        ])
        db.commit()
    print("Banco demo criado com dados fictícios.")
    print("Contas: admin@example.com / DemoAdmin2026! | prof@example.com / DemoProf2026! | coord@example.com / DemoCoord2026!")


if __name__ == "__main__":
    main()
