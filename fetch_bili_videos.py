import requests, time, hashlib, urllib.parse, json, uuid, random, string, base64, math

MID = 49246269
OUT = "/Users/zhang/WorkBuddy/yt-dlp/bilibili_videos.json"
PS = 50

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
S = requests.Session()
S.headers.update({"User-Agent": UA, "Referer": f"https://space.bilibili.com/{MID}/video",
                  "Origin": "https://space.bilibili.com", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
S.cookies.set("buvid3", f"{uuid.uuid4()}infoc", domain=".bilibili.com")

mixinKeyEncTab = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
    12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

def get_wbi():
    r = S.get("https://api.bilibili.com/x/web-interface/nav", timeout=20)
    wbi = r.json()["data"]["wbi_img"]
    lookup = ''.join([wbi["img_url"].rpartition('/')[2].partition('.')[0],
                      wbi["sub_url"].rpartition('/')[2].partition('.')[0]])
    return ''.join(lookup[i] for i in mixinKeyEncTab)[:32]

WBI = get_wbi()

def dm_params():
    def gwh(w=1920, h=1080):
        rr = math.floor(114 * random.random()); return [2*w+2*h+3*rr, 4*w-h+rr, rr]
    def gof(st=10, sl=10):
        rr = math.floor(514 * random.random()); return [3*st+2*sl+rr, 4*st-4*sl+2*rr, rr]
    return {'dm_img_list': '[]',
            'dm_img_str': base64.b64encode(''.join(random.choices(string.printable, k=random.randint(16, 64))).encode())[:-2].decode(),
            'dm_cover_img_str': base64.b64encode(''.join(random.choices(string.printable, k=random.randint(32, 128))).encode())[:-2].decode(),
            'dm_img_inter': json.dumps({'ds': [], 'wh': gwh(), 'of': gof(random.randint(0, 100), 0)}, separators=(',', ':'))}

def sign(q):
    q['wts'] = round(time.time())
    q = {k: ''.join(c for c in str(v) if c not in "!'()*") for k, v in sorted(q.items())}
    q['w_rid'] = hashlib.md5((urllib.parse.urlencode(q) + WBI).encode()).hexdigest()
    return q

def arc(pn, tries=8):
    last = None
    for attempt in range(tries):
        S.cookies.set("buvid3", f"{uuid.uuid4()}infoc", domain=".bilibili.com")
        q = {'keyword': '', 'mid': MID, 'order': 'pubdate', 'order_avoided': 'true', 'platform': 'web',
             'pn': pn, 'ps': PS, 'tid': 0, 'web_location': '333.1387', 'special_type': '', 'index': 0, **dm_params()}
        try:
            r = S.get("https://api.bilibili.com/x/space/wbi/arc/search", params=sign(q), timeout=20)
            j = r.json()
        except Exception:
            last = "html"; time.sleep(min(20, 3 + attempt * 2)); continue
        if j.get("code") == 0 and isinstance(j.get("data", {}).get("list"), dict):
            return j
        last = j.get("code")
        time.sleep(min(20, 3 + attempt * 2))
    raise RuntimeError(f"page {pn} failed, last={last}")

def fetch_all():
    j = arc(1)
    page = j["data"]["page"]
    total = page["count"]; ps = page["ps"]
    pages = math.ceil(total / ps)
    print(f"total={total} ps={ps} pages={pages}", flush=True)
    videos, excluded, seen = [], [], set()
    for pn in range(1, pages + 1):
        if pn > 1:
            j = arc(pn)
        for it in j["data"]["list"]["vlist"]:
            bvid = it.get("bvid")
            if not bvid or bvid in seen:
                continue
            seen.add(bvid)
            rec = {"bvid": bvid, "title": it.get("title", ""), "url": f"https://www.bilibili.com/video/{bvid}"}
            if it.get("is_charging_arc") or it.get("is_pay"):
                rec["reason"] = "charging_exclusive" if it.get("is_charging_arc") else "pay"
                excluded.append(rec); continue
            videos.append(rec)
        print(f"  page {pn}/{pages} collected={len(videos)} excluded={len(excluded)}", flush=True)
        time.sleep(1.0)
    return total, videos, excluded

# 冷却后重试：B站对 arc search 有间歇风控，先等冷却再抓取
for cycle in range(8):
    try:
        total, videos, excluded = fetch_all()
        break
    except RuntimeError as e:
        wait = 60 + cycle * 60
        print(f"FETCH BLOCKED ({e}); cooldown {wait}s (cycle {cycle+1}/8) ...", flush=True)
        time.sleep(wait)
else:
    raise SystemExit("GAVE UP after cooldown cycles")

out = {
    "uploader_mid": MID,
    "space_total": total,
    "charging_exclusive_count": len(excluded),
    "included_count": len(videos),
    "excluded_charging": excluded,
    "videos": videos,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"DONE -> {OUT} | included={len(videos)} excluded={len(excluded)} (space total {total})", flush=True)
