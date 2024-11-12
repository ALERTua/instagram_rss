[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua)
[![Made in Ukraine](https://img.shields.io/badge/made_in-Ukraine-ffd700.svg?labelColor=0057b7)](https://stand-with-ukraine.pp.ua)
[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)
[![Russian Warship Go Fuck Yourself](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/RussianWarship.svg)](https://stand-with-ukraine.pp.ua)

Instagram User RSS Feed Generator
---------------------------

FastAPI RSS Feed Generator for an Instagram User

.env:
```
PORT=8000

# "sessionid" cookie
SESSION_ID=123456783%1AIU7GABCDqhAB12%1A0%3ABYeDD33-3hdc3U2RlIyeS3mzfH1GDlrCST8GXqy_3g

# GET requests timeout
TIMEOUT=60

# impersonate this browser
IMPERSONATE=chrome

# max GET calls
CALLS_MAX=1

# in this period in seconds
CALLS_PERIOD=5

# retry failed GET calls after this delay in seconds
GET_RETRY_DELAY_SEC=15

# query cache duration in seconds
CACHE_DURATION=3600

# maximum responses cache quantity
MAX_CACHE_SIZE=100

VERBOSE=0
```
serves:
- /instagram/{userid_or_username}?posts=True&stories=True
- /health
