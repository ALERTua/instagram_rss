from __future__ import annotations
from zoneinfo import ZoneInfo
from datetime import datetime
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from instagram_rss import env
from global_logger import Log

LOG = Log.get_logger()


def timestamp_to_date(timestamp: str | float | None = None, _format: str = "%Y-%m-%d_%H-%M-%S") -> str:
    if isinstance(timestamp, (str, int, float)):
        timestamp = datetime.fromtimestamp(float(timestamp), tz=ZoneInfo(env.TZ))
    elif timestamp is None:
        timestamp = datetime.now(tz=ZoneInfo(env.TZ))

    return timestamp.strftime(_format)


def generate_erroreus_rss_feed(error: str):
    LOG.info(f"Generating Erroreus RSS feed with error: {error}")
    feed = FeedGenerator()
    feed.id(timestamp_to_date())
    feed.title(error)
    feed.description(error)

    entry = FeedEntry()
    entry.id(feed.id())
    entry.link(feed.link())
    content = error
    entry.title(content)
    entry.content(content)
    post_date = datetime.now(tz=ZoneInfo(env.TZ))
    entry.published(post_date)
    entry.updated(post_date)

    feed.entry([entry])

    if env.DEBUG:
        filename = "feed.atom"
        feed.atom_file(filename, pretty=True)
        import webbrowser

        webbrowser.open(filename)
    return feed.atom_str(pretty=env.DEBUG)
