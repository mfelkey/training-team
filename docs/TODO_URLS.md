# TODO — Unhealthy Source URLs

Findings from the 2026-04-22 run of `scripts/check_curator_urls.py`.

Four clearly-dead URLs were **removed** outright in that same commit.
The 17 URLs below remain in `SOURCES` (flagged with `# FIXME:`
comments) so the knowledge coverage is preserved when/if they're
fixed. Curators log fetch failures and continue — flagged URLs do
**not** break a `--mode full` run.

Re-run `python3.11 scripts/check_curator_urls.py` after any edit
here to confirm. Target: 0 unhealthy.

## Gone — need replacement URLs (404)

These endpoints moved or restructured. Each probably still exists
somewhere on the publisher's site; worth ~5 min of searching.

### Legal

| Source | Current URL | What to try |
|---|---|---|
| FCA Press Releases | `fca.org.uk/news/press-releases` | FCA consolidated news at `/news` or `/news-and-publications` |
| IAGR Global Gambling | `iagr.org/news/` | Root `iagr.org` has a resources/news section — check current nav |
| GamblingCompliance | (points at LCCP, not news) | Need an actual industry-news URL — try Vixio GamblingCompliance if accessible, or remove |

### Marketing

| Source | Current URL | What to try |
|---|---|---|
| Google Ads Gambling Policy | `support.google.com/adspolicy/answer/6023246` | Google's policy centre URLs changed — search "Google Ads gambling policy" and use the current canonical |

### HR

| Source | Current URL | What to try |
|---|---|---|
| SHRM Benefits | `shrm.org/topics-tools/tools/benefits` | SHRM topic taxonomy shifted — try `/topics-tools/topics/benefits-compensation` |

### Strategy

| Source | Current URL | What to try |
|---|---|---|
| MIT Sloan Sports Analytics | `sloansportsconference.com/research` | Try `sloansportsconference.com/content/research` or the main `sloansportsconference.com` landing page |

### Video

| Source | Current URL | What to try |
|---|---|---|
| YouTube Creator Insider | `youtube.com/@YouTubeCreatorInsider/videos` | YouTube channel URL format evolved — try `/c/YouTubeCreatorInsider` or `/user/YouTubeCreatorInsider` |

## Denied — need auth or different User-Agent (401/403)

These sources are reachable but reject our bot-identifying User-Agent.
Options:

1. Switch the curator's request header to a realistic browser UA
   (e.g. `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...`).
   Some sites pass; some still block.
2. For subscription-gated ones (Reuters), add authenticated cookies.
3. Remove the source if the content isn't worth the workaround.

### DS

| Source | URL | Notes |
|---|---|---|
| Sports Reference Soccer | `fbref.com/en/` | Major soccer analytics source. Try a realistic UA first. |

### Finance

| Source | URL | Notes |
|---|---|---|
| FASB News | `fasb.org/page/pagecontent?pageId=/news/current.html` | Possibly a JavaScript-rendered page — consider RSS alternative |
| Reuters Finance | `reuters.com/business/finance/` | Paywalled. Remove unless auth is wired up. |
| Payments Dive | `paymentsdive.com/` | Realistic UA may work |

### HR

| Source | URL | Notes |
|---|---|---|
| ILO Newsroom | `ilo.org/global/about-the-ilo/newsroom/news/lang--en/index.htm` | URL is very old-style (`--en`); try `/news` at the root |

### SME

| Source | URL | Notes |
|---|---|---|
| Legal Sports Report | `legalsportsreport.com/news/` | Important sports-betting regulation source. Realistic UA probably works. |
| ESPN Cricinfo | `espncricinfo.com/` | Realistic UA likely fixes this |
| Paulick Report | `paulickreport.com/news/` | Key thoroughbred source. Realistic UA likely works. |

### Video

| Source | URL | Notes |
|---|---|---|
| OpenAI Sora Updates | `openai.com/sora/` | Realistic UA may fix — openai.com is anti-bot aggressive |

## Intermittent

### Legal

| Source | URL | Notes |
|---|---|---|
| ACMA Gambling | `acma.gov.au/about-online-gambling` (updated) | Previous URL `/gambling` timed out. New URL probably works — re-run health-check to confirm. |

## Removed in this commit (no action needed)

For reference, these were deleted from SOURCES on 2026-04-22:

- `hr/Payscale Compensation Today` (LOW, 404 — site restructured)
- `sme/Covers` (LOW, 404 — `/sports` path doesn't exist)
- `sme/NCAA MBB News` (LOW, 404 — coverage available via NBA.com)
- `sme/NCAA FB News` (LOW, 404 — coverage available via NFL.com + ESPN later)

## Follow-up actions

- [ ] Find replacement URLs for the 6 "gone" items above
- [ ] Decide on User-Agent rotation for the 9 "denied" items
- [ ] Re-run `scripts/check_curator_urls.py` after each batch
- [ ] When all FIXMEs are resolved, delete this file

## Related

- LL-041 — HITL gate (why these candidates wouldn't have silently landed even before cleanup)
- LL-043 — Phase 2 retrospective
- `scripts/check_curator_urls.py` — the tool that produced this list
