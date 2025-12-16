import json
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, List

DATA_DIR = os.environ.get("JOURNAL_DATA_DIR", "data")

CATEGORIES_PATH = os.environ.get("JOURNAL_CATEGORIES_PATH", os.path.join(DATA_DIR, "categories.json"))
POSTS_PATH = os.environ.get("JOURNAL_POSTS_PATH", os.path.join(DATA_DIR, "posts.json"))

LLM_CONFIG_PATH = os.environ.get("JOURNAL_LLM_CONFIG_PATH", os.path.join(DATA_DIR, "llm_config.json"))
COMMENTS_PATH = os.environ.get("JOURNAL_COMMENTS_PATH", os.path.join(DATA_DIR, "comments.json"))
POST_META_PATH = os.environ.get("JOURNAL_POST_META_PATH", os.path.join(DATA_DIR, "post_meta.json"))

LOCK_CATEGORIES = CATEGORIES_PATH + ".lock"
LOCK_POSTS = POSTS_PATH + ".lock"
LOCK_LLM_CONFIG = LLM_CONFIG_PATH + ".lock"
LOCK_COMMENTS = COMMENTS_PATH + ".lock"
LOCK_POST_META = POST_META_PATH + ".lock"


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


@contextmanager
def file_lock(lock_path: str, timeout_sec: float = 5.0, poll_interval: float = 0.05):
    """Best-effort lock using a lockfile."""
    _ensure_dir(lock_path)
    start = time.time()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - start > timeout_sec:
                break
            time.sleep(poll_interval)
    try:
        yield
    finally:
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass


def _load_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dir(path)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: Dict[str, Any]) -> None:
    _ensure_dir(path)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def load_categories() -> List[Dict[str, Any]]:
    data = _load_json(CATEGORIES_PATH, {"version": 1, "categories": []})
    return list(data.get("categories", []))


def save_categories(categories: List[Dict[str, Any]]) -> None:
    _save_json(CATEGORIES_PATH, {"version": 1, "categories": categories})


def load_posts() -> List[Dict[str, Any]]:
    data = _load_json(POSTS_PATH, {"version": 1, "posts": []})
    return list(data.get("posts", []))


def save_posts(posts: List[Dict[str, Any]]) -> None:
    cleaned = []
    for p in posts:
        cleaned.append({
            "id": p.get("id"),
            "title": p.get("title", ""),
            "category": p.get("category", ""),
            "content": p.get("content", ""),
            "published_at": p.get("published_at", ""),
        })
    _save_json(POSTS_PATH, {"version": 1, "posts": cleaned})


def load_post_meta() -> Dict[str, Any]:
    default = {"version": 1, "meta": {}}
    return _load_json(POST_META_PATH, default)


def save_post_meta(meta: Dict[str, Any]) -> None:
    _save_json(POST_META_PATH, meta)


def load_llm_config() -> Dict[str, Any]:
    default = {
        "version": 1,
        "auto_enabled": True,
        "server": "127.0.0.1",
        "port": 11434,
        "allowed_models": [],
        "default_interval_minutes": 120,
        "interval_minutes_by_model": {},
        "max_comments_per_post_by_model": {},
        "max_comments_per_post_default": 2,
        "random_pick_mode": "random_uncommented_first",
        "prompt_presets": [],
        "active_prompt_preset_id": "",
        "active_prompt_preset_ids": [],
    }
    data = _load_json(LLM_CONFIG_PATH, default)
    if "auto_enabled" not in data:
        data["auto_enabled"] = True
    return data


def save_llm_config(cfg: Dict[str, Any]) -> None:
    _save_json(LLM_CONFIG_PATH, cfg)


def load_comments() -> List[Dict[str, Any]]:
    data = _load_json(COMMENTS_PATH, {"version": 1, "comments": []})
    return list(data.get("comments", []))


def save_comments(comments: List[Dict[str, Any]]) -> None:
    _save_json(COMMENTS_PATH, {"version": 1, "comments": comments})
