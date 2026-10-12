# GhostAPWorld — Ghost of Tsushima × Archipelago

An [Archipelago](https://archipelago.gg/) randomizer **world** for *Ghost of Tsushima:
Director's Cut* (Steam, PC), built on the **[Manual](https://github.com/ManualForArchipelago/Manual)**
(honor-system) template.

> **Why Manual?** Ghost of Tsushima has no official mod API and no existing randomizer. Automatic
> check-sending / item-receiving is *possible* but is a large reverse-engineering project (see
> [`DESIGN.md`](DESIGN.md)). The Manual template lets us ship and validate the whole design now —
> the player checks off locations in a client and refrains from *using* an ability until its item
> arrives — with automation reserved for a later phase.

## Status — MVP

- **Premise:** fresh save (New Game, any difficulty — Easy is fine for async).
- **Scope:** base Tsushima only. **Goal: Defeat the Khan.**
- **~180 checks:** Main Quests (24), Mythic Tales (7), Fox Dens (49), Pillars of Honor (23),
  Haiku (19), Hot Springs (18), Shinto Shrines (16), Bamboo Strikes (16), Lighthouses (8).
- **Items:** the 4 Stances, Ghost Weapons/tools, Ranged weapons, Technique Points, Health/Resolve
  upgrades, the 7 Mythic rewards, armor sets, charms, sword kits, and cosmetic/resource filler.
  Region access is gated by two progression items — **Act II Access** and **Act III Access**.

Not yet included (later phases, per `DESIGN.md`): Iki Island + the Eagle goal, the 61 side Tales,
Mongol Artifacts / Merchants / Duels / etc., category on/off toggles, Flowersanity, and any live
memory / DLL automation.

## Repo layout

```
DESIGN.md                # full feasibility study, architecture, roadmap (read this first)
src/data/game.json       # world identity + filler item ("Supplies")
src/data/items.json      # item pool (48 types, 160 copies; Manual pads the rest with filler)
src/data/locations.json  # 181 locations (180 item-holding + 1 victory)
src/data/regions.json    # Izuhara -> Toyotama -> Kamiagata, gated by Act II/III Access
src/data/categories.json # category grouping for the tracker
tools/build_data.py      # regenerates src/data/*.json deterministically (edit here, not the JSON)
tools/validate_world.py  # offline consistency + reachability check
```

The `src/data/*.json` files are **generated** — edit [`tools/build_data.py`](tools/build_data.py)
(counts, names, region splits) and re-run it rather than hand-editing the JSON:

```bash
python3 tools/build_data.py     # regenerate src/data/*.json
python3 tools/validate_world.py # verify consistency + solvability (no game/AP needed)
```

**Schema notes (verified against the Manual docs):** in a `requires` string, **pipes mean
items** — `|Act II Access|`, `|Item:3|`, `|@Category:2|` — while **curly braces `{fn()}` call a
function from `hooks/Rules.py`** (which this world does not ship). Item names may not contain
`:` or `|`, and names should stay ASCII so they render in the Archipelago client. The validator
enforces all of this.

## Building the `.apworld`

This repo stores **our data only**; combine it with the Manual base template to produce the world:

1. Download a recent **Manual** template release from
   <https://github.com/ManualForArchipelago/Manual/releases> that matches your Archipelago version.
2. Replace the template's `src/data/` with the `src/data/` from this repo (or copy our five JSON
   files over the template's). Optionally point the ManualBuilder web tool
   (<https://manualforarchipelago.github.io/ManualBuilder/>) at these files.
3. Build the template. The world is named `Manual_GhostOfTsushima_GhostAPWorld` (Manual derives
   it from `game` + `creator` in `game.json`), so the output is
   `manual_ghostoftsushima_ghostapworld.apworld` — all lowercase, no spaces, as the Archipelago
   apworld spec requires (the filename must match the folder inside the zip).
4. Drop the `.apworld` into the `custom_worlds/` folder of your Archipelago install (the
   apworld spec's `worlds/` directory, which is `lib/worlds/` in an installed build).

## Generating a game

1. Create a player YAML for the game `Manual_GhostOfTsushima_GhostAPWorld` (the Manual template
   ships a sample YAML with the built-in **goal** option — MVP exposes the single goal
   *Defeat the Khan*).
2. Run the Archipelago generator. It should fill without errors and produce a seed whose spoiler
   shows **Act II Access** and **Act III Access** reachable in order, with the victory location
   gated behind Act III.
3. Connect with the **Manual client** and open the Manual tracker.

## How to play (honor system)

Start a **new game** (fresh save). Then:

- **Report checks:** when you complete a location in-game (finish a main quest, clear a Fox Den,
  reach a Hot Spring, etc.), tick it in the Manual client. That sends the check to the multiworld.
- **Respect received items only:** don't *use* a Stance, Ghost Weapon, Ranged weapon, or Mythic
  technique until you've received that item in the client — even though a fresh playthrough will
  *unlock* some of them at fixed story beats. The rule is "don't use it until received."
- **Act gates are the hard checkpoint:** don't begin the mission that moves you to the next act
  (Toyotama, then Kamiagata) until you've received **Act II Access** / **Act III Access**.
  Everything else is on your honor.
- **Spend only what you've received:** treat Technique Points and Health/Resolve upgrades the same
  way — allocate them as they arrive.
- **Win:** defeat the Khan (the *Eternal Blue Sky* mission) and tick the goal location.

See [`DESIGN.md`](DESIGN.md) for the architecture rationale, per-category feasibility, and the
phased roadmap (Iki, side Tales, automation, Flowersanity).
