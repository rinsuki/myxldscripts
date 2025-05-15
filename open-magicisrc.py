from xldparser import XLDLog
import sys
import mutagen.mp4
from lib.cdtoc2discid import generate_discid
import re
import urllib.parse
import os.path
import httpx
import webbrowser

RE_ISRC = r"((?:JP|IT|US|TC|QM|GB|FR)[A-Z0-9]{3}[0-9]{2}[0-9]{5}|NO_ISRC)"
RE_FIRST_ISRC = re.compile(r"^.+/[0-9]{2}\(" + RE_ISRC + r"\) [^/]+\.m4a$")

# get the log file from the command line
if len(sys.argv) != 2:
    print("Usage: open-magicisrc.py <logfile>")
    sys.exit(1)

logfile = sys.argv[1]

with open(logfile, "r") as f:
    xldlog = XLDLog.parse(f)

first_track_tag = mutagen.mp4.MP4(os.path.join(os.path.dirname(logfile), os.path.basename(xldlog.tracks[0].filename)))
print(first_track_tag)
first_track_cddb = first_track_tag['----:com.apple.iTunes:iTunes_CDDB_1']
mb_cdtoc = generate_discid(first_track_cddb[0].decode("ascii"))
mb_cdtoc_url = "https://musicbrainz.org/cdtoc/" + mb_cdtoc
mb_release_id = first_track_tag['----:com.apple.iTunes:MusicBrainz Album Id'][0].decode("ascii")
mb_release_url = "https://musicbrainz.org/release/" + mb_release_id
if 'disk' in first_track_tag:
    disc_no = first_track_tag['disk'][0][0]
else:
    disc_no = 1

query: dict[str, str] = {
    "musicbrainzid": mb_release_id,
}

note: list[str] = []
note.append(f"Target Release: {mb_release_url} (Disc {disc_no})")
note.append(f"CD TOC: {mb_cdtoc_url}")
note.append("")

mb_res = httpx.get("https://musicbrainz.org/ws/2/release/" + mb_release_id, params={
    "inc": "recordings+isrcs+discids",
    "fmt": "json",
})
print(mb_res.url)
mb_res.raise_for_status()
mb_res = mb_res.json()

mb_target_media = None
for mb_media in mb_res["media"]:
    for cd in mb_media["discs"]:
        if cd["id"] == mb_cdtoc:
            mb_target_media = mb_media
assert mb_target_media is not None

need_to_add_some_isrc = False

for track in xldlog.tracks:
    isrc = RE_FIRST_ISRC.match(track.filename).group(1)
    trnum = track.no
    note_prefix = f"Tr. {trnum}: "
    if track.accuraterip_result is not None and track.accuraterip_result.success_summary is None:
        note_prefix += "(damaged) "
    if isrc == "NO_ISRC":
        note.append(note_prefix + "No ISRC found")
        continue
    mb_current_recording_isrcs = mb_target_media["tracks"][trnum - 1]["recording"].get("isrcs", [])
    query[f"isrc{disc_no}-{trnum}"] = isrc
    if isrc in mb_current_recording_isrcs:
        note.append(note_prefix + "https://musicbrainz.org/isrc/" + isrc + " (already attached)")
        continue
    note.append(note_prefix + "https://musicbrainz.org/isrc/" + isrc)
    need_to_add_some_isrc = True

if not need_to_add_some_isrc:
    print("No Unknown ISRCs found")
    sys.exit(0)

query["edit-note"] = "\n".join(note)

print(query)

MAGICISRC_BASE_URL = "https://magicisrc.kepstin.ca/"

webbrowser.open(MAGICISRC_BASE_URL + "?" + urllib.parse.urlencode(query))
input("Press Enter to continue...")
