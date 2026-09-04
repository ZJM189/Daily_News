from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from app.application.ingestion.collectors import Collector
from app.application.ingestion.dtos import CollectableSourceDTO, RawCollectedItem
from app.infrastructure.ingestion.url_safety import ensure_public_http_url


class RSSCollector(Collector):
    source_type = "rss"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        source: CollectableSourceDTO,
        *,
        since: datetime | None,
    ) -> list[RawCollectedItem]:
        if not source.url:
            raise ValueError("rss source url is required")
        ensure_public_http_url(source.url)
        response = httpx.get(
            source.url,
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "DailyNewsBot/0.1"},
        )
        response.raise_for_status()
        return parse_rss_items(response.text, since=since)


def parse_rss_items(xml_text: str, *, since: datetime | None) -> list[RawCollectedItem]:
    root = ElementTree.fromstring(xml_text)
    entries = root.findall(".//item")
    if not entries:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    items: list[RawCollectedItem] = []
    for entry in entries:
        item = _parse_entry(entry)
        if item is None:
            continue
        if since is not None and item.published_at is not None and item.published_at < since:
            continue
        items.append(item)
    return items


def _parse_entry(entry: ElementTree.Element) -> RawCollectedItem | None:
    title = _first_text(entry, "title", "{http://www.w3.org/2005/Atom}title")
    link = _link(entry)
    if not title or not link:
        return None

    published_at = _parse_datetime(
        _first_text(
            entry,
            "pubDate",
            "published",
            "updated",
            "{http://www.w3.org/2005/Atom}published",
            "{http://www.w3.org/2005/Atom}updated",
        )
    )
    payload = _entry_payload(entry)
    external_id = (
        _first_text(entry, "guid", "id", "{http://www.w3.org/2005/Atom}id")
        or link
    )

    return RawCollectedItem(
        external_id=external_id[:255] if external_id else None,
        url=link,
        canonical_url=_canonical_url(link),
        title=title,
        author=_first_text(
            entry,
            "author",
            "creator",
            "{http://purl.org/dc/elements/1.1/}creator",
            "{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name",
        ),
        published_at=published_at,
        raw_payload=payload,
    )


def _first_text(entry: ElementTree.Element, *tags: str) -> str | None:
    for tag in tags:
        value = _text(entry, tag)
        if value:
            return value
    return None


def _text(entry: ElementTree.Element, tag: str) -> str | None:
    element = entry.find(tag)
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _link(entry: ElementTree.Element) -> str | None:
    link = _text(entry, "link")
    if link:
        return link
    atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
    if atom_link is None:
        return None
    href = atom_link.attrib.get("href")
    return href.strip() if href else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


def _entry_payload(entry: ElementTree.Element) -> dict[str, Any]:
    payload: dict[str, Any] = {"tag": _strip_namespace(entry.tag), "children": {}}
    for child in list(entry):
        key = _strip_namespace(child.tag)
        payload["children"][key] = {
            "text": child.text.strip() if child.text else None,
            "attributes": dict(child.attrib),
        }
    return payload


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
