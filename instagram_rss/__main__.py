from __future__ import annotations
import os
import time
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, status, Response, Query
from fastapi.responses import RedirectResponse
from instaloader import Instaloader, TwoFactorAuthRequiredException, Profile
from pydantic import BaseModel
from dataclasses import dataclass
from global_logger import Log
from pyotp import TOTP

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


cache = LRUCache(max_size=env.MAX_CACHE_SIZE, duration=env.CACHE_DURATION)


class HealthCheck(BaseModel):
    status: str = "OK"


@app.get("/instagram/{query}")
async def instagram_query(  # noqa: PLR0913
    query: str | int | None,
    user_id: str | None = Query(default=None),
    username: str | None = Query(default=None),
    posts: bool | None = Query(default=env.POSTS),
    posts_limit: int | None = Query(default=env.POSTS_LIMIT),
    reels: bool | None = Query(default=env.REELS),
    reels_limit: int | None = Query(default=env.REELS_LIMIT),
    stories: bool | None = Query(default=env.STORIES),
    tagged: bool | None = Query(default=env.TAGGED),
    tagged_limit: int | None = Query(default=env.TAGGED_LIMIT),
):
    user_id = user_id if user_id else (query if str(query).isnumeric() else None)
    username = username if username else (query if not str(query).isnumeric() else None)
    if not any([user_id, username]):
        return Response(
            content="Please provide a username or user_id",
            media_type="text/plain",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    cache_key = (
        f"{query}-{user_id}-{username}-{posts}-{posts_limit}-{reels}-{reels_limit}{stories}-{tagged}-{tagged_limit}"
    )
    cached_response = cache.get(cache_key)
    if cached_response:
        return Response(content=cached_response, media_type="application/xml", status_code=status.HTTP_200_OK)

    il = Instaloader()  # https://instaloader.github.io/as-module.html
    logged_in = False
    if Path(env.IG_SESSION_FILEPATH).exists():
        il.load_session_from_file(env.IG_USERNAME, env.IG_SESSION_FILEPATH)
        logged_in = il.test_login()

    if not logged_in:
        try:
            il.login(env.IG_USERNAME, env.IG_PASSWORD)
        except TwoFactorAuthRequiredException:  # TODO: check IG_OTP is set
            totp = TOTP(env.IG_OTP)
            otp = totp.now()
            il.two_factor_login(otp)

        logged_in = True
        il.save_session_to_file(env.IG_SESSION_FILEPATH)

    if not logged_in:
        LOG.error("Login failed")
        return Response(content="Login failed", status_code=status.HTTP_401_UNAUTHORIZED)

    if user_id:
        profile = Profile.from_id(il.context, user_id)
    else:
        profile = Profile.from_username(il.context, username)
        user_id = profile.userid
        url = (
            f"/instagram/{user_id}"
            f"?posts={posts}&posts_limit={posts_limit}"
            f"&reels={reels}&reels_limit={reels_limit}"
            f"&stories={stories}"
            f"&tagged={tagged}&tagged_limit={tagged_limit}"
        )
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    rss = InstagramUserRSS(profile=profile, il=il)
    rss_content = rss.get_rss(
        posts=posts,
        posts_limit=posts_limit,
        reels=reels,
        reels_limit=reels_limit,
        stories=stories,
        tagged=tagged,
        tagged_limit=tagged_limit,
    )
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
