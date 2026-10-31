import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def capture_docks():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1360, 'height': 820})

        console_errors = []
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
        page.on('pageerror', lambda err: console_errors.append(str(err)))

        # -------------------------------------------------------------
        # Screenshot 1: Civil Block Cutaway with room dock scrolled to end
        # -------------------------------------------------------------
        print("Capturing 1: Civil cutaway with room dock scrolled to end...")
        page.goto('http://localhost:5174/?view=cutaway&block=CIVIL')
        page.wait_for_timeout(4000)

        # Scroll room dock to the right end
        page.evaluate("""() => {
            const track = document.querySelector('.dock-scroll-track');
            if (track) {
                track.scrollLeft = track.scrollWidth;
            }
        }""")
        page.wait_for_timeout(1000)

        # Verify CIVIL-306 pill is visible and click it
        pill_306 = page.locator('button[data-dock-id="CIVIL-306"]')
        if pill_306.is_visible():
            print("CIVIL-306 pill is visible!")
            pill_306.click()
            page.wait_for_timeout(1000)
        else:
            print("Warning: CIVIL-306 pill not directly visible, scrolling specifically into view...")
            page.evaluate("""() => {
                const el = document.querySelector('button[data-dock-id="CIVIL-306"]');
                if (el) el.scrollIntoView({ inline: 'end', block: 'nearest' });
            }""")
            page.wait_for_timeout(1000)

        page.screenshot(path='docs/screenshots/dock_01_civil_scrolled.png')
        print("Saved docs/screenshots/dock_01_civil_scrolled.png")

        # -------------------------------------------------------------
        # Screenshot 2: Campus Bottom Dock showing Canteen ? and Block N
        # -------------------------------------------------------------
        print("Capturing 2: Campus bottom dock with Canteen ? and Block N pills...")
        page.goto('http://localhost:5174/')
        page.wait_for_timeout(4500)

        # Scroll the campus dock to show Canteen, TNP, Auditorium, Library, Hostel, Block 1, Block 2...
        page.evaluate("""() => {
            const track = document.querySelector('.dock-scroll-track');
            if (track) {
                // Scroll about 380px to center the transition from facilities to Block N
                track.scrollLeft = 380;
            }
        }""")
        page.wait_for_timeout(1000)

        # Click on Canteen or Block 1 pill to verify selection
        canteen_btn = page.locator('button[data-dock-id="CANTEEN"]')
        if canteen_btn.is_visible():
            canteen_btn.click()
            page.wait_for_timeout(1000)

        page.screenshot(path='docs/screenshots/dock_02_campus_dock.png')
        print("Saved docs/screenshots/dock_02_campus_dock.png")

        browser.close()

        if console_errors:
            print("Console errors detected:", console_errors)
        else:
            print("No console errors detected!")

if __name__ == '__main__':
    capture_docks()

