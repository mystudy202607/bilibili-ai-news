# -*- coding: utf-8 -*-
"""
B站 科技/AI 新闻数据采集器

方案 (每天恰好 20 条 + 与前一天不重复):
  科技区热门 10 条: 全站当天热门(popular 6页) + 科技区榜(ranking/v2 rid=188)
  全站搜索推荐 10 条: 关键词搜索全站 (慢速, 失败 2 次即停)
  去重: 排除前一天出现过的视频 (历史记录在 bilibili_ai_news_history.json)
  补足: 优先选最近 7 天没出现过的视频; 不足时科技池补位, 最终保证恰好 20 条
  - API 失败/403 -> 随机 User-Agent / Referer 重试

要求:
  - 不依赖 Selenium / Playwright，仅用 httpx
  - 每次请求间隔 >= 1 秒
  - 输出 bilibili_ai_news.json (UTF-8)
"""

import asyncio
import json
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

# ---- 编码兜底：终端直跑时交给 Python 原生控制台输出（任何代码页都正常）；
#      仅当输出被重定向到文件/管道时，强制 UTF-8，避免写入 GBK 导致乱码。 ----
try:
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# ---- 输出文件 ----
OUTPUT_FILE = Path(__file__).resolve().parent / "bilibili_ai_news.json"
HISTORY_FILE = Path(__file__).resolve().parent / "bilibili_ai_news_history.json"

# ---- 数量 ----
TECH_TARGET = 10    # 科技区热门
ALL_TARGET = 10     # 全站搜索推荐

# ---- 关键词 ----
STRICT_KEYWORDS = [
    "AI", "GPT", "大模型", "机器人", "自动驾驶", "芯片",
    "OpenAI", "DeepSeek", "算法", "智能", "算力", "模型训练", "人工智能",
]
RELAXED_KEYWORDS = ["AI", "GPT", "模型", "智能", "芯片", "机器人", "算法"]
POOL_KEYWORDS = list(dict.fromkeys(
    STRICT_KEYWORDS + RELAXED_KEYWORDS +
    ["科技", "数码", "评测", "手机", "电脑", "硬件", "显卡", "CPU", "GPU", "华为", "无人机", "笔记本"]
))
SEARCH_KEYWORDS = ["AI", "大模型", "人工智能", "芯片", "机器人", "GPT", "DeepSeek"]

# ---- 随机 UA 池（403/反爬时切换） ----
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

REQUEST_INTERVAL = 1.0  # 秒

_buvid_cookies_cache: dict = {}


async def get_buvid_cookies() -> dict:
    """获取匿名 buvid3/buvid4 cookie，避免接口风控(412/-352)。"""
    if _buvid_cookies_cache:
        return _buvid_cookies_cache
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get("https://api.bilibili.com/x/frontend/finger/spi")
                data = resp.json().get("data", {})
                if data.get("b_3"):
                    _buvid_cookies_cache.update({
                        "buvid3": data["b_3"],
                        "buvid4": data.get("b_4", ""),
                    })
                    return _buvid_cookies_cache
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(1.5)
    _buvid_cookies_cache.update({"buvid3": "", "buvid4": ""})
    return _buvid_cookies_cache


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001 - 历史文件损坏时重新开始
            return {}
    return {}


def save_history(history: dict) -> None:
    keep = sorted(history.keys())[-30:]  # 只保留最近 30 天
    trimmed = {k: history[k] for k in keep}
    HISTORY_FILE.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")


def matches_any(title: str, keywords: list) -> bool:
    title_text = (title or "").lower()
    return any(keyword.lower() in title_text for keyword in keywords)


def dedupe(videos: list) -> list:
    seen, out = set(), []
    for v in videos:
        key = v.get("bvid") or v.get("url") or v.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def format_video(item: dict) -> dict:
    stats = item.get("stats") or item.get("stat") or {}
    owner = item.get("author") or item.get("owner") or {}
    bvid = item.get("bvid") or ""
    url = item.get("url") or item.get("short_link") or item.get("link") or ""
    if not url:
        if bvid:
            url = f"https://www.bilibili.com/video/{bvid}"
        elif item.get("aid"):
            url = f"https://www.bilibili.com/video/av{item.get('aid')}"

    return {
        "title": item.get("title", ""),
        "owner": owner.get("name", "") if isinstance(owner, dict) else str(owner),
        "view": int(stats.get("view", 0) or item.get("view", 0) or item.get("views", 0) or 0),
        "like": int(stats.get("like", 0) or item.get("like", 0) or item.get("likes", 0) or 0),
        "pubdate": int(item.get("pubdate", 0) or item.get("publish_time", 0) or 0),
        "url": url,
        "bvid": bvid,
    }


def format_legacy(item: dict) -> dict:
    """老版 ranking 接口字段兼容 (无 pubdate/like, 稍后由 view 接口补全)。"""
    bvid = item.get("bvid", "")
    return {
        "bvid": bvid,
        "title": item.get("title", ""),
        "owner": item.get("author", ""),
        "view": int(item.get("play", 0) or 0),
        "like": 0,
        "pubdate": 0,
        "url": f"https://www.bilibili.com/video/{bvid}",
    }


async def get_json_with_retry(url: str, params: dict | None = None, tries: int = 3) -> dict:
    last_err = None
    cookies = await get_buvid_cookies()
    for attempt in range(1, tries + 1):
        referer = "https://search.bilibili.com/" if "/search/" in url else "https://www.bilibili.com"
        headers = {
            "User-Agent": random.choice(UA_POOL),
            "Referer": referer,
            "Origin": "https://www.bilibili.com",
        }
        try:
            async with httpx.AsyncClient(headers=headers, cookies=cookies, timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    last_err = RuntimeError(f"HTTP {resp.status_code} on {url} (attempt {attempt})")
                    if attempt < tries:
                        await asyncio.sleep(REQUEST_INTERVAL * attempt)  # 退避: 1s, 2s, ...
                        continue
                    raise last_err
                data = resp.json()
                if not isinstance(data, dict):
                    raise RuntimeError("Unexpected JSON response format")
                return data
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            last_err = exc
            if attempt < tries:
                await asyncio.sleep(REQUEST_INTERVAL * attempt)
                continue
            raise
    raise last_err or RuntimeError("Unknown error while fetching JSON")


async def fetch_rank_list(url: str, params: dict, tries: int = 2) -> list:
    last_err = None
    for attempt in range(1, tries + 1):
        data = await get_json_with_retry(url, params=params, tries=1)
        if data.get("code") == 0:
            ranking = data.get("data", {})
            items = ranking.get("list") or ranking.get("archives") or []
            if not isinstance(items, list):
                items = []
            await asyncio.sleep(REQUEST_INTERVAL)  # 每次请求间隔 >= 1 秒
            return [format_video(item) for item in items]
        last_err = RuntimeError(f"API 错误: {data.get('message', 'unknown')} (attempt {attempt})")
        await asyncio.sleep(REQUEST_INTERVAL)
    raise last_err


async def fetch_global_rank() -> list:
    # 全站热门 popular 接口最稳定，直接抓 6 页
    videos = []
    for pn in range(1, 7):
        data = await get_json_with_retry(
            "https://api.bilibili.com/x/web-interface/popular",
            {"pn": pn, "ps": 50},
        )
        if data.get("code") != 0:
            raise RuntimeError(f"popular 错误: {data.get('message')}")
        items = (data.get("data") or {}).get("list") or []
        videos.extend(format_video(item) for item in items)
        await asyncio.sleep(REQUEST_INTERVAL + random.uniform(0, 0.5))
    return videos


async def fetch_tech_rank() -> list:
    try:
        return await fetch_rank_list(
            "https://api.bilibili.com/x/web-interface/ranking/v2",
            {"rid": 188, "type": "all"},
        )
    except Exception as exc:  # noqa: BLE001 - 风控时降级到老版 ranking 接口
        print(f"  ranking/v2 科技区榜失败({exc})，改用老版 ranking 接口")
        data = await get_json_with_retry(
            "https://api.bilibili.com/x/web-interface/ranking",
            {"rid": 188, "day": 3, "type": 1},
        )
        if data.get("code") != 0:
            raise RuntimeError(f"legacy ranking 错误: {data.get('message')}")
        items = (data.get("data") or {}).get("list") or []
        await asyncio.sleep(REQUEST_INTERVAL)
        return [format_legacy(item) for item in items]


async def enrich_video(v: dict) -> None:
    """用 view 详情接口补全老版接口缺失的 pubdate/like/owner。"""
    try:
        data = await get_json_with_retry(
            "https://api.bilibili.com/x/web-interface/view",
            {"bvid": v.get("bvid", "")},
            tries=2,
        )
        if data.get("code") == 0:
            d = data.get("data") or {}
            stat = d.get("stat") or {}
            if stat.get("view") is not None:
                v["view"] = int(stat["view"])
            if stat.get("like") is not None:
                v["like"] = int(stat["like"])
            if d.get("pubdate"):
                v["pubdate"] = int(d["pubdate"])
            owner = d.get("owner") or {}
            if owner.get("name"):
                v["owner"] = owner["name"]
    except Exception:  # noqa: BLE001 - 补全失败不影响主流程
        pass
    await asyncio.sleep(REQUEST_INTERVAL)


async def fetch_search(keyword: str) -> list:
    await asyncio.sleep(12 + random.uniform(0, 5))  # 搜索请求明显放慢，避免限流
    data = await get_json_with_retry(
        "https://api.bilibili.com/x/web-interface/search/type",
        {"search_type": "video", "keyword": keyword, "order": "click", "page": 1},
        tries=1,  # 搜索不重试，失败即跳过，避免连续请求触发限流
    )
    if data.get("code") != 0:
        return []
    items = (data.get("data") or {}).get("result") or []
    out = []
    for it in items:
        if not isinstance(it, dict) or not it.get("bvid"):
            continue
        title = re.sub(r"</?em[^>]*>", "", it.get("title", "") or "")
        out.append({
            "bvid": it.get("bvid"),
            "title": title,
            "author": {"name": it.get("author", "")},
            "stats": {"view": it.get("play", 0), "like": it.get("like", 0)},
            "publish_time": it.get("pubdate", 0),
            "url": f"https://www.bilibili.com/video/{it.get('bvid')}",
        })
    return [format_video(i) for i in out]


def select_videos(videos: list, keywords: list) -> list:
    return [v for v in videos if matches_any(v.get("title", ""), keywords)]


async def collect_videos() -> tuple:
    stats = {}
    history = load_history()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    excluded_bvids = set(history.get(yesterday, []))
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    recent_bvids = set()
    for day, bvs in history.items():
        if week_ago <= day < yesterday:
            recent_bvids.update(bvs)

    used = set(excluded_bvids)

    def available(v: dict) -> bool:
        return v.get("bvid") not in used

    def rank_candidates(videos: list) -> list:
        return sorted(
            videos,
            key=lambda v: (0 if v.get("bvid") not in recent_bvids else 1, v.get("view", 0)),
            reverse=True,
        )

    tech_pool: list = []
    search_pool: list = []

    # 1) 科技池: 全站当天热门(6页) + 科技区当天榜
    hot_videos = await fetch_global_rank()
    stats["全站当天热门榜"] = len(hot_videos)
    tech_pool = dedupe(select_videos(hot_videos, POOL_KEYWORDS))
    try:
        tech_rank = await fetch_tech_rank()
        stats["科技区当天热门榜"] = len(tech_rank)
        tech_pool = dedupe(tech_pool + select_videos(tech_rank, POOL_KEYWORDS))
    except Exception as exc:  # noqa: BLE001 - 风控/接口异常时跳过
        print(f"  科技区榜获取失败，跳过: {exc}")

    # 2) 全站搜索池: 关键词搜索全站推荐 (慢速, 失败 2 次即停)
    search_failures = 0
    for kw in SEARCH_KEYWORDS:
        if search_failures >= 2:
            break
        try:
            hits = await fetch_search(kw)
        except Exception as exc:  # noqa: BLE001
            print(f"  搜索[{kw}]失败，跳过: {exc}")
            search_failures += 1
            await asyncio.sleep(3)
            continue
        stats["关键词搜索补充"] = stats.get("关键词搜索补充", 0) + len(hits)
        search_pool = dedupe(search_pool + select_videos(hits, POOL_KEYWORDS))
        if sum(1 for v in search_pool if available(v)) >= ALL_TARGET * 2:
            break

    # 候选池中被昨天排除的条数
    pool_union = dedupe(tech_pool + search_pool)
    stats["昨日去重"] = sum(1 for v in pool_union if v.get("bvid") in excluded_bvids)

    # 3) 组1: 科技区热门 10 条
    group_tech: list = []
    for v in rank_candidates([v for v in tech_pool if available(v)]):
        if len(group_tech) >= TECH_TARGET:
            break
        group_tech.append(v)
        used.add(v.get("bvid"))

    # 4) 组2: 全站搜索推荐 10 条
    group_all: list = []
    for v in rank_candidates([v for v in search_pool if available(v)]):
        if len(group_all) >= ALL_TARGET:
            break
        group_all.append(v)
        used.add(v.get("bvid"))

    # 全站不足 10 -> 用科技池剩余候选补位
    if len(group_all) < ALL_TARGET:
        before = len(group_all)
        for v in rank_candidates([v for v in tech_pool if available(v)]):
            if len(group_all) >= ALL_TARGET:
                break
            group_all.append(v)
            used.add(v.get("bvid"))
        if len(group_all) > before:
            stats["全站补位"] = len(group_all) - before

    group_tech.sort(key=lambda v: v.get("view", 0), reverse=True)
    group_all.sort(key=lambda v: v.get("view", 0), reverse=True)
    combined = group_tech + group_all

    # 5) 总量兜底: 仍不足 20 -> 允许复用历史(含昨日), 保证恰好 20 条
    if len(combined) < TECH_TARGET + ALL_TARGET:
        before_total = len(combined)
        extra_pool = rank_candidates(pool_union)
        combined_ids = {v.get("bvid") for v in combined}
        for v in extra_pool:
            if len(combined) >= TECH_TARGET + ALL_TARGET:
                break
            if v.get("bvid") not in combined_ids:
                combined.append(v)
                combined_ids.add(v.get("bvid"))
        if len(combined) > before_total:
            stats["总量兜底"] = len(combined) - before_total

    tech_ids = {v.get("bvid") for v in group_tech}
    for v in combined:
        v["source"] = "科技区热门" if v.get("bvid") in tech_ids else "全站搜索"

    selected = combined[: TECH_TARGET + ALL_TARGET]

    # 老版接口缺 pubdate/like 的条目，用 view 接口补全
    for v in selected:
        if not v.get("pubdate") or not v.get("like"):
            await enrich_video(v)

    history[today] = [v.get("bvid", "") for v in selected]
    save_history(history)
    return selected, stats


def save_results(videos: list) -> None:
    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(videos, handle, ensure_ascii=False, indent=2)


async def main() -> None:
    print("开始采集 B站 科技/AI 视频榜单 (每日 20 条)...")
    videos, stats = await collect_videos()
    save_results(videos)

    tech_n = sum(1 for v in videos if v.get("source") == "科技区热门")
    all_n = len(videos) - tech_n

    print("\n===== 采集结果 =====")
    source_keys = ["全站当天热门榜", "科技区当天热门榜", "关键词搜索补充"]
    src_desc = " + ".join(f"{k} {stats[k]} 条" for k in source_keys if k in stats)
    print(f"抓取总数: {sum(stats.get(k, 0) for k in source_keys)} 条 ({src_desc})")
    print(f"过滤后数量: {len(videos)} 条 (科技 {tech_n} + 全站 {all_n}) "
          f"(去除昨日重复 {stats.get('昨日去重', 0)} 条)")
    if stats.get("全站补位"):
        print(f"补充说明: 全站搜索不足，用科技池补位 {stats['全站补位']} 条")
    if stats.get("总量兜底"):
        print(f"补充说明: 候选不足，复用历史 {stats['总量兜底']} 条 (仅兜底)")
    if len(videos) != TECH_TARGET + ALL_TARGET:
        print(f"警告: 本次结果 {len(videos)} 条，未达到 {TECH_TARGET + ALL_TARGET} 条")
    for i, v in enumerate(videos[:3], 1):
        print(f"  TOP{i}: {v.get('title', '')}  (播放 {v.get('view', 0)})")
    print(f"\n已保存: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
