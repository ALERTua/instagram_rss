from __future__ import annotations
import pendulum
from datetime import datetime
from itertools import islice
from typing import TYPE_CHECKING
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from instagram_rss import env, constants
from global_logger import Log

if TYPE_CHECKING:
    from instaloader import Profile, NodeIterator, Post, Story, PostSidecarNode, Instaloader, StoryItem

LOG = Log.get_logger()
TZ = pendulum.tz.local_timezone()
BASE_URL = "https://www.instagram.com/"


def rss_image(url, i, post_link):
    _link = f"{post_link}?img_index={i+1}"
    return f'<br><br><img src="{url}"/><a href="{_link}">{_link}</a>'


def rss_image_story(url, story_link):
    return f'<br><br><img src="{url}"/><a href="{story_link}">{story_link}</a>'


def rss_video(url):
    return f'<br><br><video controls><source src="{url}" type="video/mp4"></video>'


def profile_link(username):
    return f'<a href="{BASE_URL}{username}">@{username.lstrip('@')}</a>'


def link(url, text):
    return f'<a href="{url}">{text}</a>'


class InstagramUserRSS:
    def __init__(self, profile: Profile, il: Instaloader):
        assert profile, "profile must be provided"
        self.profile: Profile = profile
        self.il: Instaloader = il
        self.base_url = BASE_URL

    @property
    def url(self):
        return f"{self.base_url}{self.profile.username}"

    def generate_rss_feed(  # noqa: PLR0915, PLR0913, PLR0912, C901
        self,
        posts: NodeIterator[Post] | None = None,
        posts_limit: int = constants.POSTS_LIMIT_DEFAULT,
        reels: NodeIterator[Post] | None = None,
        reels_limit: int = constants.REELS_LIMIT_DEFAULT,
        stories: NodeIterator[Story] | None = None,
        tagged: NodeIterator[Post] | None = None,
        tagged_limit: int = constants.TAGGED_LIMIT_DEFAULT,
    ):
        posts_limit = posts_limit or constants.POSTS_LIMIT_DEFAULT
        reels_limit = reels_limit or constants.REELS_LIMIT_DEFAULT
        tagged_limit = tagged_limit or constants.TAGGED_LIMIT_DEFAULT
        LOG.info(f"Generating RSS feed for {self.profile.username} ({self.profile.userid})")
        feed = FeedGenerator()
        feed.id(self.url)
        feed.title(self.profile.username)
        if self.profile.biography:
            feed.subtitle(self.profile.biography)
        feed.description(self.profile.biography or "(no biography)")
        feed.link(href=self.url)
        if self.profile.profile_pic_url_no_iphone:
            feed.icon(self.profile.profile_pic_url_no_iphone)
            feed.logo(self.profile.profile_pic_url_no_iphone)

        entries: list[FeedEntry] = []

        if not posts and not reels and not stories and self.profile.is_private:
            LOG.info(f"No posts or private profile: {self.profile.username} ({self.profile.userid})")
            entry = FeedEntry()
            entry.id(feed.id())
            entry.link(feed.link())
            entry.author(name=self.profile.full_name)
            content = (
                f"{self.profile.username} private: {self.profile.is_private}"
                f" followed: {self.profile.followed_by_viewer}"
            )
            entry.title(content)
            entry.content(content)
            post_date = datetime.fromtimestamp(pendulum.now(TZ).timestamp(), tz=TZ)
            entry.published(post_date)
            entry.updated(post_date)
            entries.append(entry)
        else:
            all_posts = []
            if posts:
                LOG.info(f"Getting first {posts_limit} posts for {self.profile.username} ({self.profile.userid})")
                posts_limited = list(islice(posts, posts_limit))
                all_posts.extend(posts_limited)
            if reels:
                LOG.info(f"Getting first {reels_limit} reels for {self.profile.username} ({self.profile.userid})")
                reels_limited = list(islice(reels, reels_limit))
                all_posts.extend(reels_limited)
            if tagged:
                LOG.info(f"Getting first {tagged_limit} tagged posts for {self.profile.username} {self.profile.userid}")
                tagged_limited = list(islice(tagged, tagged_limit))
                all_posts.extend(tagged_limited)

            LOG.info(f"Parsing results for {self.profile.username} ({self.profile.userid})")
            for i, post in enumerate(all_posts):
                LOG.info(f"Parsing result {i+1}/{len(all_posts)} for {self.profile.username} ({self.profile.userid})")
                entry = FeedEntry()
                post_link = f"{self.base_url}p/{post.shortcode}/"
                entry.id(post_link)
                entry.link(href=post_link)
                entry.author(name=post.owner_username)
                if post.owner_username == self.profile.username:
                    post_type = "post"
                else:
                    post_type = f"tagged post by {profile_link(post.owner_username)}"

                caption = post.caption or "(no caption)"
                caption_clean = caption.replace("\n", " ")
                if len(caption_clean) > 200:  # noqa: PLR2004
                    caption_clean = caption_clean[:100] + "..."
                entry_caption = f"{self.profile.username} {post_type}: {caption_clean}"
                entry.title(entry_caption)
                entry.source(url=post_link, title=caption_clean)
                post_date = post.date_local
                entry.published(post_date)
                entry.updated(post_date)
                post_content = f"{profile_link(self.profile.username)} {link(post_link, post_type)}<br>{caption}"

                if post.tagged_users:
                    tagged_users_str = [profile_link(_) for _ in post.tagged_users]
                    post_content += "<br>" + "<br>".join(tagged_users_str)

                if post.typename == "GraphSidecar":
                    if post.mediacount > 0:
                        sidecar_nodes = post.get_sidecar_nodes()
                        for j, sidecar_node in enumerate(sidecar_nodes):
                            sidecar_node: PostSidecarNode
                            if sidecar_node.is_video:
                                post_content += rss_video(sidecar_node.video_url)
                            else:
                                post_content += rss_image(sidecar_node.display_url, j, post_link)
                elif post.typename == "GraphImage":
                    post_content += rss_image(post.url, 1, post_link)
                elif post.typename == "GraphVideo":
                    post_content += rss_video(post.video_url)
                else:
                    LOG.error(f"Warning: {post} has unknown typename: {post.typename}")

                entry.content(post_content, type="html")
                entries.append(entry)

        if stories:
            LOG.info(f"Parsing stories for {self.profile.username} ({self.profile.userid})")
            for story in stories:
                story: Story
                for story_item in story.get_items():
                    story_item: StoryItem

                    entry = FeedEntry()
                    story_link = f"{self.base_url}stories/{self.profile.username}/{story_item.mediaid}/"
                    entry.id(story_link)
                    entry.link(href=story_link)
                    entry.author(name=story.owner_username)
                    title = f"{story.owner_username} story"
                    entry.title(title)
                    entry.source(url=story_link, title=title)
                    post_content = f'{profile_link(story.owner_username)} {link(story_link, "story")}<br>{title}'
                    post_date = story_item.date_local
                    entry.published(post_date)
                    entry.updated(post_date)
                    if story_item.is_video:
                        post_content += rss_video(story_item.video_url)
                    else:
                        post_content += rss_image_story(story_item.url, story_link)

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

    def get_rss(  # noqa: PLR0913
        self,
        posts=True,
        reels=True,
        stories=True,
        tagged=False,
        posts_limit=constants.POSTS_LIMIT_DEFAULT,
        reels_limit=constants.REELS_LIMIT_DEFAULT,
        tagged_limit=constants.TAGGED_LIMIT_DEFAULT,
    ):
        posts = self.profile.get_posts() if posts else None
        reels = self.profile.get_reels() if reels else None
        stories = self.il.get_stories([self.profile.userid]) if stories else None
        tagged = self.profile.get_tagged_posts() if tagged else None
        return self.generate_rss_feed(
            posts=posts,
            posts_limit=posts_limit,
            reels=reels,
            reels_limit=reels_limit,
            stories=stories,
            tagged=tagged,
            tagged_limit=tagged_limit,
        )
