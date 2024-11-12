from __future__ import annotations
import os
from pprint import pformat
from feedgen.feed import FeedGenerator
import pendulum
from instagram_rss.exceptions import UserNotFoundError
from instagram_rss import constants, tools
from global_logger import Log

LOG = Log.get_logger()


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
        params = {"query_hash": constants.QUERY_HASH, "variables": {"id": self.user_id, "first": 10}}
        headers = {"Accept": "application/json; charset=utf-8"}
        url = f"{self.base_url}graphql/query"
        response = tools.get(url, headers=headers, params=params)
        assert response.headers.get("content-type", "").startswith("application/json"), "Expected JSON response"
        return response.json().get("data", {}).get("user", {}).get("edge_owner_to_timeline_media", {}).get("edges", [])

    def generate_rss_feed(self, posts):
        feed = FeedGenerator()
        feed.id(self.url)
        feed.title(self.username)
        feed.link(href=self.url)
        feed.description(self.biography or "(no description)")

        if not posts and self.private and not self.followed:
            entry = feed.add_entry()
            entry.id(feed.id())
            entry.link(feed.link())
            entry.author(name=self.full_name)
            entry.title(f"{self.username} private: {self.private} followed: {self.followed}")
            entry.content(f'<a href="{self.url}">{self.username}</a> private: {self.private} followed: {self.followed}')
            entry.published(pendulum.now())
        else:
            for post in posts:
                main_node = post["node"]
                entry = feed.add_entry()
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
                post_date = pendulum.from_timestamp(main_node["taken_at_timestamp"])
                entry.published(post_date)
                post_content_items = []
                children = main_node.get("edge_sidecar_to_children", {}).get("edges", [{}])
                child_nodes = [_.get("node", {}) for _ in children]
                nodes = [main_node, *child_nodes]
                nodes = [_ for _ in nodes if _]
                for i, node in enumerate(nodes):
                    post_content = f'<a href="{post_link}?img_index={i+1}">'

                    if node.get("is_video"):
                        post_content += f'<video controls><source src="{node["video_url"]}" type="video/mp4"></video>'
                    else:
                        post_content += f'<img src="{node["display_url"]}"/>'

                    post_content += "</a>"
                    post_content_items.append(post_content)

                entry.content("<br>".join(post_content_items))

        if os.getenv("DEBUG", "0") == "1":
            feed.rss_file("feed.xml", pretty=True)
            import webbrowser

            webbrowser.open("feed.xml")
        return feed.rss_str(pretty=True)

    def get_rss(self):
        posts = self.fetch_posts()
        return self.generate_rss_feed(posts)
