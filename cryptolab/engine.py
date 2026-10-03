"""Calculate cliff and linear vesting, freeze accrual on revocation and reconcile beneficiary and issuer entitlements."""

from .common import (
    number,
    integer,
    identity,
    records,
    chronology,
    allocate,
    result,
    validate_document,
)
from decimal import Decimal


def _analyze(d):
    now = integer(d["now"])
    out = []
    for g in records(d["grants"], "id"):
        total = integer(g["amount"])
        start = integer(g["start"])
        end = integer(g["end"])
        cliff = integer(g["cliff"])
        claimed = integer(g["claimed"])
        if not start <= cliff <= end or end == start:
            raise ValueError("invalid schedule")
        revoked = g.get("revoked_at")
        cutoff = now if revoked is None else min(now, integer(revoked))
        if revoked is not None and revoked < start:
            raise ValueError("revocation before start")
        vested = (
            0
            if cutoff < cliff
            else total * min(max(cutoff - start, 0), end - start) // (end - start)
        )
        if claimed > vested:
            raise ValueError("claims exceed vested amount")
        refund = total - vested if revoked is not None and revoked <= now else 0
        out.append(
            {
                "id": g["id"],
                "vested": vested,
                "claimable": vested - claimed,
                "issuer_refund": refund,
                "locked": total - vested - refund,
            }
        )
    return {
        "grants": out,
        "claimable": sum(r["claimable"] for r in out),
        "refundable": sum(r["issuer_refund"] for r in out),
    }


def analyze(document):
    validate_document(document)
    try:
        return result(_analyze(document))
    except (KeyError, TypeError, ArithmeticError, RecursionError) as error:
        raise ValueError("invalid domain input: " + str(error)) from error
