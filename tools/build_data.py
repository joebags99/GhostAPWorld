#!/usr/bin/env python3
"""Deterministic builder for the Ghost of Tsushima Manual (ManualForArchipelago) world.

Emits the five ``src/data/*.json`` files that a Manual world expects. Editing this
script and re-running it is the intended way to adjust the world (counts, names,
region splits) — it keeps ~180 hand-authored locations from drifting out of sync.

Scope: MVP per DESIGN.md — fresh save, base Tsushima only, goal = Defeat the Khan.
No Iki, no side Tales, no automation (all later phases).

Run:  python3 tools/build_data.py
"""

from __future__ import annotations

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "src", "data")

# --- Regions ------------------------------------------------------------------
# Act-based spine. The region graph itself enforces the linear chain:
# Menu -> Izuhara (start) -> Toyotama (needs Act II Access) -> Kamiagata (needs Act III Access).
# Because Kamiagata is only reachable *through* Toyotama, reaching it requires both
# access items in order, so we never need compound `requires` strings on locations.
# Syntax (verified vs Manual docs): |Item Name| references an item; {fn()} would be a
# hooks/Rules.py *function call*, which we do not ship.
IZUHARA, TOYOTAMA, KAMIAGATA = "Izuhara", "Toyotama", "Kamiagata"

REGIONS = {
    IZUHARA: {"starting": True, "connects_to": [TOYOTAMA]},
    TOYOTAMA: {"requires": "|Act II Access|", "connects_to": [KAMIAGATA]},
    KAMIAGATA: {"requires": "|Act III Access|", "connects_to": []},
}

# --- Main story quests (24 item-holding checks; Eternal Blue Sky becomes the goal) ---
MAIN_QUESTS = {
    IZUHARA: [
        "Prologue", "The Warrior's Code", "The Broken Blacksmith",
        "The Tale of Sensei Ishikawa", "The Tale of Lady Masako", "Blood on the Grass",
        "Hammer and Forge", "The Tale of Ryuzo", "The Iron Hook", "Shadow of the Samurai",
        "A New Horizon",
    ],
    TOYOTAMA: [
        "A Message in Fire", "The Walls of Yarikawa", "The Coward of Yarikawa",
        "The Ghost of Yarikawa", "Ghost from the Past", "A Reckoning in Blood",
        "The Fate of Tsushima", "From the Darkness",
    ],
    KAMIAGATA: [
        "Honor and Ash", "Wolves at the Gates", "A Gathering Storm",
        "Heart of the Jito", "The Tale of Lord Shimura",
    ],
}
# The Khan battle ("Eternal Blue Sky") is the victory location, not an item check.
GOAL_LOCATION = "Defeat the Khan (Eternal Blue Sky)"

# --- Mythic Tales (7; 3 / 3 / 1 across the acts) -----------------------------
MYTHIC_TALES = {
    IZUHARA: ["The Heavenly Strike", "The Legend of Tadayori", "The Curse of Uchitsune"],
    TOYOTAMA: ["The Unbreakable Gosaku", "The Six Blades of Kojiro", "The Undying Flame"],
    KAMIAGATA: ["The Spirit of Yarikawa's Vengeance"],
}

# --- Discrete collectible categories, split across the three regions ----------
# Totals match verified base-Tsushima counts. Per-region splits are approximate
# (refine against PowerPyx / Fextralife); they affect only *when* a check unlocks,
# not seed validity.
COLLECTIBLES = {
    # category name: {region: count}
    "Fox Dens":        {IZUHARA: 19, TOYOTAMA: 18, KAMIAGATA: 12},   # 49
    "Pillars of Honor":{IZUHARA: 8,  TOYOTAMA: 8,  KAMIAGATA: 7},    # 23
    "Haiku":           {IZUHARA: 7,  TOYOTAMA: 7,  KAMIAGATA: 5},    # 19
    "Hot Springs":     {IZUHARA: 7,  TOYOTAMA: 6,  KAMIAGATA: 5},    # 18
    "Shinto Shrines":  {IZUHARA: 6,  TOYOTAMA: 6,  KAMIAGATA: 4},    # 16
    "Bamboo Strikes":  {IZUHARA: 6,  TOYOTAMA: 6,  KAMIAGATA: 4},    # 16
    "Lighthouses":     {IZUHARA: 3,  TOYOTAMA: 3,  KAMIAGATA: 2},    # 8
}

# Singular display names for numbered collectible locations (category key stays plural
# for tracker grouping). ASCII only: the AP client font does not cover em-dashes etc.
SINGULAR = {
    "Fox Dens": "Fox Den", "Pillars of Honor": "Pillar of Honor", "Haiku": "Haiku",
    "Hot Springs": "Hot Spring", "Shinto Shrines": "Shinto Shrine",
    "Bamboo Strikes": "Bamboo Strike", "Lighthouses": "Lighthouse",
}

# --- Items --------------------------------------------------------------------
# Sum of counts must be <= number of item-holding locations (180); Manual pads the
# remainder with the `filler_item_name` from game.json ("Supplies").
# Only items referenced in logic must be progression -> Act II/III Access.
ITEMS = []


def add_item(name, category, count=1, progression=False, useful=False):
    entry = {"name": name, "category": [category], "count": count}
    if progression:
        entry["progression"] = True
    elif useful:
        entry["useful"] = True
    ITEMS.append(entry)


# Region-gate progression (referenced in regions.json requires)
add_item("Act II Access", "Progression", 1, progression=True)
add_item("Act III Access", "Progression", 1, progression=True)

# Stances (progression-classified for good fill spread; not gates)
for s in ["Stone Stance", "Water Stance", "Wind Stance", "Moon Stance"]:
    add_item(s, "Stances", 1, progression=True)

# Ghost weapons / tools
for w in ["Kunai", "Smoke Bomb", "Black Powder Bomb", "Sticky Bomb", "Wind Chime", "Blowgun"]:
    add_item(w, "Ghost Weapons", 1, progression=True)

# Ranged weapons
for w in ["Half Bow", "Longbow"]:
    add_item(w, "Ranged Weapons", 1, progression=True)

# Counted progression currency (honor system: only spend/allocate what you've received)
add_item("Technique Point", "Upgrades", 25, progression=True)
add_item("Health Upgrade", "Upgrades", 6, progression=True)
add_item("Resolve Upgrade", "Upgrades", 8, progression=True)

# Mythic rewards (useful)
for m in ["Heavenly Strike", "Dance of Wrath", "Way of the Flame", "Way of the Bow",
          "Tadayori's Armor", "Gosaku's Armor", "Sarugami Armor"]:
    add_item(m, "Mythic Rewards", 1, useful=True)

# Non-mythic armor sets (useful)
for a in ["Traveler's Attire", "Samurai Clan Armor", "Ronin Attire", "Sakai Clan Armor",
          "Kensei Armor", "Mongol Commander's Armor", "Ghost Armor", "Kagemusha Armor",
          "Fundoshi", "Sly Fox's Kimono"]:
    add_item(a, "Armor", 1, useful=True)

# Charms & sword kits
add_item("Major Charm", "Charms", 8, useful=True)
add_item("Minor Charm", "Charms", 16, useful=True)
add_item("Sword Kit", "Cosmetics", 8, useful=True)

# Thematic filler (fresh-save appropriate; NO Ghost Flowers — those are NG+ only)
for name, count in [
    ("Dye", 8), ("Vanity Gear", 6), ("Sashimono Banner", 6), ("Sakai Banner", 4),
    ("Saddle", 6), ("Singing Cricket", 6), ("Record", 6),
    ("Predator Hide", 4), ("Bamboo", 4), ("Linen", 4), ("Steel", 4),
]:
    add_item(name, "Cosmetics" if name in ("Dye", "Vanity Gear", "Sashimono Banner",
                                            "Sakai Banner", "Saddle") else "Filler", count)


# --- Locations ----------------------------------------------------------------
LOCATIONS = []


def add_location(name, category, region, victory=False):
    entry = {"name": name, "category": [category], "region": region}
    if victory:
        entry["victory"] = True
    LOCATIONS.append(entry)


for region, names in MAIN_QUESTS.items():
    for q in names:
        add_location(f"Main Quest - {q}", "Main Quests", region)

for region, names in MYTHIC_TALES.items():
    for t in names:
        add_location(f"Mythic Tale - {t}", "Mythic Tales", region)

for category, split in COLLECTIBLES.items():
    for region, count in split.items():
        for i in range(1, count + 1):
            add_location(f"{SINGULAR[category]} - {region} #{i}", category, region)

# Goal / victory
add_location(GOAL_LOCATION, "Goal", KAMIAGATA, victory=True)


# --- Categories (organization / tracker grouping; no shrink toggles in MVP) ----
CATEGORIES = {
    "Progression": {"hidden": False},
    "Goal": {"hidden": False},
    "Main Quests": {},
    "Mythic Tales": {},
    "Fox Dens": {},
    "Pillars of Honor": {},
    "Haiku": {},
    "Hot Springs": {},
    "Shinto Shrines": {},
    "Bamboo Strikes": {},
    "Lighthouses": {},
    "Stances": {},
    "Ghost Weapons": {},
    "Ranged Weapons": {},
    "Upgrades": {},
    "Mythic Rewards": {},
    "Armor": {},
    "Charms": {},
    "Cosmetics": {},
    "Filler": {},
}

GAME = {
    "game": "GhostOfTsushima",
    "creator": "GhostAPWorld",
    "filler_item_name": "Supplies",
    "death_link": False,
}


def write(name, obj):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def main():
    os.makedirs(DATA, exist_ok=True)
    write("game.json", GAME)
    write("items.json", ITEMS)
    write("locations.json", LOCATIONS)
    write("regions.json", REGIONS)
    write("categories.json", CATEGORIES)

    item_total = sum(i["count"] for i in ITEMS)
    holding = sum(1 for l in LOCATIONS if not l.get("victory"))
    victory = sum(1 for l in LOCATIONS if l.get("victory"))
    print(f"items.json      : {len(ITEMS)} item types, {item_total} total copies")
    print(f"locations.json  : {len(LOCATIONS)} locations ({holding} item-holding, {victory} victory)")
    print(f"regions.json    : {len(REGIONS)} regions")
    print(f"filler padding  : {holding - item_total} x '{GAME['filler_item_name']}'")
    assert item_total <= holding, f"item copies ({item_total}) exceed item-holding locations ({holding})"
    print("OK: item copies fit within item-holding locations.")


if __name__ == "__main__":
    main()
