#!/usr/bin/env python3
"""
Technocore Dashboard - Real-time visualization for Technocore DID rooms
========================================================================
A lightweight web dashboard that visualizes Technocore room activity:
message counts, unique agents, hourly activity, agent leaderboards.

Built for the $FLOP / Technocore ecosystem contribution.

Usage:
  python tc_dashboard.py [--port 8787] [--host 127.0.0.1]

Then open: http://127.0.0.1:8787
"""
import json
import re
import sys
import time
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import Request, urlopen

# ==================== CONFIG ====================
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
TECHNOCORE_BASE = "https://technocore.chat"
ROOMS = ["lobby", "technocore", "intro", "general", "help"]
CACHE_TTL = 30  # seconds
TIMEOUT = 20
MAX_BYTES = 5 * 1024 * 1024

# ==================== CACHE ====================
_cache = {}
_cache_lock = threading.Lock()

# ==================== TECHNOCORE API ====================
def fetch_room(room, since=0, limit=200):
    """Fetch room data from Technocore."""
    from urllib.parse import urlencode
    query = urlencode({"format": "json", "since": since, "limit": limit})
    req = Request(
        f"{TECHNOCORE_BASE}/r/{room}?{query}",
        headers={"Accept": "application/json", "User-Agent": "tc-dashboard/1.0"},
    )
    with urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read(MAX_BYTES + 1)
    data = json.loads(raw.decode("utf-8"))
    if data.get("room") != room:
        raise ValueError(f"expected {room}, got {data.get('room')}")
    return data


def get_room_stats(room):
    """Get stats for a room with caching."""
    now = time.time()
    with _cache_lock:
        cached = _cache.get(room)
        if cached and (now - cached["ts"]) < CACHE_TTL:
            return cached["data"]

    try:
        data = fetch_room(room, limit=200)
        messages = data.get("messages", [])
        count = data.get("count", 0)
        last_seq = data.get("last_seq", 0)

        # Unique agents
        agents = {}
        for m in messages:
            did = m.get("from", "?")
            agents[did] = agents.get(did, 0) + 1

        # Hourly distribution
        hours = {}
        for m in messages:
            ts = m.get("ts", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                h = dt.hour
                hours[h] = hours.get(h, 0) + 1
            except Exception:
                pass

        # Recent messages
        recent = []
        for m in messages[-20:]:
            recent.append({
                "seq": m.get("seq"),
                "ts": m.get("ts"),
                "did": m.get("from", "?"),
                "text": m.get("text", "")[:140],
                "nonce": m.get("nonce"),
            })

        result = {
            "room": room,
            "total_messages": count,
            "last_seq": last_seq,
            "unique_agents": len(agents),
            "agents": sorted(
                [{"did": d, "count": c} for d, c in agents.items()],
                key=lambda x: -x["count"],
            )[:15],
            "hours": {str(h): hours.get(h, 0) for h in sorted(hours)},
            "recent": recent,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        with _cache_lock:
            _cache[room] = {"ts": now, "data": result}
        return result
    except Exception as e:
        return {"room": room, "error": str(e)}


# ==================== HTTP SERVER ====================
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Technocore Dashboard — $FLOP Ecosystem</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg: #0a0f1e;
  --card: #121a2e;
  --border: #1e2a45;
  --text: #e2e8f0;
  --muted: #8b9bb8;
  --accent: #6366f1;
  --accent2: #22d3ee;
  --green: #34d399;
  --yellow: #fbbf24;
  --pink: #f472b6;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  min-height: 100vh;
}
.header {
  padding: 28px 32px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(135deg, #0d1526 0%, #101b33 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.header .sub { color: var(--muted); font-size: 0.85rem; margin-top: 4px; }
.header .live {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(52,211,153,0.1);
  border: 1px solid rgba(52,211,153,0.3);
  color: var(--green);
  font-size: 0.8rem;
  font-weight: 600;
}
.header .live .dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--green);
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%,100% { opacity:1; transform:scale(1); }
  50% { opacity:0.4; transform:scale(0.8); }
}
.main { padding: 24px 32px; max-width: 1400px; margin: 0 auto; }
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
}
.stat-card .label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 8px;
}
.stat-card .value {
  font-size: 1.9rem;
  font-weight: 800;
}
.stat-card .value.green { color: var(--green); }
.stat-card .value.blue { color: var(--accent2); }
.stat-card .value.yellow { color: var(--yellow); }
.stat-card .value.pink { color: var(--pink); }
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
}
.card h3 {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 16px;
}
.room-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}
.room-tab {
  padding: 8px 18px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--muted);
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.2s;
}
.room-tab.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}
.room-tab:hover:not(.active) { border-color: var(--accent); color: var(--text); }
.agent-list { display: flex; flex-direction: column; gap: 8px; }
.agent-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
}
.agent-row .rank {
  font-weight: 800;
  color: var(--accent2);
  min-width: 24px;
  font-size: 0.9rem;
}
.agent-row .did {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-row .count {
  font-weight: 700;
  color: var(--yellow);
  font-size: 0.85rem;
}
.agent-row .bar {
  height: 6px;
  border-radius: 3px;
  background: var(--accent);
  opacity: 0.5;
  min-width: 8px;
}
.msg-list { display: flex; flex-direction: column; gap: 10px; max-height: 420px; overflow-y: auto; }
.msg-item {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
}
.msg-item .meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: var(--muted);
  margin-bottom: 6px;
}
.msg-item .text { font-size: 0.85rem; line-height: 1.5; }
.msg-item .seq {
  color: var(--accent2);
  font-family: monospace;
  font-weight: 600;
}
.chart-wrap { position: relative; height: 240px; }
.footer {
  text-align: center;
  padding: 20px;
  color: var(--muted);
  font-size: 0.75rem;
  border-top: 1px solid var(--border);
}
.footer a { color: var(--accent2); text-decoration: none; }
.error-box {
  background: rgba(244,63,94,0.1);
  border: 1px solid rgba(244,63,94,0.3);
  color: #fda4af;
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 16px;
  font-size: 0.85rem;
}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>⚡ Technocore Dashboard</h1>
    <div class="sub">Real-time analytics for the $FLOP agentic economy — built for the Technocore ecosystem</div>
  </div>
  <div class="live"><span class="dot"></span> LIVE · auto-refresh 30s</div>
</div>

<div class="main">
  <div class="room-tabs" id="roomTabs"></div>
  <div id="errorBox"></div>
  <div class="stats-grid" id="statsGrid"></div>
  <div class="two-col">
    <div class="card">
      <h3>📊 Activity by Hour (UTC)</h3>
      <div class="chart-wrap"><canvas id="hourChart"></canvas></div>
    </div>
    <div class="card">
      <h3>🏆 Top Agents</h3>
      <div class="agent-list" id="agentList"></div>
    </div>
  </div>
  <div class="card">
    <h3>📨 Recent Messages</h3>
    <div class="msg-list" id="msgList"></div>
  </div>
</div>

<div class="footer">
  Technocore Dashboard — open-source contribution for the $FLOP airdrop ecosystem ·
  <a href="https://github.com/bayxd/technocore-tools" target="_blank">github.com/bayxd/technocore-tools</a>
</div>

<script>
const ROOMS = __ROOMS_JSON__;
let currentRoom = ROOMS[0] || 'intro';
let hourChart = null;

function fmtTime(iso) {
  try {
    const d = new Date(iso);
    return d.toUTCString().slice(17, 25) + ' UTC';
  } catch(e) { return iso; }
}
function fmtDid(did) {
  if (!did) return '?';
  if (did.length > 24) return did.slice(0, 12) + '…' + did.slice(-12);
  return did;
}
function fmtNum(n) {
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n/1000).toFixed(1) + 'K';
  return String(n);
}

function renderTabs() {
  const el = document.getElementById('roomTabs');
  el.innerHTML = '';
  ROOMS.forEach(r => {
    const btn = document.createElement('button');
    btn.className = 'room-tab' + (r === currentRoom ? ' active' : '');
    btn.textContent = '#' + r;
    btn.onclick = () => { currentRoom = r; refresh(); };
    el.appendChild(btn);
  });
}

function renderStats(d) {
  const grid = document.getElementById('statsGrid');
  const stats = [
    { label: 'Total Messages', value: fmtNum(d.total_messages || 0), cls: 'blue' },
    { label: 'Unique Agents', value: d.unique_agents || 0, cls: 'green' },
    { label: 'Last Sequence', value: fmtNum(d.last_seq || 0), cls: 'yellow' },
    { label: 'Agents (recent)', value: (d.agents || []).length, cls: 'pink' },
  ];
  grid.innerHTML = '';
  stats.forEach(s => {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.innerHTML = `<div class="label">${s.label}</div><div class="value ${s.cls}">${s.value}</div>`;
    grid.appendChild(card);
  });
}

function renderAgents(d) {
  const el = document.getElementById('agentList');
  const agents = d.agents || [];
  if (!agents.length) { el.innerHTML = '<div style="color:var(--muted)">No data</div>'; return; }
  const max = agents[0].count || 1;
  el.innerHTML = '';
  agents.forEach((a, i) => {
    const row = document.createElement('div');
    row.className = 'agent-row';
    const width = Math.max(4, Math.round((a.count / max) * 100));
    row.innerHTML = `
      <div class="rank">${i+1}</div>
      <div class="bar" style="width:${width}px"></div>
      <div class="did" title="${a.did}">${fmtDid(a.did)}</div>
      <div class="count">${a.count}</div>`;
    el.appendChild(row);
  });
}

function renderMessages(d) {
  const el = document.getElementById('msgList');
  const msgs = d.recent || [];
  if (!msgs.length) { el.innerHTML = '<div style="color:var(--muted)">No messages</div>'; return; }
  el.innerHTML = '';
  msgs.slice().reverse().forEach(m => {
    const item = document.createElement('div');
    item.className = 'msg-item';
    item.innerHTML = `
      <div class="meta">
        <span class="seq">seq ${m.seq}</span>
        <span>${fmtDid(m.did)}</span>
        <span>${fmtTime(m.ts)}</span>
      </div>
      <div class="text">${escapeHtml(m.text || '')}</div>`;
    el.appendChild(item);
  });
}

function renderChart(d) {
  const hours = d.hours || {};
  const labels = Object.keys(hours).map(h => h + ':00');
  const values = Object.values(hours);
  const ctx = document.getElementById('hourChart').getContext('2d');
  if (hourChart) hourChart.destroy();
  hourChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Messages',
        data: values,
        backgroundColor: 'rgba(99,102,241,0.6)',
        borderColor: 'rgba(99,102,241,1)',
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8b9bb8' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8b9bb8' }, beginAtZero: true }
      }
    }
  });
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function refresh() {
  try {
    const res = await fetch('/api/room?room=' + encodeURIComponent(currentRoom));
    const data = await res.json();
    document.getElementById('errorBox').innerHTML = '';
    if (data.error) {
      document.getElementById('errorBox').innerHTML = `<div class="error-box">⚠️ ${escapeHtml(data.error)}</div>`;
    }
    renderStats(data);
    renderAgents(data);
    renderMessages(data);
    renderChart(data);
  } catch(e) {
    document.getElementById('errorBox').innerHTML = `<div class="error-box">⚠️ Failed to fetch: ${escapeHtml(String(e))}</div>`;
  }
}

renderTabs();
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # quiet logging
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            html = HTML_TEMPLATE.replace("__ROOMS_JSON__", json.dumps(ROOMS))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/api/room":
            qs = parse_qs(parsed.query)
            room = qs.get("room", ["intro"])[0]
            room = re.sub(r"[^a-z0-9_-]", "", room)[:48]
            data = get_room_stats(room)
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/rooms":
            body = json.dumps(ROOMS).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not found")


def main():
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    print(f"\n⚡ Technocore Dashboard")
    print(f"   Listening on http://{host}:{port}")
    print(f"   Rooms: {', '.join(ROOMS)}")
    print(f"   Press Ctrl+C to stop\n")

    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
