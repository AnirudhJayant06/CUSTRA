"""Pure lease/version checks shared by transactional case operations."""

import secrets
from datetime import datetime, timedelta


class CaseConflict(ValueError):
    pass


def acquire_lease(case: dict, operation: dict, expected_version: int,
                  now: datetime, phase: str = "advance") -> dict:
    if case["currentVersion"] != expected_version:
        raise CaseConflict("Case changed; reload before retrying")
    allowed = {"PROCESSING", "ERROR"} if phase == "advance" else {"AWAITING_APPOINTMENT", "ERROR"}
    if case["status"] not in allowed or (case["status"] == "ERROR" and case.get("recoveryPhase") != phase):
        raise CaseConflict("This action is unavailable in the current case state")
    if operation.get("leaseToken") and datetime.fromisoformat(operation["expiresAt"]) > now:
        raise CaseConflict("Another request is working on this case; reload shortly")
    legacy_recovery = (phase == 'advance' and case.get('scenarioId') == 'natural'
        and operation.get('attemptCount', 0) >= 3 and not operation.get('preparation')
        and not operation.get('sendStarted') and not operation.get('legacyQuestionRecovery'))
    if operation.get("attemptCount", 0) >= 3 and not legacy_recovery:
        raise CaseConflict("Retry limit reached. Restart the failed step after checking its outcome.")
    return {**operation, **({'legacyQuestionRecovery': True} if legacy_recovery else {}), "attemptCount": operation.get("attemptCount", 0) + 1, "leaseToken": secrets.token_urlsafe(24),
            "expiresAt": (now + timedelta(seconds=60)).isoformat(), "caseVersion": expected_version}


def check_lease(case: dict, operation: dict, lease: dict, now: datetime) -> None:
    if (operation.get("leaseToken") != lease.get("leaseToken")
            or operation.get("caseVersion") != case["currentVersion"]
            or lease.get("caseVersion") != case["currentVersion"]
            or not operation.get("expiresAt")
            or datetime.fromisoformat(operation["expiresAt"]) <= now):
        raise CaseConflict("This request no longer owns the case operation")
