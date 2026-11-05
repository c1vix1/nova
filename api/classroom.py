import json
import os
import threading
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

# Configuration constants
FEED_FILE = "task_manager_feed.json"
USER_DATA_DIR = "./.playwright_profile"  # Caches session to minimize daily logins

# Your student credentials
STUDENT_EMAIL = os.getenv("CLASSROOM_EMAIL")
STUDENT_USERNAME = os.getenv("CLASSROOM_EMAIL")
STUDENT_PASSWORD = os.getenv("CLASSROOM_PASSWORD")  

# Thread lock to prevent race conditions when writing to the JSON file
file_lock = threading.Lock()


def safe_write_feed(data_dict):
  """Safely writes the scraped assignments to the local JSON feed using a lock."""
  with file_lock:
    try:
      with open(FEED_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=4)
      print(f"[Classroom Bot] Successfully updated {FEED_FILE}")
    except Exception as e:
      print(f"[Classroom Bot] Error writing to JSON feed: {e}")


def scrape_classroom():
  print("[Classroom Bot] Starting browser for Google Classroom...")
  with sync_playwright() as p:
    # Persistent context preserves your login session across runs
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,  # Set to True once you confirm login works smoothly
        slow_mo=1000000,
        args=["--disable-blink-features=AutomationControlled"],
    )

    page = context.new_page()

    try:
      # Navigate directly to Google Classroom To-Do page
      page.goto("https://classroom.google.com/u/0/todo", timeout=60000)

      # Check if we hit a sign-in, SSO, or RapidID portal wall
      if any(
          keyword in page.url
          for keyword in [
              "signin",
              "sso",
              "identifier",
              "login",
              "rapididentity",
              "auth",
          ]
      ):
        print(
            "[Classroom Bot] Sign-in / RapidIdentity portal detected."
            " Authenticating..."
        )

        # 1. Enter student email on Google's login page if present
        try:
          page.wait_for_selector('input[type="email"]', timeout=5000)
          page.fill('input[type="email"]', STUDENT_EMAIL)
          page.keyboard.press("Enter")
          page.wait_for_timeout(3000)
        except Exception:
          pass  # Might already be on the school SSO page

        # 2. Handle RapidIdentity portal fields if redirected
        if any(
            keyword in page.url
            for keyword in ["rapididentity", "sso", "portal", "auth"]
        ):
          print("[Classroom Bot] Filling RapidIdentity SSO credentials...")
          page.fill(
              'input#username, input[name="username"], input[type="text"]',
              STUDENT_USERNAME,
          )
          page.fill(
              'input#password, input[name="password"], input[type="password"]',
              STUDENT_PASSWORD,
          )
          page.click(
              'button#submitButton, button[type="submit"], input[type="submit"]'
          )

        # 3. Wait until successfully redirected back to Google Classroom
        page.wait_for_url("**/classroom.google.com/**", timeout=45000)
        print("[Classroom Bot] Authentication successful!")

      # Wait for assignment items to load in the DOM
      page.wait_for_selector('.gHcFcc, [role="listitem"]', timeout=15000)

      assignments = []
      items = page.locator('.gHcFcc, [role="listitem"]').all()

      for item in items:
        try:
          title = item.locator(".YVvSwe, .nDgy9d").inner_text()
          due_date = item.locator(".BPb8kf, .fxgd0d").inner_text()
          assignments.append({"title": title, "due": due_date})
        except Exception:
          continue

      # Fallback structure if no items are found
      if not assignments:
        assignments = [
            {"title": "Check Google Classroom directly", "due": "Today"}
        ]

      data = {
          "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
          "assignments": assignments,
      }

      # Safely output to local JSON feed
      safe_write_feed(data)
      print(f"[Classroom Bot] Successfully scraped {len(assignments)} tasks.")

    except Exception as e:
      print(f"[Classroom Bot] Error during scraping or login: {e}")
    finally:
      context.close()


if __name__ == "__main__":
  scrape_classroom()