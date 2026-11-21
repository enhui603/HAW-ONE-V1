"""HAW-ONE data layer. No Streamlit in here, so it can be tested on its own."""
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import smtplib
import ssl
import struct
import threading
import time
import uuid
from datetime import datetime
from email.message import EmailMessage

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UPLOADS = os.path.join(DATA, "uploads")
os.makedirs(UPLOADS, exist_ok=True)
CODES_FILE = os.path.join(HERE, "invite_codes.json")   # hashes only (safe to keep in the repo)

MAX_VIDEO_SECONDS = 30
MAX_VIDEO_MB = 50

_LOCK = threading.RLock()


# ---------------------------------------------------------------- json tables
def _path(name):
    return os.path.join(DATA, f"{name}.json")


def _load(name, default):
    p = _path(name)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save(name, obj):
    p = _path(name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def _mutate(name, default, fn):
    with _LOCK:
        data = _load(name, default)
        result = fn(data)
        _save(name, data)
        return result


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _id():
    return uuid.uuid4().hex[:10]


# ---------------------------------------------------------------- passwords
def hash_password(pw):
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000)
    return f"{salt}${dk.hex()}"


def check_password(pw, stored):
    try:
        salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000)
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False


_DUMMY = None


def valid_email(e):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e.strip()))


def valid_username(u):
    return bool(re.fullmatch(r"[A-Za-z0-9_.]{3,20}", u))


# ---------------------------------------------------------------- one-time codes (OTP / reset)
def _h(s):
    return hashlib.sha256(("haw-otp|" + s).encode()).hexdigest()


def new_challenge(payload=None, ttl=600):
    code = f"{secrets.randbelow(10 ** 6):06d}"
    return code, {"h": _h(code), "exp": time.time() + ttl, "tries": 0, "payload": payload}


def check_challenge(ch, code):
    if not ch or time.time() > ch["exp"] or ch["tries"] >= 5:
        return False
    ch["tries"] += 1
    return hmac.compare_digest(ch["h"], _h((code or "").strip()))


# ---------------------------------------------------------------- trial (invite) codes
def _norm(code):
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def _hc(code):
    return hashlib.sha256(("haw-one|" + _norm(code)).encode()).hexdigest()


def make_codes(n=30):
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    out = set()
    while len(out) < n:
        a = "".join(secrets.choice(alphabet) for _ in range(4))
        b = "".join(secrets.choice(alphabet) for _ in range(4))
        out.add(f"HAW-{a}-{b}")
    return sorted(out)


def _code_hashes():
    try:
        with open(CODES_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("hashes", []))
    except Exception:
        return set()


def invite_valid(code):
    if not _norm(code):
        return False
    h = _hc(code)
    return h in _code_hashes() and h not in _load("used_codes", {})


def invite_use(code, uid):
    _mutate("used_codes", {}, lambda d: d.__setitem__(_hc(code), {"uid": uid, "time": _now()}))


def invite_counts():
    total = len(_code_hashes())
    used = len([h for h in _load("used_codes", {}) if h in _code_hashes()])
    return total, used


# ---------------------------------------------------------------- users
def all_users():
    return _load("users", {})


def get_user(uid):
    return all_users().get(uid) if uid else None


def find_by_email(email):
    e = (email or "").strip().lower()
    for u in all_users().values():
        if u["email"] == e:
            return u
    return None


def find_by_username(name):
    n = (name or "").strip().lower()
    for u in all_users().values():
        if u["role"] == "visitor" and u["username"].lower() == n:
            return u
    return None


def create_seller(stall, logo, centre, unit, email, password):
    u = {"id": _id(), "role": "seller", "email": email.strip().lower(), "pw": hash_password(password),
         "stall": stall.strip(), "logo": logo, "centre": centre, "unit": unit.strip(),
         "suspended": False, "created": _now()}
    _mutate("users", {}, lambda d: d.__setitem__(u["id"], u))
    return u


def create_visitor(username, avatar, email, pw_hash):
    u = {"id": _id(), "role": "visitor", "email": email.strip().lower(), "pw": pw_hash,
         "username": username.strip(), "avatar": avatar, "subs": [], "created": _now()}
    _mutate("users", {}, lambda d: d.__setitem__(u["id"], u))
    return u


def verify_login(email, password, role):
    global _DUMMY
    u = find_by_email(email)
    if u is None:
        _DUMMY = _DUMMY or hash_password("dummy")
        check_password(password, _DUMMY)
        return None
    if u["role"] == role and check_password(password, u["pw"]):
        return u
    return None


def set_password(uid, pw):
    def fn(d):
        if uid in d:
            d[uid]["pw"] = hash_password(pw)
    _mutate("users", {}, fn)


def set_flag(uid, key, value):
    def fn(d):
        if uid in d:
            d[uid][key] = value
    _mutate("users", {}, fn)


def stalls(include_suspended=False):
    out = [u for u in all_users().values() if u["role"] == "seller"]
    if not include_suspended:
        out = [u for u in out if not u.get("suspended")]
    return sorted(out, key=lambda u: u["stall"].lower())


def toggle_follow(uid, stall_id):
    def fn(d):
        u = d.get(uid)
        if u is not None:
            subs = u.setdefault("subs", [])
            if stall_id in subs:
                subs.remove(stall_id)
            else:
                subs.append(stall_id)
    _mutate("users", {}, fn)


def display_name(u):
    if not u:
        return "HAW-ONE"
    return u["stall"] if u["role"] == "seller" else u["username"]


# ---------------------------------------------------------------- posts (broadcast + social feed)
def add_post(channel, author_id, text="", images=None, video=None, kind="update",
             start=None, end=None, link="", label=""):
    post = {"id": _id(), "channel": channel, "author_id": author_id, "time": _now(), "kind": kind,
            "text": (text or "").strip(), "images": images or [], "video": video,
            "start": start, "end": end, "link": link, "label": label,
            "reactions": {}, "comments": []}
    _mutate("posts", [], lambda d: d.insert(0, post))
    return post


def get_posts(channel=None, author_id=None):
    out = _load("posts", [])
    if channel:
        out = [p for p in out if p["channel"] == channel]
    if author_id:
        out = [p for p in out if p["author_id"] == author_id]
    return out


def get_post(pid):
    for p in _load("posts", []):
        if p["id"] == pid:
            return p
    return None


def thumb_name(name):
    return "thumb_" + name


def remove_media(images=(), video=None):
    for n in list(images) + ([video] if video else []):
        for f in (n, thumb_name(n)):
            try:
                os.remove(os.path.join(UPLOADS, f))
            except OSError:
                pass


def delete_post(pid, author_id=None):
    removed = []

    def fn(d):
        for p in list(d):
            if p["id"] == pid and (author_id is None or p["author_id"] == author_id):
                d.remove(p)
                removed.append(p)
    _mutate("posts", [], fn)
    for p in removed:
        remove_media(p.get("images", []), p.get("video"))


def react(pid, uid, emoji):
    def fn(d):
        for p in d:
            if p["id"] == pid:
                r = p.setdefault("reactions", {})
                if r.get(uid) == emoji:
                    r.pop(uid)
                else:
                    r[uid] = emoji
    _mutate("posts", [], fn)


def add_comment(pid, uid, text):
    text = (text or "").strip()[:300]
    if not text:
        return

    def fn(d):
        for p in d:
            if p["id"] == pid:
                p.setdefault("comments", []).append({"id": _id(), "uid": uid, "text": text, "time": _now()})
    _mutate("posts", [], fn)


def closures_for(stall_id, today):
    """Closure notices that have not ended yet, soonest first. today is a date."""
    out = []
    for p in get_posts("broadcast", stall_id):
        if p["kind"] == "closure" and p.get("end") and p["end"] >= today.isoformat():
            out.append(p)
    return sorted(out, key=lambda p: p["start"])


# ---------------------------------------------------------------- ratings + ranks
RANKS = [(0, "Kopi Explorer", "#8B5E3C"), (3, "Tray Scout", "#3FA66B"), (10, "The Regular", "#5B9BD5"),
         (25, "Hawker Navigator", "#8E5BD0"), (50, "Makan Master", "#E0A800")]


def rank_info(n):
    idx = max(i for i, r in enumerate(RANKS) if n >= r[0])
    nxt = RANKS[idx + 1] if idx + 1 < len(RANKS) else None
    return {"index": idx, "name": RANKS[idx][1], "color": RANKS[idx][2],
            "next_name": nxt[1] if nxt else None, "to_next": (nxt[0] - n) if nxt else 0,
            "start": RANKS[idx][0], "next_at": nxt[0] if nxt else None}


def rate(stall_id, uid, stars, comment="", image=None):
    stars = max(1, min(3, int(stars)))

    def fn(d):
        for r in d:
            if r["stall_id"] == stall_id and r["uid"] == uid:
                r.update(stars=stars, comment=comment.strip()[:500], time=_now())
                if image:
                    r["image"] = image
                return
        d.insert(0, {"id": _id(), "stall_id": stall_id, "uid": uid, "stars": stars,
                     "comment": comment.strip()[:500], "image": image, "time": _now()})
    _mutate("ratings", [], fn)


def ratings_for(stall_id):
    return [r for r in _load("ratings", []) if r["stall_id"] == stall_id]


def ratings_by(uid):
    return [r for r in _load("ratings", []) if r["uid"] == uid]


def my_rating(stall_id, uid):
    for r in ratings_for(stall_id):
        if r["uid"] == uid:
            return r
    return None


def avg_rating(stall_id):
    rs = ratings_for(stall_id)
    return (sum(r["stars"] for r in rs) / len(rs), len(rs)) if rs else (0.0, 0)


def rating_count(uid):
    """Ranks count distinct stalls rated (one rating per stall), not comments."""
    return len({r["stall_id"] for r in ratings_by(uid)})


# ---------------------------------------------------------------- reports
def add_report(stall_id, reporter_id, reason, note="", screenshot=None):
    snapshot = [{"channel": p["channel"], "time": p["time"], "text": p["text"],
                 "images": p["images"], "video": p["video"]}
                for p in get_posts(author_id=stall_id)[:5]]
    r = {"id": _id(), "stall_id": stall_id, "reporter_id": reporter_id, "reason": reason,
         "note": note.strip()[:1000], "screenshot": screenshot, "snapshot": snapshot,
         "status": "new", "time": _now()}
    _mutate("reports", [], lambda d: d.insert(0, r))
    return r


def get_reports():
    return _load("reports", [])


def set_report_status(rid, status):
    def fn(d):
        for r in d:
            if r["id"] == rid:
                r["status"] = status
    _mutate("reports", [], fn)


# ---------------------------------------------------------------- media
def _flatten(im):
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def save_image(data, max_side=1280):
    """Saves a resized JPEG and a square thumbnail. Returns the file name or None."""
    try:
        im = _flatten(Image.open(io.BytesIO(data)))
    except Exception:
        return None
    im.thumbnail((max_side, max_side))
    name = uuid.uuid4().hex + ".jpg"
    im.save(os.path.join(UPLOADS, name), "JPEG", quality=85)
    ImageOps.fit(im, (400, 400)).save(os.path.join(UPLOADS, thumb_name(name)), "JPEG", quality=80)
    return name


def save_avatar(data):
    try:
        im = _flatten(Image.open(io.BytesIO(data)))
    except Exception:
        return None
    name = "av_" + uuid.uuid4().hex + ".jpg"
    ImageOps.fit(im, (256, 256)).save(os.path.join(UPLOADS, name), "JPEG", quality=85)
    return name


def save_video(data, filename):
    ext = os.path.splitext(filename)[1].lower() or ".mp4"
    name = uuid.uuid4().hex + ext
    with open(os.path.join(UPLOADS, name), "wb") as f:
        f.write(data)
    return name


def media_path(name):
    return os.path.join(UPLOADS, name)


def mp4_duration(data):
    """Seconds, read from the MP4/MOV header (no ffmpeg needed). None if unreadable."""
    def boxes(start, end):
        pos = start
        while pos + 8 <= end:
            size, typ = struct.unpack(">I4s", data[pos:pos + 8])
            hdr = 8
            if size == 1:
                if pos + 16 > end:
                    return
                size = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
                hdr = 16
            elif size == 0:
                size = end - pos
            if size < hdr:
                return
            yield typ, pos + hdr, min(pos + size, end)
            pos += size

    try:
        for typ, s, e in boxes(0, len(data)):
            if typ == b"moov":
                for t2, s2, e2 in boxes(s, e):
                    if t2 == b"mvhd":
                        if data[s2] == 1:
                            ts, dur = struct.unpack(">IQ", data[s2 + 20:s2 + 32])
                        else:
                            ts, dur = struct.unpack(">II", data[s2 + 12:s2 + 20])
                        return dur / ts if ts and dur else None
    except Exception:
        return None
    return None


def check_video(data):
    """Returns None if OK, else the translation key of the error."""
    if len(data) > MAX_VIDEO_MB * 1024 * 1024:
        return "err_video_big"
    dur = mp4_duration(data)
    if dur is None:
        return "err_video_read"
    if dur > MAX_VIDEO_SECONDS + 0.5:
        return "err_video_len"
    return None


# ---------------------------------------------------------------- regions (North / South / East / West)
# Approximate split of the island, stretched because Singapore is wider east-west than north-south.
CENTRE_LAT, CENTRE_LON = 1.34, 103.83
SPAN_LAT, SPAN_LON = 0.08, 0.12
REGION_COLORS = {"north": "#5B9BD5", "south": "#E8587A", "east": "#F2A93B", "west": "#4CB36B"}


def region_of(lat, lon):
    dy, dx = (lat - CENTRE_LAT) / SPAN_LAT, (lon - CENTRE_LON) / SPAN_LON
    if abs(dy) >= abs(dx):
        return "north" if dy >= 0 else "south"
    return "east" if dx >= 0 else "west"


# ---------------------------------------------------------------- email
def send_email(cfg, to, subject, body):
    """cfg = dict with host, port, user, password, from. Returns True if sent."""
    if not cfg:
        return False
    try:
        msg = EmailMessage()
        msg["From"] = cfg.get("from") or cfg["user"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(cfg["host"], int(cfg.get("port", 587)), timeout=15) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
        return True
    except Exception:
        return False
