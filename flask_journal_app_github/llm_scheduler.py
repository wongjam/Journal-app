import json
import random
import threading
import time
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dateutil import tz

from storage import (
    load_posts, load_comments, save_comments,
    load_llm_config, load_post_meta, load_categories,
    file_lock, LOCK_COMMENTS
)
from ollama_client import list_models, generate_comment


def now_local_iso() -> str:
    return datetime.now(tz=tz.tzlocal()).isoformat(timespec="seconds")


def get_post_edit_seq(post_id: str) -> int:
    meta = load_post_meta()
    m = (meta.get("meta") or {}).get(post_id) or {}
    try:
        return int(m.get("edit_seq", 0))
    except Exception:
        return 0


def get_category_name(cat_id: str) -> str:
    for c in load_categories():
        if c.get("id") == cat_id:
            return c.get("name") or cat_id
    return cat_id


def _allowed_models(cfg: Dict) -> List[str]:
    server = cfg.get("server", "127.0.0.1")
    port = int(cfg.get("port", 11434))
    allowed = cfg.get("allowed_models") or []
    try:
        all_models = list_models(server, port, timeout_sec=5.0)
    except Exception:
        return list(allowed)
    if allowed:
        allowed_set = set(allowed)
        return [m for m in all_models if m in allowed_set]
    return all_models


def _get_prompt(cfg: Dict) -> Tuple[str, str]:
    presets = cfg.get("prompt_presets") or []
    ids = cfg.get("active_prompt_preset_ids") or []
    if not ids:
        raw = (cfg.get("active_prompt_preset_id") or "").strip()
        if raw:
            ids = [x.strip() for x in raw.split(",") if x.strip()]

    chosen = None
    if ids and presets:
        idset = set(ids)
        candidates = [p for p in presets if p.get("id") in idset]
        if candidates:
            chosen = random.choice(candidates)

    if not chosen and presets:
        chosen = presets[0]

    if not chosen:
        return ("", "请阅读我的笔记并给出你的看法。")
    return (chosen.get("system") or "", chosen.get("user_prefix") or "请阅读我的笔记并给出你的看法。")

def _count_comments_for_post_model(comments: List[Dict], post_id: str, model: str, edit_seq: int) -> int:
    return sum(
        1 for c in comments
        if c.get("post_id") == post_id
        and c.get("model") == model
        and int(c.get("post_edit_seq", 0)) == int(edit_seq)
    )


def pick_post_for_model(cfg: Dict, model: str) -> Optional[Dict]:
    posts = load_posts()
    if not posts:
        return None
    posts_sorted = sorted(posts, key=lambda p: p.get("published_at", ""), reverse=True)

    comments = load_comments()
    max_default = int(cfg.get("max_comments_per_post_default", 2))
    per_model = cfg.get("max_comments_per_post_by_model") or {}
    max_per = int(per_model.get(model, max_default))

    def eligible(p):
        seq = get_post_edit_seq(p.get("id"))
        return _count_comments_for_post_model(comments, p.get("id"), model, seq) < max_per

    mode = cfg.get("random_pick_mode", "random_uncommented_first")
    eligible_posts = [p for p in posts_sorted if eligible(p)]
    if not eligible_posts:
        return None
    if mode == "latest":
        return eligible_posts[0]

    zero = []
    for p in eligible_posts:
        seq = get_post_edit_seq(p.get("id"))
        if _count_comments_for_post_model(comments, p.get("id"), model, seq) == 0:
            zero.append(p)
    if zero:
        return random.choice(zero)
    return random.choice(eligible_posts)


def add_comment(post_id: str, model: str, content: str) -> str:
    comment_id = secrets.token_urlsafe(8)
    with file_lock(LOCK_COMMENTS):
        comments = load_comments()
        comments.append({
            "id": comment_id,
            "post_id": post_id,
            "post_edit_seq": get_post_edit_seq(post_id),
            "model": model,
            "content": content,
            "created_at": now_local_iso(),
            "read": False,
        })
        save_comments(comments)
    return comment_id


def run_once_for_model(model: str) -> Dict:
    cfg = load_llm_config()
    if not cfg.get("auto_enabled", True):
        return {"ok": False, "error": "自动评论已关闭（仍可手动立即评论）"}

    server = cfg.get("server", "127.0.0.1")
    port = int(cfg.get("port", 11434))

    post = pick_post_for_model(cfg, model)
    if not post:
        return {"ok": False, "error": "没有可评论的文章（可能已达到每篇上限）"}

    system, prefix = _get_prompt(cfg)
    cat_id = post.get("category", "")
    payload = {
        "title": post.get("title", ""),
        "category_id": cat_id,
        "category_name": get_category_name(cat_id),
        "published_at": post.get("published_at", ""),
        "edit_seq": get_post_edit_seq(post.get("id")),
        "content": post.get("content", ""),
    }

    user_prompt = (
        f"{prefix}\n\n"
        f"请基于下面这条笔记的 JSON 信息进行评论与反馈（不要忽略字段）：\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
    )

    try:
        resp = generate_comment(server, port, model, system=system, user_prompt=user_prompt, timeout_sec=float(cfg.get("timeout_sec", 300)))
    except Exception as e:
        return {"ok": False, "error": f"Ollama 调用失败：{e.__class__.__name__}: {e}"}

    if not resp:
        return {"ok": False, "error": "模型没有返回内容"}

    cid = add_comment(post.get("id"), model, resp.strip())
    return {"ok": True, "post_id": post.get("id"), "comment_id": cid, "model": model}


class LLMScheduler:
    def __init__(self):
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        next_run: Dict[str, float] = {}
        # Track last state so that when the user toggles auto mode ON,
        # we can re-schedule quickly (instead of waiting for the previous
        # long interval that might have been computed hours ago).
        last_auto_enabled: Optional[bool] = None
        while not self._stop.is_set():
            cfg = load_llm_config()
            auto_enabled = bool(cfg.get("auto_enabled", True))
            if not auto_enabled:
                last_auto_enabled = False
                time.sleep(2.0)
                continue

            models = _allowed_models(cfg)
            if not models:
                time.sleep(5.0)
                continue

            # If auto mode was just turned ON, reset schedule so it can take effect
            # within a few seconds (instead of potentially waiting a long time).
            if last_auto_enabled is False:
                next_run = {}
            last_auto_enabled = True

            default_interval = int(cfg.get("default_interval_minutes", 120))
            per_model = cfg.get("interval_minutes_by_model") or {}

            now = time.time()
            for m in models:
                # First run after (re)enable: 2~20 seconds by default.
                next_run.setdefault(m, now + random.uniform(2, 20))

            for m in list(next_run.keys()):
                if m not in models:
                    del next_run[m]

            for m in models:
                if self._stop.is_set():
                    break
                if now >= next_run.get(m, now + 999999):
                    _ = run_once_for_model(m)
                    interval_min = int(per_model.get(m, default_interval))
                    interval_sec = max(60, interval_min * 60)
                    next_run[m] = time.time() + interval_sec + random.uniform(0, 15)

            time.sleep(2.0)
