from __future__ import annotations
import os
from global_logger import Log
from dotenv import load_dotenv
from setuptools._distutils.util import strtobool
from instagram_rss import constants

load_dotenv()

VERBOSE = strtobool(os.getenv("VERBOSE", "0"))
log_level = Log.Levels.DEBUG if VERBOSE else Log.Levels.INFO
LOG = Log.get_logger(level=log_level)
DEBUG = strtobool(os.getenv("DEBUG", "0"))

IG_USERNAME = os.getenv("IG_USERNAME")
assert IG_USERNAME, "IG_USERNAME environment variable not set"
IG_PASSWORD = os.getenv("IG_PASSWORD")
assert IG_PASSWORD, "IG_PASSWORD environment variable not set"
IG_OTP = os.getenv("IG_OTP")
# assert IG_OTP, "IG_OTP environment variable not set"

IG_SESSION_FILEPATH = os.getenv("IG_SESSION_FILEPATH", str(constants.IG_SESSION_FILEPATH_DEFAULT))
assert IG_SESSION_FILEPATH, "IG_SESSION_FILEPATH environment variable not set"

REDIS_URL = os.getenv("REDIS_URL", "")
PORT = os.getenv("PORT", "8000")

POSTS = strtobool(os.getenv("POSTS", str(constants.POSTS_DEFAULT)))  # posts boolean default value
POSTS_LIMIT = int(os.getenv("POSTS_LIMIT", constants.POSTS_LIMIT_DEFAULT))  # Max number of posts to fetch
REELS = strtobool(os.getenv("REELS", str(constants.REELS_DEFAULT)))  # reels boolean default value
REELS_LIMIT = int(os.getenv("REELS_LIMIT", constants.REELS_LIMIT_DEFAULT))  # Max number of reels to fetch
STORIES = strtobool(os.getenv("STORIES", str(constants.STORIES_DEFAULT)))  # stories boolean default value
TAGGED = strtobool(os.getenv("TAGGED", str(constants.TAGGED_DEFAULT)))  # tagged boolean default value
TAGGED_LIMIT = int(os.getenv("TAGGED_LIMIT", constants.TAGGED_LIMIT_DEFAULT))  # Max number of tagged posts to fetch
TZ = os.getenv("TZ", constants.TZ_DEFAULT)

CACHE_DURATION = int(os.getenv("CACHE_DURATION", "3600"))  # Cache duration in seconds
