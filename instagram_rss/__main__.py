from __future__ import annotations
import time
from pathlib import Path

from fastapi import FastAPI, status, Response, Query
from fastapi.responses import RedirectResponse
from instaloader import Instaloader, TwoFactorAuthRequiredException, Profile
from pydantic import BaseModel
from global_logger import Log
from pyotp import TOTP
from aiocache import Cache
from asyncio.exceptions import TimeoutError
from instagram_rss import env
from instagram_rss.instagram_user_rss import InstagramUserRSS

LOG = Log.get_logger()
app = FastAPI()

cache = Cache.from_url(env.REDIS_URL or "memory://")
cache.ttl = env.CACHE_DURATION
cache.timeout = 15

memory_cache = Cache.from_url("memory://")
memory_cache.ttl = env.CACHE_DURATION
memory_cache.timeout = 15

instaloader_instance = None
last_login_check_time = 0
LOGIN_CHECK_INTERVAL = 60 * 60


class HealthCheck(BaseModel):
    status: str = "OK"


async def get_cached_item(key: str) -> str | None:
    try:
        cached_data = await cache.get(key)
    except TimeoutError as e:
        LOG.error(f"{type(e)} while retrieving cached item")  # noqa: TRY400
        try:
            cached_data = await memory_cache.get(key)
        except TimeoutError as e:
            LOG.error(f"{type(e)} while retrieving cached item frrom memory")  # noqa: TRY400
            cached_data = None

    if cached_data:
        LOG.debug(f"Returning cached response for {key}")
    else:
        LOG.debug(f"No cache found for {key}")
    return cached_data


async def set_cached_item(key: str, value: str):
    try:
        await cache.set(key, value)
    except TimeoutError as e:
        LOG.error(f"{type(e)} while caching item.")  # noqa: TRY400
        try:
            await memory_cache.set(key, value)
        except TimeoutError as e:
            LOG.error(f"{type(e)} while caching item to memory.")  # noqa: TRY400
            return

    LOG.debug(f"Cached {key}")


def get_instaloader() -> Instaloader:
    """Get a singleton instance of Instaloader with periodic login validation."""
    global instaloader_instance, last_login_check_time  # noqa: PLW0603

    if instaloader_instance is None:
        instaloader_instance = Instaloader(max_connection_attempts=5)

    # Only revalidate login if interval has expired
    current_time = time.time()
    if current_time - last_login_check_time > LOGIN_CHECK_INTERVAL:
        logged_in = False
        if Path(env.IG_SESSION_FILEPATH).exists():
            instaloader_instance.load_session_from_file(env.IG_USERNAME, env.IG_SESSION_FILEPATH)
            logged_in = instaloader_instance.test_login()

        if not logged_in:
            try:
                instaloader_instance.login(env.IG_USERNAME, env.IG_PASSWORD)
            except TwoFactorAuthRequiredException:
                totp = TOTP(env.IG_OTP)
                otp = totp.now()
                instaloader_instance.two_factor_login(otp)
            instaloader_instance.save_session_to_file(env.IG_SESSION_FILEPATH)

        last_login_check_time = current_time  # Update the last login check time

    return instaloader_instance


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

    cache_key = f"{user_id}-{username}-{posts}-{posts_limit}-{reels}-{reels_limit}{stories}-{tagged}-{tagged_limit}"
    cached_response = await get_cached_item(cache_key)
    if cached_response:
        return Response(content=cached_response, media_type="application/xml", status_code=status.HTTP_200_OK)

    il = get_instaloader()  # Use the cached Instaloader instance

    if user_id:
        profile = Profile.from_id(il.context, user_id)
    else:
        profile = Profile.from_username(il.context, username)
        url = (
            f"/instagram/{profile.userid}"
            f"?posts=0"
            f"&reels=0"
            f"&tagged=0"
            f"&stories=0"
            f"&posts_limit={posts_limit}"
            f"&reels_limit={reels_limit}"
            f"&tagged_limit={tagged_limit}"
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
    await set_cached_item(cache_key, rss_content.decode() if isinstance(rss_content, bytes) else rss_content)
    return Response(content=rss_content, media_type="application/xml", status_code=status.HTTP_200_OK)


@app.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
async def get_health() -> HealthCheck:
    LOG.debug("Health check endpoint accessed")
    return HealthCheck(status="OK")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(env.PORT), log_level="info")
