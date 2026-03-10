# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import os
import random
import logging
import time
from collections import defaultdict
from urllib.parse import urlparse

from scrapy import signals
from itemadapter import ItemAdapter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rotating User-Agent Middleware (TopCV & other spiders)
# ---------------------------------------------------------------------------
_TOPCV_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


class RotatingUserAgentMiddleware:
    """
    Rotate User-Agent per request for spiders that set `rotate_user_agent = True`.
    Also injects a realistic Referer header based on domain.
    """

    def process_request(self, request, spider):
        if not getattr(spider, 'rotate_user_agent', False):
            return None

        ua = random.choice(_TOPCV_USER_AGENTS)
        request.headers['User-Agent'] = ua

        # Inject Referer if not already set
        if not request.headers.get('Referer'):
            referer = getattr(spider, 'referer_base', None)
            if referer:
                request.headers['Referer'] = referer

        return None


# ---------------------------------------------------------------------------
# Proxy Rotation Middleware
# ---------------------------------------------------------------------------
class ProxyRotationMiddleware:
    """
    Rotate proxies from a text file for spiders that set `use_proxy = True`.

    Proxy file format (one per line):
        http://ip:port
        https://ip:port
        http://user:pass@ip:port

    Configure via:
        - PROXY_LIST_FILE setting or env var PROXY_LIST_FILE
        - Default: proxies.txt in project root

    If no proxy file exists or is empty, the middleware is silently skipped.
    """

    def __init__(self, proxy_list):
        self.proxies = proxy_list
        self._index = 0
        self._blacklisted = set()

    @classmethod
    def from_crawler(cls, crawler):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        proxy_file = (
            crawler.settings.get('PROXY_LIST_FILE')
            or os.getenv('PROXY_LIST_FILE')
            or os.path.join(base_dir, 'proxies.txt')
        )

        proxies = []
        if os.path.isfile(proxy_file):
            with open(proxy_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)
            if proxies:
                logger.info(f"ProxyRotationMiddleware: Loaded {len(proxies)} proxies from {proxy_file}")
            else:
                logger.info(f"ProxyRotationMiddleware: Proxy file {proxy_file} is empty, running without proxies")
        else:
            logger.info(f"ProxyRotationMiddleware: No proxy file found at {proxy_file}, running without proxies")

        return cls(proxies)

    def _get_next_proxy(self):
        """Get the next non-blacklisted proxy (round-robin)."""
        if not self.proxies:
            return None

        available = [p for p in self.proxies if p not in self._blacklisted]
        if not available:
            # All proxies blacklisted → reset and try again
            logger.warning("ProxyRotationMiddleware: All proxies blacklisted, resetting blacklist")
            self._blacklisted.clear()
            available = self.proxies

        self._index = self._index % len(available)
        proxy = available[self._index]
        self._index += 1
        return proxy

    def process_request(self, request, spider):
        if not getattr(spider, 'use_proxy', False):
            return None
        if not self.proxies:
            return None

        proxy = self._get_next_proxy()
        if proxy:
            request.meta['proxy'] = proxy
            
            # --- Playwright Proxy Support ---
            if getattr(spider, 'use_playwright', False) or request.meta.get('playwright', False):
                import urllib.parse
                parsed = urllib.parse.urlparse(proxy)
                pw_proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
                if parsed.username:
                    pw_proxy["username"] = urllib.parse.unquote(parsed.username)
                if parsed.password:
                    pw_proxy["password"] = urllib.parse.unquote(parsed.password)
                
                ctx_kwargs = request.meta.get('playwright_context_kwargs', {})
                ctx_kwargs['proxy'] = pw_proxy
                request.meta['playwright_context_kwargs'] = ctx_kwargs

                # Ensure Playwright context is unique per proxy
                import hashlib
                proxy_hash = hashlib.md5(proxy.encode()).hexdigest()[:6]
                if 'playwright_context' in request.meta:
                    base_ctx = request.meta['playwright_context'].split('_proxy_')[0]
                    request.meta['playwright_context'] = f"{base_ctx}_proxy_{proxy_hash}"
                else:
                    request.meta['playwright_context'] = f"default_proxy_{proxy_hash}"

            spider.logger.debug(f"Using proxy: {proxy} for {request.url}")
        return None

    def process_response(self, request, response, spider):
        if response.status == 403 and 'proxy' in request.meta:
            proxy = request.meta['proxy']
            self._blacklisted.add(proxy)
            spider.logger.warning(
                f"ProxyRotationMiddleware: Blacklisted proxy {proxy} after 403"
            )
            
            # If Playwright is used, we might want to close the blocked context
            if request.meta.get('playwright') and 'playwright_context' in request.meta:
                spider.logger.warning(f"Note: Playwright context {request.meta['playwright_context']} is now poisoned (403).")
                
        return response


# ---------------------------------------------------------------------------
# Rate-limit exponential backoff middleware (handles 429 AND 403)
# ---------------------------------------------------------------------------
class RateLimitBackoffMiddleware:
    """
    Handles 429 and 403 responses, plus DNS failures, with exponential
    backoff + jitter.  Only active for spiders that set
    `rate_limit_backoff = True`.

    For 429: standard backoff (BASE_WAIT=90s).
    For 403: aggressive backoff when consecutive 403s are detected.

    Backoff schedule (BASE_WAIT=90s, jitter ±30%):
      retry 1 → ~90s,  retry 2 → ~180s,  retry 3 → ~360s,
      retry 4 → ~600s,  retry 5 → ~600s  (capped)

    403 consecutive pause schedule (BASE_403_WAIT=120s):
      1-2 consecutive 403s → per-request retry with 120s base
      3+ consecutive 403s  → long pause 180–600s before retry
    """

    MAX_RETRIES     = 5
    BASE_WAIT       = 90     # seconds for 429 backoff
    BASE_403_WAIT   = 120    # seconds for 403 backoff (longer than 429)
    MAX_WAIT        = 600    # seconds cap
    JITTER          = 0.30   # ±30% random jitter

    # After this many consecutive 403s, apply extra-long pause
    CONSECUTIVE_403_THRESHOLD = 3

    def __init__(self):
        # Track consecutive 403 counts per domain
        self._consecutive_403 = defaultdict(int)

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def _get_domain(self, url):
        """Extract domain from URL for per-domain tracking."""
        return urlparse(url).netloc

    def _schedule_retry(self, request, retry_count, reason, spider, base_wait=None):
        """Compute wait with jitter and schedule retry via Twisted."""
        from twisted.internet import defer, reactor

        base_wait = base_wait or self.BASE_WAIT
        base = min(base_wait * (2 ** retry_count), self.MAX_WAIT)
        jitter = base * self.JITTER * (2 * random.random() - 1)  # ±JITTER
        wait = max(30, round(base + jitter))

        spider.logger.warning(
            f"{reason} → backing off {wait}s "
            f"(retry {retry_count + 1}/{self.MAX_RETRIES}): {request.url}"
        )

        new_req = request.copy()
        new_req.meta['_rl_retry'] = retry_count + 1
        new_req.dont_filter = True

        d = defer.Deferred()
        reactor.callLater(wait, d.callback, new_req)
        return d

    def process_response(self, request, response, spider):
        if not getattr(spider, 'rate_limit_backoff', False):
            return response

        domain = self._get_domain(request.url)

        # ── Handle success: reset 403 counter ──
        if response.status == 200:
            if self._consecutive_403[domain] > 0:
                spider.logger.info(
                    f"403 streak broken (was {self._consecutive_403[domain]}) "
                    f"— got 200 for {domain}"
                )
                self._consecutive_403[domain] = 0
            return response

        # ── Handle 429 ──
        if response.status == 429:
            retry_count = request.meta.get('_rl_retry', 0)
            if retry_count >= self.MAX_RETRIES:
                spider.logger.error(
                    f"429 after {self.MAX_RETRIES} retries, giving up: {request.url}"
                )
                return response

            return self._schedule_retry(
                request, retry_count, "429 rate limited", spider
            )

        # ── Handle 403 (anti-bot block) ──
        if response.status == 403:
            self._consecutive_403[domain] += 1
            streak = self._consecutive_403[domain]
            retry_count = request.meta.get('_rl_retry', 0)

            if retry_count >= self.MAX_RETRIES:
                spider.logger.error(
                    f"403 after {self.MAX_RETRIES} retries "
                    f"(streak={streak}), giving up: {request.url}"
                )
                return response

            # Determine base wait time based on consecutive streak
            if streak >= self.CONSECUTIVE_403_THRESHOLD:
                # Long pause: scale with streak severity
                base_wait = min(
                    self.BASE_403_WAIT * (streak - self.CONSECUTIVE_403_THRESHOLD + 2),
                    self.MAX_WAIT
                )
                spider.logger.warning(
                    f"🚨 {streak} consecutive 403s on {domain} "
                    f"— applying extended backoff (base={base_wait}s)"
                )
            else:
                base_wait = self.BASE_403_WAIT

            return self._schedule_retry(
                request, retry_count,
                f"403 blocked (streak={streak})",
                spider, base_wait=base_wait
            )

        return response

    def process_exception(self, request, exception, spider):
        """Retry on DNS resolution failures caused by temporary IP blocks."""
        if not getattr(spider, 'rate_limit_backoff', False):
            return None

        exc_str = str(exception)
        dns_errors = (
            'ERR_NAME_NOT_RESOLVED',
            'NAME_NOT_RESOLVED',
            'ConnectionRefusedError',
            'TCPTimedOutError',
        )
        if not any(e in exc_str for e in dns_errors):
            return None

        retry_count = request.meta.get('_rl_retry', 0)
        if retry_count >= self.MAX_RETRIES:
            spider.logger.error(
                f"DNS/connection failure after {self.MAX_RETRIES} retries, "
                f"giving up: {request.url}"
            )
            return None

        return self._schedule_retry(
            request, retry_count,
            f"DNS/connection failure ({exc_str[:60]})",
            spider
        )


# ---------------------------------------------------------------------------
# Spider / Downloader middleware boilerplate
# ---------------------------------------------------------------------------
class SpidersSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # maching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class SpidersDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
