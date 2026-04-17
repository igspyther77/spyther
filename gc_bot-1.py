"""
gc_bot.py  —  Two-account GC reply bot
Run:  python3 gc_bot.py
Save sessions first:  python3 gc_bot.py --save-sessions
"""

import argparse
import threading
import time
import json
import os
from playwright.sync_api import sync_playwright

# ─── CONFIG ────────────────────────────────────────────────────────────────────

SESSION_FILES = [
    "session_1.json",   # Account 1
    "session_2.json",   # Account 2
]

OWNERS = [
    "ig.spyther",
    # "another_owner",
]

REPLY_MSGS = [
    "AA CHUD LE 🤡",
    "bhai kya kar raha hai 💀",
    "tu aaya re 😂",
    # Add more — cycled in order
]

# ─── SHARED STATE ──────────────────────────────────────────────────────────────

_state_lock  = threading.Lock()
TARGET       = None
_msg_idx     = 0

# Turn system: turn_events[0] starts SET so ACC1 goes first
# After ACC1 sends: clears own event, sets turn_events[1]
# After ACC2 sends: clears own event, sets turn_events[0]
turn_events  = [threading.Event(), threading.Event()]
turn_events[0].set()   # ACC1 goes first

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def next_reply() -> str:
    global _msg_idx
    with _state_lock:
        msg = REPLY_MSGS[_msg_idx % len(REPLY_MSGS)]
        _msg_idx += 1
        return msg

def get_target():
    with _state_lock:
        return TARGET

def set_target(val: str):
    global TARGET
    with _state_lock:
        TARGET = val

# ─── BOT LOOP ──────────────────────────────────────────────────────────────────

def bot_loop(tid: int, session_file: str, ready: threading.Event):

    with sync_playwright() as p:
        print(f"[ACC{tid+1}] Launching browser")

        browser = p.chromium.launch(headless=False)

        if os.path.exists(session_file):
            with open(session_file) as f:
                storage = json.load(f)
            ctx = browser.new_context(storage_state=storage)
            print(f"[ACC{tid+1}] Session loaded from {session_file}")
        else:
            ctx = browser.new_context()
            print(f"[ACC{tid+1}] No session file — login manually")

        page = ctx.new_page()
        page.goto("https://www.instagram.com/")

        ready.wait()

        print(f"[ACC{tid+1}] Navigating to inbox...")
        page.goto("https://www.instagram.com/direct/inbox/")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # Snapshot current DOM count — ignore all existing messages on start
        MSG_SEL    = 'div[dir="auto"]'
        last_count = page.locator(MSG_SEL).count()
        print(f"[ACC{tid+1}] Ready — {last_count} existing msgs skipped")

        while True:
            try:
                loc   = page.locator(MSG_SEL)
                count = loc.count()

                # Only process when DOM has genuinely new elements
                if count <= last_count:
                    time.sleep(0.25)
                    continue

                # Process each new element by index (last_count..count-1)
                for i in range(last_count, count):
                    try:
                        text = loc.nth(i).inner_text().strip()
                    except Exception:
                        continue

                    if not text:
                        continue

                    print(f"[ACC{tid+1}] +msg[{i}]: {text!r}")

                    # /slide — only ACC1 handles to avoid double reply
                    if text.startswith("/slide") and tid == 0:
                        parts = text.split()
                        if len(parts) == 2:
                            uname = parts[1]
                            try:
                                loc.nth(i).wait_for(state="visible", timeout=5000)
                                loc.nth(i).hover()
                            except Exception:
                                pass

                            is_owner = any(
                                page.locator(
                                    f'svg[aria-label*="Reply to message from {o}"]'
                                ).count() > 0
                                for o in OWNERS
                            )

                            box = page.locator('[contenteditable="true"][role="textbox"]')
                            if is_owner:
                                set_target(uname)
                                box.click()
                                box.fill(f"✅ Target set to @{uname}")
                                page.keyboard.press("Enter")
                                print(f"[ACC{tid+1}] Target set → {uname}")
                            else:
                                box.click()
                                box.fill("you are not an owner ❌")
                                page.keyboard.press("Enter")

                    # Auto-reply to TARGET
                    else:
                        cur_target = get_target()
                        if not cur_target:
                            continue

                        try:
                            loc.nth(i).wait_for(state="visible", timeout=5000)
                            loc.nth(i).hover()
                        except Exception:
                            pass

                        reply_btn = page.locator(
                            f'svg[aria-label*="Reply to message from {cur_target}"]'
                        )

                        if reply_btn.count() == 0:
                            continue  # Not from target — skip

                        # Wait for this account's turn (strict alternation)
                        got_turn = turn_events[tid].wait(timeout=8.0)
                        if not got_turn:
                            print(f"[ACC{tid+1}] ⚠️ Turn timeout, skipping")
                            continue

                        try:
                            reply_btn.first.locator("..").click()
                            box = page.locator('[contenteditable="true"][role="textbox"]')
                            box.click()
                            box.fill(next_reply())
                            page.keyboard.press("Enter")
                            print(f"[ACC{tid+1}] ✅ Reply sent")
                        except Exception as send_e:
                            print(f"[ACC{tid+1}] Send error: {send_e}")
                        finally:
                            # Hand turn to the other account
                            turn_events[tid].clear()
                            turn_events[1 - tid].set()

                last_count = count

            except Exception as e:
                print(f"[ACC{tid+1}] ERROR: {e}")
                time.sleep(1)

# ─── SESSION SAVER ─────────────────────────────────────────────────────────────

def save_sessions():
    """
    Open both browsers simultaneously, login manually to each,
    press Enter — session JSONs saved for future bot runs.
    """
    print("\n[SESSION SAVER] Both browsers will open.")
    print("[SESSION SAVER] Login to each account, then press Enter.\n")

    with sync_playwright() as p:
        browsers  = []
        contexts  = []

        for i, sf in enumerate(SESSION_FILES):
            browser = p.chromium.launch(headless=False)
            ctx     = browser.new_context()
            page    = ctx.new_page()
            page.goto("https://www.instagram.com/accounts/login/")
            print(f"[ACC{i+1}] Browser open — login to account {i+1}")
            browsers.append(browser)
            contexts.append(ctx)

        input("\nLogin to BOTH accounts, then press Enter to save...\n")

        for i, (ctx, sf) in enumerate(zip(contexts, SESSION_FILES)):
            state = ctx.storage_state()
            with open(sf, "w") as f:
                json.dump(state, f, indent=2)
            print(f"[ACC{i+1}] ✅ Saved → {sf}")

        for b in browsers:
            try:
                b.close()
            except Exception:
                pass

    print("\n[SESSION SAVER] Done. Run: python3 gc_bot.py\n")

# ─── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GC reply bot")
    parser.add_argument(
        "--save-sessions",
        action="store_true",
        help="Save login sessions to JSON files for future use"
    )
    args = parser.parse_args()

    if args.save_sessions:
        save_sessions()
    else:
        ready   = threading.Event()
        threads = []

        for i, sf in enumerate(SESSION_FILES):
            t = threading.Thread(
                target=bot_loop,
                args=(i, sf, ready),
                daemon=True
            )
            threads.append(t)
            t.start()

        input("\n[MAIN] Login to BOTH accounts if needed, then press Enter to start...\n")
        ready.set()

        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            print("\n[MAIN] Stopped.")
