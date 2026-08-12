import math

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.schemas import Page


def paginate(
    db: Session,
    query: Select,
    page: int,
    page_size: int,
    sort: str,
    filters: dict[str, str | bool | None],
    unique: bool = False,
) -> Page:
    total = db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    ) or 0
    result = db.scalars(query.offset((page - 1) * page_size).limit(page_size))
    items = list(result.unique() if unique else result)
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
        sort=sort,
        filters={key: value for key, value in filters.items() if value is not None and value != ""},
    )
