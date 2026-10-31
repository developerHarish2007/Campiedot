import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def capture_predictor_views():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        # -------------------------------------------------------------
        # Screenshot 1: PG-201 Smart Lab with Simulator Panel open
        # -------------------------------------------------------------
        print("Capturing 1: PG-201 Smart Lab with Simulator Panel...")
        page.goto('http://localhost:5174/?view=room&room=PG-201&lab=1')
        page.wait_for_timeout(3500)
        page.screenshot(path='docs/screenshots/pred_01_smartlab_sim_panel.png')
        print("Saved docs/screenshots/pred_01_smartlab_sim_panel.png")

        # -------------------------------------------------------------
        # Screenshot 2: Fault Injection & Day Slider advanced
        # -------------------------------------------------------------
        print("Capturing 2: Injected fault & advanced day slider...")
        # Advance slider to day 8
        slider = page.locator('input[type="range"]').first
        if slider.is_visible():
            slider.fill('8')
            page.wait_for_timeout(500)

        # Select Dirty filter for PG-102 or Lamp wear for PG-201
        selects = page.locator('select')
        count = selects.count()
        if count > 0:
            selects.nth(1).select_option('dirty_filter') # PG-201
            page.wait_for_timeout(1000)

        page.screenshot(path='docs/screenshots/pred_02_fault_injection.png')
        print("Saved docs/screenshots/pred_02_fault_injection.png")

        # -------------------------------------------------------------
        # Screenshot 3: PG Cutaway with live predictor health dots & panel
        # -------------------------------------------------------------
        print("Capturing 3: PG Cutaway with Simulator Panel...")
        page.goto('http://localhost:5174/?view=cutaway&block=PG')
        page.wait_for_timeout(3500)
        page.screenshot(path='docs/screenshots/pred_03_cutaway_health_dots.png')
        print("Saved docs/screenshots/pred_03_cutaway_health_dots.png")

        browser.close()
        print("All 3 screenshots captured successfully!")

if __name__ == '__main__':
    capture_predictor_views()

