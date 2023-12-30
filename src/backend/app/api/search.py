from fastapi import APIRouter, Request
from typing import List, Tuple
from uuid import uuid4

from shared.models import SearchRequest, SearchResponse
from backend.app.lib import run_search


router = APIRouter()


@router.post("/search/")
def search(search_request: SearchRequest) -> SearchResponse:
    """search for movies using a natural language query"""

    search_response = run_search(chat_messages=search_request.chat_messages, user_id=search_request.user_id)
    return search_response
