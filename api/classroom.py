# Currentlly, Classroom Bot is not capturing some assigments and needs fixing

import json
import os
import threading
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import keyring


load_dotenv()

# Configuration constants
FEED_FILE = "task_manager_feed.json"
USER_DATA_DIR = "./.playwright_profile"  # Caches session

# Your student credentials
STUDENT_EMAIL = os.getenv("CLASSROOM_EMAIL")
STUDENT_PASSWORD = keyring.get_password("classroom-api", "email")

# Validate environment variables before running
if not STUDENT_EMAIL or not STUDENT_PASSWORD:
  raise ValueError(
      "[Classroom Bot] CRITICAL ERROR: CLASSROOM_EMAIL or CLASSROOM_PASSWORD is"
      " not set in your .env file/keyring!"
  )

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
  p = sync_playwright().start()
  try:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,  # Keep False so you can monitor the login flow
        args=["--disable-blink-features=AutomationControlled"],
    )
  except Exception as e:
    print(
        "[Classroom Bot] Error launching browser. Make sure all other Chrome"
        f" instances using profile {USER_DATA_DIR} are closed: {e}"
    )
    p.stop()
    return

  page = context.new_page()

  try:
    # Navigate directly to the Google Classroom assignments page
    page.goto("https://classroom.google.com/a/not-turned-in/all", timeout=60000)
    print(
        "[Classroom Bot] Navigated to Classroom. Checking authentication"
        " status..."
    )

    # Intelligent loop to handle Google, RapidIdentity, and verification speedbump steps dynamically
    for _ in range(15):
      page.wait_for_timeout(3000)
      current_url = page.url
      print(f"[Classroom Bot] Current URL: {current_url}")

      # Confirm we have successfully reached Google Classroom and task rows are ready
      if "classroom.google.com" in current_url:
        try:
          if page.evaluate(
              "() => document.baseURI.includes('classroom.google.com')"
          ):
            print(
                "[Classroom Bot] Successfully inside Google Classroom"
                " dashboard!"
            )
            break
        except Exception:
          pass

      # 0. Handle Google "Verify it's you" Speedbump / Saml Confirmation Screen
      if "speedbump" in current_url or "samlconfirmaccount" in current_url:
        print("[Classroom Bot] Google account verification speedbump detected.")
        continue_btn = page.locator(
            'button:has-text("Continue"), button#submitButton,'
            ' button[type="submit"]'
        )
        if continue_btn.count() > 0 and continue_btn.first.is_visible():
          print("[Classroom Bot] Clicking Continue on verification page...")
          continue_btn.first.click()
          page.wait_for_timeout(4000)
        continue

      # 1. Handle Google Email / Identifier Screen
      email_input = page.locator('input[type="email"], input#identifierId')
      if email_input.count() > 0 and email_input.first.is_visible():
        print(f"[Classroom Bot] Entering Google email: {STUDENT_EMAIL}")
        email_input.first.fill(STUDENT_EMAIL)

        next_btn = page.locator('button#identifierNext, button:has-text("Next")')
        if next_btn.count() > 0 and next_btn.first.is_visible():
          next_btn.first.click()
        else:
          page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
        continue

      # 2. Handle RapidIdentity Username/Identification Screen
      username_input = page.locator('input#identification')
      if username_input.count() > 0 and username_input.first.is_visible():
        print(f"[Classroom Bot] Entering RapidIdentity ID: {STUDENT_EMAIL}")
        username_input.first.fill(STUDENT_EMAIL)

        continue_btn = page.locator(
            'button#authn-go-button, button:has-text("Continue")'
        )
        if continue_btn.count() > 0 and continue_btn.first.is_visible():
          continue_btn.first.click()
        else:
          page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
        continue

      # 3. Handle Password Screen (Google or RapidIdentity)
      password_input = page.locator(
          'input[type="password"], input#password, input[name="password"]'
      )
      if password_input.count() > 0 and password_input.first.is_visible():
        print("[Classroom Bot] Entering password...")
        password_input.first.fill(STUDENT_PASSWORD)

        submit_btn = page.locator(
            'button#passwordNext, button#authn-go-button,'
            ' button:has-text("Sign In"), button#submitButton,'
            ' button[type="submit"], input[type="submit"]'
        )
        if submit_btn.count() > 0 and submit_btn.first.is_visible():
          submit_btn.first.click()
        else:
          page.keyboard.press("Enter")

        print("[Classroom Bot] Credentials submitted. Waiting for redirect...")
        page.wait_for_timeout(6000)
        continue

    # Wait briefly for dynamic items to fully settle
    print("[Classroom Bot] Loading assignments feed...")
    page.wait_for_timeout(3000)

    # Expand all accordion sections and extract tasks cleanly
    assignments = page.evaluate("""() => {
      // Automatically click and expand all collapsed section accordions so all tasks load into DOM
      const expandButtons = document.querySelectorAll('div[aria-expanded="false"], [role="button"]');
      expandButtons.forEach(btn => {
          const text = btn.innerText ? btn.innerText.toLowerCase() : '';
          if (text.includes('due date') || text.includes('this week') || text.includes('later') || text.includes('next week')) {
              try { btn.click(); } catch(e) {}
          }
      });

      let results = [];
      const taskRows = document.querySelectorAll('li[data-role="task-row"]');
      
      taskRows.forEach(row => {
          let assignmentType = 'assignment';
          const iconDiv = row.querySelector('[role="img"], div[aria-label]');
          if (iconDiv) {
              const label = iconDiv.getAttribute('aria-label');
              if (label) assignmentType = label.toLowerCase();
          }

          const text = row.innerText ? row.innerText.trim() : '';
          if (text) {
              let lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
              
              const ignoreWords = ['assignment', 'quiz', 'question', 'material'];
              if (lines.length > 0 && ignoreWords.includes(lines[0].toLowerCase())) {
                  assignmentType = lines[0].toLowerCase();
                  lines.shift();
              }

              let dueDate = 'No due date';
              let titleLines = [];

              lines.forEach(line => {
                  const lower = line.toLowerCase();
                  const isDateMarker = lower.includes('am') || lower.includes('pm') || 
                                      lower.includes('jan') || lower.includes('feb') || 
                                      lower.includes('mar') || lower.includes('apr') || 
                                      lower.includes('may') || lower.includes('jun') || 
                                      lower.includes('jul') || lower.includes('aug') || 
                                      lower.includes('sep') || lower.includes('oct') || 
                                      lower.includes('nov') || lower.includes('dec') ||
                                      lower.includes('today') || lower.includes('tomorrow');

                  if (isDateMarker && !line.includes(' - Per ') && dueDate === 'No due date') {
                      dueDate = line;
                  } else {
                      titleLines.push(line);
                  }
              });

              let title = titleLines.join(' ').trim();
              // Thoroughly strip any leading assignment/quiz prefix glued to the title
              title = title.replace(/^(assignment|quiz|question|material)\\s*/i, '');

              if (title) {
                  results.push({
                      type: assignmentType,
                      title: title,
                      due: dueDate
                  });
              }
          }
      });

      // Deduplicate items by title
      const unique = [];
      const seen = new Set();
      for (const r of results) {
          if (!seen.has(r.title)) {
              seen.add(r.title);
              unique.push(r);
          }
      }
      return unique;
    }""")

    if not assignments:
      assignments = [{
          "type": "none",
          "title": "No pending assignments found",
          "due": "None",
      }]

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
      print("[Classroom Bot] Saved debug screenshot to 'error_screenshot.png'.")
    except Exception:
      pass
  finally:
    try:
      context.close()
      p.stop()
    except Exception:
      pass


if __name__ == "__main__":
  scrape_classroom()