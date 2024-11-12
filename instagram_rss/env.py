import os
from global_logger import Log
from dotenv import load_dotenv
from setuptools._distutils.util import strtobool
from instagram_rss import constants

load_dotenv()

VERBOSE = strtobool(os.getenv("VERBOSE", "0"))
log_level = Log.Levels.DEBUG if VERBOSE else Log.Levels.INFO
LOG = Log.get_logger(level=log_level)

SESSION_ID = os.getenv("SESSION_ID")
assert SESSION_ID, "SESSION_ID environment variable not set"

TIMEOUT = int(os.getenv("TIMEOUT", str(constants.TIMEOUT_DEFAULT)))
IMPERSONATE = os.getenv("IMPERSONATE", "chrome")
CALLS_MAX = int(os.getenv("CALLS_MAX", "1"))
CALLS_PERIOD = int(os.getenv("CALLS_PERIOD", "5"))
GET_RETRY_DELAY_SEC = int(os.getenv("GET_RETRY_DELAY_SEC", "15"))
