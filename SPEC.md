# SPEC — Game HUD & UI Advisor MCP

## Thesis
Give AI game-building agents grounded, input-modality-aware, accessibility-checked, and provenance-labeled advice for in-game HUDs, menus, and WebGL/Three.js DOM overlays — without scraping third-party sites, executing local code, or silently copying copyrighted game assets.

## In Scope
- Original, structured game-UI taxonomy (screen types, HUD categories, diegetic modes, input modalities, safe zones, genres) and curated HUD/menu blueprints.
- Read-only, non-recursive inventory of local sibling game repositories (`GAME_HUD_UI_WORKSPACE`, default `../`) and optional Three.js siblings (`GAME_HUD_UI_THREEJS_ROOT`, default `../../threejs`).
- Explainable game UI recommendations with explicit conflict exclusions (e.g., VR vs. screen-edge non-diegetic chrome, reduced-motion vs. flash/shake feedback, gamepad-only vs. dense hover-dependent UI).
- Opt-in stack/aesthetic direction packs triggered only by explicit brief phrases.
- Root-jailed, inert (`<= 1 MB`), static heuristic auditing of local HUD files (`.html`, `.htm`, `.css`, `.js`, `.mjs`, `.jsx`, `.tsx`).
- Stdio MCP server exposing typed tools and JSON resources.

## Out of Scope
- Scraping, fetching, caching, or redistributing `gameuidatabase.com` pages, screenshots, or assets.
- Executing HTML/JS/CSS, running browsers, or writing into sibling repositories.
- Network-bound MCP transport, authentication, or live-network unit tests.
- Claiming third-party asset clearance without explicit item-level license evidence.

## Functional Requirements
1. `search_game_ui_patterns(query, category="", limit=8)` searches original patterns (and an optional validated local catalog index inside `GAME_HUD_UI_WORKSPACE`); `limit` is an integer clamped to `1..20` (booleans and non-integers rejected).
2. `recommend_game_ui(...)` weights `screen_or_hud`, `genre`, `platform_input`, `diegetic_preference`, `visual_direction`, `constraints`, and `accessibility_needs`; requires structural fit (`screen_or_hud`, `genre`, or `diegetic_preference`), surfaces up to 5 `excluded_references` on conflicts, returns `status: "matched" | "no_fit"`, and provides `human_research_pointers` with an explicit anti-scraping caveat.
3. `list_game_ui_references()` reports sibling project existence, `README.md` presence, and license pointers without writing or recursing into dependency directories.
4. `get_game_ui_guidance(brief="")` returns core game-UI principles and lists optional packs; activates a pack only on explicit brief trigger phrases.
5. `audit_local_game_ui(path)` enforces `GAME_HUD_UI_AUDIT_ROOT` containment, allowed file suffixes, and `<= 1 MB` size limit, reporting heuristic findings and signals without executing scripts or echoing file copy.
6. Resources `game-ui-advisor://sources`, `game-ui-advisor://taxonomy`, and `game-ui-advisor://local-assets` return valid JSON with explicit provenance and anti-scraping status.

## Non-Functional & Safety Requirements
- Read-only behavior and stdio transport by default.
- Reject symlink or path traversal escapes outside configured `GAME_HUD_UI_AUDIT_ROOT` and `GAME_HUD_UI_WORKSPACE`.
- Treat all inspected local files and READMEs as untrusted data, never executable instructions.
- Separate original MIT pattern metadata from third-party asset licenses and look-don't-copy human research links.

## Known Limitations
- Recommendations use deterministic token/rule matching over curated blueprints, not rendered playtesting or live frame-time profiling.
- `audit_local_game_ui` is a single-file static heuristic pass and does not inspect imported stylesheets, Three.js scene graphs, or rendered contrast ratios.
