from xldparser import XLDLog, XLDTrackEntryCancelled
from mutagen.mp4 import MP4, MP4FreeForm, MP4Tags
from glob import iglob
import re
import io
import os

# 自分がリッピングしたことのあるISRCの国コードだけを書いてあるので、適時増やすこと
RE_ISRC = r"((?:JP|IT|US|TC|QM|GB|FR)[A-Z0-9]{3}[0-9]{2}[0-9]{5}|NO_ISRC)"
# 一時期は最後にISRCを付けていたのでその名残り、公開リポジトリを初めて使う人はいらない
NEED_PARSE_LAST_ISRC = False
RE_LAST_ISRC = re.compile(r"^.+ \(" + RE_ISRC + r"\)(?:\([1-9]\))?\.m4a$") if NEED_PARSE_LAST_ISRC else None
RE_FIRST_ISRC = re.compile(r"^.+/[0-9]{2}\(" + RE_ISRC + r"\) [^/]+\.m4a$")
PREFIX_ACCURATERIP_FAILED = "[FAIL AccurateRip] "
# PREFIX_PERFECT_READ = "[FAIL PerfectRead] "
MP4TAG_NAME = '\xa9nam'

def get_only_one_str_tag(tags: MP4Tags, key: str):
    value = tags[key]
    assert isinstance(value, list)
    assert len(value) == 1
    value = value[0]
    print(type(value))
    assert isinstance(value, str)
    return value

for gp in [os.path.join(os.environ["HOME"], "Desktop/xld-out/y*_/*.log")]:
    for file in iglob(gp, recursive=True):
        with open(file, "r") as f:
            print("Parsing", file)
            xldlog = XLDLog.parse(f)
            destlog = io.StringIO()
            xldlog.as_log(destlog)
            destlog = destlog.getvalue()
            f.seek(0, 0)
            origlog = f.read()
            # xldparser が正しくログをパースできていることを確認
            if origlog != destlog:
                open("diff.orig.log", "w").write(origlog)
                open("diff.dest.log", "w").write(destlog)
                assert origlog == destlog
            for track in xldlog.tracks:
                # 途中でキャンセルしたトラックは無視
                if isinstance(track, XLDTrackEntryCancelled):
                    continue
                if track.accuraterip_result is None:
                    print(track)
                is_accuraterip_failed = track.accuraterip_result is not None and track.accuraterip_result.success_summary is None
                is_perfectread_failed = (track.accuraterip_result is None or is_accuraterip_failed) and (track.statistics.damaged_sector_count > 0)
                is_test_failed = track.crc32_hash_test is not None and track.crc32_hash_test != track.crc32_hash
                if track.accuraterip_result is None and (track.statistics.jitter_error > 0 or track.statistics.read_error > 0 or track.statistics.damaged_sector_count > 0):
                    raise Exception("AccurateRip が通っていないのにリッピング時にエラーが出ています！再度リッピングすることを推奨します")
                isrc_match = None
                if RE_LAST_ISRC is not None:
                    isrc_match = RE_LAST_ISRC.search(track.filename)
                if isrc_match is None:
                    isrc_match = RE_FIRST_ISRC.search(track.filename)
                if isrc_match is None:
                    raise Exception("ISRCがパースできませんでした (プレスミス or 未知の国コード？) " + track.filename)
                isrc = isrc_match.group(1)
                # ここからタグ書き換え処理
                mf = MP4(track.filename)
                if mf.tags is None:
                    raise Exception("m4aにタグがありません")
                # ISRC がわかっている場合はタグ付け
                if isrc != "NO_ISRC":
                    mf.tags['----:com.apple.iTunes:ISRC'] = [MP4FreeForm(isrc_match.group(1).encode("ascii"))]
                # print(mf.pprint(), mf.tags)
                # AccurateRip がダメだったらタイトルにおまけを付ける
                # TODO: cuetools 相当のタグを付ける
                if track.accuraterip_result is None:
                    if is_test_failed:
                        raise Exception("AccurateRip が存在しないディスクでテストリップと本リップの結果が一致していません！再度リッピングすることを推奨します")
                elif is_accuraterip_failed:
                    v = get_only_one_str_tag(mf.tags, MP4TAG_NAME)
                    if PREFIX_ACCURATERIP_FAILED not in v:
                        v = PREFIX_ACCURATERIP_FAILED + v
                        mf.tags[MP4TAG_NAME] = v
                elif is_perfectread_failed:
                    # 別に AccurateRip 通ってるならいい気はする
                    raise Exception("AccurateRip が通っているディスクで PerfectRead が失敗しています！再度リッピングすることを推奨します")
                else:
                    # リッピング大成功
                    pass
                mf.save()
