from playwright.sync_api import sync_playwright
import time

def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        
        # 1. Open app
        page.goto('http://localhost:5174/')
        page.wait_for_timeout(3500)

        # 2. Open Cutaway (PG Block)
        page.click('button:has-text("Cutaway")')
        page.wait_for_timeout(2000)
        page.screenshot(path='docs/screenshots/step_interiors_pg_cutaway.png')
        print('Captured cutaway view!')

        # 3. Enter Smart Lab (PG 001)
        page.click('button:has-text("PG 001")')
        page.wait_for_timeout(2500)
        page.screenshot(path='docs/screenshots/classroom_smart_lab.png')
        print('Captured smart lab diorama!')

        # 4. Click Back to cutaway
        page.click('button:has-text("Cutaway (ESC)")')
        page.wait_for_timeout(1500)

        # 5. Enter Ordinary Classroom (PG 101)
        page.click('button:has-text("PG 101")')
        page.wait_for_timeout(2500)
        page.screenshot(path='docs/screenshots/classroom_ordinary.png')
        print('Captured ordinary classroom diorama!')

        browser.close()
    print('All views captured successfully!')

if __name__ == '__main__':
    capture_all()
