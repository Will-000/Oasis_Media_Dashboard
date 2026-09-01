from sqlalchemy import select, and_, or_, func
from Tools.database import Media, session_local


def parse_media_type_filters(raw_media_type) -> list[str]:
    """ Parses for media types """
    if isinstance(raw_media_type, str):
        return [t.strip().lower() for t in raw_media_type.split(',') if t.strip()]
    elif isinstance(raw_media_type, (list, tuple, set)):
        return [str(t).strip().lower() for t in raw_media_type if str(t).strip()]
    return []


def build_base_media_query(filters: dict):
    """
    Consolidates filter parsing and builds a core select statement.
    Returns: (select_statement, search_str, active_types_list)
    """
    search_str = filters.get('search', '').strip()
    active_types = parse_media_type_filters(filters.get('media_type', 'all'))

    # Media type
    where_clauses = []
    if active_types and 'all' not in active_types:
        where_clauses.append(Media.media_type.in_(active_types))

    # Search
    if search_str:
        where_clauses.append(or_(
            Media.title.ilike(f"%{search_str}%"),
            Media.file_path.ilike(f"%{search_str}%")
        ))

    stmt = select(Media).filter(and_(*where_clauses))
    return stmt, search_str, active_types


def get_adjacent_media_id(current_id: int, delta: int, filters: dict) -> int | None:
    """ Finds adjacent file via filters """
    sort_by = filters.get('sort', 'date_desc')
    base_stmt, search_query, media_types_list = build_base_media_query(filters)

    with session_local() as db:
        # Fetch Current
        current_item = db.execute(select(Media).filter(Media.id == current_id)).scalar_one_or_none()
        if not current_item:
            return None

        # Primary Filters
        cursor_filters = []

        # Sorting
        if sort_by == 'date_desc':
            # Sorting by newest added first. Next element is OLDER than current.
            if delta == 1:
                # Next
                cursor_filters.append(or_(
                    Media.date_added < current_item.date_added,
                    and_(Media.date_added == current_item.date_added, Media.id < current_item.id)
                ))
                order_clause = [Media.date_added.desc(), Media.id.desc()]
            else:
                # Previous
                cursor_filters.append(or_(
                    Media.date_added > current_item.date_added,
                    and_(Media.date_added == current_item.date_added, Media.id > current_item.id)
                ))
                order_clause = [Media.date_added.asc(), Media.id.asc()]

        elif sort_by == 'date_asc':
            # Sorting by oldest added first. Next element is NEWER than current.
            if delta == 1:
                cursor_filters.append(or_(
                    Media.date_added > current_item.date_added,
                    and_(Media.date_added == current_item.date_added, Media.id > current_item.id)
                ))
                order_clause = [Media.date_added.asc(), Media.id.asc()]
            else:
                cursor_filters.append(or_(
                    Media.date_added < current_item.date_added,
                    and_(Media.date_added == current_item.date_added, Media.id < current_item.id)
                ))
                order_clause = [Media.date_added.desc(), Media.id.desc()]

        elif sort_by == 'title_asc':
            # Sorting alphabetically by title
            curr_title = current_item.title or current_item.file_name
            is_asc = sort_by == 'title_asc'

            if (delta == 1 and is_asc) or (delta == -1 and not is_asc):
                cursor_filters.append(or_(Media.title > curr_title, and_(Media.title == curr_title, Media.id > current_item.id)))
                order_clause = [Media.title.asc(), Media.id.asc()]
            else:
                cursor_filters.append(or_(Media.title < curr_title, and_(Media.title == curr_title, Media.id < current_item.id)))
                order_clause = [Media.title.desc, Media.id.desc()]

        elif sort_by == 'random':
            # Sort by random (seeded)
            try:
                seed_val = float(filters.get('seed', 0.5))
            except (ValueError, TypeError):
                seed_val = 0.5

            id_stmt = select(Media.id)
            if base_stmt.whereclause is not None:
                id_stmt = id_stmt.where(base_stmt.whereclause)

            bind_engine = db.get_bind().dialect.name
            if bind_engine == 'sqlite':
                random_clause = func.abs(func.sin(Media.id * seed_val))

            shuffled_ids = db.execute(id_stmt.order_by(random_clause)).scalars().all()
            try:
                idx = shuffled_ids.index(current_id) + delta
                return shuffled_ids[idx] if 0 <= idx < len(shuffled_ids) else None
            except ValueError:
                return None

        stmt = select(Media.id)
        if base_stmt.whereclause is not None:
            stmt = stmt.where(base_stmt.whereclause)

        stmt = stmt.where(and_(*cursor_filters)).order_by(*order_clause).limit(1)
        return db.execute(stmt).scalar()