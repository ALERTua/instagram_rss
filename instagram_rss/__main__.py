from __future__ import annotations
import os
import logging

from fastapi import FastAPI, status, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from instagram_user_rss import InstagramUserRSS
import constants
# noinspection PyPackageRequirements
from dotenv import load_dotenv

load_dotenv()

VERBOSE = os.getenv("VERBOSE", "0")
log_level = logging.DEBUG if VERBOSE == "1" else logging.INFO

SESSION_ID = os.getenv("SESSION_ID")
assert SESSION_ID, "SESSION_ID environment variable not set"

TIMEOUT = int(os.getenv("TIMEOUT", str(constants.TIMEOUT_DEFAULT)))

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
logger.info(f"Logging level set to {'DEBUG' if log_level == logging.DEBUG else 'INFO'}")

app = FastAPI()


class HealthCheck(BaseModel):
    """Response model to validate and return when performing a health check."""

    status: str = "OK"


@app.get("/instagram/{query}")
async def instagram_query(query: str | int):
    user_id = query if query and str(query).isnumeric() else None
    username = query if query and not str(query).isnumeric() else None
    if not user_id and not username:
        return Response(
            content="Please provide a username or user_id",
            media_type="text/plain",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    instagram_rss = InstagramUserRSS(session_id=SESSION_ID, username=username, user_id=user_id, timeout=TIMEOUT)
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
    logger.info("Health check endpoint accessed")
    return HealthCheck(status="OK")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
