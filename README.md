# Journal App · Private Notes with Local LLM Companion

A simple, privacy-first journal / note-taking app built with Flask.  
Designed for people who want to write private notes, thoughts, or journals without cloud services, while still being able to interact with a local AI model (via Ollama) — making the writing experience feel less lonely, more reflective, and sometimes more insightful.

一个基于 Flask 的轻量级私人笔记 / 日记应用。  
专为希望不依赖云服务记录个人想法、心得和日记的人而设计，同时可在本地与 Ollama 大模型交互，让写作不再孤单，更具反思性，有时也能带来新的视角。

---

## Features | 功能特点

- **Private Notes / Journaling**  
  Create, edit, delete notes  
  Category-based organization  
  Local JSON file storage (no database)

- **Local LLM Interaction (Ollama)**  
  Optional AI-generated comments on notes  
  Fully local, offline-capable  
  No data leaves your machine

- **Privacy First**  
  No cloud sync  
  No accounts  
  No tracking

- **Bilingual UI**  
  Full Chinese / English interface  
  Dynamic messages included

- **Light / Dark Theme**  
  Manual toggle  
  Saved locally in browser

---

## Run (Development Mode) | 运行（开发模式）

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open / 打开  
http://127.0.0.1:5000

---

## Data Files | 数据文件说明

All data is stored locally under the `data/` directory.  
所有数据均保存在本地 `data/` 目录中。

- **data/categories.json**  
  Category definitions (name, color, id)  
  分类数据（名称、颜色、ID）

- **data/posts.json**  
  Journal entries (**only**: title, category, content, published_at)  
  文章数据（**仅**包含：标题、分类、正文、发表时间）

Main post fields are fixed:  
`title`, `category`, `content`, `published_at` (plus internal `id`)

---

## LLM Auto Comments (Ollama)

- Config page / 配置页面：`/llm`
- Config file / 配置文件：`data/llm_config.json`
- Comment storage / 评论文件：`data/comments.json`

The LLM runs **locally via Ollama**.  
No prompts or notes are sent to external services.

---

## Open Data Directory | 打开数据目录

The top-right navigation button **“Open Data Directory”** will attempt to open the local `data/` folder using the system file manager:

- Linux: `xdg-open`
- macOS: `open`
- Windows: `explorer`

---

## Build Executable (Optional) | 打包为可执行程序（可选）

PyInstaller must be run on the target system.

### macOS / Linux

```bash
pip install pyinstaller
pyinstaller -F -n JournalApp app.py \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "data:data"
```

### Windows (PowerShell)

```powershell
pip install pyinstaller
pyinstaller -F -n JournalApp app.py `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --add-data "data;data"
```

---

## Disclaimer | 免责声明

This project is not a cloud service and not a mental health product.  
It is intended for **personal, local use only**.

本项目不是云服务，也不构成心理健康或医疗建议，仅适合个人本地使用。

---

## License

MIT License
