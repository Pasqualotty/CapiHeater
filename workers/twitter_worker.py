"""
TwitterWorker - Executes scheduled Twitter/X actions for a single account.
"""

import json
import time
import random
import traceback
from queue import Queue

from workers.base_worker import BaseWorker
from workers.actions.browse_feed import BrowseFeedAction
from core.scheduler import Scheduler
from utils.logger import get_logger

logger = get_logger(__name__)


class TwitterWorker(BaseWorker):
    """Worker thread that drives a browser for one Twitter/X account.

    Parameters
    ----------
    account : dict
        Account row from the database (must contain ``id``, ``username``,
        ``cookies_json``, ``proxy``, ``schedule_id``, ``start_date``).
    schedule_json : str | list
        The warming schedule for this account.
    targets : list[dict]
        List of target rows (each has ``username``, ``url``).
    message_queue : Queue
        Thread-safe queue for sending status updates to the GUI / engine.
    driver_factory : object, optional
        An object with a ``create_driver(proxy)`` method.  When *None*,
        ``utils.driver_factory.DriverFactory`` is imported lazily.
    """

    # Delay ranges (seconds) between individual actions — more human-like
    ACTION_DELAY_MIN = 8
    ACTION_DELAY_MAX = 25

    def __init__(
        self,
        account: dict,
        schedule_json,
        targets: list[dict],
        message_queue: Queue,
        driver_factory=None,
        db=None,
    ):
        super().__init__(name=f"Worker-{account['username']}")
        self.account = account
        self.schedule_json = schedule_json
        self.targets = list(targets)  # local copy
        self.queue = message_queue
        self.driver_factory = driver_factory
        self.driver = None
        self.db = db
        # Set by engine when a new worker replaces this one — prevents
        # the finally safety-net from overwriting the new worker's status.
        self._superseded = False

    # ------------------------------------------------------------------
    # Queue messaging helpers
    # ------------------------------------------------------------------

    def _send(self, event: str, **payload):
        """Put a message dict onto the shared queue."""
        msg = {
            "event": event,
            "account_id": self.account["id"],
            "username": self.account["username"],
            **payload,
        }
        self.queue.put(msg)

    def _log_activity(self, action_type: str, status: str,
                      target_username: str = None, target_url: str = None,
                      error_message: str = None):
        """Write an entry to the activity_logs table."""
        if self.db is None:
            return
        try:
            self.db.execute(
                """INSERT INTO activity_logs
                   (account_id, action_type, target_username, target_url, status, error_message)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self.account["id"], action_type, target_username, target_url,
                 status, error_message),
            )
        except Exception:
            pass

    def _record_action(self, target_username: str, action_type: str, day_number: int):
        """Record an action in action_history to prevent repeats on the same day."""
        if self.db is None:
            return
        try:
            self.db.execute(
                """INSERT INTO action_history
                   (account_id, target_username, action_type, schedule_day)
                   VALUES (?, ?, ?, ?)""",
                (self.account["id"], target_username, action_type, day_number),
            )
        except Exception:
            pass

    def _get_acted_targets(self, action_type: str, day_number: int) -> set:
        """Return set of target usernames already acted upon for this day."""
        if self.db is None:
            return set()
        try:
            rows = self.db.fetch_all(
                """SELECT target_username FROM action_history
                   WHERE account_id = ? AND action_type = ? AND schedule_day = ?""",
                (self.account["id"], action_type, day_number),
            )
            return {r["target_username"] for r in rows}
        except Exception:
            return set()

    def _get_all_followed_targets(self) -> set:
        """Return ALL targets ever followed by this account (any day)."""
        if self.db is None:
            return set()
        try:
            rows = self.db.fetch_all(
                """SELECT DISTINCT target_username FROM action_history
                   WHERE account_id = ? AND action_type = 'follow'""",
                (self.account["id"],),
            )
            return {r["target_username"] for r in rows}
        except Exception:
            return set()

    # ------------------------------------------------------------------
    # Browser helpers
    # ------------------------------------------------------------------

    def _create_browser(self):
        """Instantiate the browser via DriverFactory and load cookies."""
        factory = self.driver_factory
        if factory is None:
            from browser.driver_factory import DriverFactory
            factory = DriverFactory

        proxy = self.account.get("proxy")
        self.driver = factory.create_driver(proxy=proxy)

        # Navigate to Twitter so cookies can be set on the correct domain
        self.driver.get("https://x.com")
        time.sleep(3)

        # Load cookies
        cookies = self.account.get("cookies_json", "[]")
        if isinstance(cookies, str):
            cookies = json.loads(cookies)

        for cookie in cookies:
            try:
                # Ensure cookie has required fields
                if "name" not in cookie or "value" not in cookie:
                    continue
                # Fix domain if needed
                c = dict(cookie)
                if "sameSite" in c and c["sameSite"] not in ("Strict", "Lax", "None"):
                    c.pop("sameSite")
                if "expiry" in c and isinstance(c["expiry"], float):
                    c["expiry"] = int(c["expiry"])
                self.driver.add_cookie(c)
            except Exception as exc:
                logger.debug(f"Cookie skip: {cookie.get('name', '?')}: {exc}")

        # Refresh so cookies take effect
        self.driver.get("https://x.com/home")
        time.sleep(4)

        # Verify login
        if not self._is_logged_in():
            self._log_activity("login", "failed", error_message="Cookies invalidos ou expirados")
            raise RuntimeError(
                f"Falha ao logar com cookies da conta @{self.account['username']}. "
                "Verifique se os cookies estao validos."
            )
        self._log_activity("login", "success")
        logger.info(f"[{self.account['username']}] Login via cookies OK")

    def _is_logged_in(self) -> bool:
        """Check if the browser is logged into Twitter/X."""
        try:
            # If we can find the compose tweet button or the home timeline,
            # we're logged in. If we see login/signup prompts, we're not.
            page_source = self.driver.page_source
            # Check for signs of being logged out
            logged_out_signs = [
                "Inscreva-se", "Sign up", "Create account",
                "Criar conta", "Acabou de chegar",
            ]
            for sign in logged_out_signs:
                if sign in page_source:
                    return False
            # Check for signs of being logged in
            logged_in_signs = [
                'data-testid="SideNav_NewTweet_Button"',
                'data-testid="AppTabBar_Home_Link"',
                'data-testid="primaryColumn"',
                'aria-label="Home timeline"',
                'aria-label="Timeline: Your Home Timeline"',
            ]
            for sign in logged_in_signs:
                if sign in page_source:
                    return True
            return False
        except Exception:
            return False

    def _handle_profile_page(self) -> str:
        """Check the current profile page for issues and handle them.

        Returns
        -------
        str
            'ok' — profile loaded normally, ready to interact.
            'sensitive' — sensitive content warning was dismissed.
            'not_found' — page doesn't exist (404).
            'suspended' — account is suspended.
            'error' — unknown issue.
        """
        try:
            time.sleep(random.uniform(1.0, 2.0))
            page = self.driver.page_source

            # --- Page not found ---
            not_found_signs = [
                "esta página não existe",
                "this page doesn",
                "Hmm...this page",
                "Ih, esta página",
                "page doesn't exist",
            ]
            for sign in not_found_signs:
                if sign.lower() in page.lower():
                    logger.warning(f"[{self.account['username']}] Perfil nao encontrado (404)")
                    return "not_found"

            # --- Suspended account ---
            suspended_signs = [
                "Conta suspensa",
                "Account suspended",
                "suspende as contas",
                "suspend accounts",
            ]
            for sign in suspended_signs:
                if sign in page:
                    logger.warning(f"[{self.account['username']}] Conta suspensa detectada")
                    return "suspended"

            # --- Sensitive content warning ---
            sensitive_signs = [
                "conteúdo pontecialmente sensível",
                "conteúdo potencialmente sensível",
                "potentially sensitive",
                "Sim, ver perfil",
                "Yes, view profile",
                "Ainda quer vê-lo",
            ]
            for sign in sensitive_signs:
                if sign in page:
                    logger.info(f"[{self.account['username']}] Aviso de conteudo sensivel, clicando 'Sim'")
                    # Click "Sim, ver perfil" / "Yes, view profile"
                    clicked = self.driver.execute_script("""
                        var btns = document.querySelectorAll('button, [role="button"]');
                        for (var i = 0; i < btns.length; i++) {
                            var text = btns[i].innerText.trim().toLowerCase();
                            if (text.includes('sim, ver') || text.includes('yes, view')
                                || text.includes('ver perfil') || text.includes('view profile')) {
                                btns[i].click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    if clicked:
                        time.sleep(random.uniform(2, 4))
                        return "sensitive"
                    return "error"

            return "ok"
        except Exception as exc:
            logger.debug(f"_handle_profile_page error: {exc}")
            return "ok"

    def force_stop(self) -> None:
        """Force-stop by killing the chromedriver process directly.

        Use when the worker is stuck in a Selenium call and ``stop()``
        alone cannot unblock it (driver.quit() would also hang).
        """
        self._stop_event.set()
        self._pause_event.set()
        if self.driver:
            try:
                service = getattr(self.driver, "service", None)
                proc = getattr(service, "process", None) if service else None
                if proc and proc.pid:
                    import os
                    import signal
                    os.kill(proc.pid, signal.SIGTERM)
                    logger.info(
                        f"[{self.account.get('username', '?')}] "
                        f"Force-killed chromedriver PID {proc.pid}"
                    )
            except Exception as exc:
                logger.warning(f"force_stop driver kill failed: {exc}")
            finally:
                self.driver = None

    def _close_browser(self):
        """Safely close and quit the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

    # ------------------------------------------------------------------
    # Action executors
    # ------------------------------------------------------------------

    def _random_delay(self):
        """Sleep a random duration between actions."""
        delay = random.uniform(self.ACTION_DELAY_MIN, self.ACTION_DELAY_MAX)
        # Sleep in small increments so we can respond to stop quickly
        end = time.time() + delay
        while time.time() < end:
            if self.is_stopped():
                return
            time.sleep(0.5)

    def _scroll_naturally(self, times=2):
        """Scroll the page naturally before interacting."""
        for _ in range(times):
            px = random.randint(200, 500)
            self.driver.execute_script(f"window.scrollBy(0, {px});")
            time.sleep(random.uniform(1.5, 4.0))

    def _execute_likes(self, count: int):
        """Like tweets — browse the home timeline and like naturally."""
        done = 0
        if count <= 0:
            return done

        self._log_activity("like", "success", error_message=f"Iniciando {count} likes no feed")
        # Go to home timeline to like from feed
        self.driver.get("https://x.com/home")
        time.sleep(random.uniform(3, 5))

        attempts = 0
        max_attempts = count * 4  # safety limit

        while done < count and attempts < max_attempts:
            attempts += 1
            if not self.should_continue():
                break

            try:
                # Find unliked tweets
                like_buttons = self.driver.find_elements(
                    "css selector", '[data-testid="like"]'
                )
                if like_buttons:
                    # Pick a random visible like button
                    btn = random.choice(like_buttons[:5]) if len(like_buttons) > 1 else like_buttons[0]

                    # Scroll to it smoothly
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        btn,
                    )
                    time.sleep(random.uniform(1.5, 3.5))

                    btn.click()
                    done += 1
                    self._send("action_complete", action="like", progress=done)
                    self._log_activity("like", "success")
                    logger.info(f"[{self.account['username']}] Like {done}/{count}")

                    # Human-like pause after liking
                    self._random_delay()
                else:
                    # Scroll down to find more tweets
                    self._scroll_naturally(2)

                # Occasionally just scroll and read
                if random.random() < 0.3:
                    self._scroll_naturally(1)

            except Exception as exc:
                logger.warning(f"Like failed: {exc}")
                self._log_activity("like", "failed", error_message=str(exc))
                self._scroll_naturally(1)

        return done

    def _find_and_click_follow(self):
        """Find the Follow/Seguir button on the current page and click it via JS.

        Returns:
            True if clicked successfully,
            'already_following' if the account is already followed,
            False if no button found.
        """
        # Use JavaScript to find and click — avoids stale element issues
        result = self.driver.execute_script("""
            // Try data-testid that ends with -follow (Twitter's pattern)
            var btns = document.querySelectorAll('[data-testid$="-follow"]');
            for (var i = 0; i < btns.length; i++) {
                var text = btns[i].innerText.trim().toLowerCase();
                if (text === 'follow' || text === 'seguir') {
                    // Check aria-label to avoid clicking "Following" buttons
                    var aria = btns[i].getAttribute('aria-label') || '';
                    if (aria.indexOf('Following') !== -1 || aria.indexOf('Seguindo') !== -1) {
                        continue;
                    }
                    btns[i].scrollIntoView({behavior: 'smooth', block: 'center'});
                    btns[i].click();
                    return true;
                }
            }
            // Fallback: role=button with Follow/Seguir text
            var allBtns = document.querySelectorAll('[role="button"]');
            for (var i = 0; i < allBtns.length; i++) {
                var text = allBtns[i].innerText.trim();
                if ((text === 'Follow' || text === 'Seguir') && allBtns[i].offsetParent !== null) {
                    var aria = allBtns[i].getAttribute('aria-label') || '';
                    if (aria.indexOf('Following') === -1 && aria.indexOf('Seguindo') === -1) {
                        allBtns[i].scrollIntoView({behavior: 'smooth', block: 'center'});
                        allBtns[i].click();
                        return true;
                    }
                }
            }
            // Check if already following (unfollow button present)
            var unfollowBtns = document.querySelectorAll('[data-testid$="-unfollow"]');
            if (unfollowBtns.length > 0) return 'already_following';
            return false;
        """)
        return result

    def _execute_follows(self, count: int):
        """Follow target accounts.

        Iterates through ALL available targets (not just *count*).
        Skips already-followed targets and tries the next one until
        *count* new follows are done or targets are exhausted.
        """
        done = 0
        skipped_already = 0

        if count <= 0:
            return done

        if not self.targets:
            self._log_activity("follow", "skipped",
                               error_message="Nenhum alvo disponivel para follow")
            self._send("warning", message="Sem alvos disponiveis para follow. Adicione mais alvos.")
            return done

        self._log_activity("follow", "success",
                           error_message=f"Iniciando {count} follows ({len(self.targets)} alvos disponiveis)")

        for target in self._iter_available_targets():
            if not self.should_continue():
                break
            if done >= count:
                break

            try:
                target_user = target.get("username", "").lstrip("@")
                self.driver.get(f"https://x.com/{target_user}")
                time.sleep(random.uniform(4, 7))

                # Handle profile page issues
                page_status = self._handle_profile_page()
                if page_status in ("not_found", "suspended"):
                    self._log_activity("follow", "skipped", target_username=target_user,
                                       error_message=f"Perfil {page_status} - alvo removido")
                    self._remove_target(target_user, page_status)
                    self._random_delay()
                    continue

                # Scroll down a bit to look natural
                self._scroll_naturally(1)
                time.sleep(random.uniform(1.0, 2.0))

                follow_result = self._find_and_click_follow()
                if follow_result is True:
                    done += 1
                    self._send("action_complete", action="follow", target=target_user, progress=done)
                    self._log_activity("follow", "success", target_username=target_user,
                                       target_url=f"https://x.com/{target_user}")
                    self._record_action(target_user, "follow", getattr(self, "_current_day", 1))
                    logger.info(f"[{self.account['username']}] Followed @{target_user} ({done}/{count})")
                    time.sleep(random.uniform(1.5, 3.0))
                elif follow_result == "already_following":
                    skipped_already += 1
                    self._log_activity("follow", "skipped", target_username=target_user,
                                       error_message="Ja segue este perfil")
                    # Record so we filter this target on future runs
                    self._record_action(target_user, "follow", getattr(self, "_current_day", 1))
                    logger.info(f"[{self.account['username']}] Already following @{target_user}, "
                                f"skipped ({skipped_already} skipped so far)")
                    # Remove from local list so it won't be tried again this session
                    self.targets = [t for t in self.targets
                                    if t.get("username", "").lstrip("@") != target_user]
                else:
                    self._log_activity("follow", "skipped", target_username=target_user,
                                       error_message="Botao Follow nao encontrado")
                    logger.warning(f"Follow button not found for @{target_user}")

            except Exception as exc:
                self._log_activity("follow", "failed", target_username=target_user,
                                   error_message=str(exc))
                logger.warning(f"Follow failed for {target.get('username')}: {exc}")
            self._random_delay()

        # Notify if couldn't reach target count
        if done < count:
            msg = (f"Apenas {done}/{count} follows realizados. "
                   f"{skipped_already} alvos ja seguidos. "
                   f"Adicione mais alvos para a conta @{self.account['username']}.")
            self._log_activity("follow", "warning", error_message=msg)
            self._send("warning", message=msg)
            logger.warning(f"[{self.account['username']}] {msg}")

        if skipped_already > 0:
            self._log_activity("follow", "success",
                               error_message=f"Follows concluidos: {done} novos, {skipped_already} ja seguidos (pulados)")

        return done

    def _execute_retweets(self, count: int):
        """Retweet tweets from the home timeline."""
        done = 0
        if count <= 0:
            return done

        self._log_activity("retweet", "success", error_message=f"Iniciando {count} retweets")
        self.driver.get("https://x.com/home")
        time.sleep(random.uniform(3, 5))

        attempts = 0
        max_attempts = count * 4

        while done < count and attempts < max_attempts:
            attempts += 1
            if not self.should_continue():
                break

            try:
                rt_buttons = self.driver.find_elements(
                    "css selector", '[data-testid="retweet"]'
                )
                if rt_buttons:
                    btn = random.choice(rt_buttons[:3]) if len(rt_buttons) > 1 else rt_buttons[0]

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        btn,
                    )
                    time.sleep(random.uniform(1.5, 3.0))

                    btn.click()
                    time.sleep(random.uniform(0.8, 1.5))

                    # Confirm retweet
                    confirm = self.driver.find_elements(
                        "css selector", '[data-testid="retweetConfirm"]'
                    )
                    if confirm:
                        confirm[0].click()
                        done += 1
                        self._send("action_complete", action="retweet", progress=done)
                        self._log_activity("retweet", "success")
                        logger.info(f"[{self.account['username']}] Retweet {done}/{count}")

                    self._random_delay()
                else:
                    self._scroll_naturally(2)

            except Exception as exc:
                self._log_activity("retweet", "failed", error_message=str(exc))
                logger.warning(f"Retweet failed: {exc}")
                self._scroll_naturally(1)

        return done

    def _execute_unfollows(self, count: int):
        """Unfollow accounts from the following list."""
        done = 0
        if count <= 0:
            return done

        self._log_activity("unfollow", "success", error_message=f"Iniciando {count} unfollows")
        try:
            self.driver.get(f"https://x.com/{self.account['username']}/following")
            time.sleep(random.uniform(3, 5))
        except Exception as exc:
            logger.warning(f"Could not open following page: {exc}")
            return done

        for _ in range(count):
            if not self.should_continue():
                break
            try:
                # Find "Following" or "Seguindo" buttons
                all_btns = self.driver.find_elements("css selector", '[role="button"]')
                unfollow_btn = None
                for btn in all_btns:
                    try:
                        text = btn.text.strip()
                        if text in ("Following", "Seguindo") and btn.is_displayed():
                            unfollow_btn = btn
                            break
                    except Exception:
                        continue

                if unfollow_btn:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        unfollow_btn,
                    )
                    time.sleep(random.uniform(1.0, 2.0))
                    unfollow_btn.click()
                    time.sleep(random.uniform(0.8, 1.5))

                    # Confirm unfollow
                    confirm = self.driver.find_elements(
                        "css selector", '[data-testid="confirmationSheetConfirm"]'
                    )
                    if confirm:
                        confirm[0].click()
                        done += 1
                        self._send("action_complete", action="unfollow", progress=done)
                        self._log_activity("unfollow", "success")
                        logger.info(f"[{self.account['username']}] Unfollow {done}/{count}")

                    self._random_delay()
                else:
                    self._scroll_naturally(1)
            except Exception as exc:
                self._log_activity("unfollow", "failed", error_message=str(exc))
                logger.warning(f"Unfollow failed: {exc}")
            self._random_delay()

        return done

    # ------------------------------------------------------------------
    # Feed browsing
    # ------------------------------------------------------------------

    def _browse_feed(self, min_seconds: float, max_seconds: float,
                     posts_to_open: int = 0, view_comments_chance: float = 0.3):
        """Browse the feed for a random duration between min and max seconds."""
        if min_seconds <= 0 and max_seconds <= 0:
            return
        # Ensure min <= max
        if max_seconds < min_seconds:
            max_seconds = min_seconds
        duration_secs = random.uniform(min_seconds, max_seconds)
        duration_min = duration_secs / 60.0
        self._send("status", status="browsing", duration_seconds=round(duration_secs))
        self._log_activity("browse", "success",
                           error_message=f"Navegando feed por {duration_secs:.0f}s ({duration_min:.1f} min)")
        logger.info(f"[{self.account['username']}] Navegando pelo feed por {duration_secs:.0f}s ({duration_min:.1f} min)")

        def _on_browse_event(event_type: str, data: dict):
            """Callback for browse feed events — writes to activity_logs."""
            if event_type == "post_open":
                self._log_activity("browse", "success",
                                   error_message=f"Visualizando post {data['post_number']}/{data['total']}")
            elif event_type == "post_read":
                self._log_activity("browse", "success",
                                   error_message=f"Lendo post {data['post_number']} por {data['read_time']}s")
            elif event_type == "comment_view":
                self._log_activity("browse", "success",
                                   error_message=f"Visualizando comentario {data['comment_number']}/{data['total']} do post {data['post_number']}")
            elif event_type == "post_failed":
                self._log_activity("browse", "warning",
                                   error_message=f"Falha ao abrir post {data.get('post_number', '?')}: {data.get('reason', 'desconhecido')}")
            elif event_type == "browse_summary":
                status = "success" if data["posts_opened"] > 0 else "warning"
                msg = f"Browse: {data['posts_opened']} posts abertos, {data['comments_viewed']} comentarios vistos, {data['scrolls']} scrolls"
                if data["posts_opened"] == 0:
                    msg += f" (de {posts_to_open} planejados)"
                self._log_activity("browse", status, error_message=msg)

        # Load scroll config from settings
        scroll_config = None
        if self.db:
            try:
                row = self.db.fetch_one(
                    "SELECT value FROM settings WHERE key = 'scroll_config'"
                )
                if row:
                    scroll_config = json.loads(row["value"])
            except Exception:
                pass

        browser = BrowseFeedAction(self.driver, logger)
        browser.execute(
            duration_minutes=duration_min,
            stop_check=lambda: not self.should_continue(),
            posts_to_open=posts_to_open,
            view_comments_chance=view_comments_chance,
            on_event=_on_browse_event,
            scroll_config=scroll_config,
        )
        self._log_activity("browse", "success", error_message="Navegacao do feed concluida")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _remove_target(self, username: str, reason: str) -> None:
        """Permanently remove a target from the database and local list."""
        clean_user = username.lstrip("@")
        logger.info(f"[{self.account['username']}] Removendo alvo @{clean_user} ({reason})")

        # Remove from database
        if self.db:
            try:
                self.db.execute(
                    "DELETE FROM targets WHERE username = ?", (clean_user,)
                )
            except Exception as exc:
                logger.debug(f"Erro ao remover alvo do banco: {exc}")

        # Remove from local list
        self.targets = [t for t in self.targets
                        if t.get("username", "").lstrip("@") != clean_user]

    def _cycle_targets(self, count: int):
        """Yield *count* targets, cycling through the list if necessary."""
        for i in range(count):
            if not self.targets:
                return
            yield self.targets[i % len(self.targets)]

    def _iter_available_targets(self):
        """Yield all available targets once (no cycling). Used for follows."""
        for target in list(self.targets):
            yield target

    def _execute_likes_on_profiles(self, count: int):
        """Like tweets by visiting target profiles instead of the home feed."""
        done = 0
        if count <= 0:
            return done

        self._log_activity("like", "success", error_message=f"Iniciando {count} likes em perfis alvo")
        for target in self._cycle_targets(count):
            if not self.should_continue():
                break
            try:
                target_user = target.get("username", "").lstrip("@")
                self.driver.get(f"https://x.com/{target_user}")
                time.sleep(random.uniform(3, 6))

                # Handle profile page issues
                page_status = self._handle_profile_page()
                if page_status in ("not_found", "suspended"):
                    self._log_activity("like", "skipped", target_username=target_user,
                                       error_message=f"Perfil {page_status} - alvo removido")
                    self._remove_target(target_user, page_status)
                    self._random_delay()
                    continue

                # Scroll a bit to load tweets
                self._scroll_naturally(2)

                attempts = 0
                max_attempts = 4
                while attempts < max_attempts:
                    attempts += 1
                    if not self.should_continue():
                        break
                    try:
                        like_buttons = self.driver.find_elements(
                            "css selector", '[data-testid="like"]'
                        )
                        if like_buttons:
                            btn = random.choice(like_buttons[:3]) if len(like_buttons) > 1 else like_buttons[0]
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                btn,
                            )
                            time.sleep(random.uniform(1.5, 3.5))
                            btn.click()
                            done += 1
                            self._send("action_complete", action="like", target=target_user, progress=done)
                            self._log_activity("like", "success", target_username=target_user, target_url=f"https://x.com/{target_user}")
                            self._record_action(target_user, "like", getattr(self, "_current_day", 1))
                            logger.info(f"[{self.account['username']}] Like on @{target_user} profile {done}/{count}")
                            break
                        else:
                            self._scroll_naturally(1)
                    except Exception as exc:
                        self._log_activity("like", "failed", target_username=target_user, error_message=str(exc))
                        logger.warning(f"Like on profile @{target_user} failed: {exc}")
                        self._scroll_naturally(1)

                self._random_delay()

            except Exception as exc:
                logger.warning(f"Like on profile failed for {target.get('username')}: {exc}")
                self._random_delay()

        return done

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute today's scheduled actions for this account."""
        account_id = self.account["id"]
        username = self.account["username"]

        try:
            self._send("status", status="starting")
            self._log_activity("sistema", "success", error_message="Worker iniciado")
            logger.info(f"[{username}] Worker starting")

            # 1. Determine today's actions
            start_date = self.account.get("start_date")
            day_number = Scheduler.get_day_number(start_date)
            self._current_day = day_number
            actions = Scheduler.get_today_actions(self.schedule_json, start_date)
            self._send("schedule", actions=actions)
            plan = (f"Dia {day_number} - Likes: {actions.get('likes',0)}, "
                    f"Follows: {actions.get('follows',0)} (inclui {actions.get('follow_initial_count',0)} iniciais), "
                    f"Retweets: {actions.get('retweets',0)}, Unfollows: {actions.get('unfollows',0)}")
            self._log_activity("sistema", "success", error_message=f"Plano do dia: {plan}")
            logger.info(f"[{username}] Day {day_number} plan: {actions}")

            # Log targets loaded for this account (for category debugging)
            target_names = [t.get("username", "?") for t in self.targets]
            self._log_activity("sistema", "success",
                               error_message=f"Alvos carregados ({len(self.targets)}): {', '.join(target_names[:20])}")
            logger.info(f"[{username}] Targets loaded: {target_names}")

            # Filter out targets already followed (ANY day — follows should never repeat)
            already_followed = self._get_all_followed_targets()
            if already_followed:
                before = len(self.targets)
                self.targets = [t for t in self.targets
                                if t.get("username", "").lstrip("@") not in already_followed]
                filtered = before - len(self.targets)
                if filtered > 0:
                    self._log_activity("sistema", "success",
                                       error_message=f"{filtered} alvos filtrados (ja seguidos anteriormente)")
                    logger.info(f"[{username}] Filtered {filtered} already-followed targets")

            if not self.targets:
                self._log_activity("sistema", "warning",
                                   error_message="TODOS os alvos foram filtrados (ja seguidos ou sem alvos na categoria)")
                logger.warning(f"[{username}] All targets filtered out — none available")

            # 2. Launch browser
            self._create_browser()
            self._send("status", status="running")

            if not self.should_continue():
                return

            # 3. Browse feed settings from schedule
            browse_before_min = actions.get("browse_before_min", 0)
            browse_before_max = actions.get("browse_before_max", 0)
            browse_between_min = actions.get("browse_between_min", 0)
            browse_between_max = actions.get("browse_between_max", 0)

            # New behavior settings
            posts_to_open = actions.get("posts_to_open", 0)
            view_comments_chance = actions.get("view_comments_chance", 0.3)
            likes_on_feed = actions.get("likes_on_feed", True)
            follow_initial_count = actions.get("follow_initial_count", 0)

            # 3b. Execute initial follows IMMEDIATELY after login
            initial_follows_done = 0
            if follow_initial_count > 0 and self.should_continue():
                self._log_activity("follow", "success",
                                   error_message=f"Seguindo {follow_initial_count} perfis iniciais")
                initial_follows_done = self._execute_follows(follow_initial_count)
                self._log_activity("follow", "success",
                                   error_message=f"Follows iniciais concluidos: {initial_follows_done}")
                if not self.should_continue():
                    self._send("status", status="stopped")
                    return

            # 4. Browse feed BEFORE actions
            if browse_before_min > 0 or browse_before_max > 0:
                self._browse_feed(browse_before_min, browse_before_max,
                                  posts_to_open=posts_to_open,
                                  view_comments_chance=view_comments_chance)
                if not self.should_continue():
                    self._send("status", status="stopped")
                    return

            # 5. Execute actions with browsing between them
            results = {}

            # Likes: on feed (default) or on target profiles
            like_count = actions.get("likes", 0)
            if likes_on_feed:
                results["likes"] = self._execute_likes(like_count)
            else:
                results["likes"] = self._execute_likes_on_profiles(like_count)
            if not self.should_continue():
                self._send("status", status="stopped", results=results)
                return

            # Browse between likes -> follows
            follow_count = actions.get("follows", 0)
            remaining_follows = max(0, follow_count - initial_follows_done)
            if remaining_follows > 0 and (browse_between_min > 0 or browse_between_max > 0):
                self._browse_feed(browse_between_min, browse_between_max,
                                  posts_to_open=posts_to_open,
                                  view_comments_chance=view_comments_chance)
                if not self.should_continue():
                    self._send("status", status="stopped", results=results)
                    return

            results["follows"] = self._execute_follows(remaining_follows) + initial_follows_done
            if not self.should_continue():
                self._send("status", status="stopped", results=results)
                return

            # Browse between follows -> retweets
            if actions.get("retweets", 0) > 0 and (browse_between_min > 0 or browse_between_max > 0):
                self._browse_feed(browse_between_min, browse_between_max,
                                  posts_to_open=posts_to_open,
                                  view_comments_chance=view_comments_chance)
                if not self.should_continue():
                    self._send("status", status="stopped", results=results)
                    return

            results["retweets"] = self._execute_retweets(actions.get("retweets", 0))
            if not self.should_continue():
                self._send("status", status="stopped", results=results)
                return

            # Browse between retweets -> unfollows
            if actions.get("unfollows", 0) > 0 and (browse_between_min > 0 or browse_between_max > 0):
                self._browse_feed(browse_between_min, browse_between_max,
                                  posts_to_open=posts_to_open,
                                  view_comments_chance=view_comments_chance)
                if not self.should_continue():
                    self._send("status", status="stopped", results=results)
                    return

            results["unfollows"] = self._execute_unfollows(actions.get("unfollows", 0))

            # 6. Done
            summary = ", ".join(f"{k}: {v}" for k, v in results.items())
            self._log_activity("sistema", "success", error_message=f"Concluido dia {day_number} - {summary}")
            self._send("status", status="completed", results=results)
            logger.info(f"[{username}] Worker completed day {day_number}: {results}")

            # Update current_day and status in the database
            if self.db:
                try:
                    schedule_length = Scheduler.get_schedule_length(self.schedule_json)
                    capped_day = min(day_number, schedule_length)

                    if capped_day >= schedule_length:
                        # Last day (or only day) of schedule — mark as completed
                        save_day = schedule_length
                        save_status = "completed"
                    else:
                        # More days ahead — advance to next day, set idle for next run
                        save_day = capped_day + 1
                        save_status = "idle"

                    self.db.execute(
                        "UPDATE accounts SET current_day = ?, status = ? WHERE id = ?",
                        (save_day, save_status, account_id),
                    )
                    logger.info(
                        f"[{username}] Dia {capped_day}/{schedule_length} concluido -> "
                        f"current_day={save_day}, status={save_status}"
                    )
                except Exception:
                    pass

        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(f"[{username}] Worker error: {exc}\n{tb}")
            self._log_activity("sistema", "failed", error_message=str(exc))
            self._send("status", status="error", error=str(exc))
            # Update status in the database so it doesn't stay stuck as "running"
            if self.db:
                try:
                    self.db.execute(
                        "UPDATE accounts SET status = 'error' WHERE id = ?",
                        (account_id,),
                    )
                except Exception:
                    pass

        finally:
            self._close_browser()
            self._log_activity("sistema", "success", error_message="Browser fechado")
            # Safety net: never leave status as "running" after thread exits.
            # Skip if a newer worker already replaced us (avoids overwriting
            # the new worker's "running" status).
            if self.db and not self._superseded:
                try:
                    row = self.db.fetch_one(
                        "SELECT status FROM accounts WHERE id = ?",
                        (account_id,),
                    )
                    if row and row.get("status") == "running":
                        self.db.execute(
                            "UPDATE accounts SET status = 'idle' WHERE id = ?",
                            (account_id,),
                        )
                        logger.info(f"[{username}] Safety net: reset stuck 'running' → 'idle'")
                except Exception:
                    pass
