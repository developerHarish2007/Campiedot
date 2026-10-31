import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def capture_pilot_views():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1360, 'height': 820})

        # -------------------------------------------------------------
        # Screenshot 1: Day 0 (Scripted Pilot Scenario baseline)
        # -------------------------------------------------------------
        print("Capturing 1: Day 0 Scripted Pilot Scenario...")
        page.goto('http://localhost:5174/?view=cutaway&block=PG')
        page.wait_for_timeout(4000)
        page.screenshot(path='docs/screenshots/pred_pilot_01_day0.png')
        print("Saved docs/screenshots/pred_pilot_01_day0.png")

        # -------------------------------------------------------------
        # Screenshot 2: Day 14 (Preventive Work Order, Floor 2 Blocked)
        # -------------------------------------------------------------
        print("Capturing 2: Day 14 with Floor 2 preventive work order...")
        slider = page.locator('input[type="range"]').first
        if slider.is_visible():
            slider.fill('14')
            page.wait_for_timeout(1500)

        page.screenshot(path='docs/screenshots/pred_pilot_02_day14_workorder.png')
        print("Saved docs/screenshots/pred_pilot_02_day14_workorder.png")

        # -------------------------------------------------------------
        # Screenshot 3: Connection Tab with Room Diorama Projector
        # -------------------------------------------------------------
        print("Capturing 3: Connection Tab with Diorama...")
        page.goto('http://localhost:5174/?view=room&room=PG-201&lab=1')
        page.wait_for_timeout(4000)

        # Click the "How It's Connected" tab
        conn_tab = page.locator('button:has-text("How It\'s Connected")').first
        if conn_tab.is_visible():
            conn_tab.click()
            page.wait_for_timeout(1000)

        page.screenshot(path='docs/screenshots/pred_pilot_03_connection_tab.png')
        print("Saved docs/screenshots/pred_pilot_03_connection_tab.png")

        browser.close()
        print("All 3 pilot screenshots saved!")

if __name__ == '__main__':
    capture_pilot_views()

