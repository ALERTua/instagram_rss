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
IG_USERNAME=""  # Instagram login username (not email)
IG_PASSWORD=""  # Instagram Password
IG_OTP=""  # Instagram TOTP
POSTS="True"  # Include Posts Default Value
POSTS_LIMIT=5  # Posts Limit Default Value
REELS="True"  # Include Reels Default Value
REELS_LIMIT=5  # Reels Limit Default Value
STORIES="True"  # Include Stories Default Value
TAGGED="False"  # Include Tagged Posts Default Value
TAGGED_LIMIT=5  # Tagged Posts Limit Default Value

# query cache duration in seconds
CACHE_DURATION=3600

# maximum responses cache quantity
MAX_CACHE_SIZE=1000

VERBOSE=0
```
serves:
- /instagram/{user_id}?posts={posts}&posts_limit={posts_limit}&reels={reels}&reels_limit={reels_limit}&stories={stories}&tagged={tagged}&tagged_limit={tagged_limit}
- /health
