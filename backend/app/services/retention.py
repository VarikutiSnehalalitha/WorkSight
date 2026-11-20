"""Privacy-First Video & Event Metadata Retention Enforcement Service."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import RetentionPolicy, User, VisionEvent
from app.services.audit import log_audit


def run_retention_purge(db: Session, triggered_by: User = None) -> Dict[str, int]:
    """Delete expired VisionEvent metadata and any expired video files on disk."""
    settings = get_settings()
    policy = db.query(RetentionPolicy).first()
    now = datetime.now(timezone.utc)

    video_days = policy.video_retention_days if policy else settings.DEFAULT_VIDEO_RETENTION_DAYS
    event_days = policy.event_metadata_retention_days if policy else settings.DEFAULT_EVENT_RETENTION_DAYS

    # 1. Purge expired vision event metadata rows
    event_cutoff = now - timedelta(days=event_days)
    expired_events = (
        db.query(VisionEvent)
        .filter(
            (VisionEvent.expires_at != None) & (VisionEvent.expires_at < now)  # noqa: E711
            | (VisionEvent.occurred_at < event_cutoff)
        )
        .all()
    )
    deleted_events = len(expired_events)
    for ev in expired_events:
        db.delete(ev)

    # 2. Purge any expired video files from RECORDING_STORAGE_DIR
    deleted_files = 0
    storage_dir = settings.RECORDING_STORAGE_DIR
    if os.path.isdir(storage_dir):
        video_cutoff_ts = (now - timedelta(days=video_days)).timestamp()
        for root, _, files in os.walk(storage_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    if os.path.getmtime(fpath) < video_cutoff_ts:
                        os.remove(fpath)
                        deleted_files += 1
                except OSError:
                    continue

    total_deleted = deleted_events + deleted_files
    if policy:
        policy.last_purge_at = now
        policy.last_purge_deleted_count = total_deleted

    log_audit(
        db=db,
        action="retention_purge_executed",
        resource_type="retention_policy",
        resource_id=str(policy.id) if policy else None,
        details=f"Deleted {deleted_events} expired vision events and {deleted_files} expired footage files.",
        user=triggered_by,
        commit=True,
    )

    return {
        "deleted_events": deleted_events,
        "deleted_files": deleted_files,
        "total_deleted": total_deleted,
    }
