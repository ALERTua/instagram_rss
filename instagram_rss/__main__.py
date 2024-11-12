from __future__ import annotations
import os

from fastapi import FastAPI, status, Response, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from global_logger import Log

from instagram_rss import env
from instagram_rss.instagram_user_rss import InstagramUserRSS

LOG = Log.get_logger()

app = FastAPI()


class HealthCheck(BaseModel):
    """Response model to validate and return when performing a health check."""

    status: str = "OK"


@app.get("/instagram/{query}")
async def instagram_query(
    query: str | int | None,
    user_id: str | None = Query(None),
    username: str | None = Query(None),
):
    user_id = user_id if user_id else (query if str(query).isnumeric() else None)
    username = username if username else (query if not str(query).isnumeric() else None)
    if not any([user_id, username]):
        return Response(
            content="Please provide a username or user_id",
            media_type="text/plain",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    instagram_rss = InstagramUserRSS(session_id=env.SESSION_ID, username=username, user_id=user_id, timeout=env.TIMEOUT)
    if not user_id:
        user_id = instagram_rss.user_id
        return RedirectResponse(url=f"/instagram/{user_id}", status_code=status.HTTP_302_FOUND)

    rss_content = instagram_rss.get_rss()
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
