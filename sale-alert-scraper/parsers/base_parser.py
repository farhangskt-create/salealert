import time
import logging
from abc import ABC, abstractmethod
import urllib.request
import urllib.error
import ssl

logger = logging.getLogger("BaseParser")

class BaseParser(ABC):
    def __init__(self, timeout: int = 10, max_retries: int = 3, rate_limit_delay: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = "SaleAlertScraper/1.0 (+https://salealert.pk/bot)"

    def fetch_url_with_details(self, url: str) -> tuple[str | None, str, int]:
        """
        Fetches URL content. Returns tuple of (raw_content, final_redirect_url, http_status_code).
        No fabricated HTTP success defaults: status code is 0 on connection failure or actual HTTP code.
        """
        time.sleep(self.rate_limit_delay)
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        ctx = ssl.create_default_context()

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Fetching HTTP GET (Attempt {attempt}/{self.max_retries}): {url}")
                with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                    status_code = response.status
                    final_url = response.geturl()
                    content_type = response.headers.get("Content-Type", "")
                    charset = "utf-8"
                    if "charset=" in content_type:
                        charset = content_type.split("charset=")[-1].split(";")[0].strip()
                    body = response.read().decode(charset, errors="replace")
                    return body, final_url, status_code
            except urllib.error.HTTPError as e:
                logger.warning(f"HTTPError {e.code} for {url}: {e.reason}")
                return None, url, e.code
            except urllib.error.URLError as e:
                logger.warning(f"URLError for {url}: {e.reason}")
                return None, url, 0
            except Exception as e:
                logger.warning(f"Unexpected error for {url}: {e}")
                return None, url, 0

            if attempt < self.max_retries:
                time.sleep(self.rate_limit_delay * attempt)

        return None, url, 0

    @abstractmethod
    def parse(self, source_config: dict) -> list[dict]:
        pass
