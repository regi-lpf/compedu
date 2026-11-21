"""Política de autorização do CompEdu — ponto ÚNICO de decisão de acesso.

Combina dois eixos (docs/arq-decisoes-final.md §2):
  * Vertical: nível numérico 1..5 (1 = mais alto). Usuário de nível U lê conteúdo de nível P quando P >= U.
  * Horizontal: papel + vínculo com turma no ano letivo ativo.

Matriz aplicada aos registros pedagógicos:
  * admin         — todos os registros dentro do nível.
  * coordination  — apenas registros de encaminhamento (follow_up) ou marcados com nível <= 2; relatórios
                    agregados de qualquer turma. Não recebe os registros de rotina dos professores.
  * teacher       — registros (do ano ativo) de alunos matriculados atualmente nas próprias turmas do ano ativo,
                    além dos registros de autoria própria.
  * secretary / support — sem acesso a registros pedagógicos.

Os routers NUNCA filtram por conta própria: usam as funções `scope_*` (filtro SQL) e `ensure_*` (verificação pontual).
"""
from sqlalchemy import Select, and_, false, or_, select
from sqlalchemy.orm import Session

from app.deps import forbidden
from app.models import (
    AcademicYear, Enrollment, PedagogicalRecord, RecordType, Role, SchoolClass, Student, TeachingAssignment, User,
)
from fastapi import HTTPException, status

PEDAGOGICAL_READERS = {Role.admin, Role.coordination, Role.teacher}
RECORD_WRITERS = {Role.admin, Role.coordination, Role.teacher}
ANNOUNCEMENT_WRITERS = {Role.admin, Role.coordination, Role.secretary}
SCHOOL_DATA_READERS = {Role.admin, Role.coordination, Role.secretary}  # visão global de turmas/alunos
REPORT_GLOBAL = {Role.admin, Role.coordination}
COUNCIL_EDITORS = {Role.admin, Role.coordination}
AUDIT_READERS = {Role.admin, Role.support}


# ---------- Consultas auxiliares ----------
def active_year(db: Session) -> AcademicYear | None:
    return db.scalar(select(AcademicYear).where(AcademicYear.is_active.is_(True)).limit(1))


def _active_class_ids() -> Select:
    return select(SchoolClass.id).join(AcademicYear).where(AcademicYear.is_active.is_(True))


def teacher_class_ids(user: User) -> Select:
    """Turmas do ano letivo ativo às quais o profissional está vinculado."""
    return (select(TeachingAssignment.class_id)
            .join(SchoolClass, SchoolClass.id == TeachingAssignment.class_id)
            .join(AcademicYear, AcademicYear.id == SchoolClass.academic_year_id)
            .where(TeachingAssignment.user_id == user.id, AcademicYear.is_active.is_(True)))


def _teacher_student_ids(user: User) -> Select:
    return select(Enrollment.student_id).where(Enrollment.class_id.in_(teacher_class_ids(user)),
                                               Enrollment.ended_at.is_(None))


# ---------- Filtros de escopo (aplicados em SQL) ----------
def scope_records(stmt: Select, user: User) -> Select:
    stmt = stmt.where(PedagogicalRecord.deleted_at.is_(None), PedagogicalRecord.access_level >= user.access_level)
    if user.role == Role.admin:
        return stmt
    if user.role == Role.coordination:
        return stmt.where(or_(PedagogicalRecord.record_type == RecordType.follow_up,
                              PedagogicalRecord.access_level <= 2))
    if user.role == Role.teacher:
        return stmt.where(or_(
            PedagogicalRecord.author_id == user.id,
            and_(PedagogicalRecord.student_id.in_(_teacher_student_ids(user)),
                 PedagogicalRecord.class_id.in_(_active_class_ids())),
        ))
    return stmt.where(false())


def scope_students(stmt: Select, user: User) -> Select:
    if user.role in SCHOOL_DATA_READERS:
        return stmt
    if user.role == Role.teacher:
        return stmt.where(Student.id.in_(_teacher_student_ids(user)))
    return stmt.where(false())


def scope_classes(stmt: Select, user: User) -> Select:
    if user.role in SCHOOL_DATA_READERS:
        return stmt
    if user.role == Role.teacher:
        return stmt.where(SchoolClass.id.in_(teacher_class_ids(user)))
    return stmt.where(false())


# ---------- Verificações pontuais ----------
def ensure_publish_level(user: User, level: int) -> None:
    if level < user.access_level:
        raise forbidden("Você não pode publicar em um nível mais restrito que o seu")


def can_view_student(db: Session, user: User, student_id) -> bool:
    return db.scalar(scope_students(select(Student.id).where(Student.id == student_id), user)) is not None


def can_view_class(db: Session, user: User, class_id) -> bool:
    return db.scalar(scope_classes(select(SchoolClass.id).where(SchoolClass.id == class_id), user)) is not None


def record_target_class(db: Session, user: User, student: Student):
    """Valida se o usuário pode registrar sobre o aluno e devolve a turma que contextualiza o registro."""
    if user.role not in RECORD_WRITERS:
        raise forbidden("Seu perfil não pode criar registros pedagógicos")
    enrollment = db.scalar(
        select(Enrollment).join(AcademicYear, AcademicYear.id == Enrollment.academic_year_id)
        .where(Enrollment.student_id == student.id, Enrollment.ended_at.is_(None), AcademicYear.is_active.is_(True))
    )
    if enrollment is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Aluno sem matrícula no ano letivo ativo")
    if user.role == Role.teacher and db.scalar(
            teacher_class_ids(user).where(TeachingAssignment.class_id == enrollment.class_id)) is None:
        raise forbidden("Você não está vinculado à turma deste aluno")
    return enrollment.class_id


def ensure_can_edit_record(user: User, record: PedagogicalRecord) -> None:
    if record.author_id != user.id:
        raise forbidden("Somente o autor pode editar o registro")


def ensure_can_delete_record(user: User, record: PedagogicalRecord) -> None:
    if record.author_id != user.id and user.role != Role.admin:
        raise forbidden("Somente o autor ou a administração pode remover o registro")


def ensure_announcement_writer(user: User) -> None:
    if user.role not in ANNOUNCEMENT_WRITERS:
        raise forbidden("Seu perfil não pode publicar comunicados")


def ensure_can_manage_announcement(user: User, author_id) -> None:
    if author_id != user.id and user.role != Role.admin:
        raise forbidden("Somente o autor ou a administração pode alterar o comunicado")


def ensure_can_view_report(db: Session, user: User, class_id) -> None:
    if user.role in REPORT_GLOBAL:
        return
    if user.role == Role.teacher and can_view_class(db, user, class_id):
        return
    raise forbidden("Você não tem acesso ao relatório desta turma")
