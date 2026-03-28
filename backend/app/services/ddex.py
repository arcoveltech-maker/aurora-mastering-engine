"""DDEX ERN 4.1 XML generation for digital distribution."""
from __future__ import annotations

from datetime import datetime
from xml.etree import ElementTree as ET


def generate_ddex_ern(
    session_id: str,
    audio_file: dict,
    metadata: dict,
    recipient: str = "spotify",
) -> str:
    """
    Generate DDEX ERN 4.1 compliant XML for digital distribution.

    Required metadata keys:
        title, artist, album, isrc, label, year, genre
    Optional:
        upc, publisher, copyright, language
    """
    ns_ern  = "http://ddex.net/xml/ern/41"
    ns_xs   = "http://www.w3.org/2001/XMLSchema-instance"
    ns_avs  = "http://ddex.net/xml/avs/avs"

    ET.register_namespace("ern", ns_ern)
    ET.register_namespace("xs",  ns_xs)
    ET.register_namespace("avs", ns_avs)

    root = ET.Element(f"{{{ns_ern}}}NewReleaseMessage", {
        f"{{{ns_xs}}}schemaLocation": f"{ns_ern} http://ddex.net/xml/ern/41/release-notification.xsd",
        "LanguageAndScriptCode": "en",
        "MessageSchemaVersionId": "ern/41",
    })

    # ── MessageHeader ──────────────────────────────────────────────────────
    header = ET.SubElement(root, f"{{{ns_ern}}}MessageHeader")
    ET.SubElement(header, f"{{{ns_ern}}}MessageThreadId").text = f"AURORA-{session_id}"
    ET.SubElement(header, f"{{{ns_ern}}}MessageId").text = f"AURORA-MSG-{session_id}"
    ET.SubElement(header, f"{{{ns_ern}}}MessageCreatedDateTime").text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    ET.SubElement(header, f"{{{ns_ern}}}MessageControlType").text = "LiveMessage"

    sender = ET.SubElement(header, f"{{{ns_ern}}}MessageSender")
    ET.SubElement(sender, f"{{{ns_ern}}}PartyId").text = "PADPIDA2014120201U"  # Aurora's DDEX registrant ID
    ET.SubElement(sender, f"{{{ns_ern}}}PartyName").text = "Aurora AI Mastering Engine"

    recipient_el = ET.SubElement(header, f"{{{ns_ern}}}MessageRecipient")
    recipient_ids = {"spotify": "PADPIDA2012010201I", "apple": "PADPIDA2009012101Y"}
    ET.SubElement(recipient_el, f"{{{ns_ern}}}PartyId").text = recipient_ids.get(recipient, recipient_ids["spotify"])
    ET.SubElement(recipient_el, f"{{{ns_ern}}}PartyName").text = recipient.title()

    # ── UpdateIndicator ────────────────────────────────────────────────────
    ET.SubElement(root, f"{{{ns_ern}}}UpdateIndicator").text = "OriginalMessage"

    # ── ResourceList ───────────────────────────────────────────────────────
    resource_list = ET.SubElement(root, f"{{{ns_ern}}}ResourceList")
    sound_rec = ET.SubElement(resource_list, f"{{{ns_ern}}}SoundRecording")
    ET.SubElement(sound_rec, f"{{{ns_ern}}}SoundRecordingType").text = "MusicalWorkSoundRecording"

    sr_id = ET.SubElement(sound_rec, f"{{{ns_ern}}}SoundRecordingId")
    isrc = metadata.get("isrc", "")
    if isrc:
        ET.SubElement(sr_id, f"{{{ns_ern}}}ISRC").text = isrc

    ref_title = ET.SubElement(sound_rec, f"{{{ns_ern}}}ReferenceTitle")
    ET.SubElement(ref_title, f"{{{ns_ern}}}TitleText").text = metadata.get("title", "Untitled")

    duration_secs = audio_file.get("duration_seconds", 0)
    ET.SubElement(sound_rec, f"{{{ns_ern}}}Duration").text = _seconds_to_iso8601(duration_secs)

    # Audio details
    audio_el = ET.SubElement(sound_rec, f"{{{ns_ern}}}TechnicalSoundRecordingDetails")
    ET.SubElement(audio_el, f"{{{ns_ern}}}TechnicalResourceDetailsReference").text = "A1"
    ET.SubElement(audio_el, f"{{{ns_ern}}}AudioCodecType").text = audio_file.get("codec", "WAV")
    ET.SubElement(audio_el, f"{{{ns_ern}}}BitDepth").text = str(audio_file.get("bit_depth", 24))
    ET.SubElement(audio_el, f"{{{ns_ern}}}SamplingRate").text = str(audio_file.get("sample_rate", 48000))
    ET.SubElement(audio_el, f"{{{ns_ern}}}NumberOfChannels").text = str(audio_file.get("channels", 2))

    # ── ReleaseList ────────────────────────────────────────────────────────
    release_list = ET.SubElement(root, f"{{{ns_ern}}}ReleaseList")
    release = ET.SubElement(release_list, f"{{{ns_ern}}}Release")
    ET.SubElement(release, f"{{{ns_ern}}}IsMainRelease").text = "true"

    rel_id = ET.SubElement(release, f"{{{ns_ern}}}ReleaseId")
    upc = metadata.get("upc", "")
    if upc:
        ET.SubElement(rel_id, f"{{{ns_ern}}}UPC").text = upc
    if isrc:
        ET.SubElement(rel_id, f"{{{ns_ern}}}ICPN").text = isrc

    rel_type = ET.SubElement(release, f"{{{ns_ern}}}ReleaseType")
    rel_type.text = "SingleResourceRelease"

    rel_title = ET.SubElement(release, f"{{{ns_ern}}}ReferenceTitle")
    ET.SubElement(rel_title, f"{{{ns_ern}}}TitleText").text = metadata.get("title", "Untitled")

    # Release date
    rel_detail = ET.SubElement(release, f"{{{ns_ern}}}ReleaseDetailsByTerritory")
    ET.SubElement(rel_detail, f"{{{ns_ern}}}TerritoryCode").text = "Worldwide"

    label_el = ET.SubElement(rel_detail, f"{{{ns_ern}}}LabelName").text = metadata.get("label", "")

    year = metadata.get("year", str(datetime.now().year))
    orig_date = ET.SubElement(rel_detail, f"{{{ns_ern}}}OriginalReleaseDate").text = f"{year}-01-01"

    # Contributor
    artist_name = metadata.get("artist", "")
    if artist_name:
        contrib = ET.SubElement(sound_rec, f"{{{ns_ern}}}ResourceContributor")
        name_el = ET.SubElement(contrib, f"{{{ns_ern}}}PartyName")
        ET.SubElement(name_el, f"{{{ns_ern}}}FullName").text = artist_name
        ET.SubElement(contrib, f"{{{ns_ern}}}ResourceContributorRole").text = "MainArtist"

    # Format nicely
    _indent(root)
    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=True)
    return xml_str


def _seconds_to_iso8601(seconds: float) -> str:
    """Convert seconds to ISO 8601 duration: PT3M45S."""
    s = int(seconds)
    minutes = s // 60
    secs = s % 60
    if minutes:
        return f"PT{minutes}M{secs:02d}S"
    return f"PT{secs}S"


def _indent(elem: ET.Element, level: int = 0) -> None:
    """Add pretty-print indentation."""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():  # type: ignore[possibly-undefined]
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent
