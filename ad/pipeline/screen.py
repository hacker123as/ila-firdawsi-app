"""Track a blank, glowing phone screen through a clip and composite the real Ila Firdawsi UI.

The generated plates were shot with a plain white screen. For every frame we find that bright
quad, smooth its corners over time, warp the UI onto it, and use the plate's own brightness as
the matte, so a thumb or hand that crosses the glass hides the UI exactly as it would on a real
phone. Glass sheen, exposure and softness are matched back to the plate.
"""
import cv2
import numpy as np


def order_corners(pts):
    pts = np.asarray(pts, np.float32).reshape(-1, 2)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], np.float32)


OPTS = {'lo': 175.0, 'span': 45.0, 'roi': None}


def screen_mask(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    v, s = hsv[..., 2].astype(np.float32), hsv[..., 1].astype(np.float32)
    m = np.clip((v - OPTS['lo']) / OPTS['span'], 0, 1) * np.clip((70 - s) / 30, 0, 1)
    if OPTS['roi'] is not None:
        h, w = m.shape
        x0, y0, x1, y1 = OPTS['roi']
        r = np.zeros_like(m); r[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 1
        m *= r
    return m


def find_quad(frame, prev=None, min_area=0.004):
    h, w = frame.shape[:2]
    m = (screen_mask(frame) > 0.5).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, score = None, -1
    for c in cs:
        a = cv2.contourArea(c)
        if a < min_area * w * h:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        asp = bh / max(bw, 1)
        if not 1.2 < asp < 3.2:
            continue
        hull = cv2.convexHull(c)
        ap = cv2.approxPolyDP(hull, 0.03 * cv2.arcLength(hull, True), True)
        if len(ap) != 4:
            rect = cv2.minAreaRect(hull)
            ap = cv2.boxPoints(rect)
        q = order_corners(ap)
        sc = a
        if prev is not None:
            dist = np.linalg.norm(q.mean(0) - prev.mean(0))
            sc = a / (1 + dist / 40)
        if sc > score:
            best, score = q, sc
    return best


def track(frames, seed=None):
    quads, prev = [], seed
    for f in frames:
        q = find_quad(f, prev)
        if q is None:
            q = prev
        quads.append(q)
        prev = q if q is not None else prev
    # fill leading gaps, then smooth each corner coordinate over time
    first = next((q for q in quads if q is not None), None)
    quads = [q if q is not None else first for q in quads]
    arr = np.stack(quads).astype(np.float32)
    k = 5
    pad = np.pad(arr, ((k, k), (0, 0), (0, 0)), mode='edge')
    med = np.stack([np.median(pad[i:i + 2 * k + 1], axis=0) for i in range(len(arr))])
    g = cv2.getGaussianKernel(2 * k + 1, 2.0).ravel()
    pad = np.pad(med, ((k, k), (0, 0), (0, 0)), mode='edge')
    sm = np.stack([np.tensordot(g, pad[i:i + 2 * k + 1], axes=(0, 0)) for i in range(len(arr))])
    return sm


def rounded_alpha(w, h, r):
    a = np.zeros((h, w), np.uint8)
    cv2.rectangle(a, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(a, (0, r), (w, h - r), 255, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(a, (cx, cy), r, 255, -1, lineType=cv2.LINE_AA)
    return a.astype(np.float32) / 255


def composite(frame, ui_bgr, quad, inset=0.012, brightness=0.93, sheen=0.10, blur=0.0):
    """Warp ui_bgr onto quad in frame. The quad is the lit glass; the UI is inset a hair."""
    h, w = frame.shape[:2]
    uh, uw = ui_bgr.shape[:2]
    c = quad.mean(0)
    q = c + (quad - c) * (1 - inset)
    src = np.float32([[0, 0], [uw, 0], [uw, uh], [0, uh]])
    H = cv2.getPerspectiveTransform(src, q.astype(np.float32))
    ui = cv2.warpPerspective(ui_bgr, H, (w, h), flags=cv2.INTER_AREA if uw > (q[1][0] - q[0][0]) else cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_CONSTANT)
    ra = rounded_alpha(uw, uh, int(uw * 0.075))
    alpha = cv2.warpPerspective(ra, H, (w, h), flags=cv2.INTER_LINEAR)
    # the plate's own glow is the matte: fingers and hands over the glass stay in front
    m = screen_mask(frame)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    m = cv2.GaussianBlur(m, (0, 0), 1.2)
    a = (alpha * m)[..., None]
    uif = ui.astype(np.float32) * brightness
    if blur > 0:
        uif = cv2.GaussianBlur(uif, (0, 0), blur)
    # glass: keep a trace of the plate's highlights and gradients on top of the UI
    plate = frame.astype(np.float32)
    base = cv2.GaussianBlur(plate, (0, 0), 25)
    hi = np.clip(plate - base, 0, 255)
    lum_plate = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255
    shade = 0.82 + 0.18 * cv2.GaussianBlur(lum_plate, (0, 0), 20)
    uif = uif * shade + hi * sheen * 2
    out = plate * (1 - a) + np.clip(uif, 0, 255) * a
    return np.clip(out, 0, 255).astype(np.uint8)


def ui_at(t, schedule, cache):
    """schedule: list of (t_start, image_path, crossfade_s). Returns BGR UI image for time t."""
    cur = None
    for i, (ts, path, xf) in enumerate(schedule):
        if t >= ts:
            cur = i
    if cur is None:
        cur = 0
    ts, path, xf = schedule[cur]
    img = cache[path]
    if cur > 0 and xf > 0 and t < ts + xf:
        prev = cache[schedule[cur - 1][1]]
        k = (t - ts) / xf
        k = k * k * (3 - 2 * k)
        img = cv2.addWeighted(prev, 1 - k, img, k, 0)
    return img
