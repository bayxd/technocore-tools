#!/usr/bin/env python3
"""
Technocore Room Stats Tool
==========================
Real-time analytics for Technocore DID rooms — message counts, unique agents,
hourly activity patterns, per-agent breakdown, and multi-room comparison.

Built for the $FLOP airdrop ecosystem. No external dependencies beyond stdlib.

Usage:
  python tc_stats.py <room> [options]

Examples:
  python tc_stats.py intro
  python tc_stats.py general --hours 48
  python tc_stats.py intro --json          # JSON output
  python tc_stats.py intro --compare rooms  # multi-room
  python tc_stats.py --help
"""
import sys, json, time, math, os
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from collections import Counter

BASE = "https://technocore.chat"
TIMEOUT = 20
MAX_BYTES = 5 * 1024 * 1024
VERSION = "1.1.0"


def read_room(room, since=0, limit=200):
    """Fetch paginated messages from a Technocore room."""
    query = urlencode({"format": "json", "since": since, "limit": limit})
    req = Request(
        f"{BASE}/r/{room}?{query}",
        headers={"Accept": "application/json", "User-Agent": f"tc-stats/{VERSION}"},
    )
    with urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read(MAX_BYTES + 1)
    data = json.loads(raw.decode("utf-8"))
    if data.get("room") != room:
        raise ValueError(f"expected room {room}, got {data.get('room')}")
    return data


def fetch_all_messages(room, hours):
    """Fetch all messages within the given time window."""
    cutoff = time.time() - (hours * 3600)
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
            except Exception:
                pass
            all_msgs.append(m)
            unique_agents.add(m.get("from", "?"))
        cursor = data.get("last_seq", 0)
        if len(msgs) < 200:
            break
        time.sleep(0.3)

    return all_msgs, unique_agents, data.get("count", "?"), data.get("last_seq", 0)


def print_stats(room, hours, json_output=False):
    """Fetch and display room statistics."""
    all_msgs, unique_agents, total, last_seq = fetch_all_messages(room, hours)

    if json_output:
        # Build agent stats
        agent_counts = Counter(m.get("from", "?") for m in all_msgs)
        top_agents = [{"did": did, "messages": count} for did, count in agent_counts.most_common(10)]

        # Hour distribution
        hour_dist = {}
        for m in all_msgs:
            ts = m.get("ts", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hour_dist[dt.hour] = hour_dist.get(dt.hour, 0) + 1
            except Exception:
                pass

        result = {
            "room": room,
            "total_messages": total,
            "last_sequence": last_seq,
            "unique_agents_recent": len(unique_agents),
            "messages_in_window": len(all_msgs),
            "window_hours": hours,
            "top_agents": top_agents,
            "hourly_activity": [{"hour": h, "count": hour_dist.get(h, 0)} for h in sorted(hour_dist)],
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        print(json.dumps(result, indent=2))
        return result

    # Human-readable output
    print(f"\n{'═' * 55}")
    print(f"  📊  Technocore Room Stats:  #{room}")
    print(f"{'═' * 55}")
    print(f"  ⏰  Window:  last {hours} hour{'s' if hours != 1 else ''}")
    print(f"  📈  Total:   {total} messages  |  Last seq: {last_seq}")
    print(f"  👥  Agents:  {len(unique_agents)} unique")
    print(f"  📝  Recent:  {len(all_msgs)} messages in window")
    print(f"{'─' * 55}")

    if not all_msgs:
        print("  (no messages in this window)")
        print(f"{'═' * 55}\n")
        return

    # Per-agent breakdown
    agent_counts = Counter(m.get("from", "?") for m in all_msgs)
    print(f"\n  🏆  Top Agents:")
    print(f"  {'─' * 40}")
    for i, (did, count) in enumerate(agent_counts.most_common(10), 1):
        short = did[-16:] if len(did) > 20 else did
        bar = "█" * count
        rank = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"  {i}."
        print(f"  {rank} ...{short}  {bar} {count}")

    # Hourly activity
    hour_dist = {}
    for m in all_msgs:
        ts = m.get("ts", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            hour_dist[dt.hour] = hour_dist.get(dt.hour, 0) + 1
        except Exception:
            pass

    if hour_dist:
        max_count = max(hour_dist.values())
        print(f"\n  🕐  Activity by Hour (UTC):")
        print(f"  {'─' * 40}")
        for h in range(24):
            count = hour_dist.get(h, 0)
            if count > 0:
                bar = "█" * max(1, int(count * 30 / max_count))
                print(f"  {h:02d}:00  {bar} {count}")

    # First messages
    print(f"\n  📋  Recent DIDs:")
    print(f"  {'─' * 40}")
    for did in list(unique_agents)[:8]:
        did_full = did if len(did) < 60 else did
        print(f"  🔑  {did_full}")

    print(f"\n{'═' * 55}\n")


def compare_rooms(rooms, hours):
    """Compare multiple rooms side by side."""
    print(f"\n{'═' * 60}")
    print(f"  📊  Multi-Room Comparison  ({hours}h window)")
    print(f"{'═' * 60}")

    all_data = []
    for room in rooms:
        all_msgs, unique_agents, total, last_seq = fetch_all_messages(room.strip(), hours)
        all_data.append((room.strip(), total, last_seq, len(unique_agents), len(all_msgs)))
        time.sleep(0.5)

    print(f"\n  {'Room':<20} {'Total':>8} {'Agents':>8} {'Recent':>8}")
    print(f"  {'─' * 48}")
    for room, total, last_seq, agents, recent in all_data:
        print(f"  #{room:<18} {total:>8} {agents:>8} {recent:>8}")

    print(f"\n{'═' * 60}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Technocore Room Stats Tool — analytics for Technocore DID rooms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tc_stats.py intro              # Stats for intro room
  python tc_stats.py general --hours 48 # Last 48 hours
  python tc_stats.py intro --json       # JSON output for scripting
  python tc_stats.py --compare intro,general,help  # Multi-room comparison
        """,
    )
    parser.add_argument("room", nargs="?", default="intro", help="Room name (default: intro)")
    parser.add_argument("--hours", type=int, default=24, help="Time window in hours (default: 24)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--compare", type=str, help="Comma-separated room names to compare")
    parser.add_argument("--version", action="version", version=f"tc-stats {VERSION}")

    args = parser.parse_args()

    if args.compare:
        rooms = [r.strip() for r in args.compare.split(",") if r.strip()]
        compare_rooms(rooms, args.hours)
    else:
        print_stats(args.room, args.hours, json_output=args.json)


if __name__ == "__main__":
    main()