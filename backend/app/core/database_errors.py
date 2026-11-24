"""Classification helpers for database failures wrapped by drivers and middleware."""

import errno
import socket
from collections.abc import Iterator

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError


def exception_chain(error: BaseException) -> Iterator[BaseException]:
    """Walk common wrapper links, including Python 3.11 exception groups."""
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        pending.extend(
            item for item in (
                getattr(current, "__cause__", None),
                getattr(current, "__context__", None),
                getattr(current, "orig", None),
            ) if isinstance(item, BaseException)
        )
        pending.extend(getattr(current, "exceptions", ()))


def database_sqlstate(error: BaseException) -> str | None:
    for item in exception_chain(error):
        code = getattr(item, "sqlstate", None) or getattr(item, "pgcode", None)
        if code:
            return str(code)
    return None


def is_database_unavailable(error: BaseException) -> bool:
    connection_errnos = {
        errno.ECONNREFUSED, errno.ETIMEDOUT, errno.EHOSTUNREACH,
        errno.ENETUNREACH, errno.ECONNRESET, errno.EPIPE,
    }
    for item in exception_chain(error):
        err_msg = str(item).lower()
        if "no such table" in err_msg or "no such column" in err_msg:
            return False
        if isinstance(item, (OperationalError, InterfaceError)):
            if any(marker in err_msg for marker in ("connection", "connect", "timeout", "refused", "unreachable", "closed")):
                return True
            if "sqlite" in err_msg and not any(marker in err_msg for marker in ("locked", "busy", "unable to open")):
                return False
            return True
        if isinstance(item, DBAPIError) and item.connection_invalidated:
            return True
        if isinstance(item, (ConnectionError, TimeoutError, socket.gaierror)):
            return True
        if isinstance(item, OSError) and (
            item.errno in connection_errnos
            or "connect call failed" in err_msg
            or "connection refused" in err_msg
        ):
            return True
        # Drivers can expose connection failures through their own exception
        # classes, sometimes hidden inside ExceptionGroup wrappers.
        module = type(item).__module__.lower()
        name = type(item).__name__.lower()
        if ("asyncpg" in module or "psycopg" in module) and any(
            marker in name for marker in ("connection", "interface", "timeout")
        ):
            return True
    return False


def database_error_response_code(error: BaseException) -> str | None:
    sqlstate = database_sqlstate(error)
    if sqlstate in {"42P01", "42703"}:
        return "DATABASE_SCHEMA_MISMATCH"
    if sqlstate and sqlstate.startswith("28"):
        return "DATABASE_AUTHENTICATION_FAILED"
    if sqlstate == "3D000":
        return "DATABASE_NOT_FOUND"
    for item in exception_chain(error):
        msg = str(item).lower()
        if "no such table" in msg or "no such column" in msg:
            return "DATABASE_SCHEMA_MISMATCH"
    if is_database_unavailable(error):
        return "DATABASE_UNAVAILABLE"
    return None
