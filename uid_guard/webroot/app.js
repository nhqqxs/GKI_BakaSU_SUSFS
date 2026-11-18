// uid_guard WebUI
//
// 依赖 KernelSU 注入的全局 ksu 对象：
//   ksu.exec(cmd, JSON.stringify(opts), callbackName)  → window[cb](errno, out, err)
//   ksu.getPackagesInfo(JSON.stringify([pkg...]))      → 同步返回 JSON 数组
//
// 名单唯一存放在 ksud module config --internal uid_guard（键 uids，逗号分隔）。
//
// 为什么不写模块目录里的文件：/data/adb/modules/<id>/ 的内容被 SELinux
// 标成 system_file，而 WebUI 的命令跑在 u:r:ksu:s0 域，写不进去。
// KernelSU 自己的配置接口落在 /data/adb/ksu/module_configs/ 下，不受限制。
//
// 每条勾选变化都会重写配置并重跑 service.sh，让名单即时生效
// （service.sh 会 rmmod + insmod，名单只在模块加载时注入）。

const MODID = 'uid_guard';
const KSUD = '/data/adb/ksu/bin/ksud';
const SERVICE = `/data/adb/modules/${MODID}/service.sh`;
const PATH = '/system/bin:/system/xbin:/data/adb/ksu/bin';

const PULL_THRESHOLD = 68;   // 松手触发刷新的下拉距离

const el = {
  list: document.getElementById('list'),
  summary: document.getElementById('summary'),
  status: document.getElementById('status'),
  search: document.getElementById('search'),
  pull: document.getElementById('pull'),
  pullText: document.getElementById('pull-text'),
};

let counter = 0;
let apps = [];              // [{ pkg, label }]
const selected = new Set(); // 选中的包名
let extraUids = [];         // 纯数字 uid（直接填数字的场景），原样保留
let applyTimer = null;
let applying = false;
let refreshing = false;

// ---------------------------------------------------------------- ksu 桥

function ksuAvailable() {
  return typeof window.ksu !== 'undefined' && typeof window.ksu.exec === 'function';
}

function exec(cmd, opts = {}) {
  return new Promise((resolve, reject) => {
    if (!ksuAvailable()) {
      reject(new Error('ksu.exec 不可用，请用 KernelSU 管理器打开本页面'));
      return;
    }
    const name = `ug_cb_${Date.now()}_${counter++}`;
    let done = false;

    window[name] = (errno, stdout, stderr) => {
      done = true;
      try { delete window[name]; } catch (_) {}
      resolve({ errno, stdout: stdout || '', stderr: stderr || '' });
    };

    try {
      window.ksu.exec(cmd, JSON.stringify(opts), name);
    } catch (e) {
      try { delete window[name]; } catch (_) {}
      reject(e);
      return;
    }

    setTimeout(() => {
      if (!done) {
        try { delete window[name]; } catch (_) {}
        reject(new Error('执行超时: ' + cmd.slice(0, 60)));
      }
    }, 20000);
  });
}

// ---------------------------------------------------------------- 工具

function showStatus(text, kind = '') {
  el.status.hidden = false;
  el.status.className = 'status' + (kind ? ' ' + kind : '');
  el.status.textContent = text;
}

function hideStatus() {
  el.status.hidden = true;
  el.status.textContent = '';
}

function setSummary() {
  const n = selected.size;
  el.summary.textContent = n === 0
    ? `${apps.length} 个第三方应用 · 未隐藏任何应用（功能关闭）`
    : `${apps.length} 个第三方应用 · 已隐藏 ${n} 个`;
}

function parseTokens(raw) {
  selected.clear();
  extraUids = [];
  for (const tok of raw.split(/[,\n]/)) {
    const t = tok.trim();
    if (!t) continue;
    if (/^\d+$/.test(t)) extraUids.push(t);
    else selected.add(t);
  }
}

// ---------------------------------------------------------------- 读取

async function readSelection() {
  // 键不存在（errno 非 0）就是空名单，没有别的兜底来源
  const r = await exec(
    `${KSUD} module config --internal ${MODID} get uids`,
    { env: { PATH } },
  );
  parseTokens(r.errno === 0 ? r.stdout : '');
}

// 用 ksu.getPackagesInfo 补应用名；拿不到就留空，界面退回显示包名
function fillLabels(list) {
  if (typeof window.ksu?.getPackagesInfo !== 'function') return {};
  const out = {};
  // 按 20 个一批，避免一次查询太多把 PackageManager 拖慢
  for (let i = 0; i < list.length; i += 20) {
    const chunk = list.slice(i, i + 20).map(a => a.pkg);
    try {
      const parsed = JSON.parse(window.ksu.getPackagesInfo(JSON.stringify(chunk)));
      for (const info of (Array.isArray(parsed) ? parsed : [parsed])) {
        if (info && info.packageName && info.appLabel) {
          out[info.packageName] = String(info.appLabel);
        }
      }
    } catch (_) {
      // 该 API 在某些 KernelSU 分支里不存在或结构不同，忽略即可
    }
  }
  return out;
}

async function readApps() {
  const r = await exec('pm list packages -3 -U --user 0', { env: { PATH } });
  if (r.errno !== 0) {
    throw new Error(r.stderr.trim() || '读取应用列表失败');
  }

  const list = [];
  for (const line of r.stdout.split('\n')) {
    const m = line.match(/^package:(\S+)/);
    if (!m) continue;
    list.push({ pkg: m[1], label: '' });
  }

  const labels = fillLabels(list);
  for (const a of list) a.label = labels[a.pkg] || '';

  list.sort((a, b) => (a.label || a.pkg).localeCompare(b.label || b.pkg));
  return list;
}

// ---------------------------------------------------------------- 渲染

function makeRow(item) {
  const row = document.createElement('label');
  row.className = 'row';
  row.dataset.pkg = item.pkg;
  // 搜索同时匹配应用名和包名
  row.dataset.search = (item.label + ' ' + item.pkg).toLowerCase();

  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.checked = item.checked;
  cb.addEventListener('change', () => {
    if (cb.checked) selected.add(item.pkg);
    else selected.delete(item.pkg);
    setSummary();
    render();
    applyFilter();
    scheduleApply();
  });

  const meta = document.createElement('div');
  meta.className = 'meta';

  const main = document.createElement('span');
  main.className = 'title';
  main.textContent = item.label || item.pkg;

  meta.appendChild(main);
  // 有应用名时把包名作为副标题；没有应用名时主标题已经是包名，就不再重复
  if (item.label) {
    const sub = document.createElement('span');
    sub.className = 'sub';
    sub.textContent = item.pkg;
    meta.appendChild(sub);
  }

  row.appendChild(cb);
  row.appendChild(meta);
  return row;
}

function render() {
  const box = document.createDocumentFragment();

  const chosen = [];
  const rest = [];
  for (const app of apps) {
    (selected.has(app.pkg) ? chosen : rest).push({
      pkg: app.pkg, label: app.label, checked: selected.has(app.pkg),
    });
  }

  // 名单里有、但不在当前应用列表的条目（已卸载 / 装在别的用户）
  const orphans = [...selected]
    .filter(p => !apps.some(a => a.pkg === p))
    .sort()
    .map(p => ({ pkg: p, label: '', checked: true }));

  const chosenAll = chosen.concat(orphans);

  if (chosenAll.length) {
    const head = document.createElement('div');
    head.className = 'section-head';
    head.textContent = `已隐藏 ${chosenAll.length} 个`;
    box.appendChild(head);
    for (const item of chosenAll) box.appendChild(makeRow(item));
  }

  if (rest.length) {
    const head = document.createElement('div');
    head.className = 'section-head';
    head.textContent = `全部应用（${rest.length}）`;
    box.appendChild(head);
    for (const item of rest) box.appendChild(makeRow(item));
  }

  if (!apps.length && !orphans.length) {
    const p = document.createElement('div');
    p.className = 'placeholder';
    p.textContent = '没有找到第三方应用';
    box.appendChild(p);
  }

  el.list.replaceChildren(box);
  el.list.setAttribute('aria-busy', 'false');
}

function applyFilter() {
  const q = el.search.value.trim().toLowerCase();
  const heads = [...el.list.querySelectorAll('.section-head')];

  for (const row of el.list.querySelectorAll('.row')) {
    const hay = row.dataset.search || '';
    row.classList.toggle('hidden', q !== '' && !hay.includes(q));
  }

  // 整组都被过滤光时把组标题也藏掉
  for (const h of heads) {
    let n = h.nextElementSibling;
    let visible = false;
    while (n && !n.classList.contains('section-head')) {
      if (n.classList.contains('row') && !n.classList.contains('hidden')) {
        visible = true;
        break;
      }
      n = n.nextElementSibling;
    }
    h.classList.toggle('hidden', !visible);
  }
}

// ---------------------------------------------------------------- 生效

function buildValue() {
  return [...selected].sort().concat(extraUids).join(',');
}

function scheduleApply() {
  if (applyTimer) clearTimeout(applyTimer);
  applyTimer = setTimeout(applyNow, 400);
}

async function applyNow() {
  if (applying) {
    scheduleApply();
    return;
  }
  applying = true;
  showStatus('正在写入名单并重载模块…');

  try {
    const w = await exec(
      `${KSUD} module config --internal ${MODID} set uids '${buildValue()}'`,
      { env: { PATH } },
    );
    if (w.errno !== 0) {
      throw new Error('写入配置失败: ' + (w.stderr.trim() || 'errno ' + w.errno));
    }

    const r = await exec(`sh ${SERVICE}`, { env: { PATH } });
    if (r.errno !== 0) {
      throw new Error('service.sh 执行失败: ' + (r.stderr.trim() || 'errno ' + r.errno));
    }

    if (selected.size === 0) {
      showStatus('名单为空，模块已按 fail-open 关闭过滤。', 'warn');
    } else {
      showStatus('已生效 · 隐藏 ' + selected.size + ' 个应用', 'ok');
    }
  } catch (e) {
    showStatus(String(e && e.message ? e.message : e), 'err');
  } finally {
    applying = false;
  }
}

// ---------------------------------------------------------------- 下拉刷新

let pullStartY = 0;
let pullDist = 0;
let pullArmed = false;

function setPull(dist) {
  pullDist = dist;
  const armed = dist >= PULL_THRESHOLD;
  el.pull.classList.toggle('visible', dist > 4);
  el.pull.classList.toggle('armed', armed);
  el.pull.style.transform = `translateY(${Math.min(dist, PULL_THRESHOLD * 1.6)}px)`;
  el.pull.style.opacity = String(Math.min(dist / PULL_THRESHOLD, 1));
  if (armed !== pullArmed) {
    pullArmed = armed;
    el.pullText.textContent = armed ? '松开刷新' : '下拉刷新';
  }
}

function resetPull() {
  el.pull.classList.remove('visible', 'armed');
  el.pull.style.transform = '';
  el.pull.style.opacity = '';
  pullDist = 0;
  pullArmed = false;
  el.pullText.textContent = '下拉刷新';
}

window.addEventListener('touchstart', (e) => {
  if (refreshing) return;
  if (window.scrollY > 0 || document.documentElement.scrollTop > 0) return;
  pullStartY = e.touches[0].clientY;
  pullDist = 0;
}, { passive: true });

window.addEventListener('touchmove', (e) => {
  if (refreshing || !pullStartY) return;
  if (window.scrollY > 0 || document.documentElement.scrollTop > 0) {
    pullStartY = 0;
    if (pullDist) resetPull();
    return;
  }
  const dy = e.touches[0].clientY - pullStartY;
  if (dy <= 0) {
    if (pullDist) resetPull();
    return;
  }
  // 阻尼，越往下越钝
  setPull(dy * 0.55);
}, { passive: true });

window.addEventListener('touchend', () => {
  if (refreshing || !pullStartY) return;
  pullStartY = 0;
  const dist = pullDist;
  resetPull();
  if (dist >= PULL_THRESHOLD) refresh();
}, { passive: true });

window.addEventListener('touchcancel', () => {
  pullStartY = 0;
  resetPull();
}, { passive: true });

// ---------------------------------------------------------------- 入口

async function refresh() {
  if (refreshing) return;
  refreshing = true;
  el.list.setAttribute('aria-busy', 'true');
  showStatus('正在读取应用列表…');

  try {
    if (!ksuAvailable()) {
      throw new Error('ksu.exec 不可用，请用 KernelSU 管理器打开本页面');
    }
    await readSelection();
    apps = await readApps();
    render();
    applyFilter();
    setSummary();
    hideStatus();
  } catch (e) {
    el.list.replaceChildren();
    const p = document.createElement('div');
    p.className = 'placeholder';
    p.textContent = '加载失败';
    el.list.appendChild(p);
    showStatus(String(e && e.message ? e.message : e), 'err');
  } finally {
    refreshing = false;
  }
}

el.search.addEventListener('input', applyFilter);

refresh();
