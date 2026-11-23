import os
import sys
import time
import shutil
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proof_screenshots"))
ARTIFACT_DIR = r"C:\Users\Ankita\.gemini\antigravity\brain\3dce5edc-f8ef-40e4-8389-8171ef3eff54\screenshots"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_EXE,
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 850})

        print("Navigating to http://127.0.0.1:3000 ...")
        page.goto("http://127.0.0.1:3000", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Login
        print("Logging in...")
        page.fill('input[type="email"]', 'chauhanankitavirendra@gmail.com')
        page.fill('input[type="password"]', 'Suman@890')
        page.click('button:has-text("Sign In")')
        page.wait_for_timeout(3000)

        # Navigate to My Analyses
        print("Navigating to My Analyses...")
        page.click('button:has-text("My Analyses")')
        page.wait_for_timeout(3000)

        # Click Open on Pure & Cure
        print("Clicking Open button...")
        page.click('button:has-text("Open")')
        page.wait_for_timeout(3000)

        # Wait for Download Summary (PDF) button
        print("Waiting for Download Summary (PDF) button...")
        page.wait_for_selector('.far-btn-download-pdf', timeout=10000)
        print("SUCCESS! ResultsStep is displayed with Download Summary (PDF) button.")

        # 1. Desktop Viewport: 1280px
        page.set_viewport_size({"width": 1280, "height": 850})
        page.wait_for_timeout(1500)
        desktop_img = os.path.join(OUT_DIR, "results_dashboard_1280px.png")
        page.screenshot(path=desktop_img, full_page=False)
        shutil.copy(desktop_img, os.path.join(ARTIFACT_DIR, "results_dashboard_1280px.png"))
        print(f"Saved: {desktop_img}")

        header_actions = page.locator('.far-results-header-actions')
        if header_actions.is_visible():
            btn_desktop_img = os.path.join(OUT_DIR, "buttons_desktop_1280px.png")
            header_actions.screenshot(path=btn_desktop_img)
            shutil.copy(btn_desktop_img, os.path.join(ARTIFACT_DIR, "buttons_desktop_1280px.png"))
            print(f"Saved: {btn_desktop_img}")

        # 2. Mobile Viewport: 375px
        print("Switching to Mobile Viewport: 375px...")
        page.set_viewport_size({"width": 375, "height": 812})
        page.wait_for_timeout(1500)
        mobile_img = os.path.join(OUT_DIR, "results_dashboard_375px.png")
        page.screenshot(path=mobile_img, full_page=False)
        shutil.copy(mobile_img, os.path.join(ARTIFACT_DIR, "results_dashboard_375px.png"))
        print(f"Saved: {mobile_img}")

        if header_actions.is_visible():
            btn_mobile_img = os.path.join(OUT_DIR, "buttons_mobile_375px.png")
            header_actions.screenshot(path=btn_mobile_img)
            shutil.copy(btn_mobile_img, os.path.join(ARTIFACT_DIR, "buttons_mobile_375px.png"))
            print(f"Saved: {btn_mobile_img}")

        browser.close()
        print("ALL SCREENSHOTS CAPTURED PERFECTLY!")

if __name__ == "__main__":
    run()
