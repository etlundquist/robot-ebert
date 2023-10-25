from fastapi import APIRouter
from typing import List

from app.models import SearchRequest, Recommendation
from app.lib.utils import get_search_recs


router = APIRouter()


@router.post("/search/")
def search(request: SearchRequest) -> List[Recommendation]:
    """search for movies using a natural language query"""

    search_recommendations = get_search_recs(query=request.query, user_id=request.user_id, k=request.k)
    return search_recommendations
