"""Deterministic, zero-network pytest suite for game-hud-ui-mcp."""

from __future__ import annotations

import json
from pathlib import Path

from game_hud_ui_advisor import server

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_search_patterns_matching_category_clamping_and_validation() -> None:
    res = server.search_game_ui_patterns("combat minimap", limit=5)
    assert res["total"] >= 12
    assert res["matched_count"] >= 1
    assert res["results"][0]["slug"] == "action-combat-hud"

    cat = server.search_game_ui_patterns("", category="engine-threejs", limit=50)
    assert len(cat["results"]) == 1
    assert cat["results"][0]["slug"] == "threejs-dom-overlay-hud"

    racing = server.search_game_ui_patterns("racing speedometer lap boost", limit=5)
    assert racing["matched_count"] >= 1
    assert racing["results"][0]["slug"] == "racing-arcade-hud"

    bad_bool = server.search_game_ui_patterns("hud", limit=True)
    assert bad_bool["error"] == "limit_must_be_integer"
    bad_str = server.search_game_ui_patterns("hud", limit="5")  # type: ignore[arg-type]
    assert bad_str["error"] == "limit_must_be_integer"


def test_search_patterns_external_catalog_validation(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "games"
    ws.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(
        json.dumps({"schema_version": 1, "pattern_count": 1, "patterns": [{"slug": "ext", "name": "Ext"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAME_HUD_UI_WORKSPACE", str(ws))
    monkeypatch.setenv("GAME_HUD_UI_CATALOG_INDEX", str(outside))
    assert server.search_game_ui_patterns("ext")["matched_count"] == 0

    valid_idx = ws / "custom-patterns.json"
    valid_idx.write_text(
        json.dumps({
            "schema_version": 1,
            "pattern_count": 1,
            "patterns": [
                {
                    "slug": "custom-submarine-sonar",
                    "name": "Custom Submarine Sonar HUD",
                    "category": "hud-custom",
                    "genres": ["simulation"],
                    "diegetic_mode": "diegetic",
                    "input_modes": ["kbm", "gamepad"],
                    "engine_fit": ["threejs"],
                    "layout_zones": ["Center sonar scope"],
                }
            ],
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAME_HUD_UI_CATALOG_INDEX", str(valid_idx))
    found = server.search_game_ui_patterns("submarine")
    assert found["matched_count"] == 1
    assert found["results"][0]["slug"] == "custom-submarine-sonar"

    # Malformed count fails closed.
    valid_idx.write_text(
        json.dumps({"schema_version": 1, "pattern_count": 99, "patterns": [{"slug": "bad", "name": "Bad"}]}),
        encoding="utf-8",
    )
    assert server.search_game_ui_patterns("bad")["matched_count"] == 0


def test_recommend_game_ui_fps_4x_vr_reduced_motion_and_no_fit() -> None:
    fps = server.recommend_game_ui(
        screen_or_hud="combat HUD with health and minimap",
        genre="fps",
        visual_direction="threejs overlay",
    )
    assert fps["status"] == "matched"
    slugs = [r["slug"] for r in fps["recommendations"]]
    assert "action-combat-hud" in slugs
    assert fps["human_research_pointers"]["reference_archive"] == "https://www.gameuidatabase.com/"
    assert "scraping" in fps["human_research_pointers"]["policy_caveat"].lower()

    fourx = server.recommend_game_ui(screen_or_hud="command HUD resource economy map", genre="strategy-4x")
    assert fourx["status"] == "matched"
    assert fourx["recommendations"][0]["slug"] == "tactical-4x-command-hud"

    vr = server.recommend_game_ui(
        screen_or_hud="combat HUD",
        platform_input="vr headset",
        diegetic_preference="spatial",
    )
    assert vr["status"] == "matched"
    assert vr["recommendations"][0]["slug"] == "vr-spatial-curved-hud"
    excluded_slugs = {item["slug"] for item in vr["excluded_references"]}
    assert "action-combat-hud" in excluded_slugs

    calm = server.recommend_game_ui(
        screen_or_hud="combat feedback hit markers",
        accessibility_needs="reduced-motion low-flash",
    )
    calm_excluded = {item["slug"] for item in calm["excluded_references"]}
    assert "combat-feedback-juice" in calm_excluded

    no_fit = server.recommend_game_ui(screen_or_hud="dentist appointment form", genre="healthcare")
    assert no_fit["status"] == "no_fit"
    assert no_fit["recommendations"] == []

    ocean = server.recommend_game_ui(
        screen_or_hud="racing HUD speedometer lap timer boost meter buoy waypoints minimap",
        genre="racing-flight",
        platform_input="kbm gamepad",
        visual_direction="threejs cel-shaded stylized ocean",
    )
    assert ocean["status"] == "matched"
    assert ocean["recommendations"][0]["slug"] == "racing-arcade-hud"
    assert "threejs-dom-overlay-hud" in [r["slug"] for r in ocean["recommendations"]]
    assert "action-combat-hud" in {e["slug"] for e in ocean["excluded_references"]}


def test_list_game_ui_references_read_only_inventory(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "games"
    three = tmp_path / "threejs"
    (ws / "threejs-game-skills").mkdir(parents=True)
    (ws / "threejs-game-skills" / "README.md").write_text("# Skills", encoding="utf-8")
    (ws / "threejs-game-skills" / "LICENSE").write_text("MIT", encoding="utf-8")
    (three / "scallyw4g-bonsai").mkdir(parents=True)
    (ws / "custom-local-game").mkdir(parents=True)
    overlay = ws / "references.local.json"
    overlay.write_text(
        json.dumps({"games": {"custom-local-game": "Local test overlay"}, "threejs": {}}),
        encoding="utf-8",
    )

    monkeypatch.setenv("GAME_HUD_UI_WORKSPACE", str(ws))
    monkeypatch.setenv("GAME_HUD_UI_THREEJS_ROOT", str(three))
    monkeypatch.setenv("GAME_HUD_UI_LOCAL_REFS", str(overlay))

    inv = server.list_game_ui_references()
    by_name = {item["name"]: item for item in inv["references"]}
    assert by_name["threejs-game-skills"]["exists"] is True
    assert by_name["threejs-game-skills"]["has_readme"] is True
    assert by_name["threejs-game-skills"]["license_pointer"] == "LICENSE"
    assert by_name["tinyskies"]["exists"] is False
    assert by_name["scallyw4g-bonsai"]["exists"] is True
    assert by_name["scallyw4g-bonsai"]["license_pointer"] == "none_found"
    assert by_name["custom-local-game"]["exists"] is True
    assert by_name["custom-local-game"]["note"] == "Local test overlay"


def test_public_files_contain_no_private_host_paths() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    forbidden = (
        "C:\\" + "Users\\",
        "C:/" + "Users/",
        "/Users" + "/",
        "/home" + "/",
        "\\" + "steph\\",
        "/steph" + "/",
        "kb_" + "vault",
        "192." + "168.",
        "Three" + "GameForge",
        "img2" + "threejs",
    )
    skip_dirs = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.name.endswith(".local.json") or path.name.endswith(".local.md"):
            continue
        if path.suffix.casefold() in {".png", ".jpg", ".jpeg", ".pyc"}:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for needle in forbidden:
            assert needle not in content, f"Forbidden private string {needle!r} found in {path}"


def test_get_game_ui_guidance_opt_in_directions() -> None:
    plain = server.get_game_ui_guidance("standard game pause menu")
    assert len(plain["principles"]) >= 5
    assert "active_direction" not in plain

    three = server.get_game_ui_guidance("Use a Three.js DOM overlay for the HUD")
    assert three["active_direction"]["id"] == "threejs-webgl-hud"

    vr_wins = server.get_game_ui_guidance("Three.js WebXR VR headset cockpit")
    assert vr_wins["active_direction"]["id"] == "vr-spatial-hud"

    cel_and_three = server.get_game_ui_guidance("Three.js WebGL cel-shaded ocean racing HUD")
    assert cel_and_three["active_direction"]["id"] == "cel-shaded-stylized"
    assert "threejs-webgl-hud" in [d["id"] for d in cel_and_three["secondary_directions"]]


def test_audit_local_game_ui_good_risky_and_rejections(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GAME_HUD_UI_AUDIT_ROOT", str(FIXTURES.parent.parent))

    good = server.audit_local_game_ui(str(FIXTURES / "good_hud.html"))
    assert good["status"] == "reviewed"
    assert good["findings"] == []
    assert good["signals"]["pointer_events_passthrough_hint"] is True
    assert good["signals"]["user_select_none_hint"] is True
    assert good["signals"]["reduced_motion_hint"] is True
    assert good["signals"]["visible_focus_hint"] is True
    assert good["signals"]["aria_live_hint"] is True

    risky = server.audit_local_game_ui(str(FIXTURES / "risky_hud.html"))
    assert risky["status"] == "reviewed"
    finding_ids = {f["id"] for f in risky["findings"]}
    assert {
        "missing_viewport_meta",
        "image_missing_alt",
        "missing_pointer_events_passthrough",
        "missing_user_select_none",
        "tiny_hud_font_size",
        "missing_reduced_motion_fallback",
        "missing_visible_focus_style",
        "excessive_backdrop_blur",
    } <= finding_ids
    assert "SECRET_HUD_COPY_DO_NOT_ECHO" not in json.dumps(risky)

    # Outside root, bad extension, and oversized files are rejected.
    outside = tmp_path / "outside.html"
    outside.write_text("<html></html>", encoding="utf-8")
    assert server.audit_local_game_ui(str(outside))["status"] == "rejected"

    monkeypatch.setenv("GAME_HUD_UI_AUDIT_ROOT", str(tmp_path))
    py_file = tmp_path / "script.py"
    py_file.write_text("print('hi')", encoding="utf-8")
    assert server.audit_local_game_ui(str(py_file))["reason"] == "expected_supported_ui_file"

    huge = tmp_path / "huge.css"
    huge.write_bytes(b"a" * 1_000_005)
    assert server.audit_local_game_ui(str(huge))["reason"] == "file_too_large"


def test_resources_and_mcp_registration() -> None:
    sources = json.loads(server.sources_resource())
    g_db = next(s for s in sources["sources"] if s["name"] == "Game UI Database")
    assert g_db["scraping_allowed"] is False

    taxonomy = json.loads(server.taxonomy_resource())
    assert "non-diegetic" in taxonomy["diegetic_modes"]
    assert "main-menu" in taxonomy["screen_types"]

    assets = json.loads(server.local_assets_resource())
    assert assets["curated_pattern_count"] >= 13

    tool_names = set(server.mcp._tool_manager._tools.keys())
    assert {
        "search_game_ui_patterns",
        "recommend_game_ui",
        "list_game_ui_references",
        "get_game_ui_guidance",
        "audit_local_game_ui",
    } <= tool_names

    resource_uris = set(server.mcp._resource_manager._resources.keys())
    assert {
        "game-ui-advisor://sources",
        "game-ui-advisor://taxonomy",
        "game-ui-advisor://local-assets",
    } <= resource_uris
