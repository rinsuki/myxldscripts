from glob import glob
from xldparser import XLDLog
import zipfile
import os.path
from mutagen import MutagenError
from mutagen.mp4 import MP4
import hashlib
import base64
import httpx
import re
import os

BASE_DIR_SRC = os.path.join(os.environ["HOME"], "Desktop/xld-out/!done/")
BASE_DIR_DST = os.path.join(BASE_DIR_SRC, "zipdisc/")
BASE_DIR_ORIGFILES = os.path.join(BASE_DIR_DST, "origfiles/")
BASE_DIR_ORIGLOGS = os.path.join(BASE_DIR_DST, "logs/")

def itunes_cddb_to_discid(cddb: str):
    cdtoc = [int(x) for x in cddb.split("+")[1:]]

    discid_src = "%02X%02X" % (1, cdtoc[1])
    for x in range(100):
        n = 0
        if x == 0:
            n = cdtoc[0]
            print(n)
        elif x <= cdtoc[1]:
            n = cdtoc[x + 1]
            print(x + 1, n)
        discid_src += "%08X" % (n)

    discid = hashlib.sha1(discid_src.encode("ascii")).digest()
    return base64.b64encode(discid, altchars=b"._").decode("ascii").replace("=", "-")

def tstr(no: int):
    assert no > 0
    assert no < 100
    return "t%02d" % (no)

def tracks_to_readable_string(prefix: str, tracks: list[int]):
    if len(tracks) == 0:
        return ""
    ret = prefix
    NA = -999
    prev = NA
    start = NA
    for track in tracks:
        try:
            if prev == track - 1:
                if start == NA:
                    start = prev
            else:
                # fallback
                if start != NA:
                    if start != (prev-1):
                        ret += "-"
                    ret += tstr(prev)
                    start = NA
                ret += tstr(track)
        finally:
            prev = track
    if start != NA:
        if start != (prev-1):
            ret += "-"
        ret += tstr(prev)
    assert readable_string_to_tracks(ret) == tracks
    return ret

RE_READABLE_STRING_CHUNK = re.compile(r"^[0-9]{2}-?$")

def readable_string_to_tracks(inp: str):
    tracks: list[int] = []
    range_start = None
    for x in inp.replace("accrip_noinfo_partially_", "").split("t")[1:]:
        # print(x, inp)
        assert RE_READABLE_STRING_CHUNK.match(x) is not None
        if len(x) == 2:
            x = int(x)
            if range_start is None:
                tracks.append(x)
            else:
                while range_start <= x:
                    tracks.append(range_start)
                    range_start += 1
                range_start = None
        elif x.endswith("-"):
            range_start = int(x[:2])
        else:
            raise Exception("!?")
    print(tracks)
    return tracks

assert tracks_to_readable_string("", [1]) == "t01"
assert tracks_to_readable_string("", [1, 2]) == "t01t02"
assert tracks_to_readable_string("", [1, 2, 3]) == "t01-t03"
assert tracks_to_readable_string("", [1, 3, 4]) == "t01t03t04"
assert tracks_to_readable_string("", [1, 3, 4, 6]) == "t01t03t04t06"
assert tracks_to_readable_string("", [1, 3, 4, 5, 7]) == "t01t03-t05t07"

verified_disc_ids: set[str] = set()
def get_disc_id(file: MP4):
    if '----:com.apple.iTunes:MusicBrainz Disc Id' in file.tags:
        return file.tags['----:com.apple.iTunes:MusicBrainz Disc Id'][0].decode()
    if '----:com.apple.iTunes:iTunes_CDDB_1' in file.tags:
        disc_id = itunes_cddb_to_discid(file.tags['----:com.apple.iTunes:iTunes_CDDB_1'][0].decode())
        if disc_id not in verified_disc_ids:
            res = httpx.get("https://musicbrainz.org/ws/2/discid/" + disc_id)
            print(disc_id)
            assert res.status_code == 200
            verified_disc_ids.add(disc_id)
        return disc_id
    raise Exception("unknown disc id")

for file in glob(BASE_DIR_SRC + "y*_/*.log"):
    AUDIO_FILE_DIR = os.path.dirname(file) + "/"
    print(file)
    xldlog = XLDLog.parse(open(file, "r"))
    if xldlog.is_cancelled:
        print("cancelled", file)
        continue
    # print(xldlog)
    if len(xldlog.tracks) != len(xldlog.toc):
        print("wrong tracks", file)
        continue
    # if not xldlog.successfly_ripped:
    #     print("not success", file)
    #     continue
    accuraterip_status = "passed"
    if xldlog.accuraterip_disc_id is None:
        accuraterip_status = "not_found"
    else:
        for track in xldlog.tracks:
            if track.accuraterip_result is None:
                accuraterip_status = "not_found_partially"
                continue
            if track.accuraterip_result.success_summary is None:
                accuraterip_status = "failed"
                break
    if accuraterip_status != "passed" and accuraterip_status != "not_found" and accuraterip_status != "not_found_partially" and accuraterip_status != "failed":
        print("not accuraterip", accuraterip_status, file)
        continue
    track1 = MP4(AUDIO_FILE_DIR + os.path.basename(xldlog.tracks[0].filename))
    # print(track1.pprint())
    expected_cddb: list[int] = []
    BASE_SECTOR = 150
    expected_cddb.append(xldlog.toc[-1].end_sector + BASE_SECTOR + 1)
    expected_cddb.append(len(xldlog.toc))
    for t in xldlog.toc:
        expected_cddb.append(t.start_sector + BASE_SECTOR)
    expected_cddb = "+".join([str(x) for x in expected_cddb])
    CDDB_KEY = "----:com.apple.iTunes:iTunes_CDDB_1"
    cddb = track1[CDDB_KEY][0].decode()
    assert cddb[8:] == ("+" + expected_cddb)
    # print(expected_cddb)
    # print(xldlog.toc)
    disczip_filename = track1['----:com.apple.iTunes:MusicBrainz Album Id'][0].decode()
    print(track1.pprint())
    disczip_filename += ".disc" + str(track1['disk'][0][0]) + "."
    disczip_filename += get_disc_id(track1)
    if accuraterip_status == "not_found":
        disczip_filename += ".accrip_noinfo"
    else:
        tracks_noinfo = []
        tracks_fail = []
        for track in xldlog.tracks:
            if track.accuraterip_result is None:
                tracks_noinfo.append(track.no)
            elif track.accuraterip_result.success_summary is None:
                tracks_fail.append(track.no)
        disczip_filename += tracks_to_readable_string(".accrip_noinfo_partially_", tracks_noinfo)
        disczip_filename += tracks_to_readable_string(".accrip_fail_", tracks_fail)
    if not xldlog.successfly_ripped:
        disczip_filename += ".failrip"
    disczip_filename += ".zip"
    print(disczip_filename)
    assert not os.path.exists(BASE_DIR_DST + disczip_filename)
    try:
        with zipfile.ZipFile(BASE_DIR_DST + disczip_filename, "w") as zf:
            for track in xldlog.tracks:
                print(track)
                track_fn = os.path.basename(track.filename)
                track_src = AUDIO_FILE_DIR + track_fn
                track_file = MP4(track_src)
                assert track_file.tags[CDDB_KEY][0].decode() == cddb
                zf.write(track_src, "tracks/" + track_fn)
            zf.write(file, "log/" + os.path.basename(file))
    except Exception as e:
        os.unlink(BASE_DIR_DST + disczip_filename)
        if type(e) is MutagenError:
            continue
        raise
    for track in xldlog.tracks:
        track_fn = os.path.basename(track.filename)
        track_src = AUDIO_FILE_DIR + track_fn
        track_dst = BASE_DIR_ORIGFILES + disczip_filename +  "." + track_fn
        assert not os.path.exists(track_dst)
        os.rename(track_src, track_dst)
    file_dest = BASE_DIR_ORIGLOGS + disczip_filename + "." + os.path.basename(file)
    os.rename(file, file_dest)
