#!/usr/bin/env python3
"""批量下载 B 站视频 —— 调用本项目内已部署的 yt-dlp。

用法:
    python download.py -i ./json/bilibili_video.json -o ./output

说明:
    - 默认调用脚本同目录下的 .venv/bin/yt-dlp（找不到时回退到系统 PATH 的 yt-dlp）
    - 自动从 JSON 中读取视频地址（支持本工具生成的 {"videos":[...]}，也支持纯数组 / 字符串数组）
    - 文件名格式: <清洗后的标题> [<BV号>].<ext>，自动规避 / \\ : 等非法字符
    - 已存在的文件默认跳过（--no-overwrites），可断点续传/重跑
    - 默认串行下载；可用 --workers N 开启 N 路并行（注意 B 站风控，建议 1~3）
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 文件名中的非法字符（含全角斜杠）统一替换为下划线
_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t／＼]')


def _safe(s: str) -> str:
    s = _ILLEGAL.sub("_", (s or "").strip()).strip(" .")
    return s[:120] or "video"


def find_yt_dlp(script_dir: str) -> str:
    for rel in (os.path.join(".venv", "bin", "yt-dlp"),
                os.path.join("venv", "bin", "yt-dlp")):
        p = os.path.join(script_dir, rel)
        if os.path.isfile(p):
            return p
    return "yt-dlp"  # 回退到系统 PATH


def load_items(path: str):
    """返回 [(url, 标题), ...]"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = data.get("videos") or data.get("entries") or []
    else:
        items = data

    result = []
    for it in items:
        if isinstance(it, str):
            result.append((it, ""))
        elif isinstance(it, dict):
            url = it.get("url")
            if not url and it.get("bvid"):
                url = f"https://www.bilibili.com/video/{it['bvid']}"
            if not url:
                continue
            title = it.get("title") or it.get("bvid") or ""
            result.append((url, title))
    return result


def download_one(ytdlp, url, title, out_dir, fmt, atype, cookies, extra):
    name = _safe(title)
    outtmpl = f"{name} [%(id)s].%(ext)s"
    cmd = [ytdlp, url, "-P", out_dir, "-o", outtmpl, "--format", fmt,
           "--no-overwrites", "--retries", "10", "--fragment-retries", "10",
           "--concurrent-fragments", "4", "--ignore-errors", "--no-playlist"]
    if atype == "audio":
        # 仅下载音频：只取最佳音轨并抽取为 mp3（需系统已装 ffmpeg）
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
    if cookies:
        cmd += ["--cookies", cookies]
    if extra:
        cmd += extra
    if ARGS.dry_run:
        return (name, 0 if not ARGS.quiet else 0, " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    return (name, proc.returncode, proc.stdout[-400:] if proc.stdout else "")


def main():
    ap = argparse.ArgumentParser(description="批量下载 B 站视频 (本地 yt-dlp)")
    ap.add_argument("-i", "--input", required=True, help="视频列表 JSON 路径")
    ap.add_argument("-o", "--output", required=True, help="输出目录")
    ap.add_argument("-t", "--type", default="video", choices=["video", "audio"],
                    help="下载类型：video=视频(含音频，默认)；audio=仅音频(mp3)")
    ap.add_argument("--yt-dlp", default=None, help="yt-dlp 可执行文件路径（默认自动探测 .venv）")
    ap.add_argument("-f", "--format", default=None,
                    help="yt-dlp 画质/音质选择（默认 视频=bv*+ba/b，音频=ba 最佳音轨；可覆盖）")
    ap.add_argument("--workers", type=int, default=1,
                    help="并行下载数（默认 1，建议 1~3）")
    ap.add_argument("--cookies", default=None, help="cookie 文件（需要时传，如大会员高码率）")
    ap.add_argument("--cookies-from-browser", default=None,
                    help="从浏览器读取 cookie，如 chrome/safari/firefox")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要执行的命令，不下载")
    ap.add_argument("-q", "--quiet", action="store_true", help="减少输出")
    args = ap.parse_args()
    global ARGS
    ARGS = args

    atype = args.type
    fmt = args.format or ("ba" if atype == "audio" else "bv*+ba/b")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    ytdlp = args.yt_dlp or find_yt_dlp(script_dir)

    items = load_items(args.input)
    if not items:
        sys.exit(f"未在 {args.input} 中找到任何视频地址。")

    os.makedirs(args.output, exist_ok=True)

    extra = []
    if args.cookies_from_browser:
        extra += ["--cookies-from-browser", args.cookies_from_browser]

    if args.dry_run:
        print(f"[dry-run] yt-dlp: {ytdlp}")
        print(f"[dry-run] 输出目录: {os.path.abspath(args.output)}")
        print(f"[dry-run] 类型: {atype}（{'仅音频 mp3' if atype == 'audio' else '视频(含音频)'}）")
        print(f"[dry-run] 共 {len(items)} 个视频，示例命令:")
        u, t = items[0]
        _, _, cmd = download_one(ytdlp, u, t, args.output, fmt, atype, args.cookies, extra)
        print(f"  {cmd}")
        print(f"[dry-run] 实际执行: python download.py -i {args.input} -o {args.output}"
              + (" --cookies-from-browser " + args.cookies_from_browser if args.cookies_from_browser else ""))
        return

    print(f"yt-dlp: {ytdlp}")
    print(f"输出目录: {os.path.abspath(args.output)}")
    print(f"类型: {atype}（{'仅音频 mp3' if atype == 'audio' else '视频(含音频)'}）；待下载: {len(items)} 个，并行数: {args.workers}")
    print("-" * 60)

    ok = 0
    fail = 0
    lock = threading.Lock()

    def worker(idx_url_title):
        idx, (url, title) = idx_url_title
        name, rc, out = download_one(ytdlp, url, title, args.output, fmt, atype, args.cookies, extra)
        with lock:
            if rc == 0:
                nonlocal ok
                ok += 1
                if not args.quiet:
                    print(f"[{idx + 1}/{len(items)}] ✓ {name}")
            else:
                nonlocal fail
                fail += 1
                print(f"[{idx + 1}/{len(items)}] ✗ {name} (exit {rc})")
                if not args.quiet and out:
                    print("    " + out.replace("\n", "\n    ")[:300])
        return rc

    if args.workers <= 1:
        for i, it in enumerate(items):
            worker((i, it))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(worker, [(i, it) for i, it in enumerate(items)]))

    print("-" * 60)
    print(f"完成: 成功 {ok} 个, 失败 {fail} 个, 跳过/已存在若干（重跑可续传）。")


if __name__ == "__main__":
    main()
