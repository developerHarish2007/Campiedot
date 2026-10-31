import sys
import time
from PIL import Image
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        # -------------------------------------------------------------
        # STEP 1: Screenshot (a) - Room RED with count badge
        # -------------------------------------------------------------
        print("Navigating to 3D Twin PG Cutaway...")
        page.goto('http://localhost:5174/?view=cutaway&block=PG')
        page.wait_for_timeout(3500)

        # Clear any old reports/warnings first for clean baseline
        page.evaluate("""() => {
            if (window.dashboardBridge) {
                window.dashboardBridge.resolveReportsForRoom('PG-201');
            }
        }""")
        page.wait_for_timeout(500)

        # Simulate student report for PG-201
        print("Triggering simulated student report for PG-201...")
        page.evaluate("""() => {
            if (window.dashboardBridge) {
                window.dashboardBridge.simulateStudentReport('PG-201', 'AV', 'Projector flickering and loud cooling fan noise in room PG-201');
            }
        }""")
        page.wait_for_timeout(2000)

        screenshot_a = 'docs/screenshots/bridge_01_room_red_count.png'
        page.screenshot(path=screenshot_a)
        print(f"Saved: {screenshot_a}")

        # -------------------------------------------------------------
        # STEP 2: Screenshot (b) - Room YELLOW & Dashboard Predictive Warning
        # -------------------------------------------------------------
        print("Resolving open student report so RED marker clears...")
        page.evaluate("""() => {
            if (window.dashboardBridge) {
                window.dashboardBridge.resolveReportsForRoom('PG-201');
            }
        }""")
        page.wait_for_timeout(1000)

        print("Triggering fault on PG-201-PROJ to transition health to degrading/imminent (YELLOW)...")
        # Find fault dropdown for PG-201 or trigger day 14 where PG-201 is 2874h (imminent)
        pg201_select = page.locator('div:has-text("PG-201") >> select').first
        if pg201_select.is_visible():
            pg201_select.select_option('lamp_wear')
            print("Selected 'lamp_wear' for PG-201.")
        else:
            all_selects = page.locator('select').all()
            if len(all_selects) >= 3:
                all_selects[2].select_option('lamp_wear')
                print("Selected 'lamp_wear' on 3rd select.")

        page.wait_for_timeout(3000)
        twin_yellow_temp = 'work/temp_twin_yellow.png'
        page.screenshot(path=twin_yellow_temp)
        print(f"Captured twin view with YELLOW room marker: {twin_yellow_temp}")

        # Open CampusOps Dashboard on port 5173
        print("Navigating to CampusOps Dashboard at http://localhost:5173...")
        dash_page = browser.new_page(viewport={'width': 1280, 'height': 800})
        dash_page.goto('http://localhost:5173')
        dash_page.wait_for_timeout(1500)

        # Set admin portal mode in localStorage and reload
        dash_page.evaluate("""() => {
            localStorage.setItem('campusops_portal_mode', 'admin');
        }""")
        dash_page.reload()
        dash_page.wait_for_timeout(1500)

        # Switch to Work Orders tab
        wo_tab = dash_page.locator('button:has-text("Work Orders")').first
        if wo_tab.is_visible():
            wo_tab.click()
            dash_page.wait_for_timeout(1500)

        dash_temp = 'work/temp_dashboard_warning.png'
        dash_page.screenshot(path=dash_temp)
        print(f"Captured dashboard work orders ledger: {dash_temp}")

        # Combine both images side-by-side using PIL
        print("Composing side-by-side verification image for Screenshot (b)...")
        img_twin = Image.open(twin_yellow_temp)
        img_dash = Image.open(dash_temp)

        w, h = 960, 800
        img_twin_resized = img_twin.resize((w, h), Image.Resampling.LANCZOS)
        img_dash_resized = img_dash.resize((w, h), Image.Resampling.LANCZOS)

        combined = Image.new('RGB', (w * 2, h))
        combined.paste(img_twin_resized, (0, 0))
        combined.paste(img_dash_resized, (w, 0))

        screenshot_b = 'docs/screenshots/bridge_02_room_yellow_warning.png'
        combined.save(screenshot_b)
        print(f"Saved side-by-side proof: {screenshot_b}")

        browser.close()
        print("Verification completed successfully!")

if __name__ == '__main__':
    main()
