import sys
import time
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    console_logs = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        def handle_console(msg):
            text = msg.text
            console_logs.append(f"[{msg.type}] {text}")
            print(f"BROWSER CONSOLE: [{msg.type}] {text}")

        page.on('console', handle_console)
        page.on('pageerror', lambda err: page_errors.append(str(err)))

        print("\n--- TEST 1: Direct debug URL - PG Cutaway ---")
        page.goto('http://localhost:5174/?view=cutaway&block=PG')
        page.wait_for_timeout(3500)
        page.screenshot(path='docs/screenshots/a_pg_cutaway.png')
        print("Captured docs/screenshots/a_pg_cutaway.png")

        print("\n--- TEST 2: Direct debug URL - Ordinary Classroom PG-101 ---")
        page.goto('http://localhost:5174/?view=room&room=PG-101')
        page.wait_for_timeout(3500)
        page.screenshot(path='docs/screenshots/b_ordinary_classroom.png')
        print("Captured docs/screenshots/b_ordinary_classroom.png")

        print("\n--- TEST 3: Direct debug URL - Smart Lab PG-201 (&lab=1) ---")
        page.goto('http://localhost:5174/?view=room&room=PG-201&lab=1')
        page.wait_for_timeout(3500)
        page.screenshot(path='docs/screenshots/c_smart_lab.png')
        print("Captured docs/screenshots/c_smart_lab.png")

        print("\n--- TEST 4: Direct debug URL - Non-PG Block Cutaway (CIVIL) ---")
        page.goto('http://localhost:5174/?view=cutaway&block=CIVIL')
        page.wait_for_timeout(3500)
        page.screenshot(path='docs/screenshots/d_civil_cutaway.png')
        print("Captured docs/screenshots/d_civil_cutaway.png")

        print("\n--- TEST 5: Interactive Click Path ---")
        # Load base campus
        page.goto('http://localhost:5174/')
        page.wait_for_timeout(3500)

        # Open panel if not open, or verify enter button for selected PG Block
        enter_btn = page.locator('button.enter-building-btn')
        if not enter_btn.is_visible():
            # If panel is collapsed, toggle drawer button
            toggle_btn = page.locator('button:has-text("Operations")')
            if toggle_btn.is_visible():
                toggle_btn.click()
                page.wait_for_timeout(1000)

        print(f"Enter building button visible: {enter_btn.is_visible()}")
        if enter_btn.is_visible():
            btn_text = enter_btn.inner_text()
            print(f"Button text: {btn_text}")
            enter_btn.click()
            page.wait_for_timeout(2000)
            page.screenshot(path='docs/screenshots/test_click_cutaway_entered.png')
            print("Successfully entered cutaway via side panel button!")

            # In cutaway, click room PG 201 in bottom dock
            room_btn = page.locator('button:has-text("PG 201")').first
            if room_btn.is_visible():
                room_btn.click()
                page.wait_for_timeout(2500)
                page.screenshot(path='docs/screenshots/test_click_room_entered.png')
                print("Successfully entered room diorama via room dock!")

                # Press Escape to return to cutaway
                page.keyboard.press('Escape')
                page.wait_for_timeout(1500)
                print("Pressed Escape: returned to cutaway")

                # Press Escape again to return to campus
                page.keyboard.press('Escape')
                page.wait_for_timeout(1500)
                print("Pressed Escape: returned to campus")

        print("\n--- TEST 6: Double-Click Building to Enter Cutaway ---")
        # Click on canvas center where building is located or double click on building canvas
        # We can trigger dblclick on canvas
        page.mouse.dblclick(640, 420)
        page.wait_for_timeout(2000)
        page.screenshot(path='docs/screenshots/test_double_click_cutaway.png')
        print("Captured docs/screenshots/test_double_click_cutaway.png")

        browser.close()

    print("\n--- SUMMARY OF CONSOLE LOGS MATCHING [interior] ---")
    interior_logs = [log for log in console_logs if '[interior]' in log]
    for log in interior_logs:
        print(log)

    print(f"\nTotal page errors: {len(page_errors)}")
    for err in page_errors:
        print(f"PAGE ERROR: {err}")

if __name__ == '__main__':
    run_tests()
