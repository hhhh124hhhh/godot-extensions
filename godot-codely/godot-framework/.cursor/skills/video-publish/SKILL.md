---
name: video-publish
description: >-
  From user materials, generates multi-platform video publish pack: Zhihu Chinese
  article, Reddit English post, 3 landscape + 3 portrait Google image-gen cover
  prompts, and title/description/tags for Bilibili, Douyin, Xiaohongshu, Weibo,
  YouTube, X, TikTok, Instagram — each in separate files, platform-native and
  click-worthy. Use when the user wants video-publish, 视频发布, 发布文案, 封面提示词,
  标题简介标签, Zhihu/Reddit posts, or multi-platform upload copy.
---

# Video Publish

From **user materials only**, produce a full publish pack and **write files** (do not only print in chat).

## Inputs

Any mix of: video/storyboard, title ideas, product/brief text, stills, constraints.
Optional: one input file path (used only to locate the output directory).

Do not invent product facts, prices, logos, or claims not in the materials.
If goal/audience is ambiguous, state one short assumption and proceed.

## Output directory

| Mode | Write files to |
|------|----------------|
| User provides an input file | That file’s **parent directory** |
| No input file | **Project root** |

Always **overwrite** these filenames in the output directory (create if missing).

## Required output files

| File | Content |
|------|---------|
| `zhihu.md` | 1 Chinese Zhihu article |
| `reddit.md` | 1 English Reddit post |
| `covers-landscape.md` | 3 landscape Google image-gen prompts |
| `covers-portrait.md` | 3 portrait Google image-gen prompts |
| `platforms.md` | Title / description / tags for all 8 platforms |

Chat after write: short confirm only (output dir + file list). Do not dump full copy into chat unless the user asks.

## Copy-friendly MD

**Articles are normal Markdown** — `zhihu.md` and `reddit.md` stay readable long-form (headings, paragraphs). Do **not** wrap the whole article in a code fence.

**Paste fields use fences** — platform Title / Description / Tags, and each cover prompt: one field = one fence so one-click copy works.

Fence rules (covers + `platforms.md` only):
- Headings/labels outside the fence; **only the text to paste** inside
- Prefer plain ` ``` ` with no language
- Inside: raw publish text only — no extra structural markdown
- Do **not** put multiple platforms or multiple fields in one fence

## Workflow

1. Resolve output directory (file parent vs project root)
2. Inventory materials; infer topic, hook, audience, tone
3. Write all 5 files (articles as normal MD; covers + platforms with paste fences)
4. Consistency pass (same core claim/hook across platforms; no invented facts)
5. Confirm paths in chat

## Platform styles (must match)

Eye-catching first; still native to each platform — not the same paragraph pasted everywhere.

### Articles

Both articles must be **substantive**, not teaser blurbs. Expand from the user’s materials: explain context, walk through key beats, add concrete detail, and give readers something useful even if they never open the video.

**Depth (required)**
- Zhihu: typically **1500–3500 字** (or more if materials are dense); multiple `##` sections
- Reddit: typically **600–1500 words**; clear sections, still conversational
- Prefer “too much useful detail” over thin summary; do not pad with empty hype
- Structure idea: hook → background / problem → what we built or showed → how it works → takeaways → soft CTA
- Reuse facts, names, numbers, and claims **only from materials**; when expanding prose, stay faithful

**Code from the user (required when present)**
- If materials include code, snippets, scripts, API usage, or repo paths: **pull in the user’s own code**, not generic invented samples
- Prefer several short, real excerpts over one toy rewrite; keep enough context to be readable
- Use fenced code blocks with the right language tag (`gdscript`, `python`, `cpp`, …)
- Lightly annotate why each snippet matters; do not “improve” the code into something they didn’t provide
- If materials only mention code indirectly (e.g. storyboard about a feature), open related project files when a clear path/repo is in scope and quote **their** implementations
- No code in materials and none findable → skip code sections; do not fabricate demos

**知乎 (`zhihu.md`)** — Chinese, normal Markdown article
- `#` title as H1; body with `##` / `###` subheads, lists, and code fences as needed
- Long-form, structured, credible; strong hook title + opening question/conflict
- Fill sections with explanation, comparisons, pitfalls, and material-grounded examples
- Light CTA at end (watch / discuss); avoid slang spam and emoji walls

**Reddit (`reddit.md`)** — English, normal Markdown post
- `#` title as H1; body as readable prose (not one giant fence)
- Discussion-first, authentic; title like a real post, not ad copy
- Same richness bar as Zhihu (translated tone): context → build/demo → code when available → ask the room something specific
- No hard sell, no keyword stuffing; optional `## Suggested subreddits` (2–5 as a normal list)

### Cover prompts

Google image generation prompts (Imagen / Gemini image). English prompts preferred (models follow them more reliably). Each prompt must be **self-contained**: subject, mood, composition, lighting, text-in-image rules, aspect.

**`covers-landscape.md`** — 3 variants, **16:9** thumbnail / banner
- Safe margins for platform UI crop; readable focal point left/center
- State: `aspect ratio 16:9`, no watermarks, no logos unless in materials

**`covers-portrait.md`** — 3 variants, **9:16** short-video cover
- Vertical hero, face/product large in upper two-thirds; room for caption overlay
- State: `aspect ratio 9:16`, no watermarks, no logos unless in materials

Each file format:

````markdown
# Covers — landscape (16:9)

## Variant 1 — [short label]

```
[full prompt — paste-ready]
```

## Variant 2 — [short label]

```
[full prompt — paste-ready]
```

## Variant 3 — [short label]

```
[full prompt — paste-ready]
```
````

(Same structure for portrait with `9:16`.)

Three variants should differ in composition/hook (e.g. curiosity gap / bold claim visual / emotional close-up) — not three near-duplicates.

### Video platforms (`platforms.md`)

Generate **all eight**. Each section: Title, Description, Tags — each in its own fence.

| Platform | Language | Style notes |
|----------|----------|-------------|
| Bilibili | 中文 | Searchable title; description with highlights / chapters if known |
| Douyin | 中文 | Ultra-short hook title; first desc line = scroll-stopper |
| Xiaohongshu | 中文 | Title + emoji OK; lifestyle/note tone |
| Weibo | 中文 | Short punchy; @/话题 friendly; desc can double as post body |
| YouTube | English | SEO title (~≤100 chars ideal); description with hook + value + CTA |
| X | English | Punchy post-length energy; desc ≈ post text if needed |
| TikTok | English | Caption-first hook; keep title/caption tight |
| Instagram | English | Reels/caption tone; line breaks in description |

#### Tags — follow each platform’s rules (required)

Do **not** use one universal tag format. The Tags fence must match how that platform expects paste-in.

| Platform | Format inside Tags fence | Count / notes |
|----------|--------------------------|---------------|
| **Bilibili** | Plain keywords, **comma-separated**, **no `#`** (投稿标签栏) | ~8–12；中文为主；含分区向词 + 内容专有词；勿堆无关热词 |
| **Douyin** | `#话题` space-separated，**有 `#`、无结尾 `#`** | ~5–8；可混 1–2 个较热话题 + 精准词；勿刷屏式 # |
| **Xiaohongshu** | `#话题` space-separated，**有 `#`、无结尾 `#`** | ~8–15；笔记发现流常用；生活/教程向词优先 |
| **Weibo** | `#话题#` space-separated（**开闭都有 `#`**） | ~3–6；偏短、可上热搜向；勿超长句当话题 |
| **YouTube** | Comma-separated SEO phrases，**no `#`** (YouTube Studio tags field) | ~8–15；可含 2–4 词短语；英/专有名保留原样 |
| **X** | `#Hashtag` space-separated，**有 `#`** | **2–4 only**；克制；CamelCase 或短词；禁止一串标签墙 |
| **TikTok** | `#hashtag` space-separated，**有 `#`** | ~4–8；1–2 broad + rest niche；少用空洞 #fyp 堆砌（最多 1 个，可不用） |
| **Instagram** | `#hashtag` space-separated，**有 `#`** | ~8–15；可放 Tags 栏供粘贴到文末/首评；混 broad + specific |

Shared tag quality:
- Relevant to the video; mix discoverable + specific
- No irrelevant viral spam, no competitor-brand stuffing unless in materials
- Language matches the platform column above

**`platforms.md` structure:**

````markdown
# Platform publish copy

## Bilibili

### Title

```
[title]
```

### Description

```
[description]
```

### Tags

```
Godot, GDScript, 游戏开发, …
```

## Douyin

### Tags

```
#Godot #游戏开发 #独立游戏 …
```

## Xiaohongshu

### Tags

```
#Godot #游戏开发 #独立游戏
```

## Weibo

### Tags

```
#Godot# #独立游戏#
```

## YouTube

### Tags

```
Godot, GDScript, game development, …
```

## X

### Tags

```
#Godot #IndieDev
```

## TikTok

### Tags

```
#Godot #gamedev #indiedev …
```

## Instagram

### Tags

```
#Godot #gamedev #indiedev …
```
````

(Each platform still has Title / Description / Tags; examples above only show Tags shape per platform.)

Use exact section headings `## Bilibili` … `## Instagram` (stable for copy-paste / tooling).

## Quality bar

- Hook in the first line/title every time
- Articles are rich and material-grounded; include the user’s own code when available
- Same factual core across files; wording adapted per platform
- Tags: **per-platform format** (see table); relevant + discoverable; no irrelevant viral spam
- Covers: no unreadable tiny text; if on-image text is needed, keep to ≤5 words and say so in the prompt
- If materials are thin, still ship all files; mark uncertain lines with `(assumption: …)` once in chat, not inside every file

## Examples

**Input:** `res://…` storyboard + “发布这期视频”  
**Output dir:** storyboard file’s folder → write the 5 files there.

**Input:** paste brief only, no path  
**Output dir:** project root → write the 5 files there.
