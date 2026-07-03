from typing import Any

from sqlalchemy import asc, desc
from sqlalchemy.orm import Query


def apply_search(query: Query, columns: list[Any], search: str | None) -> Query:
    if not search:
        return query
    like = f"%{search.strip()}%"
    criteria = [column.ilike(like) for column in columns]
    return query.filter(criteria[0] | criteria[1] if len(criteria) == 2 else criteria[0]) if len(criteria) <= 2 else query.filter(criteria[0] | criteria[1] | criteria[2])


def apply_sort(query: Query, model: Any, sort: str | None, direction: str = "asc") -> Query:
    if not sort or not hasattr(model, sort):
        return query
    column = getattr(model, sort)
    return query.order_by(desc(column) if direction == "desc" else asc(column))


def paginate(query: Query, page: int, page_size: int) -> tuple[list[Any], int]:
    page = max(page, 1)
    total = query.count()
    return query.offset((page - 1) * page_size).limit(page_size).all(), total
