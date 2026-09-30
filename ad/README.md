# Ila Firdawsi — launch commercial

**Master:** 3840×2160, 24 fps, H.264 High ~57 Mbps, AAC 48 kHz stereo, 51.5 s, −15.9 LUFS
**Files (Higgsfield media):**
- 4K master — `https://d2ol7oe51mr4n9.cloudfront.net/user_3JxekxfRx9DiL6C77tMD5mjXb7k/d8ca0c46-724b-4864-99f6-77e72837b29b.mp4`
- 1080p review — `https://d2ol7oe51mr4n9.cloudfront.net/user_3JxekxfRx9DiL6C77tMD5mjXb7k/37772a73-2910-42eb-97ef-86f504a12876.mp4`
- Higgsfield project: *Ila Firdawsi — Launch Commercial*

## Idea

The world keeps moving; prayer makes a moment of stillness. The app helps, then steps back.
Campaign line: **Technology that knows when to step back.** End card is the app's own splash
lockup and signature line (*One prayer at a time, toward Firdaws*), with the truthful CTA
**Now on Android** (the app ships as a signed APK).

## Source of truth

Every phone screen is the real app, rendered from the `ilaads` source on a story clock and
composited onto the plates. No generated UI text anywhere.

| Fact | Value | From |
| :--- | :--- | :--- |
| Default theme | Firdawsi Classic: teal `#0E4B4E`, gold `#C99A3A`, cream `#FFF6EF`, blush | `client/js/data/themes.js` |
| Type | Fraunces (display), Nunito (UI), Noto Naskh Arabic | `client/index.html` |
| At prayer time | "Asr time" prompt → Prayer Focus Mode (the successor to "Lockdown") | `services/focusScheduler.js`, `components/focusMode.js` |
| Counting | Rakʿāt, Asr = 4; camera (on-device MoveNet) or pocket | `components/focusMode.js`, `pages/rakah.js` |
| Arabic | العصر, إلى الفردوس — the app's own strings | app source |
| Date / place | Thu 15 Oct 2026, Midtown Manhattan (40.7549, −73.9840) | chosen |
| Asr | **3:47 PM** EDT — ISNA method, Shafiʿi (the app's defaults); Qibla 58° ENE | computed |

Adhan playback is not wired into the product, so the alert is a designed two-note chime and
the UI identifies Asr — no sacred audio is used or altered.

## Continuity bible

- **City (Maryam):** early 30s, North African heritage; matte black jersey hijab; tailored black
  knee-length wool coat, black high-neck blouse, wide black trousers, black loafers, structured
  black leather tote; matte black Android phone. Late-afternoon sun from the SW, warm key, cool shade.
- **Home:** Black American man, mid 30s, short beard, oatmeal linen shirt, charcoal trousers,
  white knit kufi. Oak floor, sheer linen curtains, cream bouclé chair, olive tree. Deep-teal
  prayer rug with a cream-and-gold border; low oak stool; matte aluminium stand; same phone.
- **Grade:** one film curve for the whole spot (lifted blacks, soft roll-off, 0.94 saturation);
  city +cool, home +warm; fine grain.

## Shot list and model routing (credits: 110 available)

| # | Time | Shot | Made with |
| :- | :- | :- | :- |
| 01 | 0:00 | Midtown establishing, native city audio | Soul 2 still → Kling 3.0 (std, sound) |
| 02 | 0:04 | Maryam walking, Steadicam | Soul 2 still → Kling 3.0 Pro |
| 03 | 0:07.5 | Curb, phone buzzes, she draws it | Nano Banana Pro frame → Kling 3.0 Pro |
| 04 | 0:10.5 | **Hero reveal**: "Asr time" → Prayer Focus Mode | Kling 3.0 Pro + tracked real UI |
| 05 | 0:13.75 | 85 mm portrait, she looks up, city moves on | Nano Banana Pro → Kling 3.0 Pro |
| 06 | 0:17.75 | Match cut: phone into stand (Focus Mode) | Nano Banana Pro → Kling 3.0 Pro + UI |
| 07 | 0:20.75 | Qiyam, rear three-quarter | Nano Banana Pro → Kling 3.0 Pro (10 s) |
| 08 | 0:23.55 | Phone fg / sujood bg — **0 → 1 of 4** | Nano Banana Pro → Kling 3.0 Pro + UI |
| 09 | 0:25.95 | Sujood held, wide | shot 07 plate |
| 10 | 0:28.25 | **1 → 2 of 4**, phone falls out of focus | shot 08 plate + UI + defocus |
| 11 | 0:31.05 | Montage: times, prompt, Focus Mode, Rakʿah counter, Qibla | real UI, native 4K |
| 12 | 0:41.55 | Hero: "MashaAllah — 4 rakʿāt of Asr complete" | shot 06 plate + UI |
| 13 | 0:45.55 | Splash lockup + "Now on Android" | app's own splash animation, 4K |

Veo 3.1 (32/clip) and Cinema Studio 3.0 (25/clip) were priced and not affordable across the
spot; Kling 3.0 Pro (8.75/5 s) was the strongest human model within budget.

## Sound

Original score written in code (`pipeline/score.py`): felt piano, warm pad, low pulse, 72 BPM,
F major — pulse in the city, room for the alert, stillness at home, lift in the montage, resolve
on the logo. City bed from the Kling plate, receding (low-pass) as she reads; room tone at home;
designed chime, placement, and counter ticks. VO: Seed Audio "Soraya", Whisper-checked.

> Life moves fast. · But some moments bring us back. · It helps you remember. It helps you focus. ·
> Technology that knows when to step back. · Ila Firdawsi.

No VO or text over the prayer itself.

## Rebuild

`pipeline/run.sh <sha> <master-upload-url> <review-upload-url>` in the Higgsfield sandbox:
fetch → score → mix → 4K picture (screen tracking + UI composite + grade) → mux → upload.
`ui/` holds the rendered app plates; `endcard_splash_4k.mp4` the splash animation.
