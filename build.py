#!/usr/bin/env python3
"""
build.py — the whole build system for hueypriest.com.

What it does, in order:
  1. Reads every Markdown file in content/posts/ and turns it into a page at
     writing/<slug>/index.html (plus a plain-text copy at writing/<slug>.md).
  2. Rebuilds writing/index.html: one list of everything, on-site and off.
  3. Refreshes the marked blocks inside index.html, about.html and 404.html
     (shared head, header, footer, "latest writing", "posted elsewhere").
  4. Regenerates feed.xml, feed.json, sitemap.xml and llms.txt.

Run it with:   python3 build.py            (needs: pip install markdown)
Preview with:  python3 build.py --drafts   (also builds drafts; don't commit)

Hand-edited files:  index.html, about.html, 404.html, assets/, templates/, content/
Generated files:    writing/**, feed.xml, feed.json, sitemap.xml, llms.txt
"""
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
SITE = json.loads((ROOT / "content/site.json").read_text())
BASE = SITE["url"].rstrip("/")
DRAFTS = "--drafts" in sys.argv


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s), quote=True)


def tpl(name):
    return (ROOT / "templates" / name).read_text()


def fill(text, **kw):
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", str(v))
    left = re.findall(r"\{\{[a-z_:]+\}\}", text)
    if left:
        sys.exit(f"build.py: unfilled placeholders {sorted(set(left))}")
    return text


def d(s):
    return dt.date.fromisoformat(str(s))


def short(date):   # Feb 3 2025
    return f"{date:%b} {date.day} {date.year}"


def long(date):    # February 3, 2025
    return f"{date:%B} {date.day}, {date.year}"


def rfc822(date):
    return dt.datetime(date.year, date.month, date.day, 12, tzinfo=dt.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000")


def write(path, text):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


CONTACT_HREF = ("mailto:" + SITE["contact_email"]) if SITE.get("contact_email") else SITE["contact_url"]
CONTACT_LABEL = SITE.get("contact_email") or "LinkedIn"


def header(current=""):
    h = tpl("_header.html")
    for key in re.findall(r"\{\{cur:([a-z]+)\}\}", h):
        h = h.replace("{{cur:%s}}" % key, ' aria-current="page"' if key == current else "")
    return h.rstrip()


HEAD = tpl("_head.html").rstrip()
FOOTER = fill(tpl("_footer.html"), contact_href=esc(CONTACT_HREF)).rstrip()


# ---------------------------------------------------------------- posts
def parse_post(path):
    raw = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        sys.exit(f"build.py: {path.name} has no front matter (the block between --- lines)")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
        else:
            val = val.strip("\"'")
        meta[key.strip()] = val
    for need in ("title", "date"):
        if not meta.get(need):
            sys.exit(f"build.py: {path.name} is missing '{need}:' in its front matter")
    body_md = m.group(2).strip()
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem).lstrip("_")
    md = markdown.Markdown(extensions=["extra", "smarty", "sane_lists"])
    body_html = md.convert(body_md)
    text = re.sub(r"<[^>]+>", " ", body_html)
    words = len(text.split())
    first_para = re.search(r"<p>(.*?)</p>", body_html, re.S)
    fallback = re.sub(r"<[^>]+>", "", first_para.group(1)) if first_para else ""
    desc = meta.get("description") or meta.get("dek") or html.unescape(fallback)
    if len(desc) > 200:
        desc = desc[:197].rsplit(" ", 1)[0] + "…"
    date = d(meta["date"])
    return dict(
        slug=slug, title=meta["title"], dek=meta.get("dek", ""), description=desc,
        date=date, updated=d(meta["updated"]) if meta.get("updated") else date,
        tags=meta.get("tags") or [], image=meta.get("image") or f"{BASE}/avatar.jpg",
        draft=str(meta.get("draft", "")).lower() == "true",
        body_md=body_md, body_html=body_html, minutes=max(1, round(words / 230)), words=words,
        url=f"{BASE}/writing/{slug}/", path=f"/writing/{slug}/", md_path=f"/writing/{slug}.md",
    )


posts = [parse_post(p) for p in sorted((ROOT / "content/posts").glob("*.md"))]
posts = [p for p in posts if DRAFTS or not p["draft"]]
posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
elsewhere = json.loads((ROOT / "content/elsewhere.json").read_text())
for e in elsewhere:
    e["date"] = d(e["date"])


def person_ref():
    return {"@type": "Person", "@id": f"{BASE}/#erik", "name": SITE["author"], "url": f"{BASE}/"}


# writing/ is fully generated: clear it, then rebuild
wdir = ROOT / "writing"
if wdir.exists():
    shutil.rmtree(wdir)

for i, p in enumerate(posts):
    newer = posts[i - 1] if i > 0 else None
    older = posts[i + 1] if i + 1 < len(posts) else None
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "@id": p["url"] + "#article",
        "headline": p["title"],
        "description": p["description"],
        "url": p["url"],
        "mainEntityOfPage": p["url"],
        "datePublished": p["date"].isoformat(),
        "dateModified": p["updated"].isoformat(),
        "inLanguage": "en-US",
        "wordCount": p["words"],
        "keywords": p["tags"],
        "image": p["image"],
        "author": person_ref(),
        "publisher": person_ref(),
        "isPartOf": {"@type": "Blog", "@id": f"{BASE}/writing/#blog", "name": "Erik Martin: writing"},
    }
    jsonld = {k: v for k, v in jsonld.items() if v not in (None, [], "")}
    page = fill(
        tpl("post.html"),
        title=esc(p["title"]), description=esc(p["description"]), url=p["url"],
        url_display=p["url"].replace("https://", ""), md_url=p["md_path"], image=esc(p["image"]),
        date=p["date"].isoformat(), updated=p["updated"].isoformat(), date_long=long(p["date"]),
        head=HEAD, header=header("writing"), footer=FOOTER, contact_href=esc(CONTACT_HREF),
        jsonld=json.dumps(jsonld, indent=2, ensure_ascii=False).replace("</", "<\\/"),
        dek_html=f'<p class="article__dek">{esc(p["dek"])}</p>' if p["dek"] else "",
        updated_html=(f'<span>Updated <time datetime="{p["updated"].isoformat()}">{long(p["updated"])}</time></span>'
                      if p["updated"] != p["date"] else ""),
        minutes=p["minutes"], body=p["body_html"],
        tags_html=('<ul class="article__tags" aria-label="Topics">' +
                   "".join(f"<li>{esc(t)}</li>" for t in p["tags"]) + "</ul>") if p["tags"] else "",
        prev_html=(f'<a class="prev" href="{older["path"]}"><span class="label">&larr; Older</span>'
                   f'<span class="t">{esc(older["title"])}</span></a>') if older else "",
        next_html=(f'<a class="next" href="{newer["path"]}"><span class="label">Newer &rarr;</span>'
                   f'<span class="t">{esc(newer["title"])}</span></a>') if newer else "",
    )
    write(f"writing/{p['slug']}/index.html", page)
    md_copy = f"# {p['title']}\n\n"
    if p["dek"]:
        md_copy += f"> {p['dek']}\n\n"
    md_copy += f"By {SITE['author']}. Published {p['date'].isoformat()}"
    if p["updated"] != p["date"]:
        md_copy += f", updated {p['updated'].isoformat()}"
    md_copy += f". Canonical URL: {p['url']}\n\n{p['body_md']}\n"
    write(f"writing/{p['slug']}.md", md_copy)


# ---------------------------------------------------------------- lists
def row(date, title, href, sub="", src="", kind="", here=False):
    sub_html = f'\n        <span class="sub">{esc(sub)}</span>' if sub else ""
    src_html = (f'\n        <span class="src{" is-here" if here else ""}">{esc(src)}'
                f'{"" if here else " &nearr;"}</span>') if src else ""
    kind_attr = f' data-kind="{kind}"' if kind else ""
    return (f'      <li{kind_attr}><a href="{esc(href)}">\n'
            f'        <span class="date"><time datetime="{date.isoformat()}">{short(date)}</time></span>\n'
            f'        <span class="t">{esc(title)}</span>{sub_html}{src_html}\n'
            f'      </a></li>')


everything = (
    [dict(date=p["date"], title=p["title"], href=p["path"], sub=p["dek"], src="Here", kind="here", here=True)
     for p in posts] +
    [dict(date=e["date"], title=e["title"], href=e["url"], sub=e.get("sub", ""), src=e["source"], kind=e["kind"])
     for e in elsewhere]
)
everything.sort(key=lambda x: x["date"], reverse=True)
latest_date = max(x["date"] for x in everything)

full_list = '    <ul class="entries">\n' + "\n".join(row(**x) for x in everything) + "\n    </ul>"
collection = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "@id": f"{BASE}/writing/#page",
    "url": f"{BASE}/writing/",
    "name": "Writing by Erik Martin",
    "inLanguage": "en-US",
    "dateModified": latest_date.isoformat(),
    "author": person_ref(),
    "isPartOf": {"@id": f"{BASE}/#site"},
    "mainEntity": {
        "@type": "ItemList",
        "numberOfItems": len(everything),
        "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "name": x["title"],
             "url": (BASE + x["href"]) if x["href"].startswith("/") else x["href"]}
            for n, x in enumerate(everything)
        ],
    },
}
write("writing/index.html", fill(
    tpl("writing.html"), head=HEAD, header=header("writing"), footer=FOOTER, list=full_list,
    jsonld=json.dumps(collection, indent=2, ensure_ascii=False).replace("</", "<\\/"),
    n_all=len(everything), n_here=len(posts),
    n_newsletter=sum(1 for e in elsewhere if e["kind"] == "newsletter"),
    n_elsewhere=sum(1 for e in elsewhere if e["kind"] == "elsewhere"),
    build_date=latest_date.isoformat(), build_date_long=long(latest_date),
))

if posts:
    latest_html = ('    <ul class="entries">\n' +
                   "\n".join(row(p["date"], p["title"], p["path"], p["dek"]) for p in posts[:5]) +
                   "\n    </ul>")
else:
    latest_html = ('    <p class="empty">Articles will be published here, on this site, starting soon. '
                   'In the meantime, <a class="textlink" href="/writing/">the full list</a> has '
                   'every newsletter issue and the pieces below.</p>')

featured = sorted([e for e in elsewhere if e.get("featured")], key=lambda e: e["date"], reverse=True)
featured_html = '    <ul class="cards">\n' + "\n".join(
    f'      <li class="is-{esc(e.get("theme", "other"))}"><a href="{esc(e["url"])}">\n'
    f'        <span class="src">{esc(e["source"])} &middot; <time datetime="{e["date"].isoformat()}">{e["date"]:%b %Y}</time></span>\n'
    f'        <p class="t">{esc(e["title"])}</p>\n'
    f'        <p class="d">{esc(e.get("sub", ""))}</p>\n'
    f'      </a></li>' for e in featured) + "\n    </ul>"


# ---------------------------------------------------------------- marked blocks in hand-edited pages
def refresh(filename, blocks):
    path = ROOT / filename
    text = path.read_text()

    def sub(m):
        name, args = m.group(1), dict(a.split("=") for a in m.group(2).split())
        if name not in blocks:
            sys.exit(f"build.py: unknown block '{name}' in {filename}")
        content = blocks[name](args) if callable(blocks[name]) else blocks[name]
        return f"<!-- build:{name}{m.group(2)} -->\n{content}\n{m.group(4)}<!-- /build:{name} -->"

    text = re.sub(r"<!-- build:([a-z]+)((?: [a-z]+=[a-z]+)*) -->\n(.*?)([ \t]*)<!-- /build:\1 -->", sub, text, flags=re.S)
    path.write_text(text)


BLOCKS = {
    "head": HEAD,
    "header": lambda a: header(a.get("current", "")),
    "footer": FOOTER,
    "latest": latest_html,
    "featured": featured_html,
    "contact": f'      <p>The best way to reach me is <a href="{esc(CONTACT_HREF)}" rel="me">{esc(CONTACT_LABEL)}</a>.</p>',
}
for page in ("index.html", "about.html", "404.html"):
    refresh(page, BLOCKS)


# ---------------------------------------------------------------- feeds
def absolutize(h):
    return re.sub(r'(href|src)="/', rf'\1="{BASE}/', h)


items_xml = "".join(f"""
    <item>
      <title>{esc(p['title'])}</title>
      <link>{p['url']}</link>
      <guid isPermaLink="true">{p['url']}</guid>
      <pubDate>{rfc822(p['date'])}</pubDate>
      <dc:creator>{esc(SITE['author'])}</dc:creator>
      <description>{esc(p['description'])}</description>
      <content:encoded><![CDATA[{absolutize(p['body_html']).replace(']]>', ']]]]><![CDATA[>')}]]></content:encoded>
    </item>""" for p in posts[:30])
write("feed.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Erik Martin: writing</title>
    <link>{BASE}/writing/</link>
    <atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{esc(SITE['description'])}</description>
    <language>en-us</language>{f'''
    <lastBuildDate>{rfc822(max(p["updated"] for p in posts))}</lastBuildDate>''' if posts else ''}{items_xml}
  </channel>
</rss>
""")
write("feed.json", json.dumps({
    "version": "https://jsonfeed.org/version/1.1",
    "title": "Erik Martin: writing",
    "home_page_url": f"{BASE}/writing/",
    "feed_url": f"{BASE}/feed.json",
    "description": SITE["description"],
    "language": "en-US",
    "authors": [{"name": SITE["author"], "url": f"{BASE}/about.html"}],
    "items": [{
        "id": p["url"], "url": p["url"], "title": p["title"], "summary": p["description"],
        "content_html": absolutize(p["body_html"]), "date_published": p["date"].isoformat() + "T12:00:00Z",
        "date_modified": p["updated"].isoformat() + "T12:00:00Z", "tags": p["tags"],
    } for p in posts[:30]],
}, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- sitemap + llms.txt
def page_date(filename):
    m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', (ROOT / filename).read_text().split("<main", 1)[-1])
    return d(m.group(1)) if m else latest_date


urls = [("/", max(page_date("index.html"), latest_date)), ("/writing/", latest_date),
        ("/about.html", page_date("about.html"))] + [(p["path"], p["updated"]) for p in posts]
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{m.isoformat()}</lastmod></url>\n" for u, m in urls) +
      "</urlset>\n")

post_lines = "\n".join(
    f"- [{p['title']}]({BASE}{p['md_path']}) ({p['date'].isoformat()}): {p['description']}" for p in posts
) or "- None published on this site yet. See the Writing page for work published elsewhere."
write("llms.txt", fill(tpl("llms.txt"), posts=post_lines))

print(f"built {len(posts)} post(s), {len(everything)} entries in the writing index"
      + (" [drafts included: do not commit]" if DRAFTS else ""))
