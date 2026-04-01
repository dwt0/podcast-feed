#!/usr/bin/env python3
"""Generate a Podcast RSS 2.0 feed from episode sidecar JSON files."""

import glob
import html
import json
import os
import re
from xml.dom import minidom
import xml.etree.ElementTree as ET


FEED_URL = "https://dwt0.github.io/podcast-feed/feed.xml"
EPISODES_URL = "https://dwt0.github.io/podcast-feed/episodes"
CHANNEL_TITLE = "Law Review Podcasts"
CHANNEL_DESCRIPTION = "AI-narrated law review articles for on-the-go listening."
CHANNEL_AUTHOR = "Daniel Townsend"


def format_duration(seconds):
    """Format seconds as HH:MM:SS."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"


def generate_feed(repo_dir):
    """Scan episodes/*.json and produce feed.xml."""
    episodes_dir = os.path.join(repo_dir, "episodes")
    json_files = sorted(glob.glob(os.path.join(episodes_dir, "*.json")))

    # Load all episodes and sort by pub_date descending (newest first)
    episodes = []
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            episodes.append(json.load(f))

    # Sort by pub_date string (RFC 2822 format sorts correctly for same timezone)
    episodes.sort(key=lambda e: e.get("pub_date", ""), reverse=True)

    # Build RSS XML
    ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

    CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:itunes": ITUNES_NS,
        "xmlns:content": CONTENT_NS,
    })
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = CHANNEL_TITLE
    ET.SubElement(channel, "description").text = CHANNEL_DESCRIPTION
    ET.SubElement(channel, "link").text = FEED_URL
    ET.SubElement(channel, "language").text = "en-us"

    itunes_author = ET.SubElement(channel, "itunes:author")
    itunes_author.text = CHANNEL_AUTHOR
    itunes_explicit = ET.SubElement(channel, "itunes:explicit")
    itunes_explicit.text = "false"
    itunes_category = ET.SubElement(channel, "itunes:category")
    itunes_category.set("text", "Education")

    for ep in episodes:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep["title"]
        ET.SubElement(item, "description").text = ep.get("description", ep["title"])

        # Show notes as HTML in content:encoded
        show_notes = ep.get("show_notes")
        if show_notes:
            content_el = ET.SubElement(item, "content:encoded")
            # Use a placeholder that we'll replace with CDATA after serialization
            content_el.text = f"__CDATA__{show_notes}__ENDCDATA__"

        ET.SubElement(item, "pubDate").text = ep["pub_date"]

        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", f"{EPISODES_URL}/{ep['filename']}")
        enclosure.set("length", str(ep["file_size_bytes"]))
        enclosure.set("type", "audio/mpeg")

        duration = ET.SubElement(item, "itunes:duration")
        duration.text = format_duration(ep["duration_seconds"])

        guid = ET.SubElement(item, "guid")
        guid.set("isPermaLink", "true")
        guid.text = f"{EPISODES_URL}/{ep['filename']}"

    # Write feed.xml with pretty-printing
    rough_xml = ET.tostring(rss, encoding="unicode")
    parsed = minidom.parseString(rough_xml)
    pretty_xml = parsed.toprettyxml(indent="  ", encoding=None)
    # Remove extra xml declaration if minidom adds one, we'll write our own
    lines = pretty_xml.split("\n")
    if lines[0].startswith("<?xml"):
        lines = lines[1:]
    # Replace CDATA placeholders with actual CDATA sections
    content = "\n".join(lines)
    content = re.sub(
        r'__CDATA__(.*?)__ENDCDATA__',
        lambda m: f'<![CDATA[{html.unescape(m.group(1))}]]>',
        content, flags=re.DOTALL
    )

    feed_path = os.path.join(repo_dir, "feed.xml")
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(content)

    print(f"Generated {feed_path} with {len(episodes)} episode(s)")
    return feed_path


if __name__ == "__main__":
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    generate_feed(repo_dir)
