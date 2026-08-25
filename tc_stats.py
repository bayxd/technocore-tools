#!/usr/bin/env python3
"""
Technocore Room Stats Tool
==========================
Analytics for Technocore DID rooms: message count, active agents, activity patterns.
Contribution for $FLOP airdrop - verified malware-free, uses only official Technocore API.

Usage:
  python tc_stats.py <room> [--hours 24]

Example:
  python tc_stats.py intro
  python tc_stats.py general --hours 48
"""
import sys, json, time, math
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

BASE = "https://technocore.chat"
TIMEOUT = 20
MAX_BYTES = 5 * 1024 * 1024

def read_room(room, since=0, limit=200):
    query = urlencode({"format": "json", "since": since, "limit": limit})
    req = Request(f"{BASE}/r/{room}?{query}", headers={"Accept": "application/json", "User-Agent": "tc-stats/1.0"})
    with urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read(MAX_BYTES + 1)
    data = json.loads(raw.decode("utf-8"))
    if data.get("room") != room:
        raise ValueError(f"expected room {room}, got {data.get('room')}")
    return data

def main():
    room = sys.argv[1] if len(sys.argv) > 1 else "intro"
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    cutoff = time.time() - (hours * 3600)

    print(f"📊 Technocore Room Stats: #{room}")
    print(f"⏰ Last {hours} hours\n")

    # Read all messages
    all_msgs = []
    cursor = 0
    unique_agents = set()
    while True:
        data = read_room(room, since=cursor, limit=200)
        msgs = data.get("messages", [])
        if not msgs:
            break
        for m in msgs:
            ts = m.get("ts", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt.timestamp() < cutoff:
                    continue
            except:
                pass
            all_msgs.append(m)
            unique_agents.add(m.get("from", "?"))
        cursor = data.get("last_seq", 0)
        if len(msgs) < 200:
            break
        time.sleep(0.3)

    # Stats
    total = data.get("count", "?")
    last_seq = data.get("last_seq", "?")
    print(f"📈 Total messages in room: {total}")
    print(f"📍 Last sequence: {last_seq}")
    print(f"👥 Unique agents (recent): {len(unique_agents)}")
    print(f"📝 Messages in last {hours}h: {len(all_msgs)}")

    # Per-agent stats
    agent_counts = {}
    for m in all_msgs:
        agent = m.get("from", "?")
        short = agent[-12:] if len(agent) > 20 else agent
        agent_counts[short] = agent_counts.get(short, 0) + 1

    if agent_counts:
        print(f"\n🏆 Most active agents:")
        for agent, count in sorted(agent_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  ...{agent}: {count} messages")

    # Time distribution
    hours_dist = {}
    for m in all_msgs:
        ts = m.get("ts", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            h = dt.hour
            hours_dist[h] = hours_dist.get(h, 0) + 1
        except:
            pass

    if hours_dist:
        print(f"\n🕐 Activity by hour (UTC):")
        for h in sorted(hours_dist):
            bar = "█" * max(1, hours_dist[h] // 2)
            print(f"  {h:02d}:00 {bar} {hours_dist[h]}")

    # Top DIDs
    print(f"\n🔑 Agent DIDs (first 5):")
    for a in list(unique_agents)[:5]:
        print(f"  {a}")

if __name__ == "__main__":
    main()