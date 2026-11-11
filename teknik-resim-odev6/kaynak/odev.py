"""Yatak gövdesi – ÖN görünüş kademeli kesit (A-A), YAN ve ÜST görünüş izdüşüm, A4 antetli, ölçülü.

Kesit düzlemi: göbek eksenlerinden (X = 30) geçer, Y = Y_KADEME'de öndeki Ø8 delik
sırasına (X = 47.5) kademe yapar. Kaburgalar boyuna kesildiği için taranmaz.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("teknik-resim-odev4", "teknik-resim-odev3", "teknik-resim-odev2"):
    sys.path.insert(0, os.path.join(HERE, "..", "..", d, "kaynak"))

from ezdxf.enums import TextEntityAlignment  # noqa: E402

import hafta7 as h7  # noqa: E402
from kesitli import parca_d  # noqa: E402
from olculer import Olcu  # noqa: E402
from uc_gorunus import (add_prims, bbox, box, centerlines, clean, cut, cylinder_axes, fuse,  # noqa: E402
                        hlr, merge_lines, new_doc, project, remove_hidden_under_visible)

C1, C2, Y_KADEME = 30.0, 47.5, 101.0
K = 2.0            # ölçek 1:2 (model gerçek ölçüde, çerçeve 2 kat)
TARIH = "11.11.2026"


def kademeli_kes(shape):
    tool = fuse(box(C1, 1000, -1000, Y_KADEME, -1000, 1000), box(C2, 1000, Y_KADEME, 1000, -1000, 1000))
    return clean(cut(shape, tool))


def olcular():
    D = Olcu(K)
    # A-A (Y, Z)
    D.h("ON", (-6.5, 0), (6.5, 0), -16, text="%%c13")
    D.h("ON", (70, 0), (90, 0), -16, text="%%c20")
    D.h("ON", (80, 0), (110, 0), -32)
    D.h("ON", (110, 0), (138, 0), -32)
    D.h("ON", (-12.5, 20), (12.5, 20), 34, text="%%c25")
    D.h("ON", (62.5, 35), (97.5, 35), 49, text="%%c35")
    D.h("ON", (0, 23), (80, 38), 63)
    D.h("ON", (0, 23), (150, 10), 77)
    D.v("ON", (150, 0), (150, 10), 166)
    D.v("ON", (150, 10), (97.5, 35), 166)
    D.v("ON", (-30, 10), (-12.5, 20), -46)
    D.ang("ON", (97.5, 35), (122.5, 10), (120, 35), 24)
    # YAN (X, Z)
    D.h("SOL", (0, 0), (60, 0), -16)
    D.h("SOL", (26, 35), (34, 35), 49)
    # ÜST (Y, -X)
    D.v("UST", (138, -12.5), (138, -47.5), 188)
    D.h("UST", (0, -14.5), (20, -27), 16)
    D.rad("UST", (20, -30), 50, 212)
    D.mark("UST", (20, -30), 4)
    D.dia("UST", (138, -12.5), 4, 50, text="4x<>", dist=24)
    return D


def kesit_cizgisi(msp, bbv, dx, dy, k):
    """Üst görünüşte kademeli kesit düzlemi: çizgi, kalın uç/köşeler, oklar, harfler."""
    P = lambda p: (p[0] + dx, p[1] + dy)
    m = 8 * k
    pts = [(bbv[0] - m, -C1), (Y_KADEME, -C1), (Y_KADEME, -C2), (bbv[2] + m, -C2)]
    for a, b in zip(pts, pts[1:]):
        msp.add_line(P(a), P(b), dxfattribs={"layer": "EKSEN"})
    kal = {"layer": "KESIT"}
    t = 5 * k
    msp.add_line(P(pts[0]), P((pts[0][0] + 6 * k, pts[0][1])), dxfattribs=kal)
    msp.add_line(P(pts[3]), P((pts[3][0] - 6 * k, pts[3][1])), dxfattribs=kal)
    msp.add_line(P((pts[1][0] - t, pts[1][1])), P(pts[1]), dxfattribs=kal)     # köşeler
    msp.add_line(P(pts[1]), P((pts[1][0], pts[1][1] - t)), dxfattribs=kal)
    msp.add_line(P((pts[2][0], pts[2][1] + t)), P(pts[2]), dxfattribs=kal)
    msp.add_line(P(pts[2]), P((pts[2][0] + t, pts[2][1])), dxfattribs=kal)
    for end, s in ((pts[0], 1), (pts[3], -1)):
        tail = (end[0] + s * k, end[1])
        tip = (tail[0], tail[1] + 8 * k)                    # bakış yönü: yukarı (-X)
        msp.add_line(P(tail), P(tip), dxfattribs={"layer": "OLCU"})
        msp.add_solid([P(tip), P((tip[0] - 0.9 * k, tip[1] - 3 * k)), P((tip[0] + 0.9 * k, tip[1] - 3 * k))],
                      dxfattribs={"layer": "OLCU"})
        msp.add_text("A", height=5 * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            P((tip[0] - s * 2 * k, tip[1] + 3 * k)), align=TextEntityAlignment.MIDDLE_CENTER)


def build(outdir, name="Soru2"):
    k = K
    shape = clean(parca_d())
    half = kademeli_kes(shape)
    norib = kademeli_kes(clean(parca_d(with_ribs=False)))
    sfaces = h7.section_faces(norib, 0, C1) + h7.section_faces(norib, 0, C2)

    views = ("ON", "SOL", "UST")
    data = {}
    vv, _ = hlr(half, "ON")
    for f in sfaces:                      # taranan bölgelerin sınırları (kaburga altındaki çizgiler dahil)
        for loop in h7.face_loops(f, "ON"):
            vv += [("L", a, b) for a, b in zip(loop, loop[1:])]
    # kademe yüzeyi kesit görünüşünde çizilmez
    vv = [p for p in merge_lines(vv)
          if not (p[0] == "L" and abs(p[1][0] - Y_KADEME) < 1e-3 and abs(p[2][0] - Y_KADEME) < 1e-3)]
    cls = []
    for kk, base, r, lo, hi in cylinder_axes(half):
        if kk != 2:
            continue
        c = C1 if base[1] < Y_KADEME else C2
        if abs(base[0] - c) > r + 1e-6:
            continue
        cls.append(((base[1], lo - 3 * k), (base[1], hi + 3 * k)))
    data["ON"] = (vv, [], cls)
    for v in ("SOL", "UST"):
        a, hh = hlr(shape, v)
        a = merge_lines(a)
        hh = merge_lines(remove_hidden_under_visible(a, merge_lines(hh)))
        data[v] = (a, hh, centerlines(shape, v, ext=3 * k))

    olcu = olcular()
    gap = 10.0
    bb = {v: bbox(data[v][0]) for v in views}
    full = {}
    for v in views:
        e = olcu.extents(v)
        x0, y0, x1, y1 = bb[v]
        if e:
            x0, y0, x1, y1 = min(x0, e[0]), min(y0, e[1]), max(x1, e[2]), max(y1, e[3])
        if v == "UST":
            m = 12 * k
            x0, x1 = min(x0, bb[v][0] - m), max(x1, bb[v][2] + m)
        full[v] = [x0, y0 - 9 * k, x1, y1]
    off = {"ON": (0.0, 0.0)}
    off["SOL"] = (full["ON"][2] + gap * k - full["SOL"][0], 0.0)
    full["ON"][1] = full["SOL"][1] = min(full["ON"][1], full["SOL"][1])
    off["UST"] = (0.0, full["ON"][1] - gap * k - full["UST"][3])
    gx0 = min(full[v][0] + off[v][0] for v in views)
    gy0 = min(full[v][1] + off[v][1] for v in views)
    gx1 = max(full[v][2] + off[v][0] for v in views)
    gy1 = max(full[v][3] + off[v][1] for v in views)

    paper = "A4Y"
    ax0, ay0, ax1, ay1 = h7.drawing_area(paper, k)
    print(f"yerleşim {(gx1 - gx0) / k:.0f} x {(gy1 - gy0) / k:.0f} mm (kağıtta), alan {(ax1 - ax0) / k:.0f} x {(ay1 - ay0) / k:.0f}")
    assert gx1 - gx0 <= ax1 - ax0 and gy1 - gy0 <= ay1 - ay0, "A4'e sığmıyor"

    doc = new_doc()
    doc.header["$LTSCALE"] = k
    doc.dimstyles.get("OLCU").dxf.dimscale = k
    L = doc.layers
    L.add("TARAMA", color=8, linetype="Continuous", lineweight=18)
    L.add("KESIT", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE_INCE", color=7, linetype="Continuous", lineweight=25)
    msp = doc.modelspace()
    h7.frame(msp, "YATAK GÖVDESİ", paper, k, "1:2")
    W, H = h7.KAGIT[paper]
    msp.add_text(TARIH, height=2.5 * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
        ((W - 10 - 180 + 20 + 1.5) * k, (10 + 7 + 3.5) * k), align=TextEntityAlignment.MIDDLE_LEFT)
    sx = (ax0 + ax1) / 2 - (gx0 + gx1) / 2
    sy = (ay0 + ay1) / 2 - (gy0 + gy1) / 2

    labels = {"ON": "A-A KESİTİ (KADEMELİ)", "SOL": "SOL YAN GÖRÜNÜŞ", "UST": "ÜST GÖRÜNÜŞ"}
    for v in views:
        vis, hid, cl = data[v]
        dx, dy = off[v][0] + sx, off[v][1] + sy
        add_prims(msp, vis, "GORUNEN", dx, dy)
        add_prims(msp, hid, "GIZLI", dx, dy)
        for a, b in cl:
            msp.add_line((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy), dxfattribs={"layer": "EKSEN"})
        if v == "ON":
            hch = msp.add_hatch(dxfattribs={"layer": "TARAMA"})
            hch.set_pattern_fill("ANSI31", scale=0.8 * k)
            for f in sfaces:
                for loop in h7.face_loops(f, v):
                    hch.paths.add_polyline_path([(p[0] + dx, p[1] + dy) for p in loop], is_closed=True)
        if v == "UST":
            kesit_cizgisi(msp, bb[v], dx, dy, k)
        olcu.render(msp, v, dx, dy)
        x0, _, x1, _ = bb[v]
        msp.add_text(labels[v], height=3.5 * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            ((x0 + x1) / 2 + dx, full[v][1] + dy + 4 * k), align=TextEntityAlignment.TOP_CENTER)
    msp.add_text("Köşe kavisleri R2", height=3.5 * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
        (ax0, 14 * k))
    doc.set_modelspace_vport(height=(H + 10) * k, center=(W * k / 2, H * k / 2))
    path = os.path.join(outdir, f"{name}.dxf")
    doc.saveas(path)
    print("yazıldı:", path)
    return path


def soru_2d(outdir, name="Soru1"):
    """2D şekil: 56 taban, 86'da R14 kulak, 38/72 kademe, 58'den 28'e eğik kenar, 3 x Ø16 delik."""
    k = 1.0
    doc = new_doc()
    L = doc.layers
    L.add("CERCEVE", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE_INCE", color=7, linetype="Continuous", lineweight=25)
    msp = doc.modelspace()
    paper = "A4D"
    h7.frame(msp, "2D ŞEKİL", paper, k, "1:1")
    W, H = h7.KAGIT[paper]
    msp.add_text(TARIH, height=2.5, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
        (W - 10 - 180 + 20 + 1.5, 10 + 7 + 3.5), align=TextEntityAlignment.MIDDLE_LEFT)
    ax0, ay0, ax1, ay1 = h7.drawing_area(paper, k)
    ox = (ax0 + ax1) / 2 - 36          # ölçülerle birlikte ortala
    oy = (ay0 + ay1) / 2 - 50
    P = lambda x, y: (x + ox, y + oy)
    g = {"layer": "GORUNEN"}
    e = {"layer": "EKSEN"}
    # dış hat: sol alt köşeden saat yönünün tersine
    pts = [(0, 86), (0, 0), (56, 0), (56, 28), (38, 58), (38, 72), (28, 72), (28, 86)]
    for a, b in zip(pts, pts[1:]):
        msp.add_line(P(*a), P(*b), dxfattribs=g)
    msp.add_arc(P(14, 86), 14, 0, 180, dxfattribs=g)                 # R14
    for cx, cy, ext in ((14, 86, 17), (14, 14, 11), (42, 14, 11)):
        msp.add_circle(P(cx, cy), 8, dxfattribs=g)                   # Ø16
        msp.add_line(P(cx - ext, cy), P(cx + ext, cy), dxfattribs=e)
        msp.add_line(P(cx, cy - ext), P(cx, cy + ext), dxfattribs=e)

    D = Olcu()
    D.h("ON", (0, 0), (56, 0), -12)
    D.v("ON", (0, 0), (0, 86), -12)
    D.h("ON", (0, 86), (38, 72), 110)
    D.v("ON", (56, 0), (53, 14), 66)
    D.v("ON", (56, 0), (56, 28), 74)
    D.v("ON", (56, 0), (38, 58), 82)
    D.v("ON", (56, 0), (38, 72), 90)
    D.h("ON", (0, 14), (14, 25), 32)
    D.h("ON", (14, 25), (42, 25), 32)
    D.dia("ON", (14, 14), 8, 225, dist=17)
    D.dia("ON", (14, 86), 8, 300, dist=17)
    D.rad("ON", (14, 86), 14, 50)
    D.render(msp, "ON", ox, oy)
    doc.set_modelspace_vport(height=H + 10, center=(W / 2, H / 2))
    path = os.path.join(outdir, f"{name}.dxf")
    doc.saveas(path)
    print("yazıldı:", path)
    return path


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    soru_2d(outdir)
    build(outdir)
