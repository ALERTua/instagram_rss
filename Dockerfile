FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS production

LABEL maintainer="ALERT <alexey.rubasheff@gmail.com>"

ENV PORT=8000
ENV IG_USERNAME=""
ENV IG_PASSWORD=""
ENV IG_OTP=""
ENV IG_SESSION_FILEPATH="/data/session.json"
ENV POSTS="True"
ENV POSTS_LIMIT=5
ENV REELS="True"
ENV REELS_LIMIT=5
ENV STORIES="True"
ENV TAGGED="False"
ENV TAGGED_LIMIT=5
ENV MAX_CACHE_SIZE=1000
ENV CACHE_DURATION=3600
ENV VERBOSE=0

EXPOSE $PORT
VOLUME ["/data"]

ENV \
    # uv
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_FROZEN=1 \
    UV_NO_PROGRESS=true \
    UV_CACHE_DIR=.uv_cache \
    # Python
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    # pip
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    # app
    APP_DIR=/app \
    SOURCE_DIR_NAME=instagram_rss


WORKDIR $APP_DIR

RUN --mount=type=cache,target=$UV_CACHE_DIR \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project --no-dev

COPY $SOURCE_DIR_NAME $SOURCE_DIR_NAME

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
        CMD curl localhost:${PORT}/health || exit 1

ENTRYPOINT []

CMD uv run uvicorn $SOURCE_DIR_NAME.__main__:app --host 0.0.0.0 --port ${PORT-8000}
