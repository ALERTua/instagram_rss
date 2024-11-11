import os

from curl_cffi import requests
from feedgen.feed import FeedGenerator
import pendulum
try:
    from exceptions import UserNotFoundError
    import constants
except:  # noqa: E722
    from .exceptions import UserNotFoundError
    from . import constants


class InstagramUserRSS:
    def __init__(self, session_id, username=None, user_id=None, timeout=None):
        assert username or user_id, "Either username or user_id must be provided"
        self._username = username
        self.session_id = session_id
        self._user_id = user_id
        self.base_url = "https://www.instagram.com/"
        self.query_hash = "58b6785bea111c67129decbe6a448951"
        self.cookies = {"sessionid": self.session_id, "ds_user_id": self.ds_user_id}
        self.impersonate = "chrome"
        self.timeout = timeout or constants.TIMEOUT_DEFAULT

    @property
    def ds_user_id(self):
        return self.session_id.split("%")[0] if self.session_id else None

    @property
    def user_id(self):
        if self._user_id:
            return self._user_id

        url = f"{self.base_url}web/search/topsearch/?query={self.username}"
        response = requests.get(url, cookies=self.cookies, impersonate=self.impersonate, timeout=self.timeout)
        data = response.json()
        for user in data["users"]:
            if user["user"]["username"].lower() == self.username.lower():
                self._user_id = user["user"]["pk"]
                return self._user_id

        raise UserNotFoundError

    @property
    def username(self):
        if not self._username:
            url = f"https://i.instagram.com/api/v1/users/{self.user_id}/info/"
            user_agent = "Instagram 356.0.0.41.101 Android (23/6.0.1; 538dpi; 1440x2560; LGE; LG-E425f; vee3e; en_US"
            response = requests.get(url, headers={"User-Agent": user_agent}, timeout=self.timeout)
            data = response.json()
            self._username = data["user"]["username"]
        return self._username

    def fetch_posts(self):
        params = {"query_hash": self.query_hash, "variables": {"id": self.user_id, "first": 10}}
        headers = {"Accept": "application/json; charset=utf-8"}
        url = f"{self.base_url}graphql/query"
        response = requests.get(url, headers=headers, impersonate=self.impersonate, timeout=self.timeout, params=params)
        assert response.headers.get("content-type", "").startswith("application/json"), "Expected JSON response"
        return response.json().get("data", {}).get("user", {}).get("edge_owner_to_timeline_media", {}).get("edges", [])

    def generate_rss_feed(self, posts):
        feed = FeedGenerator()
        feed.id(f"{self.base_url}{self.username}/")
        feed.title(f"{self.username}'s Instagram Feed")
        feed.link(href=f"{self.base_url}{self.username}/")
        feed.description(f"Instagram feed for user {self.username}")

        for post in posts:
            main_node = post["node"]
            entry = feed.add_entry()
            post_link = f"{self.base_url}p/{main_node['shortcode']}/"
            entry.id(post_link)
            entry.link(href=post_link)
            entry.author(name=self.username)
            post_title = (main_node.get("edge_media_to_caption", {}).get("edges", [{}]) or [{}])[0].get(
                "node", {}).get("text", "(no title)")
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


if __name__ == "__main__":
    a = InstagramUserRSS(session_id=os.getenv("SESSION_ID"), user_id=58622439872)
    a.get_rss()
