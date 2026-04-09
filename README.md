# rss-to-email（GitHub Actions）

定时从 OPML（RSS 订阅列表）抓取最近内容，并通过 SMTP 发送到邮箱。默认配置为：**每天北京时间 09:00** 运行一次。

## 功能

- 从指定 OPML 链接读取所有 `xmlUrl`（RSS/Atom）订阅源
- 抓取最近 **24 小时**的新文章，汇总成一封邮件（HTML）
- 对每个订阅源设置超时（避免卡住）；抓取失败会跳过并在邮件末尾列出失败列表
- 通过 SMTP 发信（支持 `465/SMTP_SSL` 与 `587/STARTTLS`）

## 订阅源（OPML）

脚本默认使用这个 OPML（HN Popular Blogs 2025）：

- https://gist.github.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b

如需更换 OPML，请修改 `rss_mailer.py` 里的 `OPML_URL`。

## 文件结构

```
.
├── rss_mailer.py
├── requirements.txt
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

## 常见问题

1. **部分订阅源 403/超时**
   - 正常现象：有些站点会限制爬虫或不稳定。脚本会跳过，并在邮件末尾列出失败原因。

2. **发信失败（认证失败）**
   - QQ 邮箱必须使用「授权码」，并确保 SMTP 已开启。
   - 检查 GitHub Secrets 是否填对、是否有多余空格。

3. **定时触发有延迟**
   - GitHub 定时任务可能延迟几分钟，属于正常情况。

