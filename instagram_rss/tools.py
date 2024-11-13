import re
from ratelimit import limits, sleep_and_retry, RateLimitException
from curl_cffi import requests
from instagram_rss import env
from global_logger import Log

LOG = Log.get_logger()
_POST_QUERYHASH = None
POST_QUERYHASH_DEFAULT = "58b6785bea111c67129decbe6a448951"


def post_queryhash():
    global _POST_QUERYHASH  # noqa: PLW0603
    if _POST_QUERYHASH:
        return _POST_QUERYHASH

    LOG.debug("Fetching post queryhash")
    url = "https://www.instagram.com/static/bundles/es6/Consumer.js/260e382f5182.js"

    response = requests.get(url)
    html_body = response.text

    # noinspection RegExpRedundantEscape
    match = re.search(r'l\.pagination\},queryId:"(.*?)"', html_body, re.IGNORECASE | re.DOTALL)
    if match:
        _POST_QUERYHASH = match.group(1)
    return _POST_QUERYHASH or POST_QUERYHASH_DEFAULT


@sleep_and_retry
@limits(calls=env.CALLS_MAX, period=env.CALLS_PERIOD, raise_on_limit=True)
def get(*args, **kwargs) -> requests.Response:
    allowed_codes = kwargs.pop("allowed_codes", [])
    sleep_time = env.GET_RETRY_DELAY_SEC
    try:
        response = requests.get(*args, timeout=env.TIMEOUT, impersonate=env.IMPERSONATE, **kwargs)
    except Exception as e:
        msg = f"Exception while Requesting {args}: {type(e)} {e}. Retrying in {sleep_time} seconds"
        LOG.exception(msg, exc_info=e)
        raise RateLimitException(msg, sleep_time)  # noqa: B904

    if response is None:
        msg = f"Empty response for {args}. Retrying in {sleep_time} seconds"
        LOG.debug(msg)
        raise RateLimitException(msg, sleep_time)

    if (status := response.status_code) in (401, *allowed_codes):
        reason = response.reason
        if not reason and response.json():
            reason = response.json().get("message")
        msg = f"Request status {status}:{reason} for {args}. Retrying in {sleep_time} seconds"
        LOG.error(msg)
        raise RateLimitException(msg, sleep_time)

    return response
