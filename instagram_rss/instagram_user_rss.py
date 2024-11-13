from __future__ import annotations
from pprint import pformat
import pendulum
from datetime import datetime

from curl_cffi import requests
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from instagram_rss.exceptions import UserNotFoundError
from instagram_rss import constants, tools, env
from global_logger import Log

LOG = Log.get_logger()
TZ = pendulum.tz.local_timezone()


class InstagramUserRSS:
    def __init__(self, session_id, username=None, user_id=None, timeout=None):
        assert username or user_id, "Either username or user_id must be provided"
        self._username = username
        self.session_id = session_id
        self._user_id = user_id
        self.base_url = "https://www.instagram.com/"
        self.cookies = {"sessionid": self.session_id, "ds_user_id": self.ds_user_id}
        self._full_name: str | None = None
        self._biography: str | None = None
        self._icon_url: str | None = None
        self._private: bool | None = None
        self._followed: bool | None = None
        self._private: bool | None = None
        self.timeout = timeout or constants.TIMEOUT_DEFAULT

    @property
    def ds_user_id(self):
        return self.session_id.split("%")[0] if self.session_id else None

    def _get_user_data(self):
        if not any([self._username, self._user_id]):
            LOG.error("Cannot get user data with no username or user_id")
            raise UserNotFoundError

        LOG.debug(f"Getting user data for {self._username or self._user_id}")
        if self._user_id:
            url = f"https://i.instagram.com/api/v1/users/{self._user_id}/info/"
            response = tools.get(url, cookies=self.cookies, headers={"User-Agent": constants.MOBILE_USER_AGENT})
            user = response.json().get("user", {})
        else:
            url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={self._username}"
            response = tools.get(url, cookies=self.cookies, headers={"User-Agent": constants.MOBILE_USER_AGENT})
            user = response.json().get("data", {}).get("user", {})

        user_id = user.get("id")
        if user_id:
            self.user_id = user_id
            self._username = user.get("username")
            self._full_name = user.get("full_name")
            self._biography = user.get("biography")
            self._followed = user.get("followed_by_viewer")
            self._private = user.get("is_private")
            self._icon_url = user.get("profile_pic_url")
            return

        LOG.error(f"{self._username or self._user_id} not found\n{pformat(user)}")
        raise UserNotFoundError

    @property
    def user_id(self):
        if self._user_id is None:
            self._get_user_data()
        return self._user_id

    @user_id.setter
    def user_id(self, value):
        self._user_id = int(value)

    @property
    def username(self):
        if self._username is None:
            self._get_user_data()
        return self._username

    @property
    def full_name(self):
        if self._full_name is None:
            self._get_user_data()
        return self._full_name

    @property
    def biography(self):
        if self._biography is None:
            self._get_user_data()
        return self._biography

    @property
    def icon_url(self):
        if self._icon_url is None:
            self._get_user_data()
        return self._icon_url

    @property
    def followed(self):
        if self._followed is None:
            self._get_user_data()
        return self._followed

    @property
    def private(self):
        if self._private is None:
            self._get_user_data()
        return self._private

    @property
    def url(self):
        return f"{self.base_url}{self.username}"

    def fetch_posts(self):
        LOG.info(f"Fetching posts for {self.username} ({self.user_id})")
        params = {"query_hash": tools.post_queryhash(), "variables": {"id": self.user_id, "first": 50}}
        headers = {"Accept": "application/json; charset=utf-8"}
        url = f"{self.base_url}graphql/query"
        response = requests.get(url, headers=headers, params=params, timeout=env.TIMEOUT, impersonate=env.IMPERSONATE)
        if response.status_code == 401:  # noqa: PLR2004
            LOG.error(
                f"Failed to get posts for {self.username} ({self.user_id}):"
                f" {response.status_code} {response.json().get("message")}",
            )
            return []

        assert response.headers.get("content-type", "").startswith("application/json"), "Expected JSON response"
        return (
            (response.json().get("data", {}).get("user", {}) or {})
            .get("edge_owner_to_timeline_media", {})
            .get("edges", [])
        )

    def fetch_stories(self):
        LOG.info(f"Fetching stories for {self.username} ({self.user_id})")
        url = f"https://i.instagram.com/api/v1/feed/user/{self.user_id}/reel_media/"
        response = tools.get(url, cookies=self.cookies, headers={"User-Agent": constants.MOBILE_USER_AGENT})
        json_data = response.json()
        return json_data.get("items", [])

    def generate_rss_feed(self, posts: list, stories: list):  # noqa: C901, PLR0912, PLR0915
        LOG.info(f"Generating RSS feed for {self.username} ({self.user_id})")
        feed = FeedGenerator()
        feed.id(self.url)
        feed.title(self.username)
        if self.biography:
            feed.subtitle(self.biography)
        feed.description(self.biography or "(no description)")
        feed.link(href=self.url)
        if self.icon_url:
            feed.icon(self.icon_url)
            feed.logo(self.icon_url)

        entries: list[FeedEntry] = []
        if not posts and self.private and not self.followed:
            LOG.info(f"No posts or private profile: {self.username} ({self.user_id})")
            entry = FeedEntry()
            entry.id(feed.id())
            entry.link(feed.link())
            entry.author(name=self.full_name)
            entry.title(f"{self.username} private: {self.private} followed: {self.followed}")
            entry.content(f"{self.username} private: {self.private} followed: {self.followed}")
            post_date = datetime.fromtimestamp(pendulum.now(TZ).timestamp(), tz=TZ)
            entry.published(post_date)
            entry.updated(post_date)
            entries.append(entry)
        else:
            if posts:
                LOG.info(f"Parsing {len(posts)} posts for {self.username} ({self.user_id})")
            for post in posts:
                main_node = post["node"]
                entry = FeedEntry()
                post_link = f"{self.base_url}p/{main_node['shortcode']}/"
                entry.id(post_link)
                entry.link(href=post_link)
                entry.author(name=self.full_name)
                post_title = (
                    (main_node.get("edge_media_to_caption", {}).get("edges", [{}]) or [{}])[0]
                    .get("node", {})
                    .get("text", "(no title)")
                )
                entry.title(post_title)
                entry.source(url=post_link, title=post_title)
                timestamp = main_node["taken_at_timestamp"]
                post_date = datetime.fromtimestamp(timestamp, tz=TZ)
                entry.published(post_date)
                entry.updated(post_date)
                children = main_node.get("edge_sidecar_to_children", {}).get("edges", [{}])
                child_nodes = [_.get("node", {}) for _ in children]
                nodes = [main_node, *child_nodes]
                nodes = [_ for _ in nodes if _]
                post_content = f"{self.username} <a href='{post_link}'>post</a><br>{post_title}"
                for i, node in enumerate(nodes):
                    if node.get("is_video"):
                        url = node["video_url"]
                        post_content += f'<br><br><video controls><source src="{url}" type="video/mp4"></video>'
                    else:
                        url = node["display_url"]
                        post_content += f'<br><br><a href="{post_link}?img_index={i+1}"><img src="{url}"/></a>'

                entry.content(post_content, type="html")
                entries.append(entry)

        if stories:
            LOG.info(f"Parsing {len(stories)} stories for {self.username} ({self.user_id})")
        for story in stories:
            entry = FeedEntry()
            story_link = f"{self.base_url}stories/{self.username}/{story['pk']}/"
            entry.id(story_link)
            entry.link(href=story_link)
            entry.author(name=self.full_name)
            title = f"{self.username} story"
            entry.title(title)
            entry.source(url=story_link, title=title)
            post_content = f'{self.username} <a href="{story_link}">story</a><br>{title}'
            timestamp = story["taken_at"]
            post_date = datetime.fromtimestamp(timestamp, tz=TZ)
            entry.published(post_date)
            entry.updated(post_date)
            video = story.get("video_versions", [{}])[0]
            if video:
                url = video["url"]
                post_content += f'<br><br><video controls><source src="{url}" type="video/mp4"></video>'
            else:
                image = story.get("image_versions2", {}).get("candidates", [{}])[0]
                if image:
                    url = image["url"]
                    post_content += f'<br><br><a href="{story_link}"><img src="{url}"/></a>'

            entry.content(post_content, type="html")
            entries.append(entry)

        entries.sort(key=lambda x: x.published(), reverse=False)
        feed.entry(entries)

        if env.DEBUG:
            filename = "feed.atom"
            feed.atom_file(filename, pretty=True)
            import webbrowser

            webbrowser.open(filename)
        return feed.atom_str(pretty=env.DEBUG)

    def get_rss(self, posts=True, stories=True):
        posts = self.fetch_posts() if posts else []
        stories = self.fetch_stories() if stories else []
        return self.generate_rss_feed(posts=posts, stories=stories)
