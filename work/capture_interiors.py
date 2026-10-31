from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        
        # 1. Exterior view (drawer closed by default)
        page.goto('http://localhost:5174/')
        page.wait_for_timeout(3500)
        page.screenshot(path='docs/screenshots/step_interiors_exterior.png')
        print('1. Captured exterior')

        # 2. Toggle Operations Drawer open
        page.click('text=📋 Operations ◨')
        page.wait_for_timeout(1000)
        page.screenshot(path='docs/screenshots/step_interiors_drawer_open.png')
        print('2. Captured drawer open')

        # 3. Enter Cutaway View
        page.click('button:has-text("Cutaway")')
        page.wait_for_timeout(2500)
        page.screenshot(path='docs/screenshots/step_interiors_pg_cutaway.png')
        print('3. Captured cutaway')

        # 4. Click a room in cutaway to enter diorama (PG 001 smart lab)
        page.mouse.click(520, 520)
        page.wait_for_timeout(2500)
        page.screenshot(path='docs/screenshots/step_interiors_room_diorama.png')
        print('4. Captured diorama')

        browser.close()
    print('All screenshots captured!')

if __name__ == '__main__':
    main()

