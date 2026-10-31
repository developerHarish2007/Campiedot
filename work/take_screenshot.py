import sys
import time
from playwright.sync_api import sync_playwright

def capture(url, out_path, wait_sec=4):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        page.goto(url)
        page.wait_for_timeout(int(wait_sec * 1000))
        page.screenshot(path=out_path)
        browser.close()
    print(f"Captured {out_path}")

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:5174/?view=ground'
    out = sys.argv[2] if len(sys.argv) > 2 else 'docs/screenshots/current.png'
    wait = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    capture(url, out, wait)

