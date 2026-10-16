# Bilibili 视频 / 音频批量下载工具（基于 yt-dlp）

一个围绕 [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) 构建的小工具集，用于把指定 B 站
UP 主空间里的视频（或仅音频）批量抓取下来。

- `download.py` —— 读取一个视频列表 JSON，调用 **本地虚拟环境里的 yt-dlp** 批量下载。
- `fetch_bili_videos.py` ——（可选）抓取某个 B 站空间的全部投稿，生成上面的列表 JSON。

> 本项目**不再内嵌 yt-dlp 源码**，而是通过 `pyproject.toml` 把 `yt-dlp` 声明为依赖，
> 由 `uv` 从 PyPI 安装到 `.venv/`。这样在一台新电脑上只要装了 `uv` 就能一键部署。

---

## 一、目录结构

```
.
├── pyproject.toml          # 项目配置：声明依赖 yt-dlp / requests，package=false
├── uv.lock                 # 锁定的依赖版本（保证可复现）
├── .gitignore
├── download.py             # 批量下载主程序
├── fetch_bili_videos.py    # （可选）抓取 B 站空间视频列表
├── probe_bili.py           # 调试用：验证 B 站 wbi 签名
├── json/
│   └── bilibili_video.json # 示例输入：视频列表（也可用 bilibili_videos.json）
├── bilibili_videos.json    # 某空间全量列表（398 个，已剔除 4 个充电专属）
└── output/                 # 下载产物默认落在这里（被 .gitignore 忽略）
```

---

## 二、环境要求

| 组件        | 说明                                                                 |
|-------------|----------------------------------------------------------------------|
| `uv`        | Python 包管理器，[官网安装](https://docs.astral.sh/uv/getting-started/)。本项目用它创建虚拟环境并装依赖。 |
| Python      | 3.10 及以上（`uv sync` / `uv run` 会自动用本机可用版本，或下载受管版本；连系统没装 Python 也能跑）。 |
| `ffmpeg`    | **视频和音频模式都需要**。B 站的视频流与音频流是分离的，必须用 ffmpeg 合并成单个文件（音频模式还要靠它把音轨抽取为 mp3）。`uv sync` 只装 Python 包、**不会**装 ffmpeg，需手动安装：macOS `brew install ffmpeg`，其它平台见 [ffmpeg 官网](https://ffmpeg.org)。 |
| 网络 / Cookie | 下载 B 站视频通常无需登录；如需大会员高码率或遇到风控，用 `--cookies` / `--cookies-from-browser`。 |

---

## 三、项目部署（全新电脑完整流程）

本目录本身可以作为一个干净的 Git 仓库发布（已移除克隆自 yt-dlp 的 `.git`）。
把项目推到你的远程仓库（或拷贝整个文件夹）后，新机器上：

```bash
# 1) 拿到项目（二选一）
git clone <你的仓库地址> yt-dlp && cd yt-dlp
# 或者直接拷贝本文件夹后 cd 进去

# 2) 一键创建虚拟环境并安装 yt-dlp + requests（从 PyPI）
uv sync
# 完成后会生成 .venv/，其中已包含 .venv/bin/yt-dlp

# 3) 安装 ffmpeg（视频/音频模式都必需，uv 不会帮你装）
brew install ffmpeg        # macOS
```

`uv sync` 做了什么：读取 `pyproject.toml` 里的 `dependencies`，把
`yt-dlp`（≥2026.8.19）和 `requests` 装进 `.venv/`，并依据 `uv.lock` 锁定版本。
**无需手动 `pip install`，也无需单独下载 yt-dlp 源码。**

> **等价更简写法**：其实可以跳过第 2 步手动 `uv sync`——直接 `uv run download.py ...` 时，
> `uv` 会**自动先同步环境**（装好 yt-dlp + requests）再运行脚本。

---

## 四、使用方法

推荐用 `uv run` 运行（它会自动激活 `.venv` 并同步依赖）：

```bash
uv run download.py -i ./json/bilibili_video.json -o ./output
```

> 等价写法（先 `uv sync` 后）：`.venv/bin/python download.py ...`

### 1) 批量下载视频（默认，含音频）

```bash
uv run download.py -i ./json/bilibili_video.json -o ./output
```

- `-i` 视频列表 JSON（支持 `{"videos":[...]}`、纯数组、字符串数组三种格式）
- `-o` 输出目录（不存在会自动创建）
- 文件名格式：`<标题> [<BV号>].<ext>`，自动清洗 `/ \ : * ? "` 等非法字符（含全角斜杠）
- 已存在的文件默认**跳过**（`--no-overwrites`），可随时重跑实现断点续传

### 2) 只下载音频（mp3）

```bash
uv run download.py -i ./json/bilibili_video.json -o ./output -t audio
```

会加上 `-x --audio-format mp3 --audio-quality 0`，只取最佳音轨并抽取为 mp3。
**需要系统已装 `ffmpeg`。**

### 3) 先预览、不真正下载（dry-run）

```bash
uv run download.py -i ./json/bilibili_video.json -o ./output --dry-run
```

只打印将要执行的 yt-dlp 命令和数量，不发任何网络请求，适合先确认参数。

### 4) 自定义画质 / 音质

```bash
# 视频：最高 360P（节省空间）
uv run download.py -i ./json/bilibili_video.json -o ./output -f "bv[height<=360]+ba/b"

# 音频：指定 bestaudio
uv run download.py -i ./json/bilibili_video.json -o ./output -t audio -f ba
```

`-f` 覆盖默认格式选择器（视频默认 `bv*+ba/b`，音频默认 `ba`）。

### 5) 需要登录 / 绕过风控时传 Cookie

```bash
# 方式 A：从浏览器直接读取（需关闭浏览器或允许读取）
uv run download.py -i ./json/bilibili_video.json -o ./output --cookies-from-browser chrome

# 方式 B：指定 cookie 文件（Netscape 格式）
uv run download.py -i ./json/bilibili_video.json -o ./output --cookies ~/cookies.txt
```

### 6) 并行下载（谨慎）

```bash
uv run download.py -i ./json/bilibili_video.json -o ./output --workers 2
```

`--workers N` 开启 N 路并行。**B 站有风控，建议 1~3**，值越大越容易触发限流。

### 7) （可选）重新生成视频列表

如果你想换一个 UP 主，或刷新列表，用 `fetch_bili_videos.py`（脚本顶部 `MID` 改为目标 UP 的 uid，`OUT` 改为输出路径）：

```bash
uv run fetch_bili_videos.py
```

它会调用 B 站 `wbi` 签名接口抓取空间投稿，自动剔除「充电专属」视频，输出 `bilibili_videos.json`。
脚本内置了冷却重试以应对 B 站风控，可能需要跑几分钟。

---

## 五、核心代码解释

### 5.1 `download.py` —— 批量下载

**① `find_yt_dlp(script_dir)`：定位 yt-dlp 可执行文件**
按优先级探测 `./.venv/bin/yt-dlp` → `./venv/bin/yt-dlp` → 系统 `PATH` 里的 `yt-dlp`。
这样无论依赖装在哪、或用户用系统版 yt-dlp，脚本都能自动找到，无需硬编码路径。

```python
def find_yt_dlp(script_dir):
    for rel in (".venv/bin/yt-dlp", "venv/bin/yt-dlp"):
        p = os.path.join(script_dir, rel)
        if os.path.isfile(p):
            return p
    return "yt-dlp"   # 回退到系统 PATH
```

**② `_safe(s)` / `_ILLEGAL`：文件名清洗**
B 站标题常含 `/ : * ? "` 等非法字符（甚至全角斜杠 `／`），直接落盘会失败。
用正则统一替换成下划线，并截断到 120 字符、去掉首尾空格/点。

```python
_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t／＼]')
def _safe(s):
    s = _ILLEGAL.sub("_", (s or "").strip()).strip(" .")
    return s[:120] or "video"
```

**③ `load_items(path)`：解析输入 JSON**
兼容本工具生成的 `{"videos":[...]}`，也兼容纯数组 `[url,...]` 与字符串数组
`["url1","url2"]`；每条提取 `(url, title)`，若只有 `bvid` 则拼成完整播放地址。

**④ `download_one(...)`：构造并执行 yt-dlp 命令**
这是下载的核心。拼出的命令含一组“抗造”参数：

```python
cmd = [ytdlp, url, "-P", out_dir, "-o", outtmpl, "--format", fmt,
       "--no-overwrites", "--retries", "10", "--fragment-retries", "10",
       "--concurrent-fragments", "4", "--ignore-errors", "--no-playlist"]
```
- `--no-overwrites`：已存在则跳过，支持断点续传 / 重跑。
- `--retries 10` / `--fragment-retries 10`：网络波动时自动重试（分片也重试）。
- `--concurrent-fragments 4`：并行下载分片，提速。
- `--ignore-errors`：单条失败不中断整批。
- `--no-playlist`：防止 yt-dlp 误把合集当播放列表整页下载。
- 输出模板 `f"{name} [%(id)s].%(ext)s"`：标题 + BV 号，便于去重与识别。

音频模式额外追加：

```python
if atype == "audio":
    cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
```

`--dry-run` 时本函数**只返回拼好的命令字符串、不真正执行**，供 `main` 打印预览。

**⑤ `main()`：参数解析、dry-run、并行调度**
- `argparse` 解析 `-i -o -t -f --workers --cookies --cookies-from-browser --dry-run -q`。
- `-t/--type`：`video`（默认，画质 `bv*+ba/b`）与 `audio`（画质 `ba`，并触发上面的 `-x`）。
- dry-run 分支：仅打印示例命令与数量后返回，完全不发网络请求。
- 正式下载：用 `ThreadPoolExecutor(max_workers=workers)` 开多线程并行；
  用 `threading.Lock()` 保护 `ok` / `fail` 计数器，避免并发写竞争；
  串行（`--workers 1`）则逐条顺序执行。

```python
if args.workers <= 1:
    for i, it in enumerate(items):
        worker((i, it))
else:
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(worker, [(i, it) for i, it in enumerate(items)]))
```

### 5.2 `fetch_bili_videos.py` —— 抓取 B 站空间列表

**① 配置与会话**
顶部常量 `MID`（目标 UP 的 uid）、`OUT`（输出 JSON 路径）、`PS=50`（每页条数）。
构造一个带 UA / Referer / Origin 的 `requests.Session`，并伪造 `buvid3` Cookie
（`f"{uuid.uuid4()}infoc`）—— B 站接口要求携带该 Cookie，缺失极易触发风控。

**② wbi 签名（最关键的反爬环节）**
B 站 `x/space/wbi/arc/search` 必须带 `w_rid` 签名，否则返回 `-352`。

- `mixinKeyEncTab`：当前混淆表（73 个元素，B 站会更新，**用错表会 -352**）。
- `get_wbi()`：从 `nav` 接口取 `img_url` / `sub_url` 的文件名拼接成 64 位串，
  按 `mixinKeyEncTab` 重排后取前 32 位，得到 mixin key（即 `WBI`）。
- `dm_params()`：生成随机 base64 的弹幕干扰参数，进一步降低风控概率。
- `sign(q)`：加 `wts` 时间戳 → 按 key 排序 → **过滤值中的 `"!'()*`** →
  `urlencode` 拼接 mixin key → `md5` 得到 `w_rid`：

```python
def sign(q):
    q['wts'] = round(time.time())
    q = {k: ''.join(c for c in str(v) if c not in "!'()*") for k, v in sorted(q.items())}
    q['w_rid'] = hashlib.md5((urllib.parse.urlencode(q) + WBI).encode()).hexdigest()
    return q
```

**③ `arc(pn, tries=8)`：带重试地抓单页**
请求 `x/space/wbi/arc/search`；若抛异常或响应 `code != 0`，按 `3 + attempt*2` 秒
冷却后重试，最多 8 次。每次重试都刷新 `buvid3`，进一步规避风控。

**④ `fetch_all()`：翻页收集 + 剔除充电专属**
先取第 1 页得到总数 `count` 与每页 `ps`，算出总页数；逐页遍历 `vlist`：
- 用 `seen` 集合对 `bvid` 去重；
- `is_charging_arc` 或 `is_pay` 标记为真的，归入 `excluded`（充电专属 / 付费），
  其余归入 `videos`；
- 每页之间 `sleep(1.0)` 降低请求频率。

**⑤ 外层冷却重试**
B 站对空间接口有间歇风控。`fetch_all()` 若整轮失败，外层循环最多 8 轮，
每轮冷却 `60 + cycle*60` 秒后重抓，全部失败才放弃（避免永久卡死）。

**⑥ 写出 JSON**
最终写 `bilibili_videos.json`，结构为：

```json
{
  "uploader_mid": 49246269,
  "space_total": 398,
  "charging_exclusive_count": 4,
  "included_count": 394,
  "excluded_charging": [ {"bvid","title","url","reason"} ],
  "videos": [ {"bvid","title","url"} ]
}
```

`download.py` 后续直接消费这个 `videos` 数组。

---

## 六、常见问题

- **报 ffmpeg 相关错误（视频或音频模式都可能出现）**：B 站视频/音频流是分离的，必须靠 ffmpeg 合并（视频）或抽取（音频）。`uv sync` 不会装 ffmpeg，请先 `brew install ffmpeg`（macOS）。
- **下载个别视频失败 / 报 -352 / 风控**：多为 B 站对服务器 IP 的限流。脚本已带 `--retries 10`；可加 `--cookies-from-browser chrome` 或更换网络后重跑（重跑会跳过已下完的）。
- **`fetch_bili_videos.py` 报 -352**：几乎都是 wbi 签名问题——确认 `mixinKeyEncTab` 是当前版本、且 `sign()` 里过滤了 `"!'()*"`，并携带了 `buvid3` Cookie。
- **想改 yt-dlp 源码 / 用最新未发布特性**：本项目默认从 PyPI 装正式版。若需改源码，见下一节。

---

## 七、恢复 yt-dlp 源码（进阶，一般无需）

本项目刻意改为「依赖 yt-dlp」而非「内嵌源码」，以保证部署简单。若你确实要基于
yt-dlp 源码做二次开发，转换前已把原始克隆源码打包备份在：

```
/Users/zhang/WorkBuddy/yt-dlp-source-backup-20261016.tar.gz
```

解包即可拿到完整的 `yt_dlp/` 源码、`devscripts/` 等（不含 `.venv`）。
