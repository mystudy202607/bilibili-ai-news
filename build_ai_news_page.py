# -*- coding: utf-8 -*-
"""根据 bilibili_ai_news.json 生成静态展示页 bilibili_ai_news/index.html

所有数据写死在 HTML 里，双击 index.html 即可离线打开，无需服务器。
数据更新后重新运行本脚本即可重新生成。
"""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "bilibili_ai_news.json"
OUT_DIR = ROOT / "bilibili_ai_news"
OUT_FILE = OUT_DIR / "index.html"


def fmt_num(n: int) -> str:
    if n >= 100_000_000:
        s = f"{n / 100_000_000:.1f}"
        return s[:-2] + "亿" if s.endswith(".0") else s + "亿"
    if n >= 10_000:
        s = f"{n / 10_000:.1f}"
        return s[:-2] + "万" if s.endswith(".0") else s + "万"
    return str(n)


def fmt_date(ts: int) -> str:
    if not ts:
        return "-"
    t = time.localtime(ts)
    return f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d}"


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>B站 AI / 科技 热门视频榜</title>
<style>
:root{
  --bg:#05070f;
  --text:#e9edf9;
  --muted:#9aa4c4;
  --card:rgba(255,255,255,.045);
  --card-strong:rgba(255,255,255,.075);
  --border:rgba(255,255,255,.10);
  --blue:#4f8cff;
  --cyan:#3cd9ff;
  --purple:#9d6bff;
  --pink:#ff8fd0;
  --radius:18px;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{color-scheme:dark;}
body{
  min-height:100vh;
  background:
    radial-gradient(900px 520px at 12% -8%, rgba(79,140,255,.22), transparent 60%),
    radial-gradient(900px 520px at 88% 8%, rgba(157,107,255,.20), transparent 60%),
    radial-gradient(720px 480px at 50% 112%, rgba(60,217,255,.10), transparent 60%),
    var(--bg);
  background-attachment:fixed;
  color:var(--text);
  font-family:"PingFang SC","Microsoft YaHei","Noto Sans SC",system-ui,-apple-system,"Segoe UI",sans-serif;
  line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
body::before{
  content:"";
  position:fixed;inset:0;
  background-image:
    linear-gradient(rgba(255,255,255,.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.028) 1px, transparent 1px);
  background-size:44px 44px;
  -webkit-mask-image:radial-gradient(ellipse at 50% 0%, rgba(0,0,0,.9), transparent 75%);
  mask-image:radial-gradient(ellipse at 50% 0%, rgba(0,0,0,.9), transparent 75%);
  pointer-events:none;
}
.wrap{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:56px 22px 70px;}
header{text-align:center;margin-bottom:38px;}
.eyebrow{
  display:inline-flex;align-items:center;gap:10px;
  font-size:12px;letter-spacing:.35em;color:var(--muted);text-transform:uppercase;
}
.eyebrow::before,.eyebrow::after{content:"";width:28px;height:1px;}
.eyebrow::before{background:linear-gradient(90deg,transparent,var(--blue));}
.eyebrow::after{background:linear-gradient(90deg,var(--purple),transparent);}
h1{
  margin:14px 0 10px;
  font-size:clamp(26px,4.6vw,42px);
  font-weight:800;letter-spacing:.02em;
  background:linear-gradient(92deg,#7fb2ff 0%,#3cd9ff 42%,#c79bff 78%,#ff8fd0 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
}
.sub{color:var(--muted);font-size:14.5px;}
.stats{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-top:22px;}
.chip{
  display:inline-flex;align-items:center;gap:7px;
  padding:7px 14px;border-radius:999px;
  background:var(--card);border:1px solid var(--border);
  font-size:13px;backdrop-filter:blur(10px);
}
.chip b{color:#8cc3ff;font-weight:700;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;}
.card{
  position:relative;
  display:flex;flex-direction:column;
  padding:20px;
  background:linear-gradient(160deg,var(--card-strong),var(--card));
  border:1px solid var(--border);
  border-radius:var(--radius);
  backdrop-filter:blur(14px);
  overflow:hidden;
  animation:rise .5s ease both;
  transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease;
}
.card::before{
  content:"";position:absolute;top:0;left:16px;right:16px;height:1px;
  background:linear-gradient(90deg,transparent,rgba(124,186,255,.7),transparent);
  opacity:0;transition:opacity .22s ease;
}
.card:hover{
  transform:translateY(-4px);
  border-color:rgba(124,186,255,.45);
  box-shadow:0 18px 44px rgba(0,0,0,.5),0 0 26px rgba(79,140,255,.14);
}
.card:hover::before{opacity:1;}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.card-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;}
.rank{font-size:12px;font-weight:700;color:#6f7ba3;letter-spacing:.12em;}
.badge{
  display:inline-flex;align-items:center;gap:5px;
  font-size:12px;font-weight:700;color:#fff;
  padding:3px 10px;border-radius:999px;
  background:linear-gradient(90deg,#ff9d3f,#ff4f7e);
  box-shadow:0 4px 14px rgba(255,97,105,.35);
}
.title{
  font-size:16px;font-weight:650;line-height:1.55;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}
.divider{height:1px;background:var(--border);margin:16px 0 14px;}
.owner{display:flex;align-items:center;gap:10px;}
.avatar{
  width:32px;height:32px;border-radius:50%;flex:none;
  display:grid;place-items:center;
  font-size:14px;font-weight:700;color:#fff;
  background:linear-gradient(135deg,var(--blue),var(--purple));
}
.owner-name{font-size:13.5px;font-weight:600;}
.owner-tag{font-size:11.5px;color:var(--muted);}
.meta{display:flex;flex-wrap:wrap;gap:12px 16px;margin-bottom:20px;color:var(--muted);font-size:13px;}
.meta-item{display:inline-flex;align-items:center;gap:6px;}
.meta-item svg{width:14px;height:14px;opacity:.85;}
.meta-item b{color:#dbe4ff;font-weight:600;}
.cta{
  margin-top:auto;
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:10px 16px;border-radius:12px;
  font-size:13.5px;font-weight:600;color:#fff;text-decoration:none;
  background:linear-gradient(92deg,var(--blue),var(--purple));
  border:1px solid rgba(255,255,255,.14);
  transition:filter .2s ease,transform .2s ease;
}
.cta:hover{filter:brightness(1.15);transform:translateY(-1px);}
footer{margin-top:44px;text-align:center;color:#5f688a;font-size:12px;}
.notice{
  margin:0 0 20px;
  padding:14px 18px;
  border:1px solid rgba(124,186,255,.28);
  border-radius:14px;
  background:rgba(79,140,255,.08);
  color:#c6d3f0;
  font-size:13px;
  line-height:1.7;
}
.notice strong{color:#8cc3ff;}
.notice a{color:#5fd0ff;text-decoration:none;}
.notice a:hover{text-decoration:underline;}
.group-head{
  display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  margin:6px 2px 14px;padding-bottom:10px;border-bottom:1px solid var(--border);
}
.group-head h2{
  font-size:18px;font-weight:700;
  background:linear-gradient(92deg,#7fb2ff,#c79bff);
  -webkit-background-clip:text;background-clip:text;color:transparent;
}
.group-head small{color:var(--muted);font-size:13px;}
.grid{margin-bottom:36px;}
@media (max-width:640px){.wrap{padding:38px 16px 52px;}h1{margin-top:12px;}}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none !important;transition:none !important;}
}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="eyebrow">Bilibili Tech · AI News</span>
    <h1>B站 AI / 科技 热门视频榜</h1>
    <p class="sub">科技区热门 10 条 + 全站搜索推荐 10 条 · 每日更新 · 与昨日不重复</p>
    <div class="stats">
      <span class="chip">视频 <b>@@COUNT@@</b> 条</span>
      <span class="chip">科技区 <b>@@TECH@@</b> 条</span>
      <span class="chip">全站搜索 <b>@@ALL@@</b> 条</span>
      <span class="chip">总播放 <b>@@TOTAL_VIEWS@@</b></span>
      <span class="chip">更新 <b>@@UPDATED@@</b></span>
    </div>
  </header>
  <main id="content"></main>
  <div class="notice">
    <strong>更新说明：</strong>本页面是发布快照，不是实时榜单。站长的电脑基本只在周末早上开机，
    自动更新（原计划每天 08:00，已设置“错过就尽快补跑”）通常在开机后执行，
    因此本站一般每周末刷新一次；偶尔周末没开机，本周就不会有新快照。
    如果你需要<strong>每天自动更新</strong>的版本，请克隆
    <a href="https://github.com/mystudy202607/bilibili-ai-news" target="_blank" rel="noopener noreferrer">源代码仓库</a>，
    在本地按 README 步骤运行（每天 08:00 自动任务），或自行部署到 GitHub Actions 等定时环境。
  </div>
  <footer>数据来源：bilibili_ai_news.json · 本地双击 index.html 也可离线查看</footer>
</div>
<script>
const VIDEOS = @@DATA@@;
const KEYWORDS = ["AI","GPT","大模型","机器人","自动驾驶","芯片","OpenAI","DeepSeek","算法","智能","算力","模型训练","人工智能","模型"];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const trim1 = s => s.endsWith(".0") ? s.slice(0,-2) : s;
const fmt = n => n >= 1e8 ? trim1((n/1e8).toFixed(1)) + "亿" : n >= 1e4 ? trim1((n/1e4).toFixed(1)) + "万" : String(n);
const fmtDate = ts => {
  if (!ts) return "-";
  const d = new Date(ts*1000), p = n => String(n).padStart(2,"0");
  return d.getFullYear() + "-" + p(d.getMonth()+1) + "-" + p(d.getDate());
};
const hot = t => KEYWORDS.some(k => (t || "").toLowerCase().includes(k.toLowerCase()));
const ICONS = {
  play:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 5.5v13l11-6.5z" fill="currentColor" stroke="none"/></svg>',
  like:'<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21s-7.5-4.7-10-9.3C.5 8.5 2.6 5 6 5c2.2 0 3.7 1.2 4.5 2.6h3C14.3 6.2 15.8 5 18 5c3.4 0 5.5 3.5 4 6.7C19.5 16.3 12 21 12 21z"/></svg>',
  cal:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>'
};
const card = (v,i) => `
  <article class="card" style="animation-delay:${Math.min(i*50,500)}ms">
    <div class="card-head">
      <span class="rank">NO.${String(i+1).padStart(2,"0")}</span>
      ${hot(v.title) ? '<span class="badge">🔥 AI/科技</span>' : ""}
    </div>
    <h2 class="title">${esc(v.title)}</h2>
    <div class="divider"></div>
    <div class="owner">
      <span class="avatar">${esc((v.owner || "U").trim().charAt(0))}</span>
      <div>
        <div class="owner-name">${esc(v.owner)}</div>
        <div class="owner-tag">UP 主</div>
      </div>
    </div>
    <div class="meta">
      <span class="meta-item">${ICONS.play}<b>${fmt(v.view)}</b>&nbsp;播放</span>
      <span class="meta-item">${ICONS.like}<b>${fmt(v.like)}</b>&nbsp;点赞</span>
      <span class="meta-item">${ICONS.cal}${fmtDate(v.pubdate)}</span>
    </div>
    <a class="cta" href="${esc(v.url)}" target="_blank" rel="noopener noreferrer">前往 B站观看 ↗</a>
  </article>`;
const groups = {};
VIDEOS.forEach(v => {
  const g = (v.source === "科技区热门") ? "科技区热门" : "全站搜索";
  (groups[g] = groups[g] || []).push(v);
});
let pageHtml = "";
for (const g of ["科技区热门", "全站搜索"]) {
  const arr = (groups[g] || []).sort((a, b) => b.view - a.view);
  if (!arr.length) continue;
  const label = g === "科技区热门" ? "🚀 科技区热门" : "🌐 全站搜索推荐";
  pageHtml += `<div class="group-head"><h2>${label}</h2><small>${arr.length} 条</small></div>` +
              `<div class="grid">${arr.map(card).join("")}</div>`;
}
document.getElementById("content").innerHTML = pageHtml;
</script>
</body>
</html>
"""


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    data.sort(key=lambda v: int(v.get("view", 0) or 0), reverse=True)

    total_views = sum(int(v.get("view", 0) or 0) for v in data)
    latest = max((int(v.get("pubdate", 0) or 0) for v in data), default=0)
    tech_n = sum(1 for v in data if v.get("source") == "科技区热门")
    all_n = len(data) - tech_n
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    html = (
        TEMPLATE.replace("@@DATA@@", payload)
        .replace("@@COUNT@@", str(len(data)))
        .replace("@@TECH@@", str(tech_n))
        .replace("@@ALL@@", str(all_n))
        .replace("@@TOTAL_VIEWS@@", fmt_num(total_views))
        .replace("@@UPDATED@@", fmt_date(latest))
    )

    OUT_DIR.mkdir(exist_ok=True)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"已生成: {OUT_FILE} ({len(data)} 条，总播放 {fmt_num(total_views)})")


if __name__ == "__main__":
    main()
