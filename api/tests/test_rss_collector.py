from datetime import datetime

from app.infrastructure.ingestion.rss import parse_rss_items


def test_parse_rss_items_reads_basic_fields() -> None:
    xml = """
    <rss>
      <channel>
        <item>
          <title>New AI model</title>
          <link>https://example.com/news?id=1#section</link>
          <guid>item-1</guid>
          <author>Example Author</author>
          <pubDate>Wed, 02 Sep 2026 08:30:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    items = parse_rss_items(xml, since=None)

    assert len(items) == 1
    assert items[0].external_id == "item-1"
    assert items[0].title == "New AI model"
    assert items[0].url == "https://example.com/news?id=1#section"
    assert items[0].canonical_url == "https://example.com/news?id=1"
    assert items[0].author == "Example Author"
    assert items[0].published_at is not None


def test_parse_rss_items_filters_items_before_since() -> None:
    xml = """
    <rss>
      <channel>
        <item>
          <title>Old AI news</title>
          <link>https://example.com/old</link>
          <pubDate>Tue, 01 Sep 2026 08:30:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    items = parse_rss_items(xml, since=datetime.fromisoformat("2026-09-02T00:00:00+00:00"))

    assert items == []


def test_parse_rss_items_reads_atom_namespace_fields() -> None:
    xml = """
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Atom AI update</title>
        <id>tag:example.com,2026:atom-1</id>
        <link href="https://example.com/atom#comments" />
        <updated>2026-09-02T08:30:00+00:00</updated>
        <author><name>Atom Author</name></author>
      </entry>
    </feed>
    """

    items = parse_rss_items(xml, since=None)

    assert len(items) == 1
    assert items[0].external_id == "tag:example.com,2026:atom-1"
    assert items[0].title == "Atom AI update"
    assert items[0].canonical_url == "https://example.com/atom"
    assert items[0].author == "Atom Author"
