#!/usr/bin/env python3
"""Consistency + lightweight reachability validator for the Manual world data.

Runs offline (no Archipelago install, no game) to catch common Manual authoring
mistakes before a full generation. It parses `requires` strings with the *real*
Manual syntax (verified against docs/syntax/requires.md):

    |Item Name|            requires the item
    |Item Name:3|          requires 3 copies   (also ALL / HALF / 90%)
    |@Category|            requires 1 item from the category
    |@Category:2|          requires 2 items from the category
    {functionName(...)}    calls a function from hooks/Rules.py  (NOT an item!)

Checks:
  * every JSON file parses
  * item names are unique and contain no ':' or '|'; location names are unique
  * every location's `region` exists in regions.json
  * every |item| referenced in a requires string exists AND is progression
  * every |@category| referenced exists on at least one item
  * any {function()} reference errors unless src/hooks/Rules.py exists
  * total item copies <= number of item-holding (non-victory) locations
  * at least one victory location; game.json has game/creator/filler_item_name
  * region graph is solvable: with every item collected, each victory location's
    region is reachable from a starting region

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
RULES_HOOK = os.path.join(REPO, "src", "hooks", "Rules.py")

PIPE_TOKEN = re.compile(r"\|([^|]+)\|")   # |Item|, |Item:N|, |@Cat|, |@Cat:N|
FUNC_TOKEN = re.compile(r"\{([^}]*)\}")   # {fn(...)}  -> hooks/Rules.py function

errors: list[str] = []
warnings: list[str] = []


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def parse_requires(text):
    """Return (item_names, category_names, function_refs) referenced by a requires string."""
    items, cats, funcs = [], [], []
    for tok in PIPE_TOKEN.findall(text or ""):
        name = tok.split(":", 1)[0].strip()
        if name.startswith("@"):
            cats.append(name[1:].strip())
        else:
            items.append(name)
    funcs.extend(f.strip() for f in FUNC_TOKEN.findall(text or ""))
    return items, cats, funcs


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
    for n in item_names:
        if ":" in n or "|" in n:
            err(f"item name {n!r} contains ':' or '|' (forbidden by Manual)")
        if not n.isascii():
            warn(f"item name {n!r} has non-ASCII characters (may not render in the AP client)")
    progression = {i["name"] for i in items if i.get("progression")}
    item_categories = {c for i in items for c in i.get("category", [])}
    item_copies = sum(int(i.get("count", 1)) for i in items)

    # ---- locations ----
    loc_names = [l["name"] for l in locations]
    ldupes = {n for n in loc_names if loc_names.count(n) > 1}
    if ldupes:
        err(f"duplicate location names: {sorted(ldupes)}")
    for n in loc_names:
        if not n.isascii():
            warn(f"location name {n!r} has non-ASCII characters (may not render in the AP client)")
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

    # ---- requires strings (regions + locations) ----
    rules_hook_exists = os.path.exists(RULES_HOOK)

    def check_requires(where, text):
        its, cats, funcs = parse_requires(text)
        for name in its:
            if name not in item_names:
                err(f"{where}: requires references unknown item '{name}'")
            elif name not in progression:
                err(f"{where}: requires references non-progression item '{name}' "
                    f"(items used in logic must be progression)")
        for cat in cats:
            if cat not in item_categories:
                err(f"{where}: requires references category '@{cat}' that no item belongs to")
        for fn in funcs:
            if not rules_hook_exists:
                err(f"{where}: requires calls function '{{{fn}}}' but src/hooks/Rules.py does "
                    f"not exist. Did you mean an item? Items use pipes: |{fn}|")

    for rname, rdef in regions.items():
        for key in ("requires", "entrance_requires", "exit_requires"):
            if rdef.get(key):
                check_requires(f"region '{rname}' {key}", rdef[key])
    for l in locations:
        if l.get("requires"):
            check_requires(f"location '{l['name']}'", l["requires"])

    # ---- game.json (game, creator, filler_item_name are required by the schema) ----
    for key in ("game", "creator", "filler_item_name"):
        if not game.get(key):
            err(f"game.json missing required key '{key}'")
    if " " in str(game.get("game", "")):
        warn("game.json 'game' contains spaces; the AP apworld spec wants an all-lowercase "
             "filename matching the inner folder, so a space-free name is safer")

    # ---- reachability: full inventory should reach every victory region ----
    start = [r for r, d in regions.items() if d.get("starting")]
    reachable = set()
    if not start:
        err("no starting region (set \"starting\": true on at least one region)")
    else:
        q = deque(start)
        while q:
            r = q.popleft()
            if r in reachable:
                continue
            need_items, need_cats, _ = parse_requires(regions[r].get("requires", ""))
            need_items += parse_requires(regions[r].get("entrance_requires", ""))[0]
            if any(n not in item_names for n in need_items) or \
               any(c not in item_categories for c in need_cats):
                continue  # unsatisfiable even with everything; reported above
            reachable.add(r)
            for nxt in regions[r].get("connects_to", []):
                if nxt in regions and nxt not in reachable:
                    q.append(nxt)
        for v in victories:
            if v.get("region") and v["region"] not in reachable:
                err(f"victory '{v['name']}' in region '{v['region']}' is NOT reachable even with "
                    f"all items (reachable: {sorted(reachable)})")

    # ---- report ----
    print(f"items      : {len(items)} types, {item_copies} copies ({len(progression)} progression)")
    print(f"locations  : {len(locations)} ({len(holding)} item-holding, {len(victories)} victory)")
    print(f"regions    : {len(regions)}  reachable-with-all-items: {len(reachable)}/{len(regions)}")
    print(f"padding    : {len(holding) - item_copies} x '{game.get('filler_item_name')}' auto-added")
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
