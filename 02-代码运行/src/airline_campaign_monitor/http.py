from __future__ import annotations

import requests
from curl_cffi import requests as browser_requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36 "
    "airline-campaign-monitor/0.1"
)


class HttpClient:
    def __init__(self, timeout: tuple[float, float] = (10.0, 30.0)) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7,ja;q=0.5",
            }
        )

    def get_text(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code == 403:
            # JAL and Scoot reject the TLS fingerprint used by urllib3 even
            # with a normal UA. curl_cffi remains plain HTTP (no browser
            # automation) while matching a current Chrome TLS fingerprint.
            response = browser_requests.get(
                url,
                headers=dict(self.session.headers),
                impersonate="chrome",
                timeout=max(self.timeout),
            )
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            # Airline pages are modern UTF-8 sites; apparent_encoding often
            # misidentifies short Chinese/Japanese pages as a legacy codepage.
            response.encoding = "utf-8"
        return response.text

    def post_json(self, url: str, payload: dict) -> dict:
        response = self.session.post(url, json=payload, timeout=self.timeout)
        if response.status_code == 403:
            response = browser_requests.post(
                url,
                json=payload,
                headers=dict(self.session.headers),
                impersonate="chrome",
                timeout=max(self.timeout),
            )
        response.raise_for_status()
        return response.json()
