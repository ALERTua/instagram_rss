from ratelimit import limits, sleep_and_retry, RateLimitException
from curl_cffi import requests
from instagram_rss import env
from global_logger import Log

LOG = Log.get_logger()


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
