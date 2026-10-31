from typing import Any, Optional


class CampusOpsException(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(CampusOpsException):
    def __init__(self, message: str = "Invalid credentials or token expired", details: Optional[Any] = None):
        super().__init__(message=message, status_code=401, details=details)


class AuthorizationError(CampusOpsException):
    def __init__(self, message: str = "Permission denied for this operation", details: Optional[Any] = None):
        super().__init__(message=message, status_code=403, details=details)


class PermissionDeniedError(AuthorizationError):
    pass


class InvariantViolationError(CampusOpsException):
    def __init__(self, invariant: str, reason: str, details: Optional[Any] = None):
        message = f"Invariant Violation [{invariant}]: {reason}"
        super().__init__(message=message, status_code=409, details=details or {"invariant": invariant, "reason": reason})


class ResourceNotFoundError(CampusOpsException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(message=f"{resource} '{identifier}' not found", status_code=404)


class ConflictError(CampusOpsException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=409, details=details)


class FSMTransitionError(CampusOpsException):
    def __init__(self, from_state: str, to_state: str, role: str, reason: str = ""):
        message = f"Invalid state transition from {from_state} to {to_state} for role {role}. {reason}".strip()
        super().__init__(message=message, status_code=409, details={"from_state": from_state, "to_state": to_state, "role": role})


class InventoryShortageError(CampusOpsException):
    def __init__(self, sku: str, requested: int, available: int):
        message = f"Insufficient stock for part '{sku}': requested {requested}, available {available}"
        super().__init__(message=message, status_code=409, details={"sku": sku, "requested": requested, "available": available})


class IdempotencyConflictError(CampusOpsException):
    def __init__(self, key: str, reason: str = "Payload hash mismatch for idempotency key"):
        super().__init__(message=f"Idempotency error for key '{key}': {reason}", status_code=422, details={"idempotency_key": key})

