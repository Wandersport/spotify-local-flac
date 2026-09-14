"""Audio metadata and artwork extraction for FLAC and other audio formats."""

import os
import re
import logging
from typing import Optional, Dict, Any, Tuple
import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.wave import WAVE

logger = logging.getLogger(__name__)

COMMON_COVER_FILENAMES = [
    "cover.jpg", "cover.png", "cover.jpeg",
    "folder.jpg", "folder.png", "folder.jpeg",
    "album.jpg", "album.png", "album.jpeg",
    "front.jpg", "front.png", "front.jpeg"
]


def _clean_string(val: Any) -> Optional[str]:
    """Clean a metadata string value."""
    if val is None:
        return None
    if isinstance(val, (list, tuple)):
        if not val:
            return None
        val = val[0]
    s = str(val).strip()
    return s if s else None


def _parse_year(val: Any) -> Optional[int]:
    """Extract a 4-digit year from date or year string."""
    s = _clean_string(val)
    if not s:
        return None
    m = re.search(r'\b(19\d{2}|20\d{2})\b', s)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def _parse_int_pair(val: Any) -> Tuple[Optional[int], Optional[int]]:
    """Parse 'track/total' or 'disc/total' pair."""
    s = _clean_string(val)
    if not s:
        return None, None
    if isinstance(val, tuple) and len(val) >= 1:
        try:
            cur = int(val[0])
            total = int(val[1]) if len(val) > 1 else None
            return cur, total
        except (ValueError, TypeError):
            pass
    m = re.match(r'^(\d+)(?:/(\d+))?$', s)
    if m:
        try:
            cur = int(m.group(1))
            total = int(m.group(2)) if m.group(2) else None
            return cur, total
        except ValueError:
            pass
    return None, None


def extract_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Extract comprehensive audio metadata and stream info from an audio file.
    Returns a dictionary suitable for database insertion, or None if extraction fails completely.
    """
    if not os.path.isfile(file_path):
        return None

    ext = os.path.splitext(file_path)[1].lower()
    stat = os.stat(file_path)
    file_size = stat.st_size
    mtime = stat.st_mtime
    base_name = os.path.basename(file_path)
    name_without_ext = os.path.splitext(base_name)[0]

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None

    duration: float = 0.0
    codec: str = ext.lstrip(".").upper()
    sample_rate: int = 44100
    bit_depth: Optional[int] = None
    channels: int = 2
    bitrate: Optional[int] = None
    has_artwork: bool = False

    try:
        if ext == ".flac":
            audio = FLAC(file_path)
            codec = "FLAC"
            if audio.info:
                duration = float(audio.info.length)
                sample_rate = int(audio.info.sample_rate)
                bit_depth = int(audio.info.bits_per_sample)
                channels = int(audio.info.channels)
                if duration > 0:
                    bitrate = int((file_size * 8) / duration)

            # Vorbis tags
            title = _clean_string(audio.get("title"))
            artist = _clean_string(audio.get("artist"))
            album = _clean_string(audio.get("album"))
            album_artist = _clean_string(audio.get("albumartist") or audio.get("album_artist"))
            genre = _clean_string(audio.get("genre"))
            year = _parse_year(audio.get("date") or audio.get("year"))
            track_number, _ = _parse_int_pair(audio.get("tracknumber"))
            disc_number, _ = _parse_int_pair(audio.get("discnumber"))

            if audio.pictures and len(audio.pictures) > 0:
                has_artwork = True

        elif ext == ".mp3":
            audio = MP3(file_path)
            codec = "MP3"
            if audio.info:
                duration = float(audio.info.length)
                sample_rate = int(audio.info.sample_rate)
                channels = int(audio.info.channels)
                bitrate = int(audio.info.bitrate) if hasattr(audio.info, "bitrate") else None
                bit_depth = 16

            if audio.tags:
                title = _clean_string(audio.tags.get("TIT2"))
                artist = _clean_string(audio.tags.get("TPE1"))
                album = _clean_string(audio.tags.get("TALB"))
                album_artist = _clean_string(audio.tags.get("TPE2"))
                genre = _clean_string(audio.tags.get("TCON"))
                year = _parse_year(audio.tags.get("TDRC") or audio.tags.get("TYER"))
                track_number, _ = _parse_int_pair(audio.tags.get("TRCK"))
                disc_number, _ = _parse_int_pair(audio.tags.get("TPOS"))
                if any(k.startswith("APIC") for k in audio.tags.keys()):
                    has_artwork = True

        elif ext in (".m4a", ".mp4"):
            audio = MP4(file_path)
            codec = "ALAC" if "alac" in getattr(audio.info, "codec", "").lower() else "AAC"
            if audio.info:
                duration = float(audio.info.length)
                sample_rate = int(getattr(audio.info, "sample_rate", 44100))
                channels = int(getattr(audio.info, "channels", 2))
                bit_depth = getattr(audio.info, "bits_per_sample", 16)
                bitrate = int(getattr(audio.info, "bitrate", 0)) if getattr(audio.info, "bitrate", 0) else None

            if audio.tags:
                title = _clean_string(audio.tags.get("\xa9nam"))
                artist = _clean_string(audio.tags.get("\xa9ART"))
                album = _clean_string(audio.tags.get("\xa9alb"))
                album_artist = _clean_string(audio.tags.get("aART"))
                genre = _clean_string(audio.tags.get("\xa9gen"))
                year = _parse_year(audio.tags.get("\xa9day"))
                track_val = audio.tags.get("trkn")
                if track_val and isinstance(track_val, list) and track_val[0]:
                    track_number, _ = _parse_int_pair(track_val[0])
                disc_val = audio.tags.get("disk")
                if disc_val and isinstance(disc_val, list) and disc_val[0]:
                    disc_number, _ = _parse_int_pair(disc_val[0])
                if audio.tags.get("covr"):
                    has_artwork = True

        elif ext in (".ogg", ".opus"):
            audio = mutagen.File(file_path)
            codec = "OPUS" if ext == ".opus" else "OGG"
            if audio and audio.info:
                duration = float(audio.info.length)
                sample_rate = int(audio.info.sample_rate)
                channels = int(audio.info.channels)
                bit_depth = 16
                if hasattr(audio.info, "bitrate"):
                    bitrate = int(audio.info.bitrate)

            if audio and hasattr(audio, "tags") and audio.tags:
                title = _clean_string(audio.tags.get("title"))
                artist = _clean_string(audio.tags.get("artist"))
                album = _clean_string(audio.tags.get("album"))
                album_artist = _clean_string(audio.tags.get("albumartist") or audio.tags.get("album_artist"))
                genre = _clean_string(audio.tags.get("genre"))
                year = _parse_year(audio.tags.get("date") or audio.tags.get("year"))
                track_number, _ = _parse_int_pair(audio.tags.get("tracknumber"))
                disc_number, _ = _parse_int_pair(audio.tags.get("discnumber"))
                if hasattr(audio, "pictures") and audio.pictures:
                    has_artwork = True

        elif ext == ".wav":
            audio = WAVE(file_path)
            codec = "WAV"
            if audio.info:
                duration = float(audio.info.length)
                sample_rate = int(audio.info.sample_rate)
                bit_depth = int(getattr(audio.info, "bits_per_sample", 16))
                channels = int(audio.info.channels)

            if audio.tags:
                title = _clean_string(audio.tags.get("TIT2"))
                artist = _clean_string(audio.tags.get("TPE1"))
                album = _clean_string(audio.tags.get("TALB"))
                year = _parse_year(audio.tags.get("TDRC") or audio.tags.get("TYER"))

        else:
            audio = mutagen.File(file_path)
            if audio and audio.info:
                duration = float(getattr(audio.info, "length", 0.0))
                sample_rate = int(getattr(audio.info, "sample_rate", 44100))
                channels = int(getattr(audio.info, "channels", 2))
                bit_depth = getattr(audio.info, "bits_per_sample", 16)

    except Exception as e:
        logger.warning("Mutagen failed reading tags for %s: %s", file_path, e)

    # Fallback to directory cover art if no embedded artwork
    if not has_artwork:
        parent_dir = os.path.dirname(file_path)
        for cover_name in COMMON_COVER_FILENAMES:
            if os.path.isfile(os.path.join(parent_dir, cover_name)):
                has_artwork = True
                break

    # Fallback title if missing
    if not title:
        # Try parsing "01 - Artist - Title" or "Artist - Title" or just file name
        cleaned_name = re.sub(r'^\d+[\s\.\-_]+', '', name_without_ext)
        if " - " in cleaned_name:
            parts = cleaned_name.split(" - ", 1)
            if not artist:
                artist = parts[0].strip()
            title = parts[1].strip()
        else:
            title = cleaned_name.strip() or name_without_ext

    if not artist:
        # Use parent folder name if it looks like an artist, else "Unknown Artist"
        artist = "Unknown Artist"

    if not album:
        # Use parent directory name
        parent_name = os.path.basename(os.path.dirname(file_path))
        album = parent_name if parent_name else "Unknown Album"

    return {
        "path": os.path.realpath(file_path),
        "filename": base_name,
        "title": title,
        "artist": artist,
        "album": album,
        "album_artist": album_artist or artist,
        "genre": genre,
        "year": year,
        "track_number": track_number,
        "disc_number": disc_number,
        "duration": max(0.0, duration),
        "codec": codec,
        "sample_rate": sample_rate,
        "bit_depth": bit_depth or (16 if codec != "FLAC" else 16),
        "channels": channels,
        "bitrate": bitrate,
        "file_size": file_size,
        "mtime": mtime,
        "has_artwork": 1 if has_artwork else 0
    }


def extract_artwork_bytes(file_path: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Extract embedded artwork image data and MIME type from an audio file.
    Falls back to folder image (cover.jpg/png) if no embedded image exists.
    Returns (data, mime_type) or (None, None).
    """
    if not os.path.isfile(file_path):
        return None, None

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".flac":
            audio = FLAC(file_path)
            if audio.pictures:
                pic = audio.pictures[0]
                mime = pic.mime or "image/jpeg"
                return pic.data, mime

        elif ext == ".mp3":
            audio = MP3(file_path)
            if audio.tags:
                for key in audio.tags.keys():
                    if key.startswith("APIC"):
                        apic = audio.tags[key]
                        mime = apic.mime or "image/jpeg"
                        return apic.data, mime

        elif ext in (".m4a", ".mp4"):
            audio = MP4(file_path)
            if audio.tags and "covr" in audio.tags:
                covers = audio.tags["covr"]
                if covers:
                    cover = covers[0]
                    mime = "image/png" if getattr(cover, "imageformat", None) == MP4Cover.FORMAT_PNG else "image/jpeg"
                    return bytes(cover), mime

        elif ext in (".ogg", ".opus"):
            audio = mutagen.File(file_path)
            if audio and hasattr(audio, "pictures") and audio.pictures:
                pic = audio.pictures[0]
                return pic.data, (pic.mime or "image/jpeg")

    except Exception as e:
        logger.warning("Failed extracting embedded artwork for %s: %s", file_path, e)

    # Fallback to folder artwork
    parent_dir = os.path.dirname(file_path)
    for cover_name in COMMON_COVER_FILENAMES:
        cover_path = os.path.join(parent_dir, cover_name)
        if os.path.isfile(cover_path):
            try:
                mime = "image/png" if cover_name.lower().endswith(".png") else "image/jpeg"
                with open(cover_path, "rb") as f:
                    return f.read(), mime
            except Exception as e:
                logger.warning("Failed reading folder artwork %s: %s", cover_path, e)

    return None, None
