import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def run():
    os.makedirs('docs/screenshots', exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        print("[TEST] Loading 3D Twin on http://localhost:5174/ ...")
        await page.goto('http://localhost:5174/', wait_until='domcontentloaded')
        await page.wait_for_timeout(4000)

        # 1. Check NO Operations button
        ops_buttons = await page.locator("button:has-text('Operations')").all()
        print(f"[TEST] Operations buttons count: {len(ops_buttons)}")
        assert len(ops_buttons) == 0, f"Expected 0 Operations buttons, found {len(ops_buttons)}"

        # 2. Check Dashboard button visible
        dash_btn = page.locator("button:has-text('Dashboard')")
        assert await dash_btn.is_visible(), "Dashboard button should be visible"
        print("[TEST] Dashboard button is visible and Operations button is gone.")

        # Save Screenshot (b): Campus view showing NO Operations button and Dashboard button visible
        await page.screenshot(path='docs/screenshots/nav_01_no_ops_dashboard.png')
        print("[TEST] Saved docs/screenshots/nav_01_no_ops_dashboard.png")

        # 3. Position camera to clearly show the new broadleaf trees (at least 3 visible with canopy and trunk)
        await page.evaluate("""
            () => {
                const cam = window.__CAMERA__;
                if (cam) {
                    cam.position.set(55, 18, -110);
                    cam.lookAt(15, 6, -160);
                    cam.updateProjectionMatrix();
                }
            }
        """)
        await page.wait_for_timeout(2000)

        # Save Screenshot (a): Campus view showing the new broadleaf trees (at least 3 visible with canopy and trunk)
        await page.screenshot(path='docs/screenshots/tree_01_campus_broadleaf.png')
        print("[TEST] Saved docs/screenshots/tree_01_campus_broadleaf.png")

        # 4. Click Dashboard button 3 times from different views and verify only 1 tab exists
        print("[TEST] Testing Dashboard button tab reuse...")
        # First click from campus view
        await page.click("button:has-text('Dashboard')")
        await page.wait_for_timeout(2000)

        # Go to Cutaway view
        await page.goto('http://localhost:5174/?view=cutaway&block=PG', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.click("button:has-text('Dashboard')")
        await page.wait_for_timeout(2000)

        # Go to Room view
        await page.goto('http://localhost:5174/?view=room&room=PG-201&lab=1', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.click("button:has-text('Dashboard')")
        await page.wait_for_timeout(2000)

        # Check pages in context
        dash_pages = [p for p in context.pages if "5173" in p.url]
        print(f"[TEST] Total pages: {len(context.pages)}, Dashboard pages (port 5173): {len(dash_pages)}")
        assert len(dash_pages) == 1, f"Expected exactly 1 Dashboard tab, found {len(dash_pages)}"

        # 5. On the dashboard page, take Screenshot (c): Dashboard showing '← Back to 3D Twin' in its header
        dash_page = dash_pages[0]
        await dash_page.wait_for_timeout(2000)
        # Select Student & Faculty portal if on role picker
        student_card = dash_page.locator("text='Student & Faculty'")
        if await student_card.is_visible():
            await student_card.click()
            await dash_page.wait_for_timeout(1000)

        back_twin_btn = dash_page.locator("button:has-text('Back to 3D Twin')")
        assert await back_twin_btn.is_visible(), "'Back to 3D Twin' button must be visible in Dashboard header"
        print("[TEST] Back to 3D Twin button is visible in Dashboard header.")

        await dash_page.screenshot(path='docs/screenshots/dash_01_back_to_twin.png')
        print("[TEST] Saved docs/screenshots/dash_01_back_to_twin.png")

        await browser.close()
        print("[TEST] ALL CHECKS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    asyncio.run(run())
