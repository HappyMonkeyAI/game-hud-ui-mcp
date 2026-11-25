# MCP Intent Map

Transport: **stdio** (runs locally from this project; binds no network port).

## Tools
- `search_game_ui_patterns(query, category="", limit=8)`: Search curated HUD/menu blueprints and optional validated local catalog entries with deterministic tie-breaking.
- `recommend_game_ui(screen_or_hud, genre="", platform_input="", visual_direction="", diegetic_preference="", constraints="", accessibility_needs="", limit=3)`: Score and rank game UI patterns for a brief, emit explicit `excluded_references` on modality/accessibility conflicts, and attach look-don't-copy human research keywords for `gameuidatabase.com`.
- `list_game_ui_references()`: Non-recursive read-only inventory of sibling game and Three.js repositories with `README.md` and `LICENSE` detection.
- `get_game_ui_guidance(brief="")`: Return core game-UI design principles and activate one opt-in direction pack when explicitly requested in `brief`.
- `audit_local_game_ui(path)`: Inert, size-bounded (`<= 1 MB`), root-jailed static heuristic check on one local `.html`, `.htm`, `.css`, `.js`, `.mjs`, `.jsx`, or `.tsx` file.

## Resources
- `game-ui-advisor://sources`: Source provenance & license registry (including Game UI Database's anti-scraping / human-study-only status).
- `game-ui-advisor://taxonomy`: Structured game UI vocabulary (`screen_types`, `hud_categories`, `diegetic_modes`, `input_modalities`, `safe_zones`, `genres`).
- `game-ui-advisor://local-assets`: Live counts of curated patterns, optional local catalog entries, and detected sibling repositories.

## Optional Environment Variables
- `GAME_HUD_UI_WORKSPACE`: Parent workspace root for sibling game repo discovery (defaults to `../`).
- `GAME_HUD_UI_THREEJS_ROOT`: Optional root for sibling Three.js repos (defaults to `<WORKSPACE>/../threejs`).
- `GAME_HUD_UI_AUDIT_ROOT`: Allowed root directory for `audit_local_game_ui` (defaults to this repository root).
- `GAME_HUD_UI_CATALOG_INDEX`: Optional JSON index path (must resolve inside `GAME_HUD_UI_WORKSPACE`, max 5 MB).
- `GAME_HUD_UI_LOCAL_REFS`: Optional JSON overlay path for extra local sibling entries (defaults to gitignored `references.local.json`, max 1 MB).
