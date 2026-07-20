# Ghost of Tsushima: Director's Cut — Archipelago World Design & Feasibility

**Status:** Research & planning only — no implementation.
**Author pass:** Feasibility investigation + design proposal for review.
**Scope note:** This document is a plan to be reviewed and approved before *any* APworld
scaffolding, item tables, or Python classes are written. Nothing in here is built yet.

---

## 0. Executive summary

- **Ghost of Tsushima (GoT) has no official mod support and no existing randomizer**, but the PC
  version is *more* moddable than expected: no single-player anti-cheat, a working native-DLL
  loader ecosystem (Ultimate ASI Loader via a `d3d12.dll` proxy), existing Cheat Engine tables,
  and community save editors that already decode many completion flags.
- **Fully automatic check-sending / item-receiving is technically possible but is a large
  reverse-engineering project, not a first deliverable.** No public memory-offset or save-schema
  map exists for the progression state a randomizer needs, and *granting* items cleanly is much
  harder than *reading* checks.
- **Recommendation: build a Manual (honor-system) APworld first** using the ManualForArchipelago
  template. It ships fast, requires zero reverse-engineering, validates the whole item/location/
  logic design, and pairs naturally with the NG+ premise. Automation can be layered on later.
- **One important design wrinkle: NG+ carries over abilities.** Techniques, Armor, and Vanity
  persist into New Game+, while Collections reset. That makes NG+ a great fit for an honor-system
  world but a poor fit for "lock everything and grant on receive" automation. See §7.
- **Flowersanity (the ~1683-flowers idea) is unverified** and probably conflicts with the fact that
  Ghost Flowers are a *renewable currency*. Scoped out of the MVP pending verification.

---

## 1. Background: how an Archipelago world works (primer)

Archipelago (AP) is a multi-game randomizer. Each game integrated into AP is a **world** — a Python
package (shipped as a zipped `.apworld`) that the AP generator loads. The essentials:

- **`World` subclass** — one instance per player. Declares the `game` name, an `options_dataclass`,
  and two required maps: `item_name_to_id` and `location_name_to_id` (unique integer IDs,
  1 … 2^53−1).
- **`WebWorld`** — web presentation: tutorials, option presets, item/location descriptions on the
  AP website.
- **`Item` / `Location`** — subclasses tagging each with the game name; items are *what you
  receive*, locations are *checks you complete*.
- **`Region` / `Entrance`** — logical containers of locations connected by entrances with optional
  access rules; a `Menu` origin region is the start.
- **Generation pipeline:** `generate_early` → `create_regions` → `create_items` →
  `set_rules`/`set_rule()` (access logic via `CollectionState`, e.g. `state.has("Item", player)`)
  → fill → `generate_output`.
- **Client:** at play time a client connects to the AP server over WebSockets, sends "location
  checked" events, and receives "you got item X" events.

**The hard question for GoT is the client**, not the world definition. GoT has no native AP client
or mod API, so the check/item bridge must come from either the player (Manual) or a custom tool
(memory poller / injected DLL).

### The Manual template (honor system)

[ManualForArchipelago/Manual](https://github.com/ManualForArchipelago/Manual) is an APworld template
for games that can't (or shouldn't) be modified. There is **no game connection** — the player is the
bridge: they check off locations in the Manual client as they complete them in-game, and they
voluntarily refrain from *using* an ability until its item shows up in the client's received list
("the honor system"). It supports items, locations, regions, categories, access logic (a `requires`
DSL), victory conditions, filler, and toggleable categories via YAML options — everything this
design needs — defined in JSON, with an optional Python `hooks/` layer for custom logic (and a
future path to partial automation). It's been used for Switch games, MMOs, board games, and even
chore-gamification.

---

## 2. Verified research (facts + confidence + sources)

| Finding | Confidence |
|---|---|
| GoT PC **single-player has no anti-cheat** (EAC/BattlEye only guard Legends multiplayer). Memory read/write in SP is safe from bans. | High |
| A **native mod stack exists**: Ultimate ASI Loader as a `d3d12.dll` proxy, plus "GoT Native Loader" (Nexus #845) and "GoT Mod Launcher" (Nexus #860). Native DLLs *can* be injected — the same class of hook as Elden Ring's ModEngine3-loaded client `.dll`. | High |
| **Cheat Engine tables** already expose currency, health/stamina, consumables/ammo. Proves values are findable — but via AOB scans that break on patches. | High |
| **Save files** (`.SAV`, in `Documents\Ghost of Tsushima Director's Cut\<id>\`) already have community-decoded **completion flags** for side quests, hot springs, fox dens, duels, bamboo strikes, haiku, pillars, lighthouses, shrines, merchants, Mongol territories, etc. Saves may be encrypted and are only written at save points (not real-time). | High |
| **No documented Lua/native API for reading/writing gameplay logic state** (inventory unlocks, quest booleans, item-grant functions). Lua in the launcher appears limited to assets/config; gameplay-state access still needs CE-style reverse-engineering. | Medium |
| **NG+ carry-over/reset** (see §7): Techniques/Armor/Vanity carry over; Collections reset; Artifacts persist; Baku + Ghost Flowers are NG+-only; cutscenes skippable; difficulty selectable. | High |
| **"1683 flowers" claim: UNVERIFIED.** The source Reddit thread was not fetchable from this environment. Independent sources describe Ghost Flowers as a **renewable / near-infinite currency**, which conflicts with a fixed finite count. Needs datamining to confirm. | Low |

**Engine note:** GoT runs on **Sucker Punch's proprietary engine** — *not* Decima (that's
Guerrilla's engine). It is neither Unreal nor Unity, so **UE4SS / BepInEx do not apply**; the loader
story is the ASI / `d3d12`-proxy one above.

**Comparable AP worlds and their patterns** (for the "how do checks/items cross the boundary"
question):

| Game | Pattern | Relevance to GoT |
|---|---|---|
| **Elden Ring** | Pure-runtime client `.dll` loaded via **ModEngine3**; hooks live memory (Cheat-Engine-style), nothing patched on disk. | Closest analog — GoT has an equivalent ASI loader, so this pattern is *possible* but needs the offset RE work Elden Ring's authors already did. |
| **Hollow Knight** | C# mod on a real **Modding API** (MonoMod, Unity). | Not applicable — GoT has no managed/Unity runtime or mod API. |
| **Hades / Hades II** | **Lua** mod via a custom Lua loader (`d3d12.dll`). | Only applicable if GoT's Lua reaches gameplay state, which is unconfirmed. |
| **TUNIC** | Mod that *is* an AP client, extending AP's `CommonContext` Python client base. | Shows the standard client architecture we'd target for any future automation. |
| **(fallback) Manual** | Player self-reports; no game connection. | **The realistic starting point for GoT.** |

---

## 3. Technical architecture recommendation

**Bottom line: full automatic check-send / item-receive is *possible but not currently feasible as a
first deliverable*. Build a Manual (honor-system) APworld first, then optionally layer read-side
automation.**

Why full automation is a large project, not a quick win:

- **No public offset/flag map** for what AP must touch: inventory-unlock booleans, per-collectible
  completion flags in live memory, quest state, and item-grant functions. Existing CE tables cover
  currency/health/consumables — useful proof, but not the progression state a randomizer keys on.
- **Granting items is much harder than reading checks.** Reading "did the player clear this fox den"
  is a flag read. Making the game *unlock* an armor/technique/stance on demand means invoking or
  faking the game's own unlock path. Save editors explicitly note that writing "visited/completed"
  flags "has no effect on progression" — flipping a bit doesn't cleanly trigger the reward logic.
- **Fragility:** AOB-scan offsets break on every game patch, so any automated client needs ongoing
  maintenance by someone with engine-RE skills.

### Options considered

| Approach | What it is | Pros | Cons |
|---|---|---|---|
| **A. Manual APworld (honor system)** — **recommended MVP** | ManualForArchipelago template. Player checks off locations in the Manual client and refrains from using an ability until its AP item arrives. Pure JSON + optional Python hooks; no game hooking. | Ships fastest; zero reverse-engineering; no patch fragility; validates the full item/location/logic design; pairs perfectly with NG+. | Relies on player honesty + manual clicking; no hard enforcement; big "sanity" categories are tedious to self-report. |
| **B. External memory poller (`pymem`)** | Standalone Python AP client attaches to `GhostOfTsushima.exe`, reads flags to auto-send checks, optionally writes memory to grant items. | No in-game mod; can run *alongside* a Manual world to auto-detect a subset of checks (hybrid). | Needs a reverse-engineered offset map (doesn't exist yet); breaks on patches; writing item-grants is the risky part. |
| **C. Injected native DLL** (via Ultimate ASI Loader / GoT Mod Launcher) | A C++ ASI mod hooks game functions in-process and talks to an AP client over a local socket — the Elden Ring/ModEngine3 pattern. | Most robust once built (in-process hooks beat external polling); the loader ecosystem already exists for GoT. | Biggest engineering + reverse-engineering effort; C++ + engine RE; ongoing maintenance. Overkill for v1. |

**Recommended path:** **A now, B as an optional hybrid later, C only if the project gains a
reverse-engineer.** Start Manual → optionally bolt on a *read-only* `pymem`/save-watcher to
auto-detect the easiest check categories (the save-flag-backed ones) → reserve full C-style
automation (which also grants items) for a mature version.

---

## 4. Feasibility rating per category

"Feasibility" here is two-dimensional: how easy it is to make each category a working **check/item
in a Manual world**, and how hard it would be to **later automate**. Manual authoring of any
category is inherently Easy (it's data entry from wikis / 100% guides); the ratings therefore lean
on *design clarity* and *automation potential*.

### Items (things you receive)

| Item category | Rating | Reason |
|---|---|---|
| Stances, Ghost Weapons, Ranged Weapons, Grappling Hook, Mythical Techniques | Easy (Manual) / Hard (auto) | Clear discrete unlocks and strong progression items — but they **carry over in NG+**, so honor-system only unless re-lock hooks are built. |
| Armor, Vanity Gear, Sword Kits, Dyes, Saddles, Sashimono/Sakai Banners | Easy (Manual) | Discrete gear/cosmetics; easy items. Cosmetic ones are "useful/filler," not progression. Also carry over in NG+. |
| Major / Minor Charms | Easy (Manual) | Discrete unlockables; good progression/useful items. |
| Technique Points, Health Upgrades, Resolve Points | Easy (Manual) | Natural progression currency/upgrades to gate logic. Confirm exact NG+ reset behavior. |
| Key Items | Easy–Medium | Depends *which* key items — needs enumeration; some are story-gated. |
| Ghost Flowers (filler), Singing Crickets, Records, Records of Iki, Mongol Artifacts | Easy (Manual) | Fine as filler/useful items. Ghost Flowers exist only in NG+. |
| **Automated item-grant for any of the above** | Hard / Unknown | Requires invoking the game's unlock path via memory writes — no known method today. |

### Locations (checks you complete)

| Location category | Rating | Reason |
|---|---|---|
| Fox Dens, Hot Springs, Bamboo Strikes, Pillars of Honor, Lighthouses, Shinto / Iki Wind Shrines, Haiku, Animal Sanctuaries, Hidden Altars | Easy (Manual) / Medium (auto) | Discrete, countable, and **save files already carry completion flags** → strong auto-read candidates. They **reset in NG+**, so repeatable in an NG+ run. |
| Duels, Bokken Tournament, Archery Challenges, Reliving Memories of Father | Easy (Manual) | Discrete named events; clean checks. |
| Merchants, Legend Increases | Easy (Manual) / Medium (auto) | Discrete milestones; Legend rank is a readable stat. |
| Main Quests | Easy (Manual) / Medium (auto) | Ordered story beats; save has act/quest progress. Good spine for regions. |
| Side Quests ("Tales") | Medium | Many exist with save flags, but need a canonical enumerated list + completion-flag confirmation. |
| Kill or Observe Leaders, Mongol Artifacts | Medium | Enumerable, but **Artifacts don't reset in NG+** → already collected in an NG+ save (conflicts with the NG+ premise — see §3/§7). |
| **Flowersanity** (per-flower checks) | Unknown / likely Hard | Count unverified (~1683?), flowers are described as *renewable currency*, and there's **no known per-node collected/not data source**. Even in Manual this is a huge, painful self-report category. |

**"Depends on data we don't have yet" callout:** *every* automation rating (Medium/Hard/Unknown)
depends on a reverse-engineered offset/flag map or a decoded save schema — none of which exist
publicly today. Manual authoring depends only on canonical *lists* per category, which do exist on
wikis and 100% guides.

---

## 5. Open questions / blockers

1. **NG+ vs. fresh save — pick the premise.** NG+ carries over Techniques/Armor/Vanity, so those
   can't be genuine "locked until received" unlocks without heavy re-lock modding — they only work
   on the honor system. A **fresh base-game** run locks abilities naturally and is far better for
   *future automation*, but loses NG+'s cutscene-skip / Baku / Ghost Flowers / easy-difficulty
   perks. Which is the target? *(My read: NG+ + Manual is the coherent v1; revisit for automation.)*
2. **Flowersanity is unverified.** Is the ~1683 figure real (fixed nodes) or a misread of renewable
   currency? Can you point me at the datamine, or is confirming it in scope? Until verified I'd
   scope it out of the MVP entirely.
3. **Artifacts / non-resetting collectibles in NG+.** Mongol Artifacts (and anything else that
   persists through NG+) would be pre-completed in an NG+ save — drop them as checks in NG+, or
   only use them in a fresh-save mode?
4. **Side-quest / Tale enumeration.** Do you already have a canonical list of Tales (base + Iki)
   with names? That's the main content-gathering task for that category.
5. **Two goals, two maps.** "Defeat the Khan" (base) and "Beat the Eagle" (Iki) — one world with a
   goal option and an Iki toggle, or Iki as a separate/optional region set? Affects scope.
6. **Difficulty / async intent + run length.** You mentioned Easy+ for async. Any target for run
   length (number of checks) so I can size the MVP pool sensibly?

---

## 6. Proposed MVP scope

Smallest thing worth building and testing: **a Manual (honor-system) APworld, base game only
(no Iki, no Flowersanity), NG+-friendly.**

- **Goal:** Defeat the Khan.
- **Locations (~120–180 checks):** Main Quests (Act I–III beats) + the discrete, well-enumerated
  exploration categories — Fox Dens, Hot Springs, Bamboo Strikes, Pillars of Honor, Lighthouses,
  Shinto Shrines, Haiku, Duels, Merchants, Legend Increases. (Side quests come in a later phase once
  enumerated.)
- **Items:** A mix that gates logic *and* fills the pool — Stances, Ghost Weapons, Ranged Weapons,
  Grappling Hook, a set of Techniques / Mythic Techniques, Major/Minor Charms, Health/Resolve
  upgrades, Technique Points; **filler** = Ghost Flowers / Singing Crickets / cosmetics (Dyes,
  Vanity, Banners, Saddles).
- **Logic:** Act-gated progression (see §8) using progression items + Legend/technique gates.
- **Deliverable to test:** generates a valid seed, fills without errors, and is beatable on the
  honor system with a real Manual client + tracker.

**Why Manual for the MVP:** it's the only path that produces a *playable, testable* world in days
rather than a reverse-engineering research project, and it de-risks the whole design (item/location
balance, logic) before anyone writes a single memory hook.

---

## 7. New Game+ analysis (why it reshapes the pitch)

Your pitch is to "start in NG+." That's a good call *for a Manual world*, but NG+ has a specific
carry-over behavior that matters:

**Carries over into NG+:** Techniques, Gear Items (Armor), Vanity Pieces (+ a unique red-mane horse
and saddle). **You already own these in NG+.**

**Resets in NG+:** the Collections tab (fox dens, hot springs, bamboo strikes, pillars, haiku,
shrines, lighthouses, etc.) — *except Artifacts, which persist* — plus the map fog / fast-travel
points, and satchel resources drop to zero.

**NG+-only:** Baku the Voiceless (a merchant in Ariake who takes only Ghost Flowers), Ghost Flowers
themselves (a new collectible), new powerful charms, higher difficulty, and **skippable cutscenes**.

Implications for the design:

- **Great for Manual / honor system:** the player already has all abilities, so "receiving" a
  Stance/Technique/Weapon item simply means "you're now *allowed to use* it." The reset Collections
  give a full slate of repeatable exploration checks, cutscene-skip is ideal for async, Baku +
  Ghost Flowers give a clean filler economy, and easy difficulty suits long async runs.
- **Bad for automation:** because abilities pre-exist, you can't cheaply *re-lock* them via memory
  writes — so a "grant on receive / block until then" automated experience would need substantial
  extra modding on top of the offset RE. This is the core reason automation is a later phase.
- **Watch-outs:** Artifacts (and any other non-resetting collectible) are already done in an NG+
  save, so they don't work as checks in an NG+ run (Open Question #3). A *fresh* base-game run is
  the better substrate if/when you pursue real automation.

---

## 8. Phased roadmap after the MVP

- **Phase 2 — Content breadth (still Manual):** add Side Quests / Tales (once enumerated), Animal
  Sanctuaries, Bokken Tournament, Archery Challenges, Hidden Altars, Reliving Memories, remaining
  charms/cosmetics; add YAML options to toggle each category on/off.
- **Phase 3 — Iki Island + second goal:** add Iki regions, Iki Wind Shrines, Records of Iki, the
  Eagle goal; option to include/exclude Iki and to pick the goal (Khan / Eagle / both).
- **Phase 4 — Hybrid read-side automation (optional):** a companion `pymem` / save-watcher that
  auto-sends the easiest check categories (the save-flag-backed ones: fox dens, hot springs, bamboo,
  pillars, shrines, lighthouses) to cut manual clicking. **Reading only** — items still granted on
  the honor system. This is where a reverse-engineered flag map first pays off.
- **Phase 5 — Flowersanity (only if verified):** if the fixed-flower claim checks out *and* a
  per-flower data source is found, add it as a heavy opt-in "sanity" category.
- **Phase 6 — Full automation (stretch, needs a reverse-engineer):** injected ASI DLL (path C) for
  in-process check detection *and* item granting. Large, patch-fragile, separate track.

---

## 9. Rough logic / region sketch (high level, not implementation)

- **Origin:** `Menu` → `Tsushima` (base). Iki gated behind its own region/toggle in a later phase.
- **Act-based progression spine** mirroring the campaign:
  - `Act I — Izuhara` (open first)
  - `Act II — Toyotama` (gated by Act I main-quest completion + a small technique/Legend gate)
  - `Act III — Kamiagata` (gated by Act II completion)
  - *(Phase 3)* `Iki Island` (gated by an Iki-access item / story point)
- Exploration checks live in the act-region where they geographically sit; access rule = "can reach
  that act" (+ occasional tool gates, e.g. Grappling Hook or a specific technique for a handful of
  spots).
- **Progression items** that gate regions/logic: main-story unlock items (or the natural act gates),
  plus a few tools (Grappling Hook, key Ghost Weapons) and Legend-rank thresholds.
- **Goal(s):** `Defeat the Khan` = a victory location in Act III; `Beat the Eagle` = victory
  location on Iki. A world goal option selects which victory location must be reached.
- **NG+ honor-system framing:** because abilities pre-exist in NG+, "receiving" an item means the
  player is *permitted to start using* that stance/weapon/technique — the logic graph still gates
  progression as if it were a fresh unlock.

---

## 10. Sources

Modding / technical feasibility:
- Ghost of Tsushima Director's Cut on Nexus Mods — <https://www.nexusmods.com/games/ghostoftsushima>
- GoT Native Loader (FOV Tweak PoC), Nexus #845 — <https://www.nexusmods.com/ghostoftsushima/mods/845>
- GoT Mod Launcher, Nexus #860 — <https://www.nexusmods.com/ghostoftsushima/mods/860>
- Simple GoT Mod Menu, Nexus #355 — <https://www.nexusmods.com/ghostoftsushima/mods/355>
- Ghost of Tsushima Cheat Table, Nexus #50 — <https://www.nexusmods.com/ghostoftsushima/mods/50>
- Cheat Table for Unlimited Utility, Nexus #141 — <https://www.nexusmods.com/ghostoftsushima/mods/141>
- FearLess Cheat Engine (GoT threads) — <https://fearlessrevolution.com/viewtopic.php?t=29221>
- Ghost of Tsushima Cheat Engine risks (ExitLag) — <https://www.exitlag.com/blog/ghost-of-tsushima-cheat-engine/>
- Ultimate ASI Loader — <https://github.com/ThirteenAG/Ultimate-ASI-Loader>
- GoTFix (Lyall) — <https://github.com/Lyall/GoTFix>
- PC modders coverage (GameRant) — <https://gamerant.com/ghost-of-tsushima-pc-mods-influx-modding-potential/>

Save data / completion flags:
- PS4/PS5 Save Editor for Tsushima (codesprince) — <https://codesprince.com/2020/07/22/ghost-of-tsushima-save-editor/>
- GoT Save Files by Quests and Acts, Nexus #728 — <https://www.nexusmods.com/ghostoftsushima/mods/728>
- Save-File 100%, Nexus #12 — <https://www.nexusmods.com/ghostoftsushima/mods/12>

New Game+ behavior:
- Push Square NG+ guide — <https://www.pushsquare.com/guides/ghost-of-tsushima-how-to-start-new-game-plus-and-what-carries-over>
- Prima Games NG+ — <https://primagames.com/tips/ghost-tsushima-what-carries-over-new-game-plus>
- ScreenRant NG+ — <https://screenrant.com/ghost-tsushima-new-game-plus-guide/>
- Ghost Franchise Wiki: New Game+ — <https://ghostfranchise.fandom.com/wiki/New_Game%2B>

Flowers claim (unverified):
- Reddit thread (referenced, not fetchable from this environment) — <https://www.reddit.com/r/ghostoftsushima/comments/1qpkgbn/there_are_1683_flowers_in_ghost_of_tsushima/>
- Ghost Flowers (Fextralife) — <https://ghostoftsushima.wiki.fextralife.com/Ghost+Flowers>

Archipelago:
- Archipelago repo — <https://github.com/ArchipelagoMW/Archipelago>
- World API docs — <https://github.com/ArchipelagoMW/Archipelago/blob/main/docs/world%20api.md>
- ManualForArchipelago template — <https://github.com/ManualForArchipelago/Manual>
- Manual "how it works" — <https://github.com/ManualForArchipelago/Manual/blob/main/docs/manual/how-it-works.md>
- Elden Ring AP (jambinjambo) — <https://github.com/jambinjambo/ER_Archipelago>
- TUNIC AP randomizer — <https://github.com/silent-destroyer/tunic-randomizer-archipelago>
- Hollow Knight AP mod — <https://github.com/ArchipelagoMW-HollowKnight/Archipelago.HollowKnight>

---

*Next step after your review: confirm the open questions in §5 (especially NG+ vs. fresh-save and
whether Flowersanity is in scope), then I can begin building the Manual MVP world described in §6.*
