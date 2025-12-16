(function() {
  const key = "journal_theme";
  const btn = document.getElementById("themeBtn");
  const i18n = (window.__JOURNAL_I18N || {});
  const LABEL_DARK = i18n.themeDark || "深色主题";
  const LABEL_LIGHT = i18n.themeLight || "浅色主题";

  function applyTheme(theme){
    document.documentElement.setAttribute("data-bs-theme", theme);
    localStorage.setItem(key, theme);
    if (btn) btn.textContent = theme === "dark" ? LABEL_LIGHT : LABEL_DARK;
  }

  const saved = localStorage.getItem(key);
  if (saved === "dark" || saved === "light") applyTheme(saved);
  else applyTheme("light");

  if (btn){
    btn.addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-bs-theme") || "light";
      applyTheme(cur === "dark" ? "light" : "dark");
    });
  }
})();

function setupIndentEditor(opts){
  const ta = document.getElementById(opts.textareaId);
  if (!ta) return;

  const IND = "    ";

  function insertText(text){
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    ta.value = ta.value.slice(0, start) + text + ta.value.slice(end);
    ta.selectionStart = ta.selectionEnd = start + text.length;
    ta.focus();
  }

  function indentSelection(outdent=false){
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const val = ta.value;

    const lineStart = val.lastIndexOf("\n", start - 1) + 1;
    const lineEnd = end;

    const block = val.slice(lineStart, lineEnd);
    const lines = block.split("\n");

    const changed = lines.map(l => {
      if (!outdent) return IND + l;
      if (l.startsWith(IND)) return l.slice(IND.length);
      if (l.startsWith("   ")) return l.slice(3);
      if (l.startsWith("  ")) return l.slice(2);
      if (l.startsWith(" ")) return l.slice(1);
      return l;
    }).join("\n");

    ta.value = val.slice(0, lineStart) + changed + val.slice(lineEnd);

    if (!outdent){
      ta.selectionStart = start + IND.length;
      ta.selectionEnd = end + IND.length * lines.length;
    }else{
      ta.selectionStart = Math.max(lineStart, start - IND.length);
      ta.selectionEnd = Math.max(lineStart, end - IND.length * lines.length);
    }
    ta.focus();
  }

  ta.addEventListener("keydown", (e) => {
    if (e.key === "Tab"){
      e.preventDefault();
      if (ta.selectionStart !== ta.selectionEnd){
        indentSelection(e.shiftKey);
      }else{
        if (!e.shiftKey) insertText(IND);
        else indentSelection(true);
      }
    }
  });

  const indentBtn = document.getElementById(opts.indentBtnId);
  const outdentBtn = document.getElementById(opts.outdentBtnId);
  const insertDateBtn = document.getElementById(opts.insertDateBtnId);

  if (indentBtn) indentBtn.addEventListener("click", () => indentSelection(false));
  if (outdentBtn) outdentBtn.addEventListener("click", () => indentSelection(true));
  if (insertDateBtn) insertDateBtn.addEventListener("click", () => {
    const d = new Date();
    const pad = n => String(n).padStart(2, "0");
    const s = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    insertText(`\n[${s}]\n`);
  });
}

// ===== LLM run-now AJAX status =====

// ===== LLM toast (top-right, slide in/out) =====
function showStatus(msg, level, opts={}) {
  const duration = opts.duration ?? 3000;
  let wrap = document.getElementById('llmToastWrap');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.id = 'llmToastWrap';
    document.body.appendChild(wrap);
  }
  const toast = document.createElement('div');
  toast.className = `llm-toast alert alert-${level}`;
  toast.innerHTML = `
    <div class="llm-toast-body">
      <div class="llm-toast-msg"></div>
      <button class="llm-toast-close" type="button" aria-label="Close">×</button>
    </div>
  `;
  toast.querySelector('.llm-toast-msg').textContent = msg;
  const closeBtn = toast.querySelector('.llm-toast-close');

  const removeToast = () => {
    toast.classList.remove('show');
    toast.classList.add('hide');
    setTimeout(() => toast.remove(), 280);
  };
  closeBtn.addEventListener('click', removeToast);

  wrap.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));

  if (duration > 0) setTimeout(removeToast, duration);
  return { remove: removeToast };
}

async function runLlmComment(form) {
  const endpoint = form.dataset.endpoint;
  const sel = form.querySelector('select[name="model"]');
  const model = sel ? sel.value : '';
  if (!endpoint) { try { form.submit(); } catch(e) {} return; }

  const modelName = (model && model !== 'random') ? model : '随机模型';
  const running = showStatus(`${modelName} 正在评论中...`, 'warning', {duration: 0});

  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({model})
    });
    const data = await resp.json().catch(() => ({}));
    running.remove();

    if (resp.ok && data.ok) {
      showStatus(`${data.model || modelName} 评论完成`, 'success', {duration: 3000});
      setTimeout(() => {
        if (data.post_id) window.location.href = `/post/${data.post_id}`;
        else window.location.reload();
      }, 900);
    } else {
      showStatus((data && data.message) ? data.message : '评论失败', 'danger', {duration: 3500});
    }
  } catch (e) {
    running.remove();
    showStatus(`评论失败：${e}（将尝试普通提交）`, 'danger', {duration: 3500});
    try { form.submit(); } catch(_e) {}
  }
}


document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('button[data-action="run"]');
  if (!btn) return;
  const form = btn.closest('form.js-llm-run');
  if (!form) return;
  ev.preventDefault();
  runLlmComment(form);
});
