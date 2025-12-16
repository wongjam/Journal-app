# Flask 心得小站（分类/文章 分文件 JSON 存储版）

## 运行（开发模式）
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
打开： http://127.0.0.1:5000

## 数据文件
- `data/categories.json`：分类数据（名称、颜色、ID）
- `data/posts.json`：文章数据（**仅**包含：标题、分类、正文、发表时间）

> 文章文件字段固定为：`title`, `category`, `content`, `published_at`（以及内部用的 `id`）
> 你要求“主 json 只保存 标题/分类/正文/发表时间”，我已做到：不再保存 updated_at 等字段。

## 打包成可执行程序（PyInstaller）
PyInstaller 需要在目标系统上打包：

macOS/Linux：
```bash
pip install pyinstaller
pyinstaller -F -n JournalApp app.py --add-data "templates:templates" --add-data "static:static" --add-data "data:data"
```

Windows（PowerShell）注意 `;`：
```powershell
pip install pyinstaller
pyinstaller -F -n JournalApp app.py --add-data "templates;templates" --add-data "static;static" --add-data "data;data"
```


## LLM 自动评论（Ollama）
- 配置页：`/llm`
- 配置文件：`data/llm_config.json`
- 评论文件：`data/comments.json`


## 查看文件目录
导航栏右上角新增按钮「查看文件目录」，会尝试用系统文件管理器打开 `data/` 目录（Linux: xdg-open / macOS: open / Windows: explorer）。
