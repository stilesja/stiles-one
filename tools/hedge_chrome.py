#!/usr/bin/env python3
"""Stamp the shared Hedge site chrome into every /hedge/ subpage.

Re-runnable and idempotent. Each block lives between marker comments, so a
re-run replaces the block in place; to change the links or the copy, edit
this file and run it again:

    python3 tools/hedge_chrome.py          # from the stiles-one repo root

What it stamps (styles live in hedge/hedge.css, "Site chrome"):
  - hedge:head  Smart App Banner meta + the Space Grotesk font, only the
                pieces a page doesn't already carry
  - hedge:bar   top bar: HEDGE wordmark -> /hedge/, plus the four page links
  - hedge:get   closing download card (log entries, log index, case study)

It also removes chrome the bar replaces: a "← Hedge" back pill (the
wordmark does that job now) and the old one-line closing CTA on log
entries (the card replaces it). Every page's hedge.css link gets a
?v=<content hash> so a style change always reaches returning visitors. The
landing page (hedge/index.html) gets only that version tag.
"""
import hashlib, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEDGE = ROOT / "hedge"
APP_URL = "https://apps.apple.com/app/id6768878330"
LINKS = [
    ("/hedge/build/", "How it's built"),
    ("/hedge/log/", "Build log"),
    ("/hedge/support/", "Support"),
    ("/hedge/party/", "Host a party"),
]

def section_of(rel: str) -> str:
    return "/hedge/" + rel.split("/")[0] + "/"

def head_block(page: str) -> str:
    rest = re.sub(r"<!-- hedge:head -->.*?<!-- /hedge:head -->\n?", "", page, flags=re.S)
    lines = []
    if 'name="apple-itunes-app"' not in rest:
        lines.append(f'  <meta name="apple-itunes-app" content="app-id=6768878330">')
    if "Space+Grotesk" not in rest:
        lines += [
            '  <link rel="preconnect" href="https://fonts.googleapis.com">',
            '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
            '  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap">',
        ]
    if not lines:
        return ""
    return "  <!-- hedge:head -->\n" + "\n".join(lines) + "\n  <!-- /hedge:head -->\n"

def bar_block(current: str) -> str:
    cur = ' aria-current="page"'
    links = "\n".join(
        f'        <a href="{href}"{cur if href == current else ""}>{label}</a>'
        for href, label in LINKS
    )
    return f"""    <!-- hedge:bar -->
    <header class="hedge-bar">
      <a class="hedge-bar-mark" href="/hedge/" aria-label="Hedge home">Hedge</a>
      <nav aria-label="Hedge pages">
{links}
      </nav>
    </header>
    <!-- /hedge:bar -->
"""

GET = f"""    <!-- hedge:get -->
    <aside class="hedge-get" aria-label="Get Hedge">
      <p class="hedge-get-title"><span class="brand-caps">Hedge</span> is daily calibrated trivia: bet how sure you are.</p>
      <p class="hedge-get-platforms">Free on iPhone, iPad, Mac (Apple silicon), Apple TV, and Vision Pro.</p>
      <a href="{APP_URL}" aria-label="Download Hedge on the App Store"><img src="/hedge/appstore-badge.svg" alt="Download on the App Store" height="48"></a>
    </aside>
    <!-- /hedge:get -->
"""

OLD_CTA = re.compile(
    r'\n?[ \t]*<p>If you want to see whether your gut is calibrated, it takes about ninety seconds a day: '
    r'<a href="https://stiles\.one/hedge">stiles\.one/hedge</a></p>\n')
BACK_TO_HEDGE = re.compile(r'[ \t]*<p class="back"><a href="\.\./">← Hedge</a></p>\n\n?')

def strip(page: str, name: str) -> str:
    return re.sub(rf"[ \t]*<!-- hedge:{name} -->.*?<!-- /hedge:{name} -->\n*", "", page, flags=re.S)

CSS_VERSION = hashlib.sha256((HEDGE / "hedge.css").read_bytes()).hexdigest()[:10]
CSS_HREF = re.compile(r'(href="[./]*hedge\.css)(\?v=[0-9a-f]+)?"')

def version_css(page: str) -> str:
    """Pin the stylesheet link to the CSS content hash, so a style change
    can never be masked by a browser's cached copy of hedge.css."""
    return CSS_HREF.sub(lambda m: f'{m.group(1)}?v={CSS_VERSION}"', page)

def stamp(path: pathlib.Path) -> bool:
    rel = path.relative_to(HEDGE).as_posix()
    page = original = path.read_text()
    wants_card = rel.startswith("log/") or rel.startswith("build/")

    head = head_block(page)
    page = strip(page, "head")
    if head:
        page = page.replace("</head>", head + "</head>", 1)

    page = version_css(page)
    page = strip(page, "bar")
    page = BACK_TO_HEDGE.sub("", page)
    assert page.count("<main>") == 1, rel
    page = re.sub(r"<main>\n\s*", lambda m: "<main>\n" + bar_block(section_of(rel)) + "\n    ", page, count=1)

    page = strip(page, "get")
    if wants_card:
        page = OLD_CTA.sub("\n", page)
        if "<footer" in page:
            page = re.sub(r"\n*([ \t]*<footer)", "\n\n" + GET + r"\n\1", page, count=1)
        else:
            page = page.replace("  </main>", GET + "  </main>", 1)

    if page != original:
        path.write_text(page)
        return True
    return False

def main() -> int:
    pages = sorted(p for p in HEDGE.rglob("index.html") if p.parent != HEDGE)
    changed = [p for p in pages if stamp(p)]
    landing = HEDGE / "index.html"  # only the stylesheet version, nothing else
    text = landing.read_text()
    if version_css(text) != text:
        landing.write_text(version_css(text))
        changed.append(landing)
    print(f"{len(pages)} subpages, {len(changed)} changed")
    for p in changed:
        print("  ", p.relative_to(ROOT))
    return 0

if __name__ == "__main__":
    sys.exit(main())
