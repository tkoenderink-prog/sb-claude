"""ICS Downloader - Download and cache ICS calendar feeds with async support."""
import asyncio
import time
from pathlib import Path
from typing import Optional
import logging

import requests

logger = logging.getLogger(__name__)


class ICSDownloader:
    """Downloads ICS calendar files with caching support (async wrapper)."""

    def __init__(self, cache_dir: Path | str, ttl_seconds: int = 3600):
        """
        Initialize downloader with cache settings.

        Args:
            cache_dir: Path to cache directory
            ttl_seconds: Cache TTL in seconds (default 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ICSDownloader initialized with cache_dir={self.cache_dir}, ttl={ttl_seconds}s")

    async def download(self, url: str, calendar_name: str) -> str:
        """
        Download ICS content from URL, use cache if fresh (async).

        Args:
            url: ICS feed URL
            calendar_name: Name for cache filename

        Returns:
            ICS content as string

        Raises:
            requests.RequestException: On download failure
        """
        cache_path = self._get_cache_path(calendar_name)

        # Check if cache exists and is fresh
        if cache_path.exists() and self._is_cache_fresh(cache_path):
            logger.info(f"Using cached ICS for {calendar_name}")
            return cache_path.read_text(encoding='utf-8')

        # Download fresh content with retries (run in thread pool to avoid blocking)
        logger.info(f"Downloading fresh ICS for {calendar_name}...")

        # Run blocking requests in thread pool
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            self._download_sync,
            url,
            calendar_name,
            cache_path
        )

        return content

    def _download_sync(self, url: str, calendar_name: str, cache_path: Path) -> str:
        """
        Synchronous download implementation with retry logic.

        Args:
            url: ICS feed URL
            calendar_name: Calendar name for logging
            cache_path: Path to cache file

        Returns:
            Downloaded ICS content

        Raises:
            requests.RequestException: On final failure
        """
        max_retries = 3
        timeout = 60  # Increased timeout for slow servers (Outlook)

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                content = response.text

                # Save to cache
                self._save_to_cache(content, cache_path)

                logger.info(f"Downloaded {len(content)} bytes for {calendar_name}")
                return content

            except requests.Timeout as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries} for {calendar_name}, retrying...")
                    time.sleep(2)  # Wait before retry
                    continue
                else:
                    # Final timeout - try cache
                    if cache_path.exists():
                        logger.warning(f"All download attempts timed out for {calendar_name}, using stale cache")
                        return cache_path.read_text(encoding='utf-8')
                    else:
                        logger.error(f"Download failed and no cache available for {calendar_name}")
                        raise

            except requests.RequestException as e:
                # If download fails but cache exists, use stale cache
                if cache_path.exists():
                    logger.warning(f"Download failed ({type(e).__name__}) for {calendar_name}, using stale cache")
                    return cache_path.read_text(encoding='utf-8')
                else:
                    logger.error(f"Download failed and no cache available for {calendar_name}: {e}")
                    raise

    def _get_cache_path(self, calendar_name: str) -> Path:
        """Get cache file path for calendar."""
        # Sanitize calendar name for filename
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_'
                           for c in calendar_name)
        return self.cache_dir / f"{safe_name}.ics"

    def _is_cache_fresh(self, cache_path: Path) -> bool:
        """Check if cache file is within TTL."""
        if not cache_path.exists():
            return False

        age_seconds = time.time() - cache_path.stat().st_mtime
        is_fresh = age_seconds < self.ttl_seconds

        if not is_fresh:
            logger.debug(f"Cache is stale: {int(age_seconds)}s old (TTL: {self.ttl_seconds}s)")

        return is_fresh

    def _save_to_cache(self, content: str, cache_path: Path):
        """Save ICS content to cache file."""
        cache_path.write_text(content, encoding='utf-8')
        logger.debug(f"Saved to cache: {cache_path}")

    def clear_cache(self, calendar_name: Optional[str] = None):
        """
        Clear cache for specific calendar or all calendars.

        Args:
            calendar_name: Calendar to clear, or None for all
        """
        if calendar_name:
            cache_path = self._get_cache_path(calendar_name)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache for {calendar_name}")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.ics"):
                cache_file.unlink()
            logger.info("Cleared all cache files")

    def get_cache_age(self, calendar_name: str) -> Optional[int]:
        """
        Get age of cached file in seconds.

        Args:
            calendar_name: Calendar name

        Returns:
            Age in seconds, or None if not cached
        """
        cache_path = self._get_cache_path(calendar_name)
        if not cache_path.exists():
            return None

        return int(time.time() - cache_path.stat().st_mtime)
