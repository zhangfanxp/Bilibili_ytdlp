import requests, time, hashlib, urllib.parse, json, uuid, random, string, base64, math

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
S = requests.Session()
S.headers.update({"User-Agent": UA, "Referer": "https://space.bilibili.com/49246269/video",
                  "Origin": "https://space.bilibili.com", "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8"})
S.cookies.set("buvid3", f"{uuid.uuid4()}infoc", domain=".bilibili.com")
mixinKeyEncTab = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
    12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
def get_wbi():
    r = S.get("https://api.bilibili.com/x/web-interface/nav", timeout=20)
    wbi = r.json()["data"]["wbi_img"]
    lookup=''.join([wbi["img_url"].rpartition('/')[2].partition('.')[0],wbi["sub_url"].rpartition('/')[2].partition('.')[0]])
    return ''.join(lookup[i] for i in mixinKeyEncTab)[:32]
WBI=get_wbi()
def dm_params():
    def gwh(w=1920,h=1080):
        rr=math.floor(114*random.random());return[2*w+2*h+3*rr,4*w-h+rr,rr]
    def gof(st=10,sl=10):
        rr=math.floor(514*random.random());return[3*st+2*sl+rr,4*st-4*sl+2*rr,rr]
    return{'dm_img_list':'[]','dm_img_str':base64.b64encode(''.join(random.choices(string.printable,k=random.randint(16,64))).encode())[:-2].decode(),
          'dm_cover_img_str':base64.b64encode(''.join(random.choices(string.printable,k=random.randint(32,128))).encode())[:-2].decode(),
          'dm_img_inter':json.dumps({'ds':[],'wh':gwh(),'of':gof(random.randint(0,100),0)},separators=(',',':'))}
def sign(q):
    q['wts']=round(time.time())
    q={k:''.join(c for c in str(v) if c not in "!'()*") for k,v in sorted(q.items())}
    q['w_rid']=hashlib.md5((urllib.parse.urlencode(q)+WBI).encode()).hexdigest()
    return q
def arc(pn, tries=5):
    for t in range(tries):
        q={'keyword':'','mid':49246269,'order':'pubdate','order_avoided':'true','platform':'web',
           'pn':pn,'ps':30,'tid':0,'web_location':'333.1387','special_type':'','index':0,**dm_params()}
        r=S.get("https://api.bilibili.com/x/space/wbi/arc/search",params=sign(q),timeout=20)
        j=r.json()
        if j.get("code")==0 and "list" in j.get("data",{}):
            return j
        print(f"  retry {t}: code={j.get('code')} keys={list(j.get('data',{}).keys()) if isinstance(j.get('data'),dict) else type(j.get('data'))}")
        time.sleep(1.5)
    raise SystemExit("arc failed")

j=arc(1)
data=j["data"]
print("data keys:", list(data.keys()))
print("slist:", data["list"].get("slist"))
vl=data["list"]["vlist"]
it=vl[0]
print("ALL KEYS:", sorted(it.keys()))
print("FOUND special/charging:", {k:v for k,v in it.items() if k in ("special_type","charging","is_charging","attribute")})
# recursively search
def find(obj, keys, out=None):
    if out is None: out={}
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in keys: out.setdefault(k,[]).append(v)
            find(v,keys,out)
    elif isinstance(obj,list):
        for v in obj: find(v,keys,out)
    return out
print("RECURSIVE special/charging in item0:", find(it, {"special_type","charging","is_charging"}))
