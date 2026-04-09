import os
import ssl
import smtplib
import feedparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparser
from urllib.request import urlopen, Request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import argostranslate.package
import argostranslate.translate


OPML_URL = "https://gist.github.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b/raw/426957f043dc0054f95aae6c19de1d0b4ecc2bb2/hn-popular-blogs-2025.opml"

FEED_TIMEOUT_SECONDS = 15
PER_FEED_LIMIT = 10
LOOKBACK_HOURS = 24


def download_text(url: str, timeout: int = 60) -> str:
    req = Request(url, headers={"User-Agent": "rss-mailer/1.0"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def load_feeds_from_opml_url(opml_url: str) -> list[str]:
    content = download_text(opml_url, timeout=60).strip().strip("`").strip()
    root = ET.fromstring(content)

    urls: list[str] = []
    for node in root.findall(".//outline"):
        xml_url = node.attrib.get("xmlUrl")
        if xml_url:
            urls.append(xml_url.strip().strip("`").strip())

    seen = set()
    out = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def fetch_feed_bytes(url: str, timeout: int) -> bytes:
    req = Request(url, headers={"User-Agent": "rss-mailer/1.0"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def safe_parse_feed(url: str, timeout: int):
    try:
        data = fetch_feed_bytes(url, timeout=timeout)
        parsed = feedparser.parse(data)

        if getattr(parsed, "bozo", 0):
            ex = getattr(parsed, "bozo_exception", None)
            if ex:
                return parsed, f"bozo_exception: {type(ex).__name__}: {ex}"

        return parsed, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def entry_time_utc(entry) -> datetime | None:
    for k in ("published", "updated"):
        v = entry.get(k)
        if not v:
            continue
        try:
            dt = dtparser.parse(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return None


def fetch_recent_items(feed_urls: list[str], since_utc: datetime, per_feed_limit: int):
    items = []
    failures = []

    for url in feed_urls:
        parsed, err = safe_parse_feed(url, timeout=FEED_TIMEOUT_SECONDS)
        if parsed is None:
            print(f"[SKIP] {url} -> {err}")
            failures.append((url, err))
            continue

        if err:
            print(f"[WARN] {url} -> {err}")

        feed_title = getattr(parsed.feed, "title", url) if hasattr(parsed, "feed") else url
        entries = getattr(parsed, "entries", [])[:per_feed_limit]

        for e in entries:
            t = entry_time_utc(e)
            if t and t < since_utc:
                continue

            items.append({
                "feed": str(feed_title),
                "title": e.get("title", "无标题"),
                "link": e.get("link", ""),
                "time": (t.isoformat() if t else ""),
            })

    return items, failures


def escape_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ensure_argos_en_zh_installed():
    """
    确保 Argos 的 en->zh 翻译模型已安装（首次会下载并安装）。
    """
    try:
        # 如果已经能拿到翻译器，直接返回
        argostranslate.translate.get_translation_from_codes("en", "zh")
        return
    except Exception:
        pass

    print("[INFO] 安装离线翻译模型（en -> zh），首次运行会下载模型，请稍等...")
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()

    pkg = None
    for p in available:
        if p.from_code == "en" and p.to_code == "zh":
            pkg = p
            break
    if not pkg:
        raise RuntimeError("未找到 Argos 的 en->zh 翻译模型（请稍后重试）")

    package_path = pkg.download()
    argostranslate.package.install_from_path(package_path)
    print("[INFO] 离线翻译模型安装完成")


def translate_en_to_zh(text: str) -> str:
    """
    尝试把英文翻译成中文；失败则返回原文。
    """
    text = (text or "").strip()
    if not text:
        return text
    try:
        translator = argostranslate.translate.get_translation_from_codes("en", "zh")
        return translator.translate(text)
    except Exception:
        return text


def build_html(items, failures):
    # 仅翻译站点名/标题/失败原因里可能出现的英文
    ensure_argos_en_zh_installed()

    parts = []

    if not items:
        parts.append(f"<p>过去 {LOOKBACK_HOURS} 小时没有抓到新的 RSS 条目。</p>")
    else:
        by_feed = {}
        for it in items:
            by_feed.setdefault(it["feed"], []).append(it)

        parts.append(f"<p>每日 RSS 摘要（过去 {LOOKBACK_HOURS} 小时，共 {len(items)} 条）</p>")
        for feed, lst in by_feed.items():
            parts.append(f"<h3>{escape_html(translate_en_to_zh(feed))}</h3><ul>")
            for it in lst:
                title_zh = translate_en_to_zh(it["title"])
                parts.append(
                    f'<li><a href="{it["link"]}">{escape_html(title_zh)}</a> '
                    f'<small>{escape_html(it["time"])}</small></li>'
                )
            parts.append("</ul>")

    if failures:
        parts.append(f"<hr/><p>抓取失败（已跳过）: {len(failures)} 个</p><ul>")
        for url, reason in failures[:30]:
            parts.append(
                f"<li><code>{escape_html(url)}</code><br/><small>{escape_html(translate_en_to_zh(reason))}</small></li>"
            )
        if len(failures) > 30:
            parts.append(f"<li>……省略 {len(failures) - 30} 个</li>")
        parts.append("</ul>")

    return "\n".join(parts)


def send_email(html_body: str):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    email_user = os.environ["EMAIL_USER"]
    email_pass = os.environ["EMAIL_PASS"]
    email_to = os.environ["EMAIL_TO"]
    subject = os.environ.get("EMAIL_SUBJECT", "每日 RSS 摘要")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = email_to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=60, context=context) as server:
            server.login(email_user, email_pass)
            server.sendmail(email_user, [email_to], msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(email_user, email_pass)
            server.sendmail(email_user, [email_to], msg.as_string())


def main():
    feeds = load_feeds_from_opml_url(OPML_URL)
    if not feeds:
        raise RuntimeError("OPML 没有解析到任何 xmlUrl")

    since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items, failures = fetch_recent_items(feeds, since_utc=since, per_feed_limit=PER_FEED_LIMIT)
    html = build_html(items, failures)
    send_email(html)


if __name__ == "__main__":
    main()
