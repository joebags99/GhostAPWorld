#!/usr/bin/env python3
"""Consistency + lightweight reachability validator for the Manual world data.

Runs offline (no Archipelago install, no game) to catch the common Manual authoring
mistakes before you spend time on a full generation. Checks:

  * every JSON file parses
  * item names and location names are unique
  * every location's `region` exists in regions.json
  * every item referenced in a `requires` string exists AND is a progression item
  * total item copies <= number of item-holding (non-victory) locations
  * at least one victory location exists
  * game.json has a filler_item_name
  * region graph is solvable: with every progression item collected, the victory
    location's region is reachable from the starting region

Exit code 0 = all good, 1 = problems found.

Run:  python3 tools/validate_world.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import deque

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "src", "data")
TOKEN = re.compile(r"\{([^}]+)\}")  # {Item Name} references in a requires string

errors: list[str] = []
warnings: list[str] = []


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def main():
    try:
        game = load("game.json")
        items = load("items.json")
        locations = load("locations.json")
        regions = load("regions.json")
        load("categories.json")  # parse-only
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FATAL: could not read/parse data files: {exc}")
        return 1

    # ---- items ----
    item_names = [i["name"] for i in items]
    dupes = {n for n in item_names if item_names.count(n) > 1}
    if dupes:
        err(f"duplicate item names: {sorted(dupes)}")
    progression = {i["name"] for i in items if i.get("progression")}
    item_copies = sum(int(i.get("count", 1)) for i in items)

    # ---- locations ----
    loc_names = [l["name"] for l in locations]
    ldupes = {n for n in loc_names if loc_names.count(n) > 1}
    if ldupes:
        err(f"duplicate location names: {sorted(ldupes)}")
    holding = [l for l in locations if not l.get("victory")]
    victories = [l for l in locations if l.get("victory")]
    if not victories:
        err("no victory location found (need at least one location with \"victory\": true)")
    if item_copies > len(holding):
        err(f"item copies ({item_copies}) exceed item-holding locations ({len(holding)})")

    region_names = set(regions)
    for l in locations:
        if l.get("region") and l["region"] not in region_names:
            err(f"location '{l['name']}' references unknown region '{l['region']}'")

    # ---- requires tokens (regions + locations) must be progression items ----
    def check_requires(where, text):
        for tok in TOKEN.findall(text or ""):
            name = tok.split(":")[0].strip()
            if name not in item_names:
                err(f"{where}: requires references unknown item '{name}'")
            elif name not in progression:
                err(f"{where}: requires references non-progression item '{name}' "
                    f"(items used in logic must be progression)")

    for rname, rdef in regions.items():
        check_requires(f"region '{rname}'", rdef.get("requires", ""))
    for l in locations:
        check_requires(f"location '{l['name']}'", l.get("requires", ""))

    # ---- game.json ----
    if not game.get("filler_item_name"):
        warn("game.json has no filler_item_name; Manual will use a default filler")
    if not game.get("game"):
        err("game.json missing 'game' name")

    # ---- reachability: full inventory should reach the victory region ----
    start = [r for r, d in regions.items() if d.get("starting")]
    if not start:
        err("no starting region (set \"starting\": true on exactly one region)")
    else:
        reachable = set()
        q = deque(start)
        while q:
            r = q.popleft()
            if r in reachable:
                continue
            # region entry rule: all {items} in requires satisfied by full inventory
            need = [t.split(":")[0].strip() for t in TOKEN.findall(regions[r].get("requires", ""))]
            if any(n not in item_names for n in need):
                continue  # already reported above
            reachable.add(r)
            for nxt in regions[r].get("connects_to", []):
                if nxt in regions and nxt not in reachable:
                    q.append(nxt)
        for v in victories:
            if v.get("region") and v["region"] not in reachable:
                err(f"victory '{v['name']}' in region '{v['region']}' is NOT reachable "
                    f"even with all items (reachable: {sorted(reachable)})")

    # ---- report ----
    print(f"items      : {len(items)} types, {item_copies} copies "
          f"({len(progression)} progression)")
    print(f"locations  : {len(locations)} ({len(holding)} item-holding, {len(victories)} victory)")
    print(f"regions    : {len(regions)}  reachable-with-all-items: "
          f"{len(reachable) if start else 0}/{len(regions)}")
    print(f"padding    : {len(holding) - item_copies} filler auto-added")
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\nFAILED with {len(errors)} error(s).")
        return 1
    print("\nOK: world data is internally consistent and solvable with full inventory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
