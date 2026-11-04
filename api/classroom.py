import json
import os
import threading
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables from the .env file
load_dotenv(dotenv_path="../.env")

FEED_FILE = "classmgr_api_feed.json"
USER_DATA_DIR = "playwright_profile"

# Fetch credentials securely from environment variables
STUDENT_EMAIL = os.getenv("CLASSROOM_EMAIL")
STUDENT_PASSWORD = os.getenv("CLASSROOM_PASSWORD")


file_lock = threading.Lock()


def safe_write_feed(data_dict):
  with file_lock:
    try:
      with open(FEED_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=4)
      print(f"[Classroom Bot] Successfully updated {FEED_FILE}")
    except Exception as e:
      print(f"[Classroom Bot] Error writing to JSON feed: {e}")


def scrape_classroom():
  print("[Classroom Bot] Starting browser for Austin ISD Classroom...")
  with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,  # Keep False for your first test to watch it step through both screens!
        slow_mo=10000,  # Slow down actions for better visibility during debugging
        args=["--disable-blink-features=AutomationControlled"],
    )

    page = context.new_page()

    try:
      # Navigate directly to your assignments page
      page.goto(
          "https://classroom.google.com/a/not-turned-in/all", timeout=60000
      )

      # Check if we hit a sign-in wall
      if any(
          keyword in page.url
          for keyword in ["signin", "sso", "rapididentity", "portal", "auth"]
      ):
        print("[Classroom Bot] Sign-in wall detected. Starting multi-step login...")

        # STEP 1: Handle the initial Google / Email prompt
        try:
          page.wait_for_selector(
              'input[type="email"], input#identifierId', timeout=5000
          )
          page.fill('input[type="email"], input#identifierId', STUDENT_EMAIL)
          page.keyboard.press("Enter")
          print("[Classroom Bot] Submitted email to Google.")
        except Exception:
          print(
              "[Classroom Bot] Skipped or already past the initial email"
              " prompt."
          )

        # Wait for transition to the RapidIdentity portal
        page.wait_for_timeout(3000)

        # STEP 2: Handle the RapidIdentity portal prompt
        if "rapididentity" in page.url or "sso" in page.url or page.locator('input[type="password"]').count() > 0:
          print("[Classroom Bot] RapidIdentity portal active. Entering password...")
          
          # If RapidIdentity asks for username/email again:
          try:
            user_input = page.locator('input#username, input[name="username"]')
            if user_input.is_visible():
              user_input.fill(STUDENT_EMAIL)
          except Exception:
            pass

          # Fill password
          page.fill('input[type="password"]', STUDENT_PASSWORD)
          
          # Click submit button on the portal
          page.click('button#submitButton, button[type="submit"], input[type="submit"]')
          print("[Classroom Bot] Submitted credentials to RapidIdentity.")

        # 3. Wait until successfully redirected back into Google Classroom
        page.wait_for_url("**/classroom.google.com/**", timeout=30000)
        print("[Classroom Bot] Successfully authenticated through SSO!")

      # Wait for assignment list items to load
      page.wait_for_selector(
          '.gHcFcc, [role="listitem"], .gXqA6c', timeout=15000
      )

      assignments = []
      items = page.locator('.gHcFcc, [role="listitem"], .gXqA6c').all()

      for item in items:
        try:
          title = item.locator(".YVvSwe, .nDgy9d, .asQXV").inner_text()
          due_date = item.locator(".BPb8kf, .fxgd0d, .ZxGRMe").inner_text()
          assignments.append({"title": title, "due": due_date})
        except Exception:
          continue

      if not assignments:
        assignments = [{"title": "No pending assignments found", "due": "None"}]

      data = {
          "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
          "assignments": assignments,
      }

      safe_write_feed(data)
      print(f"[Classroom Bot] Successfully scraped {len(assignments)} tasks.")

    except Exception as e:
      print(f"[Classroom Bot] Error during scraping or multi-step login: {e}")
    finally:
      context.close()


if __name__ == "__main__":
  scrape_classroom()