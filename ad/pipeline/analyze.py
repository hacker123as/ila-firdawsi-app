"""Timing and QC pass over the plates: screen-quad stability, motion, faces."""
import sys, os, cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); import screen
W = sys.argv[1]
def frames(p, scale=0.5):
    cap = cv2.VideoCapture(p); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(cv2.resize(f, None, fx=scale, fy=scale))
    return out
import json
SH = {x.get('plate','').replace('.mp4',''): x.get('screen', {}) for x in json.load(open(os.path.join(os.path.dirname(__file__), 'shots.json')))['shots']}
for name in sys.argv[2:]:
    screen.OPTS.update({'lo': 175.0, 'span': 45.0, 'roi': None}); screen.OPTS.update(SH.get(name, {}))
    fr = frames(f'{W}/plates/{name}.mp4')
    print(f'== {name}: {len(fr)} frames')
    raw = [screen.find_quad(f) for f in fr]
    found = sum(q is not None for q in raw)
    print(f' screen quad found in {found}/{len(fr)}')
    if found > len(fr) * 0.3:
        sm = screen.track(fr)
        for i in range(0, len(fr), 6):
            q = sm[i]; c = q.mean(0); wq = np.linalg.norm(q[1] - q[0]); hq = np.linalg.norm(q[3] - q[0])
            print(f'  t={i/24:4.2f} c=({c[0]:.0f},{c[1]:.0f}) w={wq:.0f} h={hq:.0f} raw={"y" if raw[i] is not None else "n"}')
    g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in fr]
    mot = [0] + [float(np.mean(np.abs(g[i] - g[i - 1]))) for i in range(1, len(g))]
    print(' motion/0.25s:', ' '.join(f'{np.mean(mot[i:i+6]):.1f}' for i in range(0, len(mot), 6)))
    try:
        import mediapipe as mp
        fd = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        s = []
        for i in range(0, len(fr), 12):
            r = fd.process(cv2.cvtColor(fr[i], cv2.COLOR_BGR2RGB))
            s.append(len(r.detections) if r.detections else 0)
        print(' faces per 0.5s:', s)
    except Exception as e:
        print(' face check skipped', e)
