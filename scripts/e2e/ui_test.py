"""Drive the Plant Manager panel in a real HA instance."""

import json, struct, zlib
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

BASE = "http://host.docker.internal:8124"
TOKEN = json.load(open("/out/tokens.json"))["tokens"]["access_token"]
OUT = "/out"
errors = []


def png(w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


open(f"{OUT}/leaf.png", "wb").write(png(300, 300, (60, 140, 70)))


def step(msg):
    print("STEP:", msg, flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    step("login")
    page.goto(BASE + "/")
    page.locator('input[name="username"]').fill("test")
    page.locator('input[name="password"]').fill("test1234")
    page.keyboard.press("Enter")
    page.wait_for_function(
        "() => document.querySelector('home-assistant')?.hass?.connected", timeout=60000
    )

    step("sidebar link")
    page.locator("ha-sidebar").get_by_text("Plants").first.wait_for(timeout=30000)

    step("open panel")
    page.goto(BASE + "/plant-manager")
    panel = page.locator("plant-manager-panel")
    panel.locator("text=No plants yet").wait_for(timeout=30000)
    page.screenshot(path=f"{OUT}/01-empty.png")

    step("add plant with photo")
    panel.locator('[data-action="new-plant"]').click()
    panel.locator("text=choose a service").wait_for(timeout=10000)
    panel.locator("input[type=file][data-identify]").last.set_input_files(f"{OUT}/leaf.png")
    panel.locator(".photo.pending").first.wait_for(timeout=15000)
    panel.locator('[data-field="species"]').fill("Monstera deliciosa")
    panel.locator('[data-field="species"]').dispatch_event("change")
    panel.locator("text=built-in database").wait_for(timeout=15000)
    assert panel.locator('[data-field="name"]').input_value() == "Swiss cheese plant"
    panel.locator('[data-field="name"]').fill("Monty")
    panel.locator('select[data-field="pot_material"]').select_option("terracotta")
    panel.locator('[data-field="pot_diameter_cm"]').fill("21")
    panel.locator('select[data-field="temperature_sensor"]').select_option(
        "sensor.living_room_temperature"
    )
    panel.locator('select[data-field="humidity_sensor"]').select_option(
        "sensor.living_room_humidity"
    )
    page.screenshot(path=f"{OUT}/02-editor.png", full_page=True)
    panel.locator('[data-action="save-plant"]').click()
    panel.locator(".toast", has_text="Saved Monty").wait_for(timeout=15000)
    panel.locator(".plant-card", has_text="Monty").locator("img").wait_for(timeout=15000)

    step("more plants through the API")
    old = (date.today() - timedelta(days=25)).isoformat()
    panel.evaluate(
        """async (el, old) => {
      await el.hass.callWS({type: "plant_manager/plants/create", plant: {
        name: "Fern", species: "Nephrolepis exaltata", light: "low", last_watered: old}});
      await el.hass.callWS({type: "plant_manager/plants/create", plant: {
        name: "Snake plant", species: "Dracaena trifasciata", pot_diameter_cm: 18}});
    }""",
        old,
    )
    panel.locator(".plant-card", has_text="Fern").wait_for(timeout=15000)
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/03-plants.png")

    step("plant detail")
    panel.locator(".plant-card", has_text="Monty").locator(".name").click()
    panel.locator("text=Why every").wait_for(timeout=15000)
    page.screenshot(path=f"{OUT}/04-detail.png", full_page=True)
    panel.locator('[data-action="close-editor"]').click()

    step("today")
    panel.locator('[data-action="view"][data-view="today"]').click()
    panel.locator(".list-row", has_text="Fern").wait_for(timeout=10000)
    page.screenshot(path=f"{OUT}/05-today.png")
    panel.locator(".list-row", has_text="Fern").locator('[data-action="water"]').first.click()
    panel.locator(".toast", has_text="Fern watered").wait_for(timeout=10000)
    panel.locator(".toast button", has_text="Undo").click()
    panel.locator(".toast", has_text="Undone").wait_for(timeout=10000)
    panel.locator(".list-row", has_text="Fern").wait_for(timeout=10000)

    step("schedule")
    panel.locator('[data-action="view"][data-view="schedule"]').click()
    panel.locator(".day-head").first.wait_for(timeout=10000)
    page.screenshot(path=f"{OUT}/06-schedule.png")

    step("vacation")
    panel.locator('[data-action="view"][data-view="vacation"]').click()
    panel.locator("text=Plan a vacation").wait_for(timeout=10000)
    panel.locator("th", has_text="While away").wait_for(timeout=10000)
    leave = date.today() + timedelta(days=2)
    panel.locator('[data-trip="start_date"]').fill(leave.isoformat())
    panel.locator('[data-trip="start_date"]').dispatch_event("change")
    panel.locator('[data-trip="end_date"]').fill((leave + timedelta(days=14)).isoformat())
    panel.locator('[data-trip="end_date"]').dispatch_event("change")
    panel.locator("text=Projected for 14.4 days away").wait_for(timeout=10000)
    panel.locator('[data-trip="sitter"]').fill("Anna")
    panel.locator('[data-trip="notes"]').fill("The watering can is on the balcony.")
    panel.locator('[data-action="save-trip"]').click()
    panel.locator('[data-action="end-trip"]', has_text="Cancel vacation").wait_for(timeout=10000)
    panel.locator("h2", has_text="Anna waters on").wait_for(timeout=10000)
    page.screenshot(path=f"{OUT}/09-vacation.png", full_page=True)
    panel.locator('[data-action="view"][data-view="schedule"]').click()
    panel.locator(".banner").wait_for(timeout=10000)
    panel.locator("text=Plant sitter waters").first.wait_for(timeout=10000)
    page.screenshot(path=f"{OUT}/10-schedule-vacation.png")

    step("mobile")
    page.set_viewport_size({"width": 390, "height": 844})
    panel.locator('[data-action="view"][data-view="plants"]').click()
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/07-mobile.png")
    panel.locator('[data-action="view"][data-view="vacation"]').click()
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/11-mobile-vacation.png", full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})

    step("import and export")
    panel.locator('[data-action="view"][data-view="plants"]').click()
    panel.locator('[data-action="toggle-data"]').click()
    with page.expect_download() as download:
        panel.locator('[data-action="export-csv"]').click()
    exported = open(download.value.path(), encoding="utf-8").read()
    assert exported.startswith("name,species,"), exported[:80]
    assert "Monty" in exported
    open(f"{OUT}/import.csv", "w", encoding="utf-8").write(
        "name;species;light;pot_diameter_cm\nBasil;Ocimum basilicum;direct;12\n"
        "Pothos;Epipremnum aureum;low;14\nBroken;;;\n"
    )
    panel.locator("input[data-import-csv]").set_input_files(f"{OUT}/import.csv")
    panel.locator("text=Imported 2 plant(s).").wait_for(timeout=15000)
    panel.locator(".plant-card", has_text="Pothos").wait_for(timeout=15000)
    page.screenshot(path=f"{OUT}/12-import.png")
    with page.expect_download() as download:
        panel.locator('[data-action="backup"]').click()
    download.value.save_as(f"{OUT}/backup.zip")

    step("card")
    page.evaluate("""async () => {
      const hass = document.querySelector('home-assistant').hass;
      await hass.callWS({type: "lovelace/dashboards/create", url_path: "dashboard-plants",
        title: "Plant card", mode: "storage"});
      await hass.callWS({type: "lovelace/config/save", url_path: "dashboard-plants", config: {
        views: [{title: "Home", cards: [{type: "custom:plant-manager-card"}]}]}});
    }""")
    page.goto(BASE + "/dashboard-plants/0")
    try:
        page.locator("plant-manager-card").locator("text=Fern").wait_for(timeout=30000)
    finally:
        page.screenshot(path=f"{OUT}/08-card.png")
    page.wait_for_timeout(500)
    page.screenshot(path=f"{OUT}/08-card.png")

    step("card editor")
    page.goto(BASE + "/dashboard-plants/0?edit=1")
    try:
        page.get_by_text("Add card").first.click(timeout=30000)
        page.get_by_text("By card", exact=True).first.click(timeout=15000)
        page.get_by_placeholder("Search cards").first.fill("Plant Manager", timeout=15000)
        page.get_by_text("Plant Manager", exact=True).first.click(timeout=15000, force=True)
        page.get_by_text("Show counts (plants, need water, problems)").first.wait_for(
            timeout=15000
        )
    finally:
        page.screenshot(path=f"{OUT}/14-card-editor.png")
    page.keyboard.press("Escape")

    step("my notifications")
    page.goto(BASE + "/plant-manager/plants")
    panel.locator('[data-action="open-notify"]').click(timeout=30000)
    panel.locator("text=No phones yet").wait_for(timeout=10000)
    panel.locator("text=Daily summary").wait_for(timeout=10000)
    page.screenshot(path=f"{OUT}/15-notifications.png")
    panel.locator('[data-action="close-notify"]').click()

    step("restore backup")
    page.goto(BASE + "/plant-manager/plants")
    panel.locator(".plant-card", has_text="Pothos").wait_for(timeout=30000)
    panel.evaluate(
        """async (el) => {
      const plant = el._plants.find((p) => p.name === "Pothos");
      await el.hass.callWS({type: "plant_manager/plants/delete", plant_id: plant.id});
    }"""
    )
    panel.locator(".plant-card", has_text="Pothos").wait_for(state="detached", timeout=15000)
    page.once("dialog", lambda dialog: dialog.accept())
    panel.locator('[data-action="toggle-data"]').click()
    panel.locator("input[data-restore]").set_input_files(f"{OUT}/backup.zip")
    panel.locator(".toast", has_text="Restored 5 plant(s)").wait_for(timeout=15000)
    panel.locator(".plant-card", has_text="Pothos").wait_for(timeout=30000)
    page.screenshot(path=f"{OUT}/13-restored.png")

    browser.close()

relevant = [e for e in errors if "plant" in e.lower() or "pageerror" in e]
print("ERRORS:", json.dumps(relevant, indent=1) if relevant else "none")
