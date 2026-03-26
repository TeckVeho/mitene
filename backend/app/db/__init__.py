"""Data access layer (jobs, e-learning entities)."""

from app.db.articles import get_article_by_git_path, list_articles, upsert_article
from app.db.categories import get_categories, get_category_by_slug, upsert_category
from app.db.comments import (
    comment_to_api_dict,
    create_comment,
    get_comment_row,
    list_comments_for_video,
    toggle_comment_like,
)
from app.db.connection import DATABASE_URL, close_db, init_db
from app.db.engagement import (
    get_liked_video_ids,
    get_liked_videos,
    get_video_watch_counts,
    get_watch_history,
    get_watch_later_ids,
    get_watch_later_videos,
    record_watch,
    toggle_liked_video,
    toggle_watch_later,
)
from app.db.jobs import get_raw_store, store_create, store_get, store_list, store_update
from app.db.users import get_or_create_user, get_user
from app.db.videos import (
    create_video,
    delete_video,
    get_video,
    get_video_by_job_id,
    list_videos,
    update_video,
)

__all__ = [
    "DATABASE_URL",
    "close_db",
    "comment_to_api_dict",
    "create_comment",
    "create_video",
    "delete_video",
    "get_article_by_git_path",
    "get_categories",
    "get_category_by_slug",
    "get_comment_row",
    "get_liked_video_ids",
    "get_liked_videos",
    "get_or_create_user",
    "get_raw_store",
    "get_user",
    "get_video",
    "get_video_by_job_id",
    "get_video_watch_counts",
    "get_watch_history",
    "get_watch_later_ids",
    "get_watch_later_videos",
    "init_db",
    "list_articles",
    "list_comments_for_video",
    "list_videos",
    "record_watch",
    "store_create",
    "store_get",
    "store_list",
    "store_update",
    "toggle_comment_like",
    "toggle_liked_video",
    "toggle_watch_later",
    "update_video",
    "upsert_article",
    "upsert_category",
]
