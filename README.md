# rss-to-qqemail
定时从 `feeds.opml`（RSS 订阅列表）抓取最近内容，并通过 SMTP 发送到邮箱。邮件内容为 **中英文对照：中文（英文）**（离线翻译，无需 Key）。默认配置为：**每天北京时间 09:00** 运行一次。

## 功能

- 从仓库内 `feeds.opml` 读取所有 `xmlUrl`（RSS/Atom）订阅源（你以后只需要改这个文件来增删订阅）
- 抓取最近 **24 小时**的新文章，汇总成一封邮件（HTML）
- 对每个订阅源设置超时（避免卡住）；抓取失败会跳过并在邮件末尾列出失败列表
- 通过 SMTP 发信（支持 `465/SMTP_SSL` 与 `587/STARTTLS`）
- 离线翻译：使用 **Argos Translate** 把站点名/标题等翻译为中文，并输出 **中英文对照**（无需任何 API Key）

## 订阅源（feeds.opml）

订阅源由仓库文件 `feeds.opml` 管理（只靠这个文件增删订阅）。

当前 `feeds.opml` 已包含：
- HN Popular Blogs 2025（博客合集）
- BestBlogs.dev AI（最近 1 天文章）

## 文件结构

```
.
├── rss_mailer.py
├── requirements.txt
├── feeds.opml
└── .github/
    └── workflows/
        └── rss_mailer.yml
```

## 配置（以 QQ 邮箱为例）

### 1) 开启 QQ 邮箱 SMTP 并获取授权码

QQ 邮箱网页版 → 设置 → 账户 → 开启 **SMTP 服务** → 生成 **授权码**（后续作为 `EMAIL_PASS` 使用）。

### 2) 配置 GitHub Secrets

仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，添加：

| Secret 名称 | 示例值 | 说明 |
|---|---|---|
| `SMTP_HOST` | `smtp.qq.com` | SMTP 服务器 |
| `SMTP_PORT` | `465` | QQ 常用 465（SSL） |
| `EMAIL_USER` | `123456@qq.com` | 发件邮箱 |
| `EMAIL_PASS` | `你的QQ邮箱授权码` | **不是**QQ登录密码 |
| `EMAIL_TO` | `yourname@outlook.com` | 收件邮箱（可以是 Outlook/QQ 等） |

> 如果你用的是其他邮箱：把 `SMTP_HOST/SMTP_PORT` 换成对应服务商的值即可（465=SSL，587=STARTTLS）。

## 中英文对照翻译（无需 Key）

本项目使用 **Argos Translate**（离线翻译）生成中英文对照（中文（英文））。首次运行会自动下载英语→中文模型（几十 MB），可能会慢 1–3 分钟；后续会通过 GitHub Actions cache 变快。

### requirements.txt

确保包含：

```txt
feedparser==6.0.11
python-dateutil==2.9.0.post0
argostranslate==1.9.6
```

### 工作流缓存（强烈推荐）

在 `.github/workflows/rss_mailer.yml` 的 `actions/setup-python` 后、`Install dependencies` 前加入：

```yaml
- name: Cache Argos Translate models
  uses: actions/cache@v4
  with:
    path: ~/.local/share/argos-translate
    key: argos-translate-en-zh-v1
```

## 定时运行（每天早上 9 点）

工作流文件：`.github/workflows/rss_mailer.yml`

默认 cron：

```yaml
on:
  schedule:
    - cron: "0 1 * * *"  # UTC 01:00 = 北京时间 09:00
  workflow_dispatch:
```

GitHub Actions 的 cron 使用 **UTC** 时区（不是北京时间）。

## 手动测试运行

仓库 → **Actions** → 选择工作流 → **Run workflow**。

运行成功后检查收件邮箱是否收到 “每日 RSS 摘要”。

## 自定义

### 新增/删除订阅源（只改 feeds.opml）

打开仓库根目录 `feeds.opml`，在任意 `<outline ...>` 分组里新增一行即可，例如：

```xml
<outline type="rss" text="某某站" title="某某站" xmlUrl="https://example.com/feed.xml"/>
```

**注意：**
1. 如果 URL 里包含 `&`，必须写成 `&amp;`  
   例如：`...rss?x=1&y=2` → `...rss?x=1&amp;y=2`
2. 保存并 Commit 后就会生效；不需要改 `rss_mailer.py`、不需要改 Secrets、也不需要改 workflow。

### 修改抓取窗口（默认最近 24 小时）

编辑 `rss_mailer.py`：
- `LOOKBACK_HOURS = 24`

### 修改运行时间（北京时间）

编辑 `.github/workflows/rss_mailer.yml` 的 cron（注意要换算成 UTC）：
- 北京时间 09:00 = UTC 01:00 → `0 1 * * *`
- 北京时间 08:00 = UTC 00:00 → `0 0 * * *`

### 邮件主题

工作流里可改：

```yaml
EMAIL_SUBJECT: "每日 RSS 摘要"
```

## 常见问题

1. **部分订阅源 403/超时**
   - 正常现象：有些站点会限制爬虫或不稳定。脚本会跳过，并在邮件末尾列出失败原因。

2. **发信失败（认证失败）**
   - QQ 邮箱必须使用「授权码」，并确保 SMTP 已开启。
   - 检查 GitHub Secrets 是否填对、是否有多余空格。

3. **定时触发有延迟**
   - GitHub 定时任务可能延迟几分钟，属于正常情况。

4. **首次运行很慢**
   - 多数情况下是在下载并安装 Argos 离线翻译模型；建议开启 workflow 里的 cache（README 上面已给出配置）。
