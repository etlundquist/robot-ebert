from fastapi import APIRouter
from typing import List, Optional

from app.models import Recommendation
from app.lib.utils import get_user_recs, get_query_recs, get_user_query_recs
from app.constants import collaborative_index, content_index


router = APIRouter()


@router.get("/recs/", status_code=200)
def get_recs(user_id: Optional[str] = None, query: Optional[str] = None, k: int = 10) -> List[Recommendation]:
    """get recommended movies for a given user and/or query"""

    if user_id and query:
        recs = get_user_query_recs(collaborative_index, content_index, user_id, query, k)
    elif user_id and not query:
        recs = get_user_recs(collaborative_index, user_id, k)
    elif query and not user_id:
        recs = get_query_recs(content_index, query, k)
    else:
        raise ValueError("either [user_id] or [query] must be included in the request as query parameters")
    return recs
