from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status


def parse_date_range(from_date: str | None, to_date: str | None) -> tuple[datetime | None, datetime | None]:
    """Parse YYYY-MM-DD bounds; to_date is inclusive through end of that day."""
    from_dt = None
    to_exclusive = None

    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date must be formatted as YYYY-MM-DD",
            ) from exc

    if to_date:
        try:
            to_exclusive = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=UTC) + timedelta(days=1)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="to_date must be formatted as YYYY-MM-DD",
            ) from exc

    if from_dt and to_exclusive and from_dt >= to_exclusive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be on or before to_date",
        )

    return from_dt, to_exclusive


def default_last_n_days(n: int = 7) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=n)
    return start, end


def resolve_range(
    from_date: str | None,
    to_date: str | None,
    *,
    default_days: int = 7,
) -> tuple[datetime, datetime]:
    start, end = parse_date_range(from_date, to_date)
    if start is None and end is None:
        return default_last_n_days(default_days)
    if start is None:
        start = end - timedelta(days=default_days)
    if end is None:
        end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return start, end
