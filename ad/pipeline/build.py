"""Ila Firdawsi launch commercial: picture build (runs in the Higgsfield sandbox).

Usage: python3 build.py <workdir>
Reads shots.json (plates, in/out points, UI schedules), writes <workdir>/picture_4k.mp4.
"""
import json, os, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import screen

W, H, FPS = 3840, 2160, 24
WORK = sys.argv[1]
CFG = json.load(open(os.path.join(os.path.dirname(__file__), 'shots.json')))
UI = os.path.join(WORK, 'ui')
FONTS = os.path.join(WORK, 'fonts')


def sh(cmd):
    print('+', cmd[:160], flush=True)
    subprocess.run(cmd, shell=True, check=True)


def read_frames(path, t0, dur, size=(W, H)):
    """Decode [t0, t0+dur) at 24 fps, upscaled with lanczos to 4K."""
    cmd = (f'ffmpeg -v error -ss {t0} -i "{path}" -t {dur} -vf "fps={FPS},scale={size[0]}:{size[1]}:flags=lanczos" '
           f'-f rawvideo -pix_fmt bgr24 -')
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    n = size[0] * size[1] * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(size[1], size[0], 3).copy()
    p.wait()


class Writer:
    def __init__(self, path):
        self.p = subprocess.Popen(
            f'ffmpeg -v error -y -f rawvideo -pix_fmt bgr24 -s {W}x{H} -r {FPS} -i - '
            f'-c:v libx264 -preset medium -crf 14 -pix_fmt yuv420p -x264-params keyint=24 "{path}"',
            shell=True, stdin=subprocess.PIPE)
        self.n = 0

    def write(self, f):
        self.p.stdin.write(np.ascontiguousarray(f).tobytes()); self.n += 1

    def close(self):
        self.p.stdin.close(); self.p.wait()


# ---------------------------------------------------------------- grade
def grade(f, look):
    """One film response for the whole spot; city a touch cooler, home a touch warmer."""
    x = f.astype(np.float32) / 255
    wb = {'city': (1.03, 1.0, 0.97), 'home': (0.96, 1.0, 1.04), 'neutral': (1, 1, 1)}[look]  # BGR gains
    x = x * np.array(wb, np.float32)
    x = x * look_exposure.get(look, 1.0)
    # gentle S-curve with lifted blacks and soft highlight roll-off
    x = np.clip(x, 0, 1.25)
    k = np.clip(x, 0, 1)
    x = 0.8 * x + 0.2 * (k * k * (3 - 2 * k))            # gentle S-curve
    over_ = np.maximum(x - 0.82, 0)
    x = np.minimum(x, 0.82) + over_ / (1 + over_ * 3.2)   # soft highlight roll-off
    x = 0.016 + (1 - 0.016) * x                            # lifted, never crushed, blacks
    lum = x @ np.array([0.114, 0.587, 0.299], np.float32)
    x = lum[..., None] + (x - lum[..., None]) * 0.94
    return np.clip(x * 255, 0, 255).astype(np.uint8)


look_exposure = {'city': 1.0, 'home': 1.0}


def grain(f, rng, amt=2.2):
    n = rng.normal(0, amt, (H // 2, W // 2, 1)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    return np.clip(f.astype(np.float32) + n, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- UI plates
def load_ui(name, camfill=None):
    img = cv2.imread(os.path.join(UI, name + '.png'))
    if camfill is not None:
        # the Focus Mode camera preview: the product shows the live camera here. Fill it with a
        # softened frame of the prayer from the phone's side, so it reads as a preview, not a feed.
        h_, w_ = img.shape[:2]
        ref = img[int(h_ * 0.83), int(w_ * 0.5)].astype(int)
        box = np.zeros(img.shape[:2], bool)
        if ref[2] > ref[0] + 15 and ref.max() < 140:   # the dark warm preview area is present
            box = np.abs(img.astype(int) - ref).max(-1) < 12
        ys, xs = np.where(box)
        if len(ys):
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            fill = cv2.resize(camfill, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
            fill = cv2.GaussianBlur(fill, (0, 0), 7)
            fill = (fill.astype(np.float32) * 0.8).astype(np.uint8)
            region = img[y0:y1, x0:x1]
            m = box[y0:y1, x0:x1][..., None]
            img[y0:y1, x0:x1] = np.where(m, fill, region)
    return img


# ---------------------------------------------------------------- text
def font(kind, size):
    path = {'display': 'Fraunces.ttf', 'ui': 'Nunito.ttf'}[kind]
    f = ImageFont.truetype(os.path.join(FONTS, path), size)
    try:
        f.set_variation_by_axes([700] if kind == 'ui' else [72, 600, 0, 0][:len(f.get_variation_axes())])
    except Exception:
        pass
    return f


def text_layer(lines, anchor_xy, align='left'):
    """lines: [(text, kind, size, rgba)] stacked; returns RGBA 4K layer."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, y = anchor_xy
    for text, kind, size, col in lines:
        f = font(kind, size)
        bw = d.textlength(text, font=f)
        tx = x - bw / 2 if align == 'center' else x
        d.text((tx, y), text, font=f, fill=col)
        y += int(size * 1.35)
    return im


def over(frame_bgr, rgba, opacity=1.0, dy=0.0):
    a = np.asarray(rgba).astype(np.float32)
    if dy:
        a = np.roll(a, int(dy), axis=0)
    al = a[..., 3:4] / 255 * opacity
    rgb = a[..., :3][..., ::-1]
    return np.clip(frame_bgr * (1 - al) + rgb * al, 0, 255).astype(np.uint8)


def ease(k):
    k = min(max(k, 0), 1)
    return k * k * (3 - 2 * k)


# ---------------------------------------------------------------- phone mock for the montage
def phone_mock(ui_bgr, width):
    """A plain modern Android phone: thin black bezel, punch-hole camera, soft edge light."""
    uh, uw = ui_bgr.shape[:2]
    sw = width
    sh_ = int(uh * sw / uw)
    bez = int(sw * 0.035)
    PW, PH = sw + 2 * bez, sh_ + 2 * bez
    rr = int(PW * 0.12)
    ss = 2
    body = Image.new('RGBA', (PW * ss, PH * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle([0, 0, PW * ss - 1, PH * ss - 1], radius=rr * ss, fill=(18, 19, 21, 255))
    d.rounded_rectangle([3 * ss, 3 * ss, PW * ss - 4 * ss, PH * ss - 4 * ss], radius=(rr - 3) * ss, outline=(58, 60, 64, 255), width=2 * ss)
    body = body.resize((PW, PH), Image.LANCZOS)
    scr = Image.fromarray(cv2.cvtColor(cv2.resize(ui_bgr, (sw, sh_), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)).convert('RGBA')
    mask = Image.new('L', (sw * ss, sh_ * ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw * ss - 1, sh_ * ss - 1], radius=(rr - bez) * ss, fill=255)
    mask = mask.resize((sw, sh_), Image.LANCZOS)
    body.paste(scr, (bez, bez), mask)
    d = ImageDraw.Draw(body)
    cr = int(sw * 0.018)
    d.ellipse([PW // 2 - cr, bez + int(sw * 0.03) - cr, PW // 2 + cr, bez + int(sw * 0.03) + cr], fill=(8, 8, 9, 255))
    # glass sheen
    sheen = Image.new('L', (PW, PH), 0)
    ImageDraw.Draw(sheen).polygon([(0, 0), (int(PW * 0.55), 0), (0, int(PH * 0.45))], fill=18)
    sheen = sheen.filter(ImageFilter.GaussianBlur(PW * 0.05))
    white = Image.new('RGBA', (PW, PH), (255, 255, 255, 0))
    white.putalpha(sheen)
    body = Image.alpha_composite(body, Image.composite(white, Image.new('RGBA', (PW, PH), (0, 0, 0, 0)), body.split()[3]))
    return body


def drop_shadow(size, radius_frac=0.12, blur=60, opacity=110):
    PW, PH = size
    pad = blur * 3
    sh_ = Image.new('L', (PW + 2 * pad, PH + 2 * pad), 0)
    ImageDraw.Draw(sh_).rounded_rectangle([pad, pad + blur // 2, pad + PW, pad + PH + blur // 2], radius=int(PW * radius_frac), fill=opacity)
    return sh_.filter(ImageFilter.GaussianBlur(blur)), pad


# ---------------------------------------------------------------- shot renderers
def render_plate(shot, wr, rng):
    src = os.path.join(WORK, 'plates', shot['plate'])
    sched = shot.get('ui')
    cam = cv2.imread(os.path.join(WORK, 'camfill.png'))
    cache = {}
    if sched:
        for _, name, _ in sched:
            if name not in cache:
                cache[name] = load_ui(name, cam if 'cam' in name else None)
    frames = list(read_frames(src, shot['in'], shot['dur']))
    quads = screen.track(frames) if sched else None
    defocus = shot.get('defocus_phone')  # (t_start, t_end, max_sigma): phone falls out of focus
    push = shot.get('push', 0.0)
    for i, f in enumerate(frames):
        t = i / FPS
        if sched and quads[i] is not None:
            ui = screen.ui_at(t, [(a, b, c) for a, b, c in sched], cache)
            f = screen.composite(f, ui, quads[i], blur=shot.get('ui_blur', 0.6))
            if defocus and t > defocus[0]:
                k = ease((t - defocus[0]) / (defocus[1] - defocus[0]))
                q = quads[i]
                c = q.mean(0); qq = c + (q - c) * 1.9
                m = np.zeros(f.shape[:2], np.float32)
                cv2.fillConvexPoly(m, qq.astype(np.int32), 1.0)
                m = cv2.GaussianBlur(m, (0, 0), 40)[..., None]
                bl = cv2.GaussianBlur(f, (0, 0), 1 + defocus[2] * k)
                f = (f * (1 - m) + bl * m).astype(np.uint8)
        if push:
            z = 1 + push * (i / max(1, len(frames) - 1))
            M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
            f = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        f = grade(f, shot.get('look', 'neutral'))
        f = grain(f, rng)
        if shot.get('super'):
            s = shot['super']
            k = ease((t - s['t']) / 0.6) * (1 - ease((t - s['t'] - s['hold']) / 0.5))
            if k > 0:
                f = over(f, SUPERS[s['id']], k, dy=(1 - k) * 12)
        wr.write(f)
    return len(frames)


def render_montage(shot, wr, rng):
    """The phone floats in the warm home light; the screen moves through the real app."""
    bg = cv2.imread(os.path.join(WORK, 'montage_bg.png'))
    bg = cv2.resize(bg, (W, H))
    bg = cv2.GaussianBlur(bg, (0, 0), 38)
    bg = grade(bg, 'home')
    bg = (bg.astype(np.float32) * 0.9 + np.array([239, 246, 255], np.float32) * 0.1).astype(np.uint8)
    cards = shot['cards']
    n = int(round(shot['dur'] * FPS))
    phone_w = 820
    mocks = {c['ui']: phone_mock(load_ui(c['ui'], cv2.imread(os.path.join(WORK, 'camfill.png')) if 'cam' in c['ui'] else None), phone_w) for c in cards}
    PW, PH = next(iter(mocks.values())).size
    shadow, pad = drop_shadow((PW, PH))
    labels = {c['label']: text_layer([(c['label'], 'ui', 64, (22, 33, 31, 235))], (2380, 1020)) for c in cards if c.get('label')}
    subs = {c['sub']: text_layer([(c['sub'], 'ui', 44, (74, 92, 90, 220))], (2380, 1118)) for c in cards if c.get('sub')}
    starts = np.cumsum([0] + [c['dur'] for c in cards])
    for i in range(n):
        t = i / FPS
        ci = int(np.searchsorted(starts, t, side='right') - 1)
        ci = min(ci, len(cards) - 1)
        c, tl = cards[ci], t - starts[ci]
        img = mocks[c['ui']]
        if ci > 0 and tl < 0.22:
            prev = mocks[cards[ci - 1]['ui']]
            img = Image.blend(prev, img, ease(tl / 0.22))
        # slow drift: the whole montage is one continuous camera move
        drift = t / shot['dur']
        cx = int(1360 - 40 * drift)
        cy = int(H / 2 + 18 * np.sin(t * 0.7))
        scale = 1.0 + 0.035 * drift
        im = img.resize((int(PW * scale), int(PH * scale)), Image.LANCZOS)
        frame = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB)).convert('RGBA')
        shs = shadow.resize((int(shadow.size[0] * scale), int(shadow.size[1] * scale)))
        black = Image.new('RGBA', shs.size, (40, 28, 20, 255)); black.putalpha(shs)
        frame.alpha_composite(black, (cx - shs.size[0] // 2 + 30, cy - shs.size[1] // 2 + 50))
        frame.alpha_composite(im, (cx - im.size[0] // 2, cy - im.size[1] // 2))
        out = cv2.cvtColor(np.asarray(frame.convert('RGB')), cv2.COLOR_RGB2BGR)
        if c.get('label'):
            k = ease(tl / 0.5) * (1 - ease((tl - c['dur'] + 0.35) / 0.3)) if ci < len(cards) - 1 else ease(tl / 0.5)
            out = over(out, labels[c['label']], k, dy=(1 - k) * 16)
            if c.get('sub'):
                out = over(out, subs[c['sub']], k * 0.95, dy=(1 - k) * 22)
        wr.write(grain(out, rng, 1.4))
    return n


def render_endcard(shot, wr, rng):
    src = os.path.join(WORK, 'endcard_splash_4k.mp4')
    frames = list(read_frames(src, 0, 4.0))
    n = int(round(shot['dur'] * FPS))
    cta = text_layer([(shot['cta'], 'ui', 50, (14, 75, 78, 230))], (W // 2, 1560), align='center')
    for i in range(n):
        t = i / FPS
        f = frames[min(i, len(frames) - 1)]
        if t >= shot['cta_t']:
            k = ease((t - shot['cta_t']) / 0.8)
            f = over(f, cta, k, dy=(1 - k) * 10)
        fade = shot.get('fade_out', 0)
        if fade and t > shot['dur'] - fade:
            k = (t - (shot['dur'] - fade)) / fade
            f = (f.astype(np.float32) * (1 - 0.0 * k)).astype(np.uint8)
        wr.write(f)
    return n


SUPERS = {}


def main():
    rng = np.random.default_rng(3)
    for sid, s in CFG.get('supers', {}).items():
        SUPERS[sid] = text_layer([(s['text'], s.get('kind', 'display'), s.get('size', 84), tuple(s.get('rgba', [255, 250, 242, 240])))],
                                 tuple(s['xy']), align=s.get('align', 'center'))
    parts = []
    only = set(os.environ.get('ONLY', '').split(',')) - {''}
    for idx, shot in enumerate(CFG['shots']):
        out = os.path.join(WORK, 'parts', f"{idx:02d}_{shot['id']}.mp4")
        parts.append(out)
        if only and shot['id'] not in only and os.path.exists(out):
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        wr = Writer(out)
        kind = shot.get('kind', 'plate')
        n = {'plate': render_plate, 'montage': render_montage, 'endcard': render_endcard}[kind](shot, wr, rng)
        wr.close()
        print(f"shot {shot['id']}: {n} frames ({n / FPS:.2f}s)", flush=True)
    with open(os.path.join(WORK, 'parts.txt'), 'w') as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    sh(f'ffmpeg -v error -y -f concat -safe 0 -i {WORK}/parts.txt -c copy {WORK}/picture_4k.mp4')
    sh(f'ffprobe -v error -show_entries format=duration -of csv=p=0 {WORK}/picture_4k.mp4')


if __name__ == '__main__':
    main()
