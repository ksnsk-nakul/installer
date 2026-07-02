/* Global dashboard JS — log panel, WebSocket, install flow, search */

'use strict';

// ── Active job state ─────────────────────────────────────────────────────────
window._activeJobId = null;
let _ws = null;

// ── Log panel ─────────────────────────────────────────────────────────────────
const logPanel  = document.getElementById('log-panel');
const logOutput = document.getElementById('log-output');

function openLogPanel() { logPanel.classList.add('open'); }
function closeLogPanel() { logPanel.classList.remove('open'); logOutput.textContent = ''; }

function appendLog(line) {
  const text = document.createTextNode(line + '\n');
  logOutput.appendChild(text);
  logOutput.scrollTop = logOutput.scrollHeight;
}

// ── Step bar ──────────────────────────────────────────────────────────────────
const STEP_KEYWORDS = [
  [1, /detect/i],
  [2, /adapter/i],
  [3, /verif/i],
  [4, /install/i],
  [5, /check/i],
];

function updateStepBar(line) {
  for (const [n, re] of STEP_KEYWORDS) {
    if (re.test(line)) {
      document.querySelectorAll('.step').forEach(s => {
        const id = parseInt(s.id.split('-')[1], 10);
        s.classList.toggle('active', id === n);
        s.classList.toggle('done',   id < n);
      });
      break;
    }
  }
}

// ── WebSocket log streaming ───────────────────────────────────────────────────
function connectJobLog(jobId) {
  if (_ws) { _ws.close(); }

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  _ws = new WebSocket(`${proto}://${location.host}/ws/logs/${jobId}`);

  _ws.addEventListener('message', e => {
    const line = e.data;
    if (line === '[ping]') return;
    if (line === '[done]') {
      appendLog('── Done ──');
      _ws.close();
      return;
    }
    if (line.startsWith('[db-config-needed]')) {
      openDbModal(jobId);
      return;
    }
    appendLog(line);
    updateStepBar(line);
  });

  _ws.addEventListener('error', () => appendLog('[connection error]'));
}

// ── DB config modal ───────────────────────────────────────────────────────────
function openDbModal(jobId) {
  window._activeJobId = jobId;
  document.getElementById('db-modal').style.display = 'flex';
}

function closeDbModal() {
  document.getElementById('db-modal').style.display = 'none';
}

// ── Install flow (called by explore.html cards) ───────────────────────────────
window.startInstall = async function startInstall(preset) {
  const payload = { preset, project_path: '/var/www/app', domain: '' };

  const resp = await fetch('/api/install', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  const jobId = data.job_id;

  logOutput.textContent = '';
  openLogPanel();
  connectJobLog(jobId);
};

// ── Search bar ────────────────────────────────────────────────────────────────
const searchBar = document.getElementById('search-bar');
if (searchBar) {
  searchBar.addEventListener('input', () => {
    const q = searchBar.value.toLowerCase();
    document.querySelectorAll('.card, .data-table tr:not(:first-child)').forEach(el => {
      el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
}

// ── Server status dot ─────────────────────────────────────────────────────────
(async () => {
  const dot = document.getElementById('server-dot');
  const ip  = document.getElementById('server-ip');
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    dot.className = 'status-dot status-ok';
    if (d.host) ip.textContent = d.host;
  } catch {
    dot.className = 'status-dot status-fail';
  }
})();
