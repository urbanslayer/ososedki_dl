"""Base crawler for ososedki and clone sites."""

from __future__ import annotations

import asyncio
import re
from abc import ABC
from itertools import chain
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag
from core_helpers.logs import logger
from rich import print
from typing_extensions import override

from ..consts import DEFAULT_ALBUM_TITLE, DEFAULT_PAGINATION_SIZE
from .base_crawler import BaseCrawler

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from typing import TypedDict
    from urllib.parse import ParseResult

    class PayloadType(TypedDict):
        album_id: str
        owner_id: str
        download: int
        download_id: int
        offset: int
        limit: int


class OsosedkiBaseCrawler(BaseCrawler, ABC):
    """Base class for crawlers of ososedki and clone sites."""

    album_path: str
    model_url: str | None = None
    cosplay_url: str | None = None
    fandom_url: str | None = None
    button_class: str | None = None
    pagination: bool

    def _resolve_media_href(self, href: str | None) -> str | None:
        """
        Resolves an anchor's href (which may be relative or absolute) against
        the site URL and returns it only if it points at the site's media host.

        Args:
            href (str | None): The raw href attribute value, or None if the
                tag has no href.

        Returns:
            str | None: The absolute media URL, or None if `href` is missing
                or doesn't point at `base_media_url`.
        """
        if not href:
            return None
        full_href: str = urljoin(self.site_url, href)
        return full_href if self.base_media_url in full_href else None

    @staticmethod
    def _url_matches_section(url: str, section: str | None) -> bool:
        """
        Checks whether `url` falls under a configured site section (e.g.
        `album_path`, `model_url`), comparing parsed URL paths rather than
        raw string prefixes.

        `section` may be a bare path (e.g. "/photos/") or a full URL (e.g.
        "https://ososedki.com/model/"); either way, only the path component
        is compared, so scheme (http/https), host (www vs. no-www, or a
        historical domain alias), and a missing trailing slash on `section`
        don't cause a false negative.

        Args:
            url (str): The URL to check.
            section (str | None): The section path or URL to match against,
                or None if this crawler doesn't support that section.

        Returns:
            bool: True if `url`'s path starts with `section`'s path.
        """
        if not section:
            return False

        section_path: str = urlparse(section).path
        if not section_path.endswith("/"):
            section_path += "/"

        return urlparse(url).path.startswith(section_path)

    def _get_article_title(self, soup: BeautifulSoup) -> str:
        logger.debug("Extracting article title from soup")

        tags: set[str] = {
            "leak",
            "leaked",
            "leaks",
            "nude",
            "nudes",
            "of",
            "onlyfans for",
            "onlyfans leak",
            "reddit",
            "twitter",
            "video",
            "vk",
            "xxx",
            "onlyfan",
            "onlyfanfor",
        }

        # Get the page article:tag and extract the title
        article_tags: list[Tag] = soup.find_all("meta", {"property": "article:tag"})
        for article_tag in article_tags:
            tag_content: str = article_tag.get("content", "")
            for tag in tags:
                tag_suffix: str = f" {tag.lower()}"
                if tag_content.lower().endswith(tag_suffix):
                    logger.info(f"Found article tag: {tag_content}")
                    return tag_content.replace(tag_suffix, "")

        logger.warning(
            f"No suitable article tag found in the soup for {self.__class__.__name__}"
        )
        return DEFAULT_ALBUM_TITLE

    @override
    def get_album_title(self, soup: BeautifulSoup, url: str) -> str:
        """
        Extracts the title of an album or model page from the provided
        BeautifulSoup object.

        Attempts to find a title by checking for an anchor tag with a specific
        button class, parsing the "title" tag for known patterns, or falling
        back to meta tags. Returns `DEFAULT_ALBUM_TITLE` if no suitable title is
        found.

        Args:
            soup (BeautifulSoup): The parsed HTML content of the page.
            url (str): The URL of the page being processed (not used in this
                method).

        Returns:
            str: The extracted title of the album or model, or
                `DEFAULT_ALBUM_TITLE` if no title could be extracted.
        """
        logger.debug("Extracting title from soup")

        if self.button_class:
            button_html: Tag | NavigableString | None = soup.find(
                "a", class_=self.button_class
            )
            if button_html:
                logger.info(f"Found button with class '{self.button_class}'")
                print(f"Found button: {button_html.text}")
                return button_html.text

        text_div: Tag | NavigableString | None = soup.find("title")
        if not text_div:
            logger.warning(
                f"No title tag found in the soup for {self.__class__.__name__}"
            )
            return DEFAULT_ALBUM_TITLE

        text: str = text_div.text.strip()
        title: str = DEFAULT_ALBUM_TITLE

        try:
            if " (@" in text:
                title = text.split(" (@")[0].strip()
            elif re.search(r" - [0-9]*\s", text):
                title = text.split(" - ")[0].strip()
        except IndexError:
            logger.error(f"Failed to extract title from '{text}'")
            print(f"ERROR: Failed to extract title from '{text}'")

        if title == DEFAULT_ALBUM_TITLE:
            title = self._get_article_title(soup)

        logger.info(f"Extracted title: {title}")
        return title

    def get_set_title(self, soup: BeautifulSoup, url: str) -> str | None:
        """
        Extracts the "set" an album belongs to, i.e. the specific
        cosplay character or fandom a subject's album is grouped under, so
        that albums for the same character don't get mixed together under a
        single subject folder.

        Looks for a structural link on the album page pointing at
        `cosplay_url` first, falling back to `fandom_url`, rather than
        string-splitting the page title: the site tags each album with
        dedicated buttons/badges linking to those sections, and that holds up
        across albums (including ones with no set at all) better than parsing
        free-form text.

        Args:
            soup (BeautifulSoup): The parsed HTML content of the album page.
            url (str): The URL of the album page being processed (not used in
                this method).

        Returns:
            str | None: The extracted set name, or None if the album page
                doesn't link to a cosplay or fandom section.
        """
        logger.debug("Extracting set title from soup")

        for attr_name in ("cosplay_url", "fandom_url"):
            base_url: str | None = getattr(self, attr_name, None)
            if not base_url:
                continue

            path: str = urlparse(base_url).path
            if not path or "{" in path:
                # Not a real, matchable URL path (e.g. a template placeholder)
                continue

            anchor: Tag | NavigableString | None = soup.find(
                "a", href=lambda href: href and href.startswith(path)
            )
            if not anchor or isinstance(anchor, NavigableString):
                continue

            text: str = anchor.get_text(strip=True)
            if text:
                logger.info(f"Extracted set title: {text}")
                return text

        logger.debug("No set title found in soup")
        return None

    def _get_album_id(self, url: str) -> str:
        """
        Derives a stable fallback identifier for an album from its URL, for
        use as a folder name when no set could be determined.

        Args:
            url (str): The album URL.

        Returns:
            str: The album id, e.g. "10015936" for
                ".../photos/-10000001_10015936".
        """
        segment: str = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        if "_" in segment:
            segment = segment.rsplit("_", 1)[-1]
        return segment or "unknown"

    @override
    def get_album_path_parts(
        self, soup: BeautifulSoup, url: str, title: str
    ) -> tuple[str, ...]:
        """
        Nests each album under `<subject>/<set>`, so albums for different
        cosplay characters/fandoms never mix under the same subject folder.
        Falls back to `<subject>/<album id>` when no set can be determined,
        so albums without one still get their own folder instead of dumping
        files loose into the subject folder.
        """
        set_title: str | None = self.get_set_title(soup, url)
        return (title, set_title or self._get_album_id(url))

    async def _extract_paginated_images(
        self,
        owner_id: str,
        album_id: str,
        pagination_size: int = DEFAULT_PAGINATION_SIZE,
    ) -> list[str]:
        """
        Asynchronously retrieves all image URLs from a paginated album using
        the site's API.

        Args:
            owner_id (str): The owner ID of the album.
            album_id (str): The album ID to fetch images from.
            pagination_size (int): Number of images to fetch per request. Defaults to
                DEFAULT_PAGINATION_SIZE.

        Returns:
            list[str]: A list of image URLs extracted from all pages of the
                album.
        """
        logger.debug(
            f"Extracting paginated images for owner_id: {owner_id}, album_id: {album_id}"
        )

        images: list[str] = []
        url: str = self.site_url + "/cms/load-more-photos.php"

        payload: PayloadType = {
            "album_id": album_id,
            "owner_id": owner_id,
            "download": 1,
            "download_id": 0,
            "offset": 0,
            "limit": pagination_size,
        }

        while True:
            try:
                data = await self.downloader.fetch(
                    url, "POST", response_property="json", json=payload
                )
            except Exception as e:
                logger.error(f"Failed to fetch paginated images: {e}")
                print(f"ERROR: Failed to fetch paginated images: {e}")
                break
            photos: list[dict[str, str]] = data["photos"]
            if not photos:
                break

            logger.info(f"Fetched {len(photos)} photos from offset {payload['offset']}")
            for photo in photos:
                soup = BeautifulSoup(photo["html"], "html.parser")
                resolved_href: str | None = None
                for anchor in soup.find_all("a", href=True):
                    href: str | list[str] = anchor["href"]
                    if isinstance(href, list):
                        href = href[0]
                    resolved_href = self._resolve_media_href(href)
                    if resolved_href:
                        break
                if not resolved_href:
                    continue
                logger.debug(f"Found image URL: {resolved_href}")
                images.append(resolved_href)

            if len(photos) < pagination_size:
                break

            payload["offset"] += pagination_size

        return images

    def _extract_album_info(self, soup: BeautifulSoup) -> tuple[str, str]:
        """
        Extracts the owner ID and album ID from the provided BeautifulSoup
        object.

        Attempts to locate these IDs by first searching for a preload link tag
        with rel="preload" and as="image", extracting the relevant path
        segments from its href. If not found, it falls back to parsing the
        content of the og:image meta tag. Returns empty strings if neither
        method yields valid IDs.

        Args:
            soup (BeautifulSoup): The parsed HTML content of the album page.

        Returns:
            tuple[str, str]: A tuple containing the owner ID and album ID, or
            empty strings if not found.
        """
        logger.debug("Extracting album info from soup")

        preload: Tag | NavigableString | None = soup.find(
            "link", {"rel": "preload", "as": "image"}
        )
        if preload and isinstance(preload, Tag):
            href: str | list[str] = preload.get("href", "")
            if isinstance(href, list):
                href = href[0]
            if href:
                parts: list[str] = href.split("/")[-3:-1]
                owner_id, album_id = parts[0], parts[1]
                logger.info(
                    f"Extracted album info from preload: owner_id={owner_id}, album_id={album_id}"
                )
                return owner_id, album_id

        og_image: Tag | NavigableString | None = soup.find(
            "meta", {"property": "og:image"}
        )
        if og_image and isinstance(og_image, Tag):
            content: str | list[str] = og_image.get("content", "")
            if isinstance(content, list):
                content = content[0]
            if content:
                parts = content.split("/")
                owner_id, album_id = parts[-2], parts[-1].split(".")[0]
                logger.info(
                    f"Extracted album info from og:image: owner_id={owner_id}, album_id={album_id}"
                )
                return owner_id, album_id

        logger.error("Failed to extract album info from soup")
        return "", ""

    @override
    async def get_media_urls(self, soup: BeautifulSoup, url: str) -> list[str]:
        """
        Asynchronously extracts all media (image) URLs from an album or page.

        If pagination is enabled, retrieves images using paginated API requests
        based on album and owner IDs extracted from the page. Otherwise,
        collects image URLs from anchor tags referencing the base media URL,
        or, if none are found, from links starting with "https://sun". Cleans
        and normalizes URLs as needed.

        Args:
            soup (BeautifulSoup): The parsed HTML content of the album or page.
            url (str): The URL of the album or page being processed (not used
                in this method).

        Returns:
            list[str]: List of extracted image URLs.
        """
        logger.debug("Extracting media from soup")

        if self.pagination:
            owner_id, album_id = self._extract_album_info(soup)
            if not owner_id or not album_id:
                logger.error("Failed to find album information in the page.")
                print("ERROR: Failed to find album information in the page.")
                return []

            return await self._extract_paginated_images(owner_id, album_id)

        # ? If images under a tag return 404, use tag img and get src
        images: list[str] = []
        for tag in soup.find_all("a", href=True):
            resolved_href: str | None = self._resolve_media_href(tag.get("href"))
            if resolved_href:
                images.append(resolved_href.replace("/604/", "/1280/"))
        if images:
            logger.info(f"Found {len(images)} images in the soup")
            return images

        logger.warning("No images found in the soup, searching for alternative sources")
        # ? If no images are found, search for "https://sun9-" in img_url
        for tag in soup.find_all(
            "a", href=lambda href: href and href.startswith("https://sun")  # type: ignore
        ):
            href: str = tag.get("href")
            logger.info(f"Found sun9 image before cleanup: {href}")
            print(f"Found sun9 image: {href}")
            parsed_url: ParseResult = urlparse(href)
            query: dict[str, list[str]] = parse_qs(
                parsed_url.query, keep_blank_values=True
            )
            query.pop("cs", None)
            u: ParseResult = parsed_url._replace(query=urlencode(query, True))
            images.append(u.geturl())

        logger.info(f"Found {len(images)} images after alternative search")
        return images

    async def _find_albums(self, url: str) -> AsyncGenerator[list[str], None]:
        """
        Asynchronously iterates through paginated pages to yield the discovered
        album URLs.

        This method is designed to handle model or cosplay pages that list
        multiple albums, fetching each page incrementally to avoid overwhelming
        the server and to allow for real-time processing of found albums.

        Args:
            url (str): The URL of the model page to start from.

        Yields:
            list[str]: A list of album URLs found on the current page.
        """
        logger.debug(f"Finding albums for URL: {url}")

        if not self.album_path:
            logger.warning(
                f"Album path is not set for {self.__class__.__name__}. Skipping album fetch."
            )
            return

        # Clean the URL removing the query parameters
        url = url.split("?")[0]

        soup: BeautifulSoup = await self.fetch_soup(url)

        i = 1
        albums_found = True

        while albums_found:
            page_url: str = f"{url}?page={i}"
            logger.debug("Fetching albums from page %s", page_url)

            soup: BeautifulSoup = await self.fetch_soup(page_url)

            logger.debug(f"Extracting albums from soup for {self.__class__.__name__}")
            albums_extracted: list[str] = list(
                {
                    f"{self.site_url}{a['href']}"
                    for a in soup.find_all(
                        "a", href=lambda href: href and href.startswith(self.album_path)
                    )
                }
            )
            if not albums_extracted:
                albums_found = False
                continue

            logger.info(f"Found {len(albums_extracted)} albums on page {page_url}")
            yield albums_extracted
            i += 1

            # Sleep for a while to avoid being banned
            await asyncio.sleep(1)

        title: str = self.get_album_title(soup, url)
        logger.debug(f"Finished finding albums for: {title}")

    @override
    async def download(self, url: str) -> list[dict[str, str]]:
        """
        Download and extract media and metadata from a given album, model or
        cosplay URL.

        If the URL corresponds to an album, processes and returns its media and
        metadata. If the URL matches a model or cosplay section, finds all
        associated albums and processes them concurrently, aggregating their
        results. Returns an empty list for unknown URL formats.

        Args:
            url (str): The album, model, or cosplay URL to process.

        Returns:
            list[dict[str, str]]: A list of dictionaries containing media URLs
            and associated metadata.
        """
        logger.debug(f"Downloading from URL {url} using {self.__class__.__name__}")

        if self._url_matches_section(url, self.album_path):
            logger.info(f"Downloading album from {url}")
            return await self.process_album(url)
        elif (
            self._url_matches_section(url, self.model_url)
            or self._url_matches_section(url, self.cosplay_url)
            or self._url_matches_section(url, self.fandom_url)
        ):
            logger.info(f"Downloading albums from {url}")
            results: list[dict[str, str]] = []

            # Find all the albums incrementally
            async for albums in self._find_albums(url):
                logger.info(f"Processing {len(albums)} albums concurrently")
                tasks = [self.process_album(album) for album in albums]

                # Process the tasks for this chunk and collect results
                chunk_results: list[dict[str, str]] = list(
                    chain.from_iterable(await asyncio.gather(*tasks))
                )
                results.extend(chunk_results)

            return results

        logger.error(f"Unknown URL format: {url}")
        print(f"ERROR: Unknown URL format: {url}")
        return []
