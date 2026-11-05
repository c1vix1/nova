import json
import os
import threading
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

# Configuration constants
FEED_FILE = "task_manager_feed.json"
USER_DATA_DIR = "./.playwright_profile"  # Caches session to minimize daily logins

# Your student credentials
STUDENT_EMAIL = os.getenv("CLASSROOM_EMAIL")
STUDENT_PASSWORD = os.getenv("CLASSROOM_PASSWORD")

print(STUDENT_EMAIL)
print(STUDENT_PASSWORD)
# Thread lock to prevent race conditions when writing to the JSON file
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
  print("[Classroom Bot] Starting browser for School Google Classroom...")
  with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,  # Keep False for the first run to complete your SSO login securely
        args=["--disable-blink-features=AutomationControlled"],
    )

    page = context.new_page()

    try:
      # Navigate directly to the Google Classroom assignments page
      page.goto(
          "https://classroom.google.com/a/not-turned-in/all", timeout=60000
      )
      page.wait_for_load_state("domcontentloaded", timeout=15000)

      # Handle Google / RapidIdentity Login Walls if present
      if (
          "accounts.google.com" in page.url
          or "portal" in page.url
          or "sso" in page.url
      ):
        print(
            "[Classroom Bot] Login/SSO wall detected. Checking for email field..."
        )

        email_input = page.locator(
            'input[type="email"], input#identifierId, input#username,'
            ' input[name="username"]'
        )
        if email_input.count() > 0 and email_input.first.is_visible():
          email_input.first.fill(STUDENT_EMAIL)
          page.keyboard.press("Enter")
          page.wait_for_timeout(3000)

        # Check for password/RapidIdentity portal input field
        password_input = page.locator(
            'input[type="password"], input#password, input[name="password"]'
        )
        if password_input.count() > 0 and password_input.first.is_visible():
          print(
              "[Classroom Bot] Password/SSO field active. Entering"
              " credentials..."
          )
          password_input.first.fill(STUDENT_PASSWORD)

          submit_btn = page.locator(
              'button#submitButton, button[type="submit"],'
              ' input[type="submit"], button#login-button'
          )
          if submit_btn.count() > 0 and submit_btn.first.is_visible():
            submit_btn.first.click()
          else:
            page.keyboard.press("Enter")

          print("[Classroom Bot] Submitted credentials. Waiting for SSO...")

      # Wait until successfully redirected back into Google Classroom dashboard
      print(
          "[Classroom Bot] Waiting for redirect to Google Classroom dashboard..."
      )
      page.wait_for_url("**/classroom.google.com/**", timeout=60000)
      print("[Classroom Bot] Successfully authenticated!")

      # Give the dynamic content time to render tasks
      print("[Classroom Bot] Loading assignments feed...")
      page.wait_for_timeout(5000)

      assignments = []
      # Target common assignment card containers in Google Classroom
      items = page.locator(
          '.gHcFcc, [role="listitem"], .gXqA6c, div.toI8Rb'
      ).all()

      for item in items:
        try:
          title_elem = item.locator(".YVvSwe, .nDgy9d, .asQXV, span.onkcGd")
          due_elem = item.locator(".BPb8kf, .fxgd0d, .ZxGRMe, div.yi4h_")

          if title_elem.count() > 0:
            title = title_elem.first.inner_text().strip()
            due_date = (
                due_elem.first.inner_text().strip()
                if due_elem.count() > 0
                else "No due date"
            )
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
      print(f"[Classroom Bot] Error during scraping or login: {e}")
      try:
        page.screenshot(path="error_screenshot.png")
        print(
            "[Classroom Bot] Saved debug screenshot to 'error_screenshot.png'."
        )
      except Exception:
        pass
    finally:
     # Keep context open briefly or close safely
      context.close()


if __name__ == "__main__":
  scrape_classroom()