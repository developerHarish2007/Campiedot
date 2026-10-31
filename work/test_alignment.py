from playwright.sync_api import sync_playwright

def test_alignment():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist']
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        page.goto('http://localhost:5174/')
        page.wait_for_timeout(3000)
        
        # Click Alignment button
        page.click('text=Alignment')
        page.wait_for_timeout(2000)
        page.screenshot(path='docs/screenshots/verify_alignment_tool.png')
        browser.close()
    print("Captured docs/screenshots/verify_alignment_tool.png")

if __name__ == '__main__':
    test_alignment()

