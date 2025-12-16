\
# PowerShell: Windows 打包（需在 Windows 上运行）
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller

pyinstaller -F -n JournalApp app.py `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --add-data "data;data"
