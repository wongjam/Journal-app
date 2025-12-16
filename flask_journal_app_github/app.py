import os
import sys
import json
import secrets
import hashlib
import random
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    jsonify,
    send_file,
    session,
    g
)

from storage import (
    DATA_DIR,
    load_categories,
    save_categories,
    load_posts,
    save_posts,
    load_llm_config,
    save_llm_config,
    load_comments,
    save_comments,
    load_post_meta,
    save_post_meta,
    file_lock,
    LOCK_CATEGORIES,
    LOCK_POSTS,
    LOCK_LLM_CONFIG,
    LOCK_COMMENTS,
    LOCK_POST_META,
)

from ollama_client import list_models, generate_comment
from llm_scheduler import (
    LLMScheduler,
    now_local_iso,
    get_post_edit_seq,
    get_category_name,
    _get_prompt,
)

# Global scheduler instance (started lazily on first request)
scheduler = LLMScheduler()


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))
    # ===== UI language (simple i18n) =====
    SUPPORTED_LANGS = {"zh": "中文", "en": "EN"}
    TRANSLATIONS = {
    "en": {
        "📒 心得": "📒 Journal",
        "文章列表": "Posts",
        "写文章": "New Post",
        "分类管理": "Categories",
        "LLM 评论设置": "LLM Comments",
        "文件管理": "Files",
        "查看文件目录": "Open data folder",
        "远程管理文件": "Manage files",
        "切换主题": "Theme",
        "深色主题": "Dark theme",
        "浅色主题": "Light theme",
        "筛选": "Filter",
        "分类": "Category",
        "关键词": "Keyword",
        "搜索": "Search",
        "清空": "Clear",
        "全部": "All",
        "文章": "Posts",
        "这里还没有文章。": "No posts yet.",
        "点右上角“写文章”开始记录吧。": "Click “New Post” to start writing.",
        "上一页": "Prev",
        "下一页": "Next",
        "第": "Page",
        "共": "of",
        "本地 JSON 存储 · 适合个人记录": "Local JSON storage · Personal journaling",
        "我的心得": "Journal",
        "新评论": "New comments",
        "条未读": "unread",
        "评论时间：": "Comment time: ",
        "打开": "Open",
        "一键清除": "Clear all",
        "没有未读评论。": "No unread comments.",
        "目录：": "Directory: ",
        "搜索（文件名/路径）": "Search (name/path)",
        "路径": "Path",
        "大小": "Size",
        "修改时间": "Modified",
        "没有匹配的文件": "No matching files.",
        "编辑文件": "Edit file",
        "提示：保存会直接覆盖原文件。": "Tip: saving will overwrite the original file.",
        "回到首页": "Back to home",
        "页面不存在": "Page not found",
        "编辑文章": "Edit Post",
        "返回列表": "Back",
        "标题": "Title",
        "例如：今天我意识到……": "e.g., Today I realized…",
        "请选择分类": "Select a category",
        "没有合适分类？去「分类管理」新建。": "No suitable category? Create one in “Categories”.",
        "正文": "Content",
        "支持缩进：按 Tab 插入 4 个空格，也支持 Shift+Tab 反向缩进。": "Indent supported: Tab inserts 4 spaces; Shift+Tab outdents.",
        "缩进": "Indent",
        "反缩进": "Outdent",
        "插入时间": "Insert time",
        "保存": "Save",
        "未分类": "Uncategorized",
        "发表：": "Published: ",
        "编辑": "Edit",
        "删除": "Delete",
        "确定删除这篇文章吗？": "Are you sure you want to delete this post?",
        "评论": "Comments",
        "条": "items",
        "还没有评论。": "No comments yet.",
        "你可以点上面的“立即评论”，或者在「LLM 评论设置」里定时自动生成。": "You can click “Comment now” above, or enable scheduled auto-comments in “LLM Comments”.",
        "选择模型立即评论": "Choose a model to comment now",
        "🎲 随机模型": "🎲 Random model",
        "立即评论": "Comment now",
        "LLM 设置": "LLM settings",
        "回文章列表": "Back to posts",
        "新建分类": "New category",
        "分类名称": "Category name",
        "例如：读书笔记": "e.g., Reading notes",
        "分类ID/英文代号（可选）": "Category ID / slug (optional)",
        "例如：reading-notes（不填会自动生成）": "e.g., reading-notes (leave blank to auto-generate)",
        "用于URL与内部存储；建议只用字母数字、_、-。": "Used for URL & storage; use letters/numbers/_/- only.",
        "颜色": "Color",
        "#RRGGBB 或 #RGB": "#RRGGBB or #RGB",
        "添加": "Add",
        "现有分类": "Existing categories",
        "还没有分类。": "No categories yet.",
        "颜色：": "Color: ",
        "确定删除分类吗？（必须该分类下没有文章）": "Delete this category? (It must have no posts.)",
        "标题 / 正文 中搜索": "Search in title / content",
        "应用": "Apply",
        "重置": "Reset",
        "篇": "posts",
        "当前分类：": "Current category: ",
        "仅支持编辑": "Only editable:",
        "文件。": "files.",
        "Ollama / LLM 配置": "Ollama / LLM Config",
        "自动评论": "Auto comments",
        "开启": "On",
        "关闭": "Off",
        "当前自动评论状态：": "Auto-comment status: ",
        "切换失败：请检查服务是否正常运行。": "Switch failed: please check the service is running.",
        "服务器": "Server",
        "端口": "Port",
        "模型限制（可多选；不选=允许全部）": "Allowed models (multi-select; none = allow all)",
        "如果这里空白，说明当前未能拉取模型列表（可先点“测试连接”）。": "If blank, the model list couldn’t be fetched (try “Test connection”).",
        "默认频率（分钟）": "Default interval (minutes)",
        "默认每 120 分钟（=2小时）": "Default: every 120 minutes (=2 hours)",
        "每篇默认最多评论次数": "Default max comments per post",
        "挑选文章策略": "Post selection strategy",
        "优先没被评论过的文章，其次随机": "Prefer un-commented posts; otherwise random",
        "优先最新文章": "Prefer newest posts",
        "模型细化设置（可选）": "Per-model overrides (optional)",
        "你可以针对每个模型设置：间隔分钟数 / 每篇最多评论次数。": "For each model, you can set: interval minutes / max comments per post.",
        "间隔(分钟)": "Interval (min)",
        "每篇上限": "Max per post",
        "例如 120": "e.g. 120",
        "例如 2": "e.g. 2",
        "测试连接": "Test connection",
        "保存配置": "Save settings",
        "立即评论（生成一条）": "Comment now (generate one)",
        "立刻挑一篇可评论的笔记，生成 1 条评论（不会超过“每篇上限”）。": "Pick an eligible note and generate 1 comment (won’t exceed “Max per post”).",
        "评论内容：": "Comments: ",
        "提示词管理": "Prompt presets",
        "为了简单好维护，这里用“JSON 数组”编辑提示词预设（每个预设包含 id/name/system/user_prefix）。": "For simplicity, edit prompt presets as a JSON array (each has id/name/system/user_prefix).",
        "当前启用的预设 ID（可多个，用英文逗号分隔；将随机选择）": "Active preset IDs (comma-separated; randomly chosen)",
        "提示词预设（JSON 数组）": "Prompt presets (JSON array)",
        "关闭时，后台不会定时生成；但“立即评论”仍然可用。": "When off, scheduled generation stops, but “Comment now” still works.",
        "请选择": "Please select",
        "选择模型": "Model",
        "保存位置": "Storage locations",
        "LLM 设置：": "LLM settings: ",
        "下载": "Download",
        "共计": "Total",
        "已保存。": "Saved.",
        "已删除。": "Deleted.",
        "分类已添加。": "Category added.",
        "分类已删除。": "Category deleted.",
        "LLM 配置已保存。": "LLM settings saved.",
        "已清除所有新评论提醒。": "All new comment notices cleared.",
        "评论不存在或已处理。": "Comment not found or already handled.",
        "请选择模型。": "Please select a model.",
        "文章不存在。": "Post not found.",
        "没有文章可以评论。": "No posts to comment on.",
        "模型没有返回内容。": "The model returned no content.",
        "标题不能为空。": "Title cannot be empty.",
        "请选择分类。": "Please select a category.",
        "正文不能为空。": "Content cannot be empty.",
        "分类名称不能为空。": "Category name cannot be empty.",
    },
    "zh": {
        "📒 Journal": "📒 心得"
    }
}

    def get_lang() -> str:
        lang = (session.get("lang") or "").strip().lower()
        return lang if lang in SUPPORTED_LANGS else "zh"

    def t(key: str) -> str:
        if key is None:
            return ""
        lang = get_lang()
        # If key is already in the target language, return as-is
        return TRANSLATIONS.get(lang, {}).get(key, key)

    @app.before_request
    def _set_lang():
        g.lang = get_lang()

    @app.context_processor
    def _inject_i18n():
        return {"lang": getattr(g, "lang", "zh"), "t": t, "SUPPORTED_LANGS": SUPPORTED_LANGS}

    @app.get("/lang/<lang_code>")
    def set_lang(lang_code: str):
        lang_code = (lang_code or "").strip().lower()
        if lang_code in SUPPORTED_LANGS:
            session["lang"] = lang_code
        next_url = request.args.get("next") or request.referrer or url_for("index")
        return redirect(next_url)


    # ===== Background scheduler (safe for `flask run` debug reloader) =====
    def _maybe_start_scheduler() -> None:
        # Avoid double-start when debug reloader is on
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
            try:
                scheduler.start()
            except Exception:
                pass

    @app.before_request
    def _start_scheduler_once():
        if not getattr(app, "_scheduler_started", False):
            _maybe_start_scheduler()
            app._scheduler_started = True

    # ===== Helpers =====
    def slugify(s: str) -> str:
        s = (s or "").strip().lower()
        out = []
        for ch in s:
            if ch.isalnum() or ch in ("_", "-"):
                out.append(ch)
            elif ch.isspace():
                out.append("-")
        slug = "".join(out).strip("-")
        return slug[:40] if slug else "cat"

    def find_category(cat_id: str) -> Optional[dict]:
        for c in load_categories():
            if c.get("id") == cat_id:
                return c
        return None

    def unread_count() -> int:
        return sum(1 for c in load_comments() if not c.get("read", False))

    @app.context_processor
    def inject_globals():
        return {"unread_count": unread_count()}

    def allowed_models_from_cfg(cfg: Dict[str, Any]) -> List[str]:
        models = list_models(cfg.get("server", "127.0.0.1"), int(cfg.get("port", 11434)))
        allowed = cfg.get("allowed_models") or []
        if allowed:
            aset = set(allowed)
            models = [m for m in models if m in aset]
        return models

    def init_post_meta(post_id: str, content: str) -> None:
        meta = load_post_meta()
        meta.setdefault("meta", {})[post_id] = {
            "edit_seq": 0,
            "updated_at": now_local_iso(),
            "content_hash": hashlib.sha256((content or "").encode("utf-8")).hexdigest(),
        }
        save_post_meta(meta)

    def bump_post_edit_seq(post_id: str, content: str) -> int:
        meta = load_post_meta()
        m = (meta.get("meta") or {}).get(post_id) or {}
        seq = int(m.get("edit_seq", 0)) + 1
        m["edit_seq"] = seq
        m["updated_at"] = now_local_iso()
        m["content_hash"] = hashlib.sha256((content or "").encode("utf-8")).hexdigest()
        meta.setdefault("meta", {})[post_id] = m
        save_post_meta(meta)
        return seq

    def build_prompt_for_post(cfg: Dict[str, Any], post: Dict[str, Any]) -> Dict[str, str]:
        cat_id = post.get("category", "")
        payload = {
            "title": post.get("title", ""),
            "category_id": cat_id,
            "category_name": get_category_name(cat_id),
            "published_at": post.get("published_at", ""),
            "edit_seq": get_post_edit_seq(post.get("id")),
            "content": post.get("content", ""),
        }
        system, prefix = _get_prompt(cfg)
        user_prompt = (
            f"{prefix}\n\n"
            "请基于下面这条笔记的 JSON 信息进行评论与反馈（不要忽略字段）：\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
        )
        return {"system": system, "user_prompt": user_prompt}

    def add_comment_record(post_id: str, model: str, content: str) -> str:
        cid = secrets.token_urlsafe(8)
        with file_lock(LOCK_COMMENTS):
            comments = load_comments()
            comments.append(
                {
                    "id": cid,
                    "post_id": post_id,
                    "post_edit_seq": get_post_edit_seq(post_id),
                    "model": model,
                    "content": (content or "").strip(),
                    "created_at": now_local_iso(),
                    "read": False,
                }
            )
            save_comments(comments)
        return cid

    def pick_random_model(cfg: Dict[str, Any]) -> str:
        models = allowed_models_from_cfg(cfg)
        if not models:
            raise RuntimeError("没有可用模型（请检查 Ollama 是否运行，或 allowed_models 是否正确）。")
        return random.choice(models)

    # ===== Optional admin token for file management =====
    def require_admin() -> bool:
        token = (os.environ.get("JOURNAL_ADMIN_TOKEN") or "").strip()
        if not token:
            return True
        got = (request.args.get("token") or request.headers.get("X-Admin-Token") or "").strip()
        if got == token:
            return True
        abort(403)

    def _safe_data_path(rel_path: str) -> str:
        rel_path = (rel_path or "").lstrip("/\\")
        norm = os.path.normpath(rel_path)
        if norm.startswith("..") or os.path.isabs(norm):
            raise ValueError("非法路径")
        full = os.path.abspath(os.path.join(DATA_DIR, norm))
        base = os.path.abspath(DATA_DIR)
        if not (full == base or full.startswith(base + os.sep)):
            raise ValueError("非法路径")
        return full

    def _allowed_ext(path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in (".json", ".log", ".txt")

    def _human_size(n: int) -> str:
        try:
            n = int(n)
        except Exception:
            return "-"
        units = ["B", "KB", "MB", "GB", "TB"]
        x = float(n)
        for u in units:
            if x < 1024 or u == units[-1]:
                if u == "B":
                    return f"{int(x)} {u}"
                return f"{x:.2f} {u}"
            x /= 1024.0
        return f"{n} B"

    # ===== Home/List =====
    @app.get("/")
    def index():
        cats = load_categories()
        cm = {c["id"]: c for c in cats}

        cat = request.args.get("cat", "").strip()
        q = request.args.get("q", "").strip()

        posts = load_posts()
        posts.sort(key=lambda p: p.get("published_at", ""), reverse=True)

        if cat:
            posts = [p for p in posts if p.get("category") == cat]
        if q:
            ql = q.lower()
            posts = [
                p
                for p in posts
                if ql in (p.get("title", "").lower() + " " + p.get("content", "").lower())
            ]


        # Pagination
        try:
            page = int(request.args.get("page", "1"))
        except Exception:
            page = 1
        if page < 1:
            page = 1
        per_page = 8
        total = len(posts)
        pages = max(1, (total + per_page - 1) // per_page)
        if page > pages:
            page = pages
        start = (page - 1) * per_page
        end = start + per_page
        page_posts = posts[start:end]
        return render_template(
            "index.html",
            posts=page_posts,
            categories=cats,
            cat_map=cm,
            selected_cat=cat,
            q=q,
            page=page,
            pages=pages,
            total=total,
        )

    # ===== Posts =====
    @app.get("/post/new")
    def new_post():
        return render_template("editor.html", mode="new", post=None, categories=load_categories())

    @app.post("/post/new")
    def create_post():
        title = (request.form.get("title") or "").strip()
        category = (request.form.get("category") or "").strip()
        content = (request.form.get("content") or "").rstrip()

        if not title:
            flash("标题不能为空。", "danger")
            return redirect(url_for("new_post"))
        if not category:
            flash("请选择分类。", "danger")
            return redirect(url_for("new_post"))
        if not content:
            flash("正文不能为空。", "danger")
            return redirect(url_for("new_post"))
        if not find_category(category):
            flash("分类不存在（可能被删除）。请重新选择。", "danger")
            return redirect(url_for("new_post"))

        with file_lock(LOCK_POSTS):
            posts = load_posts()
            post_id = secrets.token_urlsafe(8)
            posts.append(
                {
                    "id": post_id,
                    "title": title,
                    "category": category,
                    "content": content,
                    "published_at": now_local_iso(),
                }
            )
            save_posts(posts)

        with file_lock(LOCK_POST_META):
            init_post_meta(post_id, content)

        flash("已保存。", "success")
        return redirect(url_for("view_post", post_id=post_id))

    @app.get("/post/<post_id>")
    def view_post(post_id: str):
        post = next((p for p in load_posts() if p.get("id") == post_id), None)
        if not post:
            abort(404)
        category = find_category(post.get("category", ""))

        comments = load_comments()
        post_comments = [c for c in comments if c.get("post_id") == post_id]
        post_comments.sort(key=lambda c: c.get("created_at", ""))

        cfg = load_llm_config()
        try:
            models = allowed_models_from_cfg(cfg)
        except Exception:
            models = []

        return render_template(
            "view.html",
            post=post,
            category=category,
            comments=post_comments,
            models=models,
        )

    @app.get("/post/<post_id>/edit")
    def edit_post(post_id: str):
        post = next((p for p in load_posts() if p.get("id") == post_id), None)
        if not post:
            abort(404)
        return render_template("editor.html", mode="edit", post=post, categories=load_categories())

    @app.post("/post/<post_id>/edit")
    def update_post(post_id: str):
        title = (request.form.get("title") or "").strip()
        category = (request.form.get("category") or "").strip()
        content = (request.form.get("content") or "").rstrip()

        if not title or not category or not content:
            flash("标题 / 分类 / 正文 都不能为空。", "danger")
            return redirect(url_for("edit_post", post_id=post_id))
        if not find_category(category):
            flash("分类不存在（可能被删除）。请重新选择。", "danger")
            return redirect(url_for("edit_post", post_id=post_id))

        with file_lock(LOCK_POSTS):
            posts = load_posts()
            post = next((p for p in posts if p.get("id") == post_id), None)
            if not post:
                abort(404)
            post["title"] = title
            post["category"] = category
            post["content"] = content
            save_posts(posts)

        with file_lock(LOCK_POST_META):
            bump_post_edit_seq(post_id, content)

        flash("已更新（编辑后会允许各模型再次追加评论）。", "success")
        return redirect(url_for("view_post", post_id=post_id))

    @app.post("/post/<post_id>/delete")
    def delete_post(post_id: str):
        with file_lock(LOCK_POSTS):
            posts = load_posts()
            posts = [p for p in posts if p.get("id") != post_id]
            save_posts(posts)

        with file_lock(LOCK_COMMENTS):
            comments = load_comments()
            comments = [c for c in comments if c.get("post_id") != post_id]
            save_comments(comments)

        with file_lock(LOCK_POST_META):
            meta = load_post_meta()
            mm = meta.get("meta") or {}
            if post_id in mm:
                del mm[post_id]
            meta["meta"] = mm
            save_post_meta(meta)

        flash("已删除。", "warning")
        return redirect(url_for("index"))

    # ===== Categories =====
    @app.get("/categories")
    def categories():
        return render_template("categories.html", categories=load_categories())

    @app.post("/categories")
    def create_category():
        name = (request.form.get("name") or "").strip()
        color = (request.form.get("color") or "").strip() or "#0d6efd"
        cat_id = slugify(request.form.get("id") or name)

        if not name:
            flash("分类名称不能为空。", "danger")
            return redirect(url_for("categories"))
        if not (color.startswith("#") and len(color) in (4, 7)):
            flash("颜色格式不正确，请使用 #RGB 或 #RRGGBB。", "danger")
            return redirect(url_for("categories"))

        with file_lock(LOCK_CATEGORIES):
            cats = load_categories()
            if any(c.get("id") == cat_id for c in cats):
                flash(f"分类ID已存在：{cat_id}", "danger")
                return redirect(url_for("categories"))
            cats.append({"id": cat_id, "name": name, "color": color})
            save_categories(cats)

        flash("分类已添加。", "success")
        return redirect(url_for("categories"))

    @app.post("/categories/<cat_id>/delete")
    def delete_category(cat_id: str):
        if any(p.get("category") == cat_id for p in load_posts()):
            flash("该分类下还有文章，不能删除。请先移动/删除文章。", "danger")
            return redirect(url_for("categories"))

        with file_lock(LOCK_CATEGORIES):
            cats = load_categories()
            cats = [c for c in cats if c.get("id") != cat_id]
            save_categories(cats)

        flash("分类已删除。", "warning")
        return redirect(url_for("categories"))

    # ===== Notifications =====
    @app.get("/notifications")
    def notifications():
        comments = load_comments()
        unread = [c for c in comments if not c.get("read", False)]
        posts = {p["id"]: p for p in load_posts()}
        unread.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        items = []
        for c in unread:
            p = posts.get(c.get("post_id"))
            if not p:
                continue
            items.append(
                {
                    "comment_id": c.get("id"),
                    "post_id": p.get("id"),
                    "post_title": p.get("title", ""),
                    "model": c.get("model", ""),
                    "created_at": c.get("created_at", ""),
                }
            )
        return render_template("notifications.html", items=items)

    @app.post("/notifications/clear")
    def notifications_clear():
        with file_lock(LOCK_COMMENTS):
            comments = load_comments()
            for c in comments:
                c["read"] = True
            save_comments(comments)
        flash("已清除所有新评论提醒。", "success")
        return redirect(url_for("notifications"))

    @app.get("/comment/<comment_id>/open")
    def open_comment(comment_id: str):
        with file_lock(LOCK_COMMENTS):
            comments = load_comments()
            target = next((c for c in comments if c.get("id") == comment_id), None)
            if target:
                target["read"] = True
                save_comments(comments)
                post_id = target.get("post_id")
                return redirect(url_for("view_post", post_id=post_id) + f"#c-{comment_id}")
        flash("评论不存在或已处理。", "secondary")
        return redirect(url_for("notifications"))

    # ===== Open data directory (local machine helper) =====
    @app.get("/open_data_dir")
    def open_data_dir():
        next_url = request.args.get("next") or url_for("index")
        data_dir = os.path.abspath(os.environ.get("JOURNAL_DATA_DIR", str(DATA_DIR)))
        try:
            if os.name == "nt":
                os.startfile(data_dir)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", data_dir])
            else:
                subprocess.Popen(["xdg-open", data_dir])
            # flash(f"已尝试打开目录：{data_dir}", "success")
        except Exception as e:
            flash(f"打开目录失败：{e.__class__.__name__}: {e}", "danger")
        return redirect(next_url)

    # ===== File manager (remote edit json/log/txt under DATA_DIR) =====
    @app.get("/files")
    def files():
        require_admin()

        q = (request.args.get("q") or "").strip()
        ql = q.lower()

        base = os.path.abspath(DATA_DIR)
        files_list = []

        for root, _dirs, filenames in os.walk(base):
            for fn in filenames:
                full = os.path.join(root, fn)
                if not _allowed_ext(full):
                    continue

                rel = os.path.relpath(full, base).replace("\\", "/")

                # 支持按文件名/路径搜索
                if q and ql not in rel.lower():
                    continue

                try:
                    st = os.stat(full)
                    files_list.append(
                        {
                            "path": rel,
                            # 兼容模板：既给人类可读，也给原始字节
                            "size": int(st.st_size),
                            "size_h": _human_size(st.st_size),
                            # 兼容模板：给格式化字符串，同时也给时间戳
                            "mtime_ts": int(st.st_mtime),
                            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                except Exception:
                    continue

        # 最近修改的排前
        files_list.sort(key=lambda x: x.get("mtime_ts", 0), reverse=True)

        # ✅关键：模板大概率用 files 变量名，这里同时传 files 和 items（不破坏旧模板）
        return render_template("files.html", files=files_list, items=files_list, base_dir=base, q=q)

    @app.get("/files/edit")
    def file_edit():
        require_admin()
        rel = request.args.get("path", "")
        try:
            full = _safe_data_path(rel)
        except Exception:
            abort(400)
        if not _allowed_ext(full) or not os.path.isfile(full):
            abort(404)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            flash(f"读取失败：{e.__class__.__name__}: {e}", "danger")
            return redirect(url_for("files"))
        return render_template("file_edit.html", path=rel, content=content)

    @app.post("/files/edit")
    def file_edit_save():
        require_admin()
        rel = (request.form.get("path") or "").strip()
        body = request.form.get("content") or ""
        try:
            full = _safe_data_path(rel)
        except Exception:
            abort(400)
        if not _allowed_ext(full):
            abort(403)
        if not os.path.isfile(full):
            abort(404)
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(body)
            flash("已保存。", "success")
        except Exception as e:
            flash(f"保存失败：{e.__class__.__name__}: {e}", "danger")
        return redirect(url_for("file_edit", path=rel))

    @app.get("/files/download")
    def file_download():
        require_admin()
        rel = request.args.get("path", "")
        try:
            full = _safe_data_path(rel)
        except Exception:
            abort(400)
        if not _allowed_ext(full) or not os.path.isfile(full):
            abort(404)
        return send_file(full, as_attachment=True, download_name=os.path.basename(full))

    # ===== LLM Settings =====
    @app.get("/llm")
    def llm_settings():
        cfg = load_llm_config()
        models: List[str] = []
        error = None
        try:
            models = list_models(cfg.get("server", "127.0.0.1"), int(cfg.get("port", 11434)))
        except Exception as e:
            error = f"无法连接 Ollama：{e.__class__.__name__}: {e}"
        prompt_presets_text = json.dumps(cfg.get("prompt_presets") or [], ensure_ascii=False, indent=2)
        return render_template(
            "llm.html",
            cfg=cfg,
            models=models,
            error=error,
            prompt_presets_text=prompt_presets_text,
        )

    @app.post("/llm/test")
    def llm_test_connection():
        cfg = load_llm_config()
        try:
            models = list_models(cfg.get("server", "127.0.0.1"), int(cfg.get("port", 11434)))
            flash(f"连接成功，检测到 {len(models)} 个模型。", "success")
        except Exception as e:
            flash(f"连接失败：{e.__class__.__name__}: {e}", "danger")
        return redirect(url_for("llm_settings"))

    @app.post("/llm/toggle_auto")
    def llm_toggle_auto():
        with file_lock(LOCK_LLM_CONFIG):
            cfg = load_llm_config()
            cfg["auto_enabled"] = not bool(cfg.get("auto_enabled", True))
            save_llm_config(cfg)
        flash(
            "自动评论已开启。" if cfg["auto_enabled"] else "自动评论已关闭（仍可手动立即评论）。",
            "success" if cfg["auto_enabled"] else "warning",
        )
        return redirect(url_for("llm_settings"))

    # ===== LLM Auto Toggle (AJAX/JSON, no full page refresh) =====
    @app.post("/api/llm/auto_enabled")
    def api_llm_set_auto_enabled():
        """Set auto_enabled quickly from a UI switch.

        Body JSON: {"enabled": true/false}
        If omitted, it toggles.
        """
        payload = request.get_json(silent=True) or {}
        want = payload.get("enabled", None)
        with file_lock(LOCK_LLM_CONFIG):
            cfg = load_llm_config()
            if want is None:
                cfg["auto_enabled"] = not bool(cfg.get("auto_enabled", True))
            else:
                cfg["auto_enabled"] = bool(want)
            save_llm_config(cfg)
        return jsonify({"ok": True, "auto_enabled": bool(cfg.get("auto_enabled", True))})

    @app.post("/llm/save")
    def llm_save():
        with file_lock(LOCK_LLM_CONFIG):
            cfg = load_llm_config()
            cfg["server"] = (request.form.get("server") or "127.0.0.1").strip()
            cfg["port"] = int(request.form.get("port") or 11434)
            cfg["allowed_models"] = [x.strip() for x in request.form.getlist("allowed_models") if x.strip()]

            cfg["default_interval_minutes"] = int(request.form.get("default_interval_minutes") or 120)
            cfg["max_comments_per_post_default"] = int(request.form.get("max_comments_per_post_default") or 2)
            cfg["random_pick_mode"] = (request.form.get("random_pick_mode") or "random_uncommented_first").strip()

            intervals: Dict[str, int] = {}
            maxes: Dict[str, int] = {}
            for k, v in request.form.items():
                if k.startswith("interval__") and v.strip():
                    m = k[len("interval__") :]
                    intervals[m] = int(v)
                if k.startswith("max__") and v.strip():
                    m = k[len("max__") :]
                    maxes[m] = int(v)
            cfg["interval_minutes_by_model"] = intervals
            cfg["max_comments_per_post_by_model"] = maxes

            presets_json = (request.form.get("prompt_presets_json") or "").strip()
            if presets_json:
                try:
                    presets = json.loads(presets_json)
                    if isinstance(presets, list):
                        cfg["prompt_presets"] = presets
                except Exception:
                    flash("提示词 JSON 解析失败：请检查格式（必须是 JSON 数组）。", "danger")
                    return redirect(url_for("llm_settings"))

            ids_raw = (request.form.get("active_prompt_preset_id") or "").strip()
            cfg["active_prompt_preset_id"] = ids_raw
            cfg["active_prompt_preset_ids"] = [x.strip() for x in ids_raw.split(",") if x.strip()]

            save_llm_config(cfg)

        flash("LLM 配置已保存。", "success")
        return redirect(url_for("llm_settings"))

    # ===== LLM Run Now (Fallback POST, no JS needed) =====
    @app.post("/llm/run_now")
    def llm_run_now_fallback():
        cfg = load_llm_config()
        model = (request.form.get("model") or "").strip()
        if not model:
            flash("请选择模型。", "danger")
            return redirect(url_for("llm_settings"))

        if model == "random":
            model = pick_random_model(cfg)

        posts = load_posts()
        if not posts:
            flash("没有文章可以评论。", "warning")
            return redirect(url_for("llm_settings"))
        posts.sort(key=lambda p: p.get("published_at", ""), reverse=True)
        post = posts[0]

        try:
            prompt = build_prompt_for_post(cfg, post)
            resp = generate_comment(
                cfg.get("server", "127.0.0.1"),
                int(cfg.get("port", 11434)),
                model,
                system=prompt["system"],
                user_prompt=prompt["user_prompt"],
                timeout_sec=1800.0,
            )
            if not resp:
                flash("模型没有返回内容。", "danger")
                return redirect(url_for("llm_settings"))
            add_comment_record(post.get("id"), model, resp)
            flash(f"{model} 评论完成：{post.get('title', '')}", "success")
            return redirect(url_for("view_post", post_id=post.get("id")))
        except Exception as e:
            flash(f"评论失败：{e.__class__.__name__}: {e}", "danger")
            return redirect(url_for("llm_settings"))

    @app.post("/post/<post_id>/llm_run_now")
    def llm_run_now_for_post_fallback(post_id: str):
        cfg = load_llm_config()
        model = (request.form.get("model") or "").strip()
        if not model:
            flash("请选择模型。", "danger")
            return redirect(url_for("view_post", post_id=post_id))

        if model == "random":
            model = pick_random_model(cfg)

        post = next((p for p in load_posts() if p.get("id") == post_id), None)
        if not post:
            flash("文章不存在。", "danger")
            return redirect(url_for("index"))

        try:
            prompt = build_prompt_for_post(cfg, post)
            resp = generate_comment(
                cfg.get("server", "127.0.0.1"),
                int(cfg.get("port", 11434)),
                model,
                system=prompt["system"],
                user_prompt=prompt["user_prompt"],
                timeout_sec=1800,
            )
            if not resp:
                flash("模型没有返回内容。", "danger")
                return redirect(url_for("view_post", post_id=post_id))
            cid = add_comment_record(post_id, model, resp)
            flash(f"{model} 评论完成。", "success")
            return redirect(url_for("view_post", post_id=post_id) + f"#c-{cid}")
        except Exception as e:
            flash(f"评论失败：{e.__class__.__name__}: {e}", "danger")
            return redirect(url_for("view_post", post_id=post_id))

    # ===== LLM Run Now APIs (used by JS for toasts) =====
    @app.post("/api/llm/run_now")
    def api_llm_run_now():
        model = (request.json or {}).get("model", "")
        cfg = load_llm_config()
        if model == "random":
            model = pick_random_model(cfg)

        posts = load_posts()
        if not posts:
            return jsonify({"ok": False, "message": "没有文章可以评论", "model": model}), 400
        posts.sort(key=lambda p: p.get("published_at", ""), reverse=True)
        post = posts[0]

        try:
            prompt = build_prompt_for_post(cfg, post)
            resp = generate_comment(
                cfg.get("server", "127.0.0.1"),
                int(cfg.get("port", 11434)),
                model,
                system=prompt["system"],
                user_prompt=prompt["user_prompt"],
                timeout_sec=1800,
            )
            if not resp:
                return jsonify({"ok": False, "message": "模型没有返回内容", "model": model}), 400
            add_comment_record(post.get("id"), model, resp)
            return jsonify({"ok": True, "message": f"{model} 评论完成", "model": model, "post_id": post.get("id")})
        except Exception as e:
            return jsonify({"ok": False, "message": f"失败：{e.__class__.__name__}: {e}", "model": model}), 500

    @app.post("/api/post/<post_id>/llm_run_now")
    def api_llm_run_now_for_post(post_id: str):
        model = (request.json or {}).get("model", "")
        cfg = load_llm_config()
        post = next((p for p in load_posts() if p.get("id") == post_id), None)
        if not post:
            return jsonify({"ok": False, "message": "文章不存在", "model": model}), 404

        if model == "random":
            model = pick_random_model(cfg)

        try:
            prompt = build_prompt_for_post(cfg, post)
            resp = generate_comment(
                cfg.get("server", "127.0.0.1"),
                int(cfg.get("port", 11434)),
                model,
                system=prompt["system"],
                user_prompt=prompt["user_prompt"],
                timeout_sec=1800,
            )
            if not resp:
                return jsonify({"ok": False, "message": "模型没有返回内容", "model": model}), 400
            cid = add_comment_record(post_id, model, resp)
            return jsonify(
                {
                    "ok": True,
                    "message": f"{model} 评论完成",
                    "model": model,
                    "post_id": post_id,
                    "comment_id": cid,
                }
            )
        except Exception as e:
            return jsonify({"ok": False, "message": f"失败：{e.__class__.__name__}: {e}", "model": model}), 500

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app


# For `flask run` (e.g. FLASK_APP=app:app)
app = create_app()


if __name__ == "__main__":
    # When running directly: python app.py
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5006)), debug=True)