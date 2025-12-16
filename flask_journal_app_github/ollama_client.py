import requests
import threading
import os
from datetime import datetime
from typing import Dict, List


# =========================
# 基础工具
# =========================

def base_url(server: str, port: int) -> str:
    server = (server or "").strip() or "127.0.0.1"
    return f"http://{server}:{int(port)}"


def _ensure_data_dir() -> str:
    """
    确保 data 目录存在，返回日志文件路径
    """
    data_dir = os.path.abspath("data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "ollama_timeout.log")


def _log_timeout(message: str):
    """
    将超时信息追加写入 data/ollama_timeout.log
    """
    log_path = _ensure_data_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


# =========================
# Ollama API
# =========================

def list_models(server: str, port: int, timeout_sec: float = 5.0) -> List[str]:
    """
    Return model names from Ollama /api/tags
    """
    url = base_url(server, port) + "/api/tags"
    r = requests.get(url, timeout=timeout_sec)
    r.raise_for_status()
    data = r.json()
    return [m.get("name") for m in data.get("models", []) if m.get("name")]


def _do_generate(url: str, payload: Dict, timeout, result: Dict):
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        result["data"] = r.json()
    except Exception as e:
        result["error"] = e


def generate_comment(
    server: str,
    port: int,
    model: str,
    system: str,
    user_prompt: str,
    timeout_sec: float = 1800.0,  # ✅ 30 分钟硬超时
    temperature: float = 0.7,
) -> str:
    """
    Generate a single comment using Ollama /api/generate (non-stream)

    - 连接超时：5 秒
    - 总耗时硬超时：timeout_sec（默认 30 分钟）
    - 超时：控制台输出 + 写入 data/ollama_timeout.log
    """

    url = base_url(server, port) + "/api/generate"

    payload: Dict = {
        "model": model,
        "prompt": user_prompt,
        "system": system or "",
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    result: Dict = {}
    connect_timeout = 5.0
    read_timeout = timeout_sec

    t = threading.Thread(
        target=_do_generate,
        args=(url, payload, (connect_timeout, read_timeout), result),
        daemon=True,
    )
    t.start()
    t.join(timeout_sec)

    # =========================
    # 硬超时处理
    # =========================
    if t.is_alive():
        msg = (
            f"[OLLAMA][TIMEOUT] model='{model}' "
            f"hard-timeout={int(timeout_sec)}s url={url}"
        )

        # 控制台
        print(msg)

        # 写日志
        _log_timeout(msg)

        raise RuntimeError(
            f"Ollama 模型超时：{model}（超过 {int(timeout_sec)} 秒仍未返回）"
        )

    if "error" in result:
        raise result["error"]

    data = result.get("data") or {}
    return (data.get("response") or "").strip()
