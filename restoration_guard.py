"""Offline restoration reconciliation. No database, network or production authorization."""
from dataclasses import dataclass
from datetime import datetime, timezone
import re

class RestorationError(ValueError):
    pass

def require(condition):
    if not condition:
        raise RestorationError('Restoration evidence incomplete or inconsistent.')

def utc(value):
    require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None)
    return value.astimezone(timezone.utc)

def digest(value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None)
    return value

@dataclass(frozen=True)
class Obligation:
    fingerprint: str
    completed_at: datetime

@dataclass(frozen=True)
class ExternalManifest:
    restore_id: str
    covered_from: datetime
    covered_until: datetime
    obligations: tuple

@dataclass(frozen=True)
class Reconciliation:
    fingerprint: str
    verified_at: datetime
    remaining_records: int


def assess_restore(*, restore_id, restored_to, restored_at, checked_at,
                   manifest, reconciliations, inventory_verified=False,
                   external_stores_verified=False, ingestion_suspended=False):
    """Evaluate synthetic evidence; never grant permission to resume processing.

    Manifest authenticity, completeness and independent retention must be
    established by a future trusted staging adapter, not by this function.
    Reconciliation records are attestations, not proof of actual erasure.
    """
    require(isinstance(restore_id,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',restore_id) is not None)
    start, restored, end = map(utc,(restored_to,restored_at,checked_at))
    require(start <= restored <= end)
    require(type(manifest) is ExternalManifest and manifest.restore_id == restore_id)
    require(utc(manifest.covered_from)<=start and utc(manifest.covered_until)>=end)
    require(type(manifest.obligations) is tuple and type(reconciliations) is tuple)
    require(len(manifest.obligations)<=10000 and len(reconciliations)<=10000)
    expected={}
    for item in manifest.obligations:
        require(type(item) is Obligation)
        key=digest(item.fingerprint); at=utc(item.completed_at)
        require(key not in expected and utc(manifest.covered_from)<=at<=end)
        # Recheck every supplied obligation, even those predating the restore point.
        expected[key]=at
    seen=set()
    for item in reconciliations:
        require(type(item) is Reconciliation)
        key=digest(item.fingerprint); at=utc(item.verified_at)
        require(key in expected and key not in seen)
        require(max(restored,expected[key])<=at<=end)
        require(type(item.remaining_records) is int and item.remaining_records==0)
        seen.add(key)
    require(seen==set(expected))
    require(inventory_verified is True and external_stores_verified is True and ingestion_suspended is True)
    return {'mode':'OFFLINE_RESTORATION_EVIDENCE_ONLY', 'evidence_consistent':True,
            'obligations_reconciled':len(seen), 'production_resume_authorized':False,
            'http_acknowledgment_authorized':False, 'database_writes':0,
            'external_manifest_authenticity_verified':False}
