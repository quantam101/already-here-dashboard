from typing import Any

from models import AuditEvent, StatusEnum


async def log_audit_event(
    db,
    event_type: str,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    status: StatusEnum = StatusEnum.SUCCESS,
) -> AuditEvent:
    """
    Log an audit event to the database.
    All system actions should be audited for security and compliance.
    """
    event = AuditEvent(
        event_type=event_type,
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        metadata=metadata or {},
    )

    doc = event.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()

    await db.audit_log.insert_one(doc)
    return event
