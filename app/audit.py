from sqlalchemy.orm import Session

from app.models import AuditLog, User


def audit(db: Session, actor: User | None, action: str, entity: str, entity_id=None, detail: str | None = None) -> None:
    """Adiciona uma entrada de auditoria à transação corrente (o commit fica a cargo do chamador)."""
    db.add(AuditLog(actor_id=actor.id if actor else None, action=action, entity=entity,
                    entity_id=str(entity_id) if entity_id is not None else None,
                    detail=detail[:255] if detail else None))
