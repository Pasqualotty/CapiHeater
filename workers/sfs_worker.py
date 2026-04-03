"""
SfsWorker - Executes SFS (Shoutout For Shoutout) session actions for a single account.

Visits each pending target profile and performs the configured actions
(follow, like, retweet, comment_like, like_latest_post, rt_latest_post).
"""

import json
import time
import random
import traceback
from queue import Queue

from workers.base_worker import BaseWorker
from utils.logger import get_logger
from utils.humanizer import smooth_scroll, smooth_scroll_to_element

logger = get_logger(__name__)

# Pace -> (min_seconds, max_seconds) between targets
PACE_DELAYS = {
    "slow":   (120, 300),
    "normal": (60,  180),
    "fast":   (30,   90),
}


class SfsWorker(BaseWorker):
    """Worker thread that drives a browser for one SFS session.

    Parameters
    ----------
    account : dict
        Account row from the database (must contain ``id``, ``username``,
        ``cookies_json``, ``proxy``).
    session_data : dict
        SFS session row from the database.
    sfs_manager : SfsManager
        Manager for updating session/target state.
    db : Database
        Shared database instance.
    message_queue : Queue
        Thread-safe queue for sending status updates to the GUI / engine.
    driver_factory : object, optional
        Object with a ``create_driver(proxy)`` method.  Defaults to
        ``browser.driver_factory.DriverFactory`` when *None*.
    """

    ACTION_DELAY_MIN = 8
    ACTION_DELAY_MAX = 25

    def __init__(
        self,
        account: dict,
        session_data: dict,
        sfs_manager,
        db,
        message_queue: Queue,
        driver_factory=None,
    ):
        super().__init__(name=f"SfsWorker-{account['username']}-s{session_data['id']}")
        self.account = account
        self.session = session_data
        self.sfs_manager = sfs_manager
        self.db = db
        self.queue = message_queue
        self.driver_factory = driver_factory
        self.driver = None
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
            "session_id": self.session["id"],
            **payload,
        }
        self.queue.put(msg)

    def _log_activity(
        self,
        action_type: str,
        status: str,
        target_username: str = None,
        target_url: str = None,
        error_message: str = None,
    ):
        """Write an entry to the activity_logs table."""
        if self.db is None:
            return
        try:
            self.db.execute(
                """INSERT INTO activity_logs
                   (account_id, action_type, target_username, target_url,
                    status, error_message, executed_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
                (
                    self.account["id"],
                    action_type,
                    target_username,
                    target_url,
                    status,
                    error_message,
                ),
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Browser helpers (mirror of TwitterWorker — same selectors / logic)
    # ------------------------------------------------------------------

    def _create_browser(self):
        """Instantiate the browser via DriverFactory and load cookies."""
        factory = self.driver_factory
        if factory is None:
            from browser.driver_factory import DriverFactory
            factory = DriverFactory

        proxy = self.account.get("proxy")
        self.driver = factory.create_driver(proxy=proxy)

        if proxy:
            username = self.account["username"]
            logger.info(f"[{username}] SFS — Proxy ativo, verificando IP...")
            self._log_activity(
                "sistema", "success", error_message="SFS — Verificando proxy..."
            )
            self.driver.get("https://whatismyipaddress.com")
            time.sleep(5)
            try:
                self.driver.get("https://httpbin.org/ip")
                time.sleep(2)
                import re as _re
                page_text = self.driver.find_element("tag name", "body").text
                ip_match = _re.search(r'"origin"\s*:\s*"([^"]+)"', page_text)
                detected_ip = ip_match.group(1) if ip_match else "desconhecido"
                logger.info(f"[{username}] SFS — Proxy OK — IP: {detected_ip}")
            except Exception:
                logger.warning(
                    f"[{username}] SFS — Nao foi possivel verificar IP do proxy"
                )

        self.driver.get("https://x.com")
        time.sleep(3)

        cookies = self.account.get("cookies_json", "[]")
        if isinstance(cookies, str):
            cookies = json.loads(cookies)

        for cookie in cookies:
            try:
                if "name" not in cookie or "value" not in cookie:
                    continue
                c = {"name": cookie["name"], "value": cookie["value"]}
                if "domain" in cookie:
                    c["domain"] = cookie["domain"]
                if "path" in cookie:
                    c["path"] = cookie["path"]
                if cookie.get("secure"):
                    c["secure"] = True
                if cookie.get("httpOnly"):
                    c["httpOnly"] = True
                sam = cookie.get("sameSite")
                if sam in ("Strict", "Lax", "None"):
                    c["sameSite"] = sam
                expiry = cookie.get("expiry") or cookie.get("expirationDate")
                if expiry and not cookie.get("session"):
                    c["expiry"] = int(expiry)
                self.driver.add_cookie(c)
            except Exception as exc:
                logger.debug(f"Cookie skip: {cookie.get('name', '?')}: {exc}")

        self.driver.get("https://x.com/home")
        time.sleep(4)

        if not self._is_logged_in():
            self._log_activity(
                "login", "failed",
                error_message="Cookies invalidos ou expirados",
            )
            raise RuntimeError(
                f"SFS — Falha ao logar com cookies da conta @{self.account['username']}. "
                "Verifique se os cookies estao validos."
            )
        self._log_activity("login", "success")
        logger.info(f"[{self.account['username']}] SFS — Login via cookies OK")

    def _is_logged_in(self) -> bool:
        """Check if the browser is logged into Twitter/X."""
        try:
            page_source = self.driver.page_source
            logged_out_signs = [
                "Inscreva-se", "Sign up", "Create account",
                "Criar conta", "Acabou de chegar",
            ]
            for sign in logged_out_signs:
                if sign in page_source:
                    return False
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
        """Detect and handle profile page edge cases.

        Returns 'ok', 'sensitive', 'not_found', 'suspended', or 'error'.
        """
        try:
            time.sleep(random.uniform(1.0, 2.0))
            page = self.driver.page_source

            not_found_signs = [
                "esta página não existe", "this page doesn",
                "Hmm...this page", "Ih, esta página", "page doesn't exist",
            ]
            for sign in not_found_signs:
                if sign.lower() in page.lower():
                    logger.warning(
                        f"[{self.account['username']}] SFS — Perfil nao encontrado (404)"
                    )
                    return "not_found"

            suspended_signs = [
                "Conta suspensa", "Account suspended",
                "suspende as contas", "suspend accounts",
            ]
            for sign in suspended_signs:
                if sign in page:
                    logger.warning(
                        f"[{self.account['username']}] SFS — Conta suspensa detectada"
                    )
                    return "suspended"

            sensitive_signs = [
                "conteúdo pontecialmente sensível",
                "conteúdo potencialmente sensível",
                "potentially sensitive",
                "Sim, ver perfil", "Yes, view profile",
                "Ainda quer vê-lo",
            ]
            for sign in sensitive_signs:
                if sign in page:
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
        """Force-stop by killing the chromedriver process directly."""
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
                        f"SFS — Force-killed chromedriver PID {proc.pid}"
                    )
            except Exception as exc:
                logger.warning(f"SFS force_stop driver kill failed: {exc}")
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

    def _random_delay(self):
        """Sleep a random short duration between individual actions."""
        delay = random.uniform(self.ACTION_DELAY_MIN, self.ACTION_DELAY_MAX)
        end = time.time() + delay
        while time.time() < end:
            if self.is_stopped():
                return
            time.sleep(0.5)

    def _pace_delay(self):
        """Sleep the inter-target delay configured by session pace."""
        pace = self.session.get("pace", "normal")
        min_s, max_s = PACE_DELAYS.get(pace, PACE_DELAYS["normal"])
        delay = random.uniform(min_s, max_s)
        logger.info(
            f"[{self.account['username']}] SFS — Aguardando {delay:.0f}s antes do proximo alvo (pace={pace})"
        )
        end = time.time() + delay
        while time.time() < end:
            if self.is_stopped():
                return
            if self.is_paused():
                # Will block inside wait_if_paused — reset timer on resume
                if not self.wait_if_paused():
                    return
                end = time.time() + random.uniform(min_s, max_s)
            time.sleep(0.5)

    def _scroll_profile(self):
        """Scroll the target profile naturally."""
        num_scrolls = random.randint(2, 4)
        for _ in range(num_scrolls):
            if self.is_stopped():
                return
            px = random.randint(200, 800)
            smooth_scroll(self.driver, px)
            time.sleep(random.uniform(1.5, 4.0))

    # ------------------------------------------------------------------
    # Action executors (SFS-specific: one target at a time)
    # ------------------------------------------------------------------

    def _do_follow(self, target_user: str) -> bool:
        """Attempt to follow the target. Returns True on success."""
        result = self.driver.execute_script("""
            var btns = document.querySelectorAll('[data-testid$="-follow"]');
            for (var i = 0; i < btns.length; i++) {
                var text = btns[i].innerText.trim().toLowerCase();
                if (text === 'follow' || text === 'seguir') {
                    var aria = btns[i].getAttribute('aria-label') || '';
                    if (aria.indexOf('Following') !== -1 || aria.indexOf('Seguindo') !== -1) {
                        continue;
                    }
                    btns[i].scrollIntoView({behavior: 'smooth', block: 'center'});
                    btns[i].click();
                    return true;
                }
            }
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
            var unfollowBtns = document.querySelectorAll('[data-testid$="-unfollow"]');
            if (unfollowBtns.length > 0) return 'already_following';
            return false;
        """)
        if result is True:
            self._send("action_complete", action="follow", target=target_user)
            self._log_activity(
                "follow", "success", target_username=target_user,
                target_url=f"https://x.com/{target_user}",
                error_message="SFS follow",
            )
            logger.info(f"[{self.account['username']}] SFS — Followed @{target_user}")
            return True
        if result == "already_following":
            self._log_activity(
                "follow", "skipped", target_username=target_user,
                error_message="SFS — Ja segue este perfil",
            )
            logger.info(
                f"[{self.account['username']}] SFS — Ja segue @{target_user}, pulando follow"
            )
        else:
            self._log_activity(
                "follow", "skipped", target_username=target_user,
                error_message="SFS — Botao Follow nao encontrado",
            )
            logger.warning(
                f"[{self.account['username']}] SFS — Follow button nao encontrado para @{target_user}"
            )
        return False

    def _do_like_on_profile(self, target_user: str, use_latest: bool) -> bool:
        """Open a post from the target's profile and like it."""
        try:
            tweets = self.driver.find_elements("css selector", '[data-testid="tweet"]')
            original_tweets = [
                tw for tw in tweets
                if not tw.find_elements("css selector", '[data-testid="socialContext"]')
            ]
            if not original_tweets:
                logger.warning(
                    f"[{self.account['username']}] SFS — Sem tweets para curtir em @{target_user}"
                )
                return False

            candidates = original_tweets[:1] if use_latest else original_tweets[:min(5, len(original_tweets))]
            chosen = None
            for candidate in candidates:
                if not candidate.find_elements("css selector", '[data-testid="unlike"]'):
                    chosen = candidate
                    break

            if chosen is None:
                self._log_activity(
                    "like", "skipped", target_username=target_user,
                    error_message="SFS — Todos os posts ja curtidos",
                )
                return False

            smooth_scroll_to_element(self.driver, chosen)
            time.sleep(random.uniform(1.0, 3.0))

            clickable = self._find_clickable_in_tweet(chosen)
            if clickable is None:
                return False

            self._click_to_open_post(clickable)
            time.sleep(random.uniform(3.0, 8.0))

            like_buttons = self.driver.find_elements("css selector", '[data-testid="like"]')
            if like_buttons:
                smooth_scroll_to_element(self.driver, like_buttons[0])
                time.sleep(random.uniform(0.5, 1.5))
                like_buttons[0].click()
                self._send("action_complete", action="like", target=target_user)
                self._log_activity(
                    "like", "success", target_username=target_user,
                    target_url=f"https://x.com/{target_user}",
                    error_message="SFS like no post",
                )
                logger.info(
                    f"[{self.account['username']}] SFS — Like no post de @{target_user}"
                )
                self.driver.back()
                time.sleep(random.uniform(2.0, 4.0))
                return True

            self.driver.back()
            time.sleep(random.uniform(2.0, 4.0))
            return False

        except Exception as exc:
            self._log_activity(
                "like", "failed", target_username=target_user, error_message=str(exc)
            )
            logger.warning(
                f"[{self.account['username']}] SFS — Like failed para @{target_user}: {exc}"
            )
            self._safe_back_from_post()
            return False

    def _do_rt_on_profile(self, target_user: str, use_latest: bool) -> bool:
        """Open a post from the target's profile and retweet it."""
        try:
            tweets = self.driver.find_elements("css selector", '[data-testid="tweet"]')
            original_tweets = [
                tw for tw in tweets
                if not tw.find_elements("css selector", '[data-testid="socialContext"]')
            ]
            if not original_tweets:
                logger.warning(
                    f"[{self.account['username']}] SFS — Sem tweets para RT em @{target_user}"
                )
                return False

            candidates = original_tweets[:1] if use_latest else original_tweets[:min(5, len(original_tweets))]
            chosen = None
            for candidate in candidates:
                if not candidate.find_elements("css selector", '[data-testid="unretweet"]'):
                    chosen = candidate
                    break

            if chosen is None:
                self._log_activity(
                    "retweet", "skipped", target_username=target_user,
                    error_message="SFS — Todos os posts ja retweetados",
                )
                return False

            smooth_scroll_to_element(self.driver, chosen)
            time.sleep(random.uniform(1.0, 3.0))

            clickable = self._find_clickable_in_tweet(chosen)
            if clickable is None:
                return False

            self._click_to_open_post(clickable)
            time.sleep(random.uniform(3.0, 8.0))

            rt_buttons = self.driver.find_elements("css selector", '[data-testid="retweet"]')
            if rt_buttons:
                smooth_scroll_to_element(self.driver, rt_buttons[0])
                time.sleep(random.uniform(1.0, 2.5))
                rt_buttons[0].click()
                time.sleep(random.uniform(0.8, 1.5))
                confirm = self.driver.find_elements(
                    "css selector", '[data-testid="retweetConfirm"]'
                )
                if confirm:
                    confirm[0].click()
                    self._send("action_complete", action="retweet", target=target_user)
                    self._log_activity(
                        "retweet", "success", target_username=target_user,
                        target_url=f"https://x.com/{target_user}",
                        error_message="SFS retweet no post",
                    )
                    logger.info(
                        f"[{self.account['username']}] SFS — RT no post de @{target_user}"
                    )
                    self.driver.back()
                    time.sleep(random.uniform(2.0, 4.0))
                    return True

            self.driver.back()
            time.sleep(random.uniform(2.0, 4.0))
            return False

        except Exception as exc:
            self._log_activity(
                "retweet", "failed", target_username=target_user, error_message=str(exc)
            )
            logger.warning(
                f"[{self.account['username']}] SFS — RT failed para @{target_user}: {exc}"
            )
            self._safe_back_from_post()
            return False

    def _do_comment_like(self, target_user: str) -> bool:
        """Visit a post on the target's profile and like one of its comments."""
        try:
            tweets = self.driver.find_elements("css selector", '[data-testid="tweet"]')
            if not tweets:
                return False

            chosen_tweet = random.choice(tweets[:min(5, len(tweets))])
            smooth_scroll_to_element(self.driver, chosen_tweet)
            time.sleep(random.uniform(1.0, 3.0))

            clickable = self._find_clickable_in_tweet(chosen_tweet)
            if clickable is None:
                return False

            self._click_to_open_post(clickable)
            time.sleep(random.uniform(3.0, 8.0))

            # Scroll into comment section
            smooth_scroll(self.driver, random.randint(600, 900))
            time.sleep(random.uniform(1.5, 3.0))

            # Find like buttons in comments (exclude the first which is the main post)
            like_buttons = self.driver.find_elements("css selector", '[data-testid="like"]')
            if len(like_buttons) > 1:
                comment_like = like_buttons[1]
                smooth_scroll_to_element(self.driver, comment_like)
                time.sleep(random.uniform(0.5, 1.5))
                comment_like.click()
                self._send("action_complete", action="comment_like", target=target_user)
                self._log_activity(
                    "like_comment", "success", target_username=target_user,
                    target_url=f"https://x.com/{target_user}",
                    error_message="SFS like em comentario",
                )
                logger.info(
                    f"[{self.account['username']}] SFS — Like em comentario de @{target_user}"
                )
                self.driver.back()
                time.sleep(random.uniform(2.0, 4.0))
                return True

            self.driver.back()
            time.sleep(random.uniform(2.0, 4.0))
            return False

        except Exception as exc:
            self._log_activity(
                "like_comment", "failed", target_username=target_user,
                error_message=str(exc),
            )
            logger.warning(
                f"[{self.account['username']}] SFS — Comment like failed para @{target_user}: {exc}"
            )
            self._safe_back_from_post()
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_clickable_in_tweet(self, tweet_element):
        """Find a clickable timestamp link or tweet text inside a tweet article."""
        try:
            time_links = tweet_element.find_elements(
                "css selector", "a[href*='/status/'] time"
            )
            if time_links:
                return time_links[0].find_element("xpath", "..")
        except Exception:
            pass
        try:
            return tweet_element.find_element(
                "css selector", '[data-testid="tweetText"]'
            )
        except Exception:
            pass
        return None

    def _click_to_open_post(self, clickable):
        """Click a tweet element and wait for the /status/ page to load."""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.support.ui import WebDriverWait

        ActionChains(self.driver).move_to_element(clickable).pause(
            random.uniform(0.3, 0.8)
        ).click().perform()
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: "/status/" in d.current_url
            )
        except Exception:
            pass

    def _safe_back_from_post(self):
        """Navigate back if currently on a /status/ page."""
        try:
            if "/status/" in self.driver.current_url:
                self.driver.back()
                time.sleep(random.uniform(2.0, 4.0))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Per-target execution
    # ------------------------------------------------------------------

    def _process_target(self, target: dict) -> None:
        """Navigate to a target profile and execute all configured actions."""
        session = self.session
        target_user = target.get("username", "").lstrip("@")

        logger.info(
            f"[{self.account['username']}] SFS — Processando alvo @{target_user}"
        )
        self._log_activity(
            "sistema", "success", target_username=target_user,
            error_message=f"SFS — Iniciando acoes em @{target_user}",
        )

        self.driver.get(f"https://x.com/{target_user}")
        time.sleep(random.uniform(4, 7))

        page_status = self._handle_profile_page()
        if page_status in ("not_found", "suspended"):
            self._log_activity(
                "sistema", "skipped", target_username=target_user,
                error_message=f"SFS — Perfil {page_status}, pulando alvo",
            )
            logger.warning(
                f"[{self.account['username']}] SFS — @{target_user} {page_status}, pulando"
            )
            return

        # Scroll profile before interacting
        self._scroll_profile()
        time.sleep(random.uniform(1.0, 2.0))

        # --- Follow ---
        if session.get("action_follow", 1):
            if not self.should_continue():
                return
            self._do_follow(target_user)
            time.sleep(random.uniform(2.0, 4.0))

        # --- Like latest post ---
        if session.get("action_like", 1):
            if not self.should_continue():
                return
            use_latest = bool(session.get("like_latest_post", 0))
            self._do_like_on_profile(target_user, use_latest=use_latest)
            try:
                current_url = self.driver.current_url or ""
            except Exception:
                current_url = ""
            if "/status/" not in current_url:
                time.sleep(random.uniform(1.0, 2.0))

        # --- RT latest post ---
        if session.get("action_retweet", 1):
            if not self.should_continue():
                return
            use_latest = bool(session.get("rt_latest_post", 0))
            # Reload profile page in case we navigated away during like
            try:
                current_url = self.driver.current_url or ""
            except Exception:
                current_url = ""
            if "/status/" in current_url:
                self.driver.get(f"https://x.com/{target_user}")
                time.sleep(random.uniform(3, 6))
                self._handle_profile_page()
            self._do_rt_on_profile(target_user, use_latest=use_latest)

        # --- Comment like ---
        if session.get("action_comment_like", 0):
            if not self.should_continue():
                return
            try:
                current_url = self.driver.current_url or ""
            except Exception:
                current_url = ""
            if "/status/" in current_url:
                self.driver.get(f"https://x.com/{target_user}")
                time.sleep(random.uniform(3, 6))
                self._handle_profile_page()
            self._do_comment_like(target_user)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute all pending targets for this SFS session."""
        session_id = self.session["id"]
        account_username = self.account["username"]

        logger.info(
            f"[{account_username}] SFS — Iniciando sessao {session_id} "
            f"'{self.session.get('name', '')}'"
        )
        self._send("sfs_started", session_id=session_id)

        try:
            self._create_browser()

            targets = self.sfs_manager.get_session_targets(session_id)
            pending = [t for t in targets if not t.get("completed")]

            if not pending:
                logger.info(
                    f"[{account_username}] SFS — Sessao {session_id} ja concluida (sem pendentes)"
                )
                self.sfs_manager.update_status(session_id, "completed")
                self._send("sfs_completed", session_id=session_id, total=len(targets))
                return

            total = len(targets)
            completed_count = total - len(pending)

            self._send(
                "sfs_progress",
                session_id=session_id,
                completed=completed_count,
                total=total,
            )

            for i, target in enumerate(pending):
                if not self.should_continue():
                    logger.info(
                        f"[{account_username}] SFS — Sessao {session_id} parada/cancelada"
                    )
                    break

                try:
                    self._process_target(target)
                except Exception as exc:
                    logger.error(
                        f"[{account_username}] SFS — Erro ao processar alvo "
                        f"@{target.get('username', '?')}: {exc}\n"
                        f"{traceback.format_exc()}"
                    )
                    self._log_activity(
                        "sistema", "failed",
                        target_username=target.get("username"),
                        error_message=f"SFS erro alvo: {exc}",
                    )

                # Mark target completed even on partial/failed actions.
                # Prevents re-processing on restart which could cause duplicate actions.
                self.sfs_manager.mark_target_completed(session_id, target["id"])
                completed_count += 1

                self._send(
                    "sfs_progress",
                    session_id=session_id,
                    completed=completed_count,
                    total=total,
                )

                logger.info(
                    f"[{account_username}] SFS — Alvo {completed_count}/{total} concluido "
                    f"(@{target.get('username', '?')})"
                )

                # Pace delay before the next target (skip after last)
                if i < len(pending) - 1 and not self.is_stopped():
                    self._pace_delay()

            # Determine final status
            if self.is_stopped():
                # Stopped before finishing — keep current DB status (idle/paused)
                pass
            else:
                self.sfs_manager.update_status(session_id, "completed")
                self._send(
                    "sfs_completed", session_id=session_id, total=total
                )
                logger.info(
                    f"[{account_username}] SFS — Sessao {session_id} concluida "
                    f"({completed_count}/{total} alvos)"
                )

        except Exception as exc:
            logger.error(
                f"[{account_username}] SFS — Erro fatal na sessao {session_id}: {exc}\n"
                f"{traceback.format_exc()}"
            )
            self._log_activity(
                "sistema", "failed",
                error_message=f"SFS erro fatal: {exc}",
            )
            if not self._superseded:
                self.sfs_manager.update_status(session_id, "error")
            self._send("sfs_error", session_id=session_id, error=str(exc))

        finally:
            self._close_browser()
