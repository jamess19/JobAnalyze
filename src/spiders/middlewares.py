# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import random
import logging
from scrapy import signals
from itemadapter import ItemAdapter


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
# Rate-limit exponential backoff middleware (handles 429)
# ---------------------------------------------------------------------------
class RateLimitBackoffMiddleware:
    """
    Handles 429 responses and DNS failures (ERR_NAME_NOT_RESOLVED) with
    exponential backoff + jitter.  Only active for spiders that set
    `rate_limit_backoff = True`.

    Backoff schedule (BASE_WAIT=90s, jitter ±25%):
      retry 1 → ~90s,  retry 2 → ~180s,  retry 3 → ~360s,
      retry 4 → ~600s,  retry 5 → ~600s  (capped)
    """

    MAX_RETRIES = 5
    BASE_WAIT   = 90    # seconds (was 60)
    MAX_WAIT    = 600   # seconds cap
    JITTER      = 0.25  # ±25% random jitter

    def _schedule_retry(self, request, retry_count, reason, spider):
        """Compute wait with jitter and schedule retry via Twisted."""
        from twisted.internet import defer, reactor

        base = min(self.BASE_WAIT * (2 ** retry_count), self.MAX_WAIT)
        jitter = base * self.JITTER * (2 * random.random() - 1)  # ±JITTER
        wait = max(30, round(base + jitter))

        spider.logger.warning(
            f"{reason} → backing off {wait}s (retry {retry_count + 1}/{self.MAX_RETRIES}): {request.url}"
        )

        new_req = request.copy()
        new_req.meta['_rl_retry'] = retry_count + 1
        new_req.dont_filter = True

        d = defer.Deferred()
        reactor.callLater(wait, d.callback, new_req)
        return d

    def process_response(self, request, response, spider):
        if response.status != 429:
            return response
        if not getattr(spider, 'rate_limit_backoff', False):
            return response

        retry_count = request.meta.get('_rl_retry', 0)
        if retry_count >= self.MAX_RETRIES:
            spider.logger.error(
                f"429 after {self.MAX_RETRIES} retries, giving up: {request.url}"
            )
            return response

        return self._schedule_retry(request, retry_count, "429 rate limited", spider)

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
                f"DNS/connection failure after {self.MAX_RETRIES} retries, giving up: {request.url}"
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
