from __future__ import annotations
import os
import time
from collections import OrderedDict
from fastapi import FastAPI, status, Response, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from dataclasses import dataclass
from global_logger import Log
from instagram_rss import env
from instagram_rss.instagram_user_rss import InstagramUserRSS

LOG = Log.get_logger()
app = FastAPI()


@dataclass
class CacheItem:
    """Data structure for an item in the LRU cache."""

    data: str
    timestamp: float  # Timestamp when the item was added to cache


class LRUCache:
    def __init__(self, max_size: int, duration: int):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.duration = duration

    def get(self, key: str) -> str | None:
        item = self.cache.get(key)
        if item:
            if time.time() - item.timestamp < self.duration:
                self.cache.move_to_end(key)  # Mark as recently accessed
                LOG.debug("Returning cached response")
                return item.data

            del self.cache[key]  # Remove expired item
        return None

    def set(self, key: str, value: str):
        if key in self.cache:
            self.cache.move_to_end(key)  # Update order if key exists
        elif len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # Remove oldest item if max size reached
        self.cache[key] = CacheItem(data=value, timestamp=time.time())


# Initialize cache with max size and duration
cache = LRUCache(max_size=env.MAX_CACHE_SIZE, duration=env.CACHE_DURATION)


class HealthCheck(BaseModel):
    status: str = "OK"


@app.get("/instagram/{query}")
async def instagram_query(
    query: str | int | None,
    user_id: str | None = Query(default=None),
    username: str | None = Query(default=None),
    stories: bool | None = Query(default=True),
    posts: bool | None = Query(default=True),
):
    user_id = user_id if user_id else (query if str(query).isnumeric() else None)
    username = username if username else (query if not str(query).isnumeric() else None)
    if not any([user_id, username]):
        return Response(
            content="Please provide a username or user_id",
            media_type="text/plain",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    cache_key = f"{query}-{user_id}-{username}-{posts}-{stories}"
    cached_response = cache.get(cache_key)
    if cached_response:
        return Response(content=cached_response, media_type="application/xml", status_code=status.HTTP_200_OK)

    instagram_rss = InstagramUserRSS(session_id=env.SESSION_ID, username=username, user_id=user_id, timeout=env.TIMEOUT)
    if not user_id:
        user_id = instagram_rss.user_id
        return RedirectResponse(
            url=f"/instagram/{user_id}?posts={posts}&stories={stories}",
            status_code=status.HTTP_302_FOUND,
        )

    rss_content = instagram_rss.get_rss(posts=posts, stories=stories)
    cache.set(cache_key, rss_content)
    return Response(content=rss_content, media_type="application/xml", status_code=status.HTTP_200_OK)


@app.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
def get_health() -> HealthCheck:
    """
    ## Perform a Health Check
    Endpoint to perform a healthcheck on. This endpoint can primarily be used Docker
    to ensure a robust container orchestration and management is in place. Other
    services which rely on proper functioning of the API service will not deploy if this
    endpoint returns any other HTTP status code except 200 (OK).

    Returns
    -------
        HealthCheck: Returns a JSON response with the health status

    """
    LOG.debug("Health check endpoint accessed")
    return HealthCheck(status="OK")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
