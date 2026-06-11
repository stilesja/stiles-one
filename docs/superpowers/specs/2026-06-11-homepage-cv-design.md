# Homepage as job-application link — design

**Date:** 2026-06-11
**Goal:** Make stiles.one the single URL Jason links when applying to jobs: a light professional summary plus project portfolio, with the Hedge case study surfaced. Not a full public résumé.

## Decisions

- **Depth:** Light professional summary only — no employer/client names, no dates, no education, no phone/location. Full history lives on LinkedIn and the real CV.
- **Placement:** Expand the existing homepage (no new /about or /cv page).
- **Links out:** Email (existing) + LinkedIn (`linkedin.com/in/stilesjason`). No GitHub (only repo is private).
- **Copy rule:** No dev-tool names in public copy (existing site rule). Domain terms like "conversational AI" and "applied ML" are fine.

## Changes

### index.html

1. **Hero + bio.** Keep chip, greeting, gradient h1. Replace the one-line `.lead` with:
   - Lead: "Engineering leader by day. Indie builder the rest of the time."
   - P1: 20+ years building/operating mission-critical enterprise software; a decade+ leading teams; currently leads a 15–20 person cross-functional org running a conversational-AI platform handling 150k+ interactions/day across 66+ locales for a top global brand.
   - P2: Hands-on with applied ML and agentic AI in production; ships own products end-to-end on the side.
2. **Projects.** Hedge card keeps title link + description, adds "Live on the App Store," and a second meta line linking to `hedge/build/` ("Read the engineering case study →").
3. **Footer.** Email · LinkedIn · © 2026.
4. **Head.** Updated meta description; basic Open Graph + Twitter Card tags (title/description/url, no image).

### styles.css

- `.bio` paragraph style (readable measure under the lead).
- Scoped `.cards > li .meta a` style so the case-study link renders as a normal inline link instead of inheriting the bold card-title anchor style (and suppress its `::after` arrow since the arrow is literal text).
- `.footer-links` inline-flex grouping for email · LinkedIn.

## Out of scope

Skills grid, employer names, dates, education, OG image for homepage, any changes to Hedge pages.

## Verification

Render locally; confirm `hedge/` and `hedge/build/` links resolve; check light + dark mode; confirm no tool names in copy.
