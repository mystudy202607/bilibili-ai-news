# B站 AI / 科技 热门视频榜

每天自动抓取 B站 科技区与全站热门内容，筛选 AI / 科技关键词视频，生成一份**每天 20 条、与前一天不重复**的深色科技风榜单网页。

- 🔗 在线演示（GitHub Pages）：<https://mystudy202607.github.io/bilibili-ai-news/>
- 📦 源码仓库：<https://github.com/mystudy202607/bilibili-ai-news>

## 功能

- **每日 20 条**：🚀 科技区热门 10 条 + 🌐 全站搜索推荐 10 条
- **每日不重复**：结果记录到历史文件，次日自动排除前一天出现过的视频，并优先推荐最近 7 天没出现过的内容
- **自动更新**：Windows 计划任务每天 08:00 自动抓取并重新生成网页（本地）
- **多级降级**：接口被风控（-352 / 403 / 412）时自动换 UA、换 Referer、降级到备用接口，搜索失败自动停止，不硬撞限流
- **纯静态页面**：所有数据写死在 HTML，双击即可离线打开，也可发布到 GitHub Pages

## 文件结构

| 文件 | 说明 |
|---|---|
| `index.html` | 榜单静态网页（GitHub Pages 入口） |
| `bilibili_ai_news_collector.py` | 采集器：热门榜 + 科技区榜 + 全站关键词搜索 + 去重 |
| `build_ai_news_page.py` | 网页生成器：把 JSON 数据渲染成静态 HTML |
| `bilibili_ai_news.json` | 最新一期榜单数据（UTF-8） |
| `bilibili_ai_news_history.json` | 每日展示历史的 BV 记录（用于去重） |
| `update_ai_news.ps1` | 每日自动更新脚本（采集 + 生成网页 + 写日志） |
| `setup_automation.ps1` | 注册 Windows 计划任务（每天 08:00） |

## 本地使用

```bash
# 1. 抓取并生成 JSON（每天 20 条）
python bilibili_ai_news_collector.py

# 2. 生成静态网页
python build_ai_news_page.py

# 3. 双击 index.html 即可查看
```

每天 08:00 自动更新（Windows）：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_automation.ps1
```

## 说明

- 仓库中的 `index.html` / `bilibili_ai_news.json` 是发布时的快照；本地日常更新仍在原工作目录执行，需要时手动 `git add -A && git commit && git push` 同步到仓库。
- 关键词覆盖 AI、GPT、大模型、机器人、自动驾驶、芯片、OpenAI、DeepSeek、算法、智能、算力、科技、数码、评测、手机、电脑等。
