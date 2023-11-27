from fastapi import APIRouter, Request
from typing import List
from uuid import uuid4

from shared.models import SearchRequest, Recommendation
from backend.app.lib import get_search_recs


router = APIRouter()


@router.post("/search/")
def search(raw_request: Request, search_request: SearchRequest) -> List[Recommendation]:
    """search for movies using a natural language query"""

    session_id = raw_request.headers.get("session-id", str(uuid4()))
    search_recommendations = get_search_recs(session_id=session_id, query=search_request.query, user_id=search_request.user_id, k=search_request.k)
    return search_recommendations
