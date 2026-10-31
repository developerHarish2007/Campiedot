import sys
import time
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_human_path():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        # -----------------------------------------------------------------
        # STEP 1: Default URL with NO query parameters
        # -----------------------------------------------------------------
        print("=== STEP 1: Loading default URL http://localhost:5174/ ===")
        page.goto('http://localhost:5174/')
        page.wait_for_timeout(4000)

        # Check hint text
        hint = page.locator('text=Click a building, then Enter. Esc to go back.').first
        print(f"Hint visible: {hint.is_visible()}")
        page.screenshot(path='docs/screenshots/humanpath_01.png')
        print("Saved docs/screenshots/humanpath_01.png")

        # -----------------------------------------------------------------
        # STEP 2: Project PG Building centroid and click on canvas
        # -----------------------------------------------------------------
        print("\n=== STEP 2: Projecting PG Building & clicking canvas ===")
        
        # PG Building centroid is around x=63.44, y=8.0, z=56.01
        coords = page.evaluate("""() => {
            const camera = window.__CAMERA__;
            if (!camera) return null;
            camera.updateMatrixWorld();
            const vec = camera.position.clone();
            vec.set(63.44, 8.0, 56.01);
            vec.project(camera);
            return {
                x: (vec.x * 0.5 + 0.5) * window.innerWidth,
                y: (-vec.y * 0.5 + 0.5) * window.innerHeight,
                raw: { x: vec.x, y: vec.y, z: vec.z }
            };
        }""")
        print(f"Projected coordinates for PG Building: {coords}")

        if coords and 0 <= coords['x'] <= 1280 and 0 <= coords['y'] <= 800:
            click_x = coords['x']
            click_y = coords['y']
        else:
            # Fallback coordinates based on camera framing (PG is in the center-right foreground)
            click_x = 720
            click_y = 520

        print(f"Clicking canvas at ({click_x:.1f}, {click_y:.1f})")
        page.mouse.click(click_x, click_y)
        page.wait_for_timeout(2000)

        # Check if PG block enter button appeared
        enter_btn = page.locator('button:has-text("Enter PG Block")').first
        print(f"Canvas Enter Building button visible: {enter_btn.is_visible()}")
        if not enter_btn.is_visible():
            # If raycast was slight offset, let's try clicking the building card or landmark dock pill for PG
            print("Trying click at slightly adjusted position or clicking label...")
            label_coords = page.evaluate("""() => {
                const camera = window.__CAMERA__;
                if (!camera || typeof camera.project !== 'function') return null;
                const vec = camera.position.clone();
                vec.set(63.44, 18.0, 56.01);
                vec.project(camera);
                return {
                    x: (vec.x * 0.5 + 0.5) * window.innerWidth,
                    y: (-vec.y * 0.5 + 0.5) * window.innerHeight
                };
            }""")
            print(f"Label coords: {label_coords}")
            if label_coords:
                page.mouse.click(label_coords['x'], label_coords['y'])
                page.wait_for_timeout(2000)

        page.screenshot(path='docs/screenshots/humanpath_02.png')
        print("Saved docs/screenshots/humanpath_02.png")

        # -----------------------------------------------------------------
        # STEP 3: Click Enter (Canvas Overlay Button or Cutaway)
        # -----------------------------------------------------------------
        print("\n=== STEP 3: Clicking Enter Button ===")
        enter_btn = page.locator('button:has-text("Enter PG Block"), button:has-text("Enter"), button:has-text("Cutaway")').first
        if enter_btn.is_visible():
            enter_btn.click()
            page.wait_for_timeout(2500)
        else:
            # Maybe the label click in Step 2 already entered it directly per Requirement 3!
            print("Checking if already inside cutaway...")
        
        page.screenshot(path='docs/screenshots/humanpath_03.png')
        print("Saved docs/screenshots/humanpath_03.png")

        # -----------------------------------------------------------------
        # STEP 4: Click Room Pill (e.g. PG 201)
        # -----------------------------------------------------------------
        print("\n=== STEP 4: Clicking Room Pill ===")
        room_btn = page.locator('button:has-text("PG 201")').first
        if not room_btn.is_visible():
            room_btn = page.locator('button:has-text("PG 101")').first
            
        print(f"Room pill visible: {room_btn.is_visible()}")
        if room_btn.is_visible():
            room_btn.click()
            page.wait_for_timeout(3000)

        page.screenshot(path='docs/screenshots/humanpath_04.png')
        print("Saved docs/screenshots/humanpath_04.png")

        # -----------------------------------------------------------------
        # STEP 5: Press Esc twice to return to campus
        # -----------------------------------------------------------------
        print("\n=== STEP 5: Pressing Esc twice ===")
        page.keyboard.press('Escape')
        page.wait_for_timeout(1500)
        print("Pressed Escape 1 (returned to cutaway)")
        page.keyboard.press('Escape')
        page.wait_for_timeout(2000)
        print("Pressed Escape 2 (returned to campus)")

        page.screenshot(path='docs/screenshots/humanpath_05.png')
        print("Saved docs/screenshots/humanpath_05.png")

        browser.close()

    print("\n=== VERIFICATION FINISHED ===")

if __name__ == '__main__':
    test_human_path()
