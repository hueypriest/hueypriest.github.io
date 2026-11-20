# hueypriest.com

Erik Martin's personal site. Plain HTML, one stylesheet, one small build script.

## Publish an article

1. In `content/posts/`, copy `_example.md` to a new file, e.g. `minitel.md`.
   The file name becomes the address: `hueypriest.com/writing/minitel/`.
2. Fill in the top block (`title` and `date` are required; add `linebreaks: true`
   for pieces written in short lines, so each line break is kept), write the piece in
   Markdown, delete the `draft: true` line.
3. Commit. GitHub builds and publishes it in about a minute.

The build adds the piece to the home page, the Writing index, the RSS and JSON
feeds, the sitemap, and llms.txt, and writes its structured data. Files whose
names start with `_`, or that say `draft: true`, are never published.

## Special blocks inside an article

    ::: clipping                      an archival scan, mounted, with its source line
    ![describe the image](/assets/img/scan.jpg)
    source: The Daily Tar Heel        (required)
    date: December 9, 1974
    page: p. 1
    link: https://link-to-the-scan
    note: optional caption
    :::

    ::: pullquote                     one sentence, set large
    The sentence.
    :::

    ::: wide                          an image or table wider than the text column
    ![describe the image](/assets/img/photo.jpg)
    :::

`_example.md` shows all three. Clipping sources are also written into the page's
structured data as citations.

## Other common edits

| To change | Edit |
|---|---|
| "Currently down these holes" | add a new dated entry at the top of `content/now.json`. Old entries stay in the log at `/now/`. |
| A link to something published elsewhere | add an entry to `content/elsewhere.json` |
| Which outside pieces show on the home page | `"featured": true` in that file |
| Contact method | `contact_email` in `content/site.json` (blank = LinkedIn) |
| Nav, footer, shared head tags | `templates/_header.html`, `_footer.html`, `_head.html` |
| Colors, type, layout | `assets/site.css` |
| Bio, newsletters section | `index.html` |
| Work history | `about.html` (keep the JSON block at the top in step with the timeline) |

Never edit `writing/`, `now/`, `feed.xml`, `feed.json`, `sitemap.xml` or `llms.txt` by
hand. The build overwrites them.

## Build locally

    pip install markdown
    python3 build.py            # real build
    python3 build.py --drafts   # preview drafts too (don't commit the result)
    python3 -m http.server      # then open http://localhost:8000

## One-time setup

Repo Settings > Pages > Build and deployment > Source: **GitHub Actions**.
Until that is switched, GitHub serves the committed files as they are, so new
Markdown posts will not appear unless `build.py` was run before committing.
