import hashlib
import base64

def generate_discid(cddb: str):
    cdtoc = [int(x) for x in cddb.split("+")[1:]]

    discid_src = "%02X%02X" % (1, cdtoc[1])
    for x in range(100):
        n = 0
        if x == 0:
            n = cdtoc[0]
            # print(n)
        elif x <= cdtoc[1]:
            n = cdtoc[x + 1]
            # print(x + 1, n)
        discid_src += "%08X" % (n)

    discid = hashlib.sha1(discid_src.encode("ascii")).digest()
    discid = base64.b64encode(discid, altchars=b"._").decode("ascii").replace("=", "-")
    # print(discid_src, discid)
    return discid
