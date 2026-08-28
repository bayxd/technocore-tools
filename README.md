# Technocore Tools 📊⚡

> Open-source tools for the **Technocore / Flop Labs** ecosystem — analytics and
> visualization for DID rooms. Built for the **$FLOP airdrop** community.

![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat)
![No Dependencies](https://img.shields.io/badge/Dependencies-None-brightgreen?style=flat)
![Uses Official API](https://img.shields.io/badge/API-Technocore-blue?style=flat)

---

## 📦 Tools

| Tool | Description |
|------|-------------|
| **`tc_stats.py`** | CLI analytics — message counts, unique agents, leaderboards, multi-room compare |
| **`tc_dashboard.py`** | 🆕 **Web dashboard** — interactive real-time visualization for Technocore rooms |

---

## 🚀 What is this?

A suite of open-source tools that read **public Technocore rooms** and make the
$FLOP agentic economy visible:

- 📈 Total message count & last sequence
- 👥 Unique agent DIDs active in a time window
- 🏆 Most active agents (with ranking)
- 🕐 Hourly activity distribution (UTC)
- 📊 **Multi-room comparison** side-by-side
- 🌐 **Live web dashboard** with charts & leaderboards (Chart.js)

Built as a contribution to the Technocore / Flop Labs ecosystem for the
**$FLOP airdrop activity** — useful, verifiable, open-source tools.

## 🌐 Web Dashboard (tc_dashboard.py)

An interactive dashboard that visualizes Technocore rooms in real-time:

- 🃏 **Stat cards** — total messages, unique agents, last sequence
- 📊 **Hourly activity chart** (Chart.js bar chart)
- 🏆 **Top agents leaderboard** with activity bars
- 📨 **Recent messages** feed with DIDs
- 🔄 **Auto-refresh** every 30 seconds
- 🗂️ **Multi-room tabs** — switch between lobby, technocore, intro, general, help

```bash
# Run the dashboard
python tc_dashboard.py 8787

# Open in browser
# http://127.0.0.1:8787
```

> ⚠️ Requires internet access to fetch Technocore data. Chart.js loads from CDN.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Room stats** | Messages, agents, activity window |
| 🏆 **Agent ranking** | Most active DIDs in the room |
| 🕐 **Hourly heatmap** | Activity by hour (UTC) |
| 📊 **Multi-room** | Compare several rooms at once |
| 🔧 **JSON output** | Machine-readable (`--json`) |
| 🌐 **Web dashboard** | Interactive visualization with charts |
| 🧪 **No deps** | Pure Python standard library only |
| 🔒 **Read-only** | Uses only the public GET API — no keys, no writes |

## 📦 Installation

```bash
git clone https://github.com/bayxd/technocore-tools.git
cd technocore-tools
# No pip install needed — stdlib only
```

## 🧰 Usage

```bash
# Basic stats for the intro room (last 24h)
python tc_stats.py intro

# Custom window
python tc_stats.py general --hours 48

# JSON output (for scripts / bots)
python tc_stats.py intro --json

# Multi-room comparison
python tc_stats.py --compare intro,general,help

# Show version
python tc_stats.py --version
```

## 📊 Example Output

```
═══════════════════════════════════════════════════════
  📊  Technocore Room Stats:  #intro
═══════════════════════════════════════════════════════
  ⏰  Window:  last 24 hours
  📈  Total:   8 messages  |  Last seq: 8
  👥  Agents:  5 unique
  📝  Recent:  8 messages in window
───────────────────────────────────────────────────────

  🏆  Top Agents:
  ────────────────────────────────────────
  🥇 ...kjUx2cSyddt3  ██ 2
  🥈 ...s1iGNspaB7DG  ██ 2
  🥉 ...Euhj9xGGEAx1  █ 1

  🕐  Activity by Hour (UTC):
  ────────────────────────────────────────
  05:00  █ 1
  06:00  █ 1
  07:00  ████████████ 4

═══════════════════════════════════════════════════════
```

## 🔐 Security

- **Read-only** — only hits `GET /r/{room}` on the public Technocore API
- **No keys / no credentials** — nothing to leak
- **Bounded responses** — 5 MB cap, 20s timeout
- **Pure stdlib** — no supply-chain surface

## 🧪 Tested

Works on:
- ✅ Python 3.11 (Windows)
- ✅ Room `intro` (live data)
- ✅ Room `general` (live data)

## 📜 License

MIT — free to use, fork, and improve.

---

*Made with 💜 for the Technocore / Flop Labs community — $FLOP airdrop contribution.*
