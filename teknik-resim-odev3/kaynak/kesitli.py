"""3. ödev: kesit görünüşlü teknik resimler (A4, antetli, ölçülü).

Parça A, B : ÖN görünüş (A-A tam kesit) + ÜST görünüş
Parça C    : ÖN görünüş (A-A tam kesit) + SOL YAN görünüş   (Pabuç)
Parça D    : ÖN görünüş (A-A tam kesit) + ÜST görünüş        (Yatak gövdesi)

Model ekseni:  X = derinlik (ön yüz +X tarafında, "ÖN" okunun geldiği taraf)
               Y = ön görünüşte soldan sağa,  Z = yukarı
Görünüş düzlemleri: ON (Y, Z)   UST (Y, -X)   SOL (X, Z)
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "teknik-resim-odev2", "kaynak"))

import ezdxf  # noqa: E402
from ezdxf.enums import TextEntityAlignment  # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface  # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common  # noqa: E402
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone  # noqa: E402
from OCP.GCPnts import GCPnts_QuasiUniformDeflection  # noqa: E402
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Plane  # noqa: E402
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE  # noqa: E402
from OCP.TopExp import TopExp_Explorer  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402

from olculer import Olcu  # noqa: E402
from uc_gorunus import (VIEWS, X, Y, Z, add_prims, bbox, box, centerlines, clean, cut,  # noqa: E402
                        cyl, fuse, hlr, merge_lines, new_doc, prism,
                        remove_hidden_under_visible)


def common(a, b):
    return BRepAlgoAPI_Common(a, b).Shape()


def cone(p, r1, r2, h):
    return BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(*p), gp_Dir(0, 0, 1)), r1, r2, h).Shape()


# ====================================================================== PARÇALAR


def parca_a():
    """Çatallı bağlantı parçası (120 x 35 x 64)."""
    foot_l = prism([(0, 0, 4), (35, 0, 4), (35, 40), (0, 40)], "XY", 0, 14)
    foot_r = prism([(0, 80), (35, 80), (35, 120, 4), (0, 120, 4)], "XY", 0, 14)
    mid = box(0, 35, 40, 80, 0, 14)
    plate_l = prism([(30, 0), (50, 0), (50, 64), (30, 64, 5)], "YZ", 0, 35)
    block_r = prism([(70, 0), (90, 0), (90, 64, 5), (70, 64)], "YZ", 0, 35)
    web = box(0, 35, 50, 70, 0, 32)
    s = fuse(foot_l, foot_r, mid, plate_l, block_r, web)
    s = cut(s,
            box(-1, 36, 40, 80, -1, 18),                       # alttaki 18'lik kanal
            cyl((17.5, 25, 50), Y, 6.5, 70),                   # Ø13 delik
            cyl((17.5, 15, -1), Z, 5, 16), cone((17.5, 15, 12), 5, 8, 3),    # Ø10 + 2x45°
            cyl((17.5, 105, -1), Z, 5, 16), cone((17.5, 105, 12), 5, 8, 3))
    return s


def parca_b():
    """Flanşlı burç: R19 / R10 flanş (5 kalın), Ø23 / Ø15 burç, 50 yükseklik."""
    D, r1, r2 = 22.5, 19.0, 10.0
    k = (r1 - r2) / D
    sq = math.sqrt(1 - k * k)
    lobe = [(r1 * sq, r1 * k), (r2 * sq, D + r2 * k), (-r2 * sq, D + r2 * k), (-r1 * sq, r1 * k)]
    lobe2 = [(x, -y) for x, y in reversed(lobe)]
    plate = fuse(prism(lobe, "XY", 0, 5), prism(lobe2, "XY", 0, 5),
                 cyl((0, 0, 0), Z, r1, 5), cyl((0, D, 0), Z, r2, 5), cyl((0, -D, 0), Z, r2, 5))
    s = fuse(plate, cyl((0, 0, 0), Z, 11.5, 50))
    s = cut(s, cyl((0, 0, -1), Z, 7.5, 52), cyl((0, D, -1), Z, 3.75, 7), cyl((0, -D, -1), Z, 3.75, 7))
    return s


LUG_C, LUG_R = (25.0, 40.0), 15.0


def _lug_profile():
    from uc_gorunus import tangent_point
    tl = tangent_point((0, 18), LUG_C, LUG_R, +1)
    tr = tangent_point((50, 18), LUG_C, LUG_R, -1)
    return tl, tr


def parca_c():
    """Pabuç: 95 x 50 x 18 taban, altta 30'luk ray, Ø12/Ø24x3 havşa, R15 kulak (14 kalın)."""
    base = fuse(box(0, 50, 0, 95, 5, 18), box(10, 40, 0, 95, 0, 5))
    tl, tr = _lug_profile()
    lug_prof = [(0, 5), (50, 5), (50, 18), tr, tl, (0, 18)]
    lug = fuse(prism(lug_prof, "XZ", 81, 95), cyl((LUG_C[0], 81, LUG_C[1]), Y, LUG_R, 14))
    # taban üstü ile kulak arasındaki R5 iç kavis, kulak profiline göre kırpılmış
    cove = cut(box(0, 50, 76, 81, 18, 23), cyl((-1, 76, 23), X, 5, 52))
    clip = fuse(prism(lug_prof, "XZ", 70, 95), cyl((LUG_C[0], 70, LUG_C[1]), Y, LUG_R, 25))
    cove = common(cove, clip)
    s = fuse(base, lug, cove)
    s = cut(s,
            cyl((25, 40, -1), Z, 6, 20),          # Ø12 delik
            cyl((25, 40, 15), Z, 12, 4),          # Ø24 x 3 havşa
            cyl((LUG_C[0], 70, LUG_C[1]), Y, 6, 30))   # kulak deliği Ø12
    return s


def parca_d(with_ribs=True):
    """Yatak gövdesi: 60 derinlik, 10 kalın taban (sol ucu R50), Ø25 ve Ø35 göbekler, 8'lik kaburgalar."""
    # model X = derinlik (0 arka, 60 ön), Y = boy (küçük göbek ekseni Y=0)
    plate = common(box(0, 60, -30, 150, 0, 10),
                   fuse(cyl((30, 20, -1), Z, 50, 12), box(-1, 61, 20, 151, -1, 11)))
    boss1 = cyl((30, 0, 0), Z, 12.5, 20)
    boss2 = cyl((30, 80, 0), Z, 17.5, 35)
    parts = [plate, boss1, boss2]
    if with_ribs:
        parts.append(prism([(5, 10), (75, 10), (75, 35), (62.5, 35), (12.5, 20), (5, 20)], "YZ", 26, 34))
        parts.append(prism([(85, 10), (122.5, 10), (97.5, 35), (85, 35)], "YZ", 26, 34))
    s = fuse(*parts)
    holes = [cyl((30, 0, -1), Z, 6.5, 22), cyl((30, 80, -1), Z, 10, 37)]
    for x in (12.5, 47.5):
        for y in (110, 138):
            holes.append(cyl((x, y, -1), Z, 4, 12))
    return cut(s, *holes)


# ====================================================================== ÖLÇÜLER


def olcu_a():
    D = Olcu()
    # A-A (Y, Z)
    D.h("ON", (0, 0), (40, 0), -10)
    D.h("ON", (40, 0), (80, 0), -10)
    D.h("ON", (80, 0), (120, 0), -10)
    D.h("ON", (0, 0), (120, 0), -18)
    D.v("ON", (0, 0), (0, 14), -10)
    D.v("ON", (0, 0), (30, 50), -18)
    D.v("ON", (0, 0), (40, 64), -26)
    D.v("ON", (40, 0), (45, 18), 45)
    D.v("ON", (80, 0), (60, 32), 60)
    D.v("ON", (90, 43.5), (90, 56.5), 100, text="%%c13")
    D.rad("ON", (35, 59), 5, 135)
    D.h("ON", (10, 14), (20, 14), 22, text="%%c10")
    D.lead("ON", (21, 13), (32, 24), "2x45%%d")
    # ÜST (Y, -X)
    D.h("UST", (0, 0), (30, 0), 10)
    D.h("UST", (30, 0), (50, 0), 10)
    D.h("UST", (50, 0), (70, 0), 10)
    D.h("UST", (70, 0), (90, 0), 10)
    D.v("UST", (120, 0), (120, -35), 130)
    D.v("UST", (105, -17.5), (120, -35), 122, text="17,5")
    D.h("UST", (0, -35), (15, -17.5), -45)
    D.rad("UST", (4, -31), 4, 225)
    return D


def olcu_b():
    D = Olcu()
    # A-A (Y, Z)
    D.h("ON", (-26.25, 0), (-18.75, 0), -8, text="%%c7,5")
    D.h("ON", (-22.5, 0), (22.5, 0), -15)
    D.v("ON", (32.5, 0), (32.5, 5), 40)
    D.v("ON", (-32.5, 0), (-11.5, 50), -40)
    D.h("ON", (-7.5, 50), (7.5, 50), 55, text="%%c15")
    D.h("ON", (-11.5, 50), (11.5, 50), 64, text="%%c23")
    # ÜST (Y, -X)
    D.rad("UST", (0, 0), 19, 35)
    D.rad("UST", (22.5, 0), 10, -30)
    return D


def olcu_c():
    D = Olcu()
    tl, tr = _lug_profile()
    # A-A (Y, Z)
    D.h("ON", (34, 0), (46, 0), -10, text="%%c12")
    D.h("ON", (0, 0), (95, 0), -18)
    D.h("ON", (0, 18), (40, 21), 64)
    D.h("ON", (28, 18), (52, 18), 26, text="%%c24")
    D.v("ON", (48, 15), (52, 18), 50)
    D.h("ON", (81, 55), (95, 55), 64)
    D.v("ON", (95, 0), (95, 18), 105)
    D.v("ON", (95, 0), (95, 40), 113)
    D.rad("ON", (76, 23), 5, 135)
    # SOL YAN (X, Z)
    D.h("SOL", (0, 5), (10, 0), -16)
    D.h("SOL", (10, 0), (40, 0), -16)
    D.h("SOL", (40, 0), (50, 5), -16)
    D.h("SOL", (0, 5), (50, 5), -24)
    D.v("SOL", (40, 0), (50, 5), 60)
    D.v("SOL", (40, 0), (50, 18), 68)
    D.rad("SOL", LUG_C, LUG_R, 45)
    D.dia("SOL", LUG_C, 6, 165, dist=26)
    return D


def olcu_d():
    D = Olcu()
    # A-A (Y, Z)
    D.h("ON", (-6.5, 0), (6.5, 0), -10, text="%%c13")
    D.h("ON", (70, 0), (90, 0), -10, text="%%c20")
    D.h("ON", (-12.5, 20), (12.5, 20), 30, text="%%c25")
    D.h("ON", (62.5, 35), (97.5, 35), 44, text="%%c35")
    D.h("ON", (0, 23), (80, 38), 52)
    D.h("ON", (0, 23), (150, 10), 60)
    D.v("ON", (150, 0), (150, 10), 160)
    D.v("ON", (150, 10), (97.5, 35), 160)
    D.v("ON", (-30, 10), (-12.5, 20), -40)
    D.ang("ON", (97.5, 35), (122.5, 10), (117.5, 35), 16)
    # ÜST (Y, -X)
    D.v("UST", (150, 0), (150, -60), 168)
    D.v("UST", (138, -12.5), (138, -47.5), 158)
    D.h("UST", (80, -60), (110, -47.5), -70)
    D.h("UST", (110, -47.5), (138, -47.5), -70)
    D.h("UST", (0, -14.5), (20, -27), 10)
    D.rad("UST", (20, -30), 50, 160)
    D.mark("UST", (20, -30), 3)
    D.v("UST", (122.5, -26), (122.5, -34), 130)
    D.dia("UST", (138, -12.5), 4, 45, text="4x<>", dist=14)
    return D


# ====================================================================== KESİT YARDIMCILARI


def section_faces(shape, c):
    """X = c düzlemindeki (kesit) yüzeyler."""
    out = []
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        f = TopoDS.Face(exp.Current())
        s = BRepAdaptor_Surface(f)
        if s.GetType() == GeomAbs_Plane:
            pl = s.Plane()
            n = pl.Axis().Direction()
            if abs(abs(n.X()) - 1) < 1e-6 and abs(pl.Location().X() - c) < 1e-6:
                out.append(f)
        exp.Next()
    return out


def face_loops(face):
    """Yüzey sınırlarını (Y, Z) düzleminde kapalı çokgenler olarak döndür."""
    segs = []
    exp = TopExp_Explorer(face, TopAbs_EDGE)
    while exp.More():
        e = TopoDS.Edge(exp.Current())
        c = BRepAdaptor_Curve(e)
        if c.GetType() == GeomAbs_Line:
            p0, p1 = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
            pts = [(p0.Y(), p0.Z()), (p1.Y(), p1.Z())]
        else:
            d = GCPnts_QuasiUniformDeflection(c, 0.01)
            pts = [(d.Value(i).Y(), d.Value(i).Z()) for i in range(1, d.NbPoints() + 1)]
        segs.append(pts)
        exp.Next()
    loops = []
    close = lambda a, b: abs(a[0] - b[0]) < 1e-4 and abs(a[1] - b[1]) < 1e-4
    while segs:
        loop = list(segs.pop(0))
        changed = True
        while changed and not close(loop[0], loop[-1]):
            changed = False
            for i, s in enumerate(segs):
                if close(s[0], loop[-1]):
                    loop += s[1:]
                elif close(s[-1], loop[-1]):
                    loop += list(reversed(s))[1:]
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        loops.append(loop)
    return loops


def boundary_prims(faces):
    prims = []
    for f in faces:
        for loop in face_loops(f):
            for a, b in zip(loop, loop[1:]):
                prims.append(("L", a, b))
    return prims


# ====================================================================== ÇİZİM


KAGIT = {"A4": (297.0, 210.0), "A3": (420.0, 297.0)}


def drawing_area(paper):
    W, H = KAGIT[paper]
    return (20 + 4, 10 + 28 + 4, W - 10 - 4, H - 10 - 4)


def frame(msp, title, paper, scale_txt="1:1"):
    """Yatay çerçeve ve antet (kaynak sayfadaki antete benzer)."""
    W, H = KAGIT[paper]
    attr = lambda layer: {"layer": layer}
    msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True, dxfattribs=attr("CERCEVE_INCE"))
    x0, y0, x1, y1 = 20, 10, W - 10, H - 10
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs=attr("CERCEVE"))
    # antet: 180 x 28
    ax0 = x1 - 180
    rows = [y0 + 7 * i for i in range(5)]
    msp.add_lwpolyline([(ax0, y0), (x1, y0), (x1, rows[4]), (ax0, rows[4])], close=True,
                       dxfattribs=attr("CERCEVE"))
    for r in rows[1:4]:
        msp.add_line((ax0, r), (ax0 + 60, r), dxfattribs=attr("CERCEVE_INCE"))
    c1, c2, c3, c4 = ax0 + 20, ax0 + 60, ax0 + 75, ax0 + 125
    for cx in (c1, c2, c3, c4):
        msp.add_line((cx, y0), (cx, rows[4]), dxfattribs=attr("CERCEVE_INCE"))
    msp.add_line((c2, rows[3]), (c3, rows[3]), dxfattribs=attr("CERCEVE_INCE"))
    msp.add_line((c4, rows[1]), (x1, rows[1]), dxfattribs=attr("CERCEVE_INCE"))
    t = lambda s, p, h=2.5, al=TextEntityAlignment.MIDDLE_LEFT: msp.add_text(
        s, height=h, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(p, align=al)
    for i, s in enumerate(["Kontrol", "Tarih", "Sınıf - No", "Çizen"]):
        t(s, (ax0 + 1.5, rows[i] + 3.5))
    t("Ölçek", ((c2 + c3) / 2, rows[3] + 3.5), al=TextEntityAlignment.MIDDLE_CENTER)
    t(scale_txt, ((c2 + c3) / 2, rows[1] + 3.5), h=3.5, al=TextEntityAlignment.MIDDLE_CENTER)
    t(title, ((c3 + c4) / 2, rows[2]), h=3.5, al=TextEntityAlignment.MIDDLE_CENTER)
    t("Resim Numarası", ((c4 + x1) / 2, rows[1] + 3.5), al=TextEntityAlignment.MIDDLE_CENTER)
    t(paper, (x1 - 2, rows[4] + 3), h=2.5, al=TextEntityAlignment.MIDDLE_RIGHT)


def section_line(msp, view, c, ext, dx, dy, letter="A"):
    """Kesit düzlemi çizgisi, okları ve harfleri."""
    def P(p):
        return (p[0] + dx, p[1] + dy)

    if view == "UST":          # X = c  ->  v = -c, bakış yönü -X  => ok yukarı
        a, b = (ext[0], -c), (ext[1], -c)
        d = (1, 0)
        arrow = (0, 1)
    else:                      # SOL: X = c  ->  u = c, bakış yönü -X => ok sola
        a, b = (c, ext[0]), (c, ext[1])
        d = (0, 1)
        arrow = (-1, 0)
    msp.add_line(P(a), P(b), dxfattribs={"layer": "EKSEN"})
    for end, s in ((a, 1), (b, -1)):
        e2 = (end[0] + s * d[0] * 6, end[1] + s * d[1] * 6)
        msp.add_line(P(end), P(e2), dxfattribs={"layer": "KESIT"})
        tail = (end[0] + s * d[0] * 1, end[1] + s * d[1] * 1)
        tip = (tail[0] + arrow[0] * 8, tail[1] + arrow[1] * 8)
        msp.add_line(P(tail), P(tip), dxfattribs={"layer": "OLCU"})
        n = (-arrow[1], arrow[0])
        base = (tip[0] - arrow[0] * 3, tip[1] - arrow[1] * 3)
        msp.add_solid([P(tip), P((base[0] + n[0] * 0.9, base[1] + n[1] * 0.9)),
                       P((base[0] - n[0] * 0.9, base[1] - n[1] * 0.9))], dxfattribs={"layer": "OLCU"})
        lp = (tip[0] + arrow[0] * 3 - s * d[0] * 2, tip[1] + arrow[1] * 3 - s * d[1] * 2)
        msp.add_text(letter, height=5, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            P(lp), align=TextEntityAlignment.MIDDLE_CENTER)


def build(name, title, shape, views, sec_c, olcu, outdir, norib_shape=None, notes=(), gap=12.0,
          label_gap=9.0):
    """views: ('ON', 'UST') veya ('ON', 'SOL'); ON görünüşü X=sec_c düzleminde tam kesit."""
    shape = clean(shape)
    half = clean(cut(shape, box(sec_c, 1000, -1000, 1000, -1000, 1000)))

    data = {}
    vis, _ = hlr(half, "ON")
    hatch_src = half if norib_shape is None else clean(
        cut(clean(norib_shape), box(sec_c, 1000, -1000, 1000, -1000, 1000)))
    sfaces = section_faces(hatch_src, sec_c)
    vis = merge_lines(vis + (boundary_prims(sfaces) if norib_shape is not None else []))
    from uc_gorunus import cylinder_axes
    keep = [ax for ax in cylinder_axes(half) if ax[0] == 0 or abs(ax[1][0] - sec_c) <= ax[2] + 1e-6]
    cls_on = []
    for k, base, r, lo, hi in keep:
        if k == 0:
            continue
        p0, p1 = list(base), list(base)
        p0[k], p1[k] = lo, hi
        a = (p0[1], p0[2])
        b = (p1[1], p1[2])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        cls_on.append(((a[0] - 3 * ux, a[1] - 3 * uy), (b[0] + 3 * ux, b[1] + 3 * uy)))
    data["ON"] = (vis, [], cls_on)
    for v in views[1:]:
        vv, hh = hlr(shape, v)
        vv = merge_lines(vv)
        hh = merge_lines(remove_hidden_under_visible(vv, merge_lines(hh)))
        data[v] = (vv, hh, centerlines(shape, v))

    bb = {v: bbox(data[v][0]) for v in views}
    full = {}
    for v in views:
        e = olcu.extents(v)
        x0, y0, x1, y1 = bb[v]
        if e:
            x0, y0, x1, y1 = min(x0, e[0]), min(y0, e[1]), max(x1, e[2]), max(y1, e[3])
        if v == views[1]:     # kesit çizgisi ve harfleri için pay
            if v == "UST":
                x0, x1 = x0 - 14, x1 + 14
            else:
                y0, y1 = y0 - 16, y1 + 16
        full[v] = [x0, y0 - label_gap, x1, y1]

    off = {"ON": (0.0, 0.0)}
    if views[1] == "UST":
        off["UST"] = (0.0, full["ON"][1] - gap - full["UST"][3])
    else:
        off["SOL"] = (full["ON"][2] + gap - full["SOL"][0], 0.0)
        full["ON"][1] = full["SOL"][1] = min(full["ON"][1], full["SOL"][1])

    # tüm yerleşimi A4 çizim alanının ortasına taşı
    gx0 = min(full[v][0] + off[v][0] for v in views)
    gy0 = min(full[v][1] + off[v][1] for v in views)
    gx1 = max(full[v][2] + off[v][0] for v in views)
    gy1 = max(full[v][3] + off[v][1] for v in views)

    doc = new_doc()
    L = doc.layers
    L.add("TARAMA", color=8, linetype="Continuous", lineweight=18)
    L.add("KESIT", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE_INCE", color=7, linetype="Continuous", lineweight=25)
    msp = doc.modelspace()
    paper = "A4"
    ax0, ay0, ax1, ay1 = drawing_area(paper)
    if gx1 - gx0 > ax1 - ax0 or gy1 - gy0 > ay1 - ay0:
        paper = "A3"
        ax0, ay0, ax1, ay1 = drawing_area(paper)
    frame(msp, title, paper)
    sx = (ax0 + ax1) / 2 - (gx0 + gx1) / 2
    sy = (ay0 + ay1) / 2 - (gy0 + gy1) / 2
    print(f"{name}: {paper}  yerleşim {gx1 - gx0:.0f} x {gy1 - gy0:.0f}")

    labels = {"ON": "A-A KESİTİ", "UST": "ÜST GÖRÜNÜŞ", "SOL": "SOL YAN GÖRÜNÜŞ"}
    for v in views:
        vis, hid, cls = data[v]
        dx, dy = off[v][0] + sx, off[v][1] + sy
        add_prims(msp, vis, "GORUNEN", dx, dy)
        add_prims(msp, hid, "GIZLI", dx, dy)
        for a, b in cls:
            msp.add_line((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy), dxfattribs={"layer": "EKSEN"})
        if v == "ON":
            h = msp.add_hatch(dxfattribs={"layer": "TARAMA"})
            h.set_pattern_fill("ANSI31", scale=0.8)
            for f in sfaces:
                for loop in face_loops(f):
                    h.paths.add_polyline_path([(p[0] + dx, p[1] + dy) for p in loop], is_closed=True)
        else:
            ex0, _, ex1, _ = bb[v]
            if v == "UST":
                section_line(msp, v, sec_c, (ex0 - 8, ex1 + 8), dx, dy)
            else:
                _, ey0, _, ey1 = bb[v]
                section_line(msp, v, sec_c, (ey0 - 5, ey1 + 5), dx, dy)
        olcu.render(msp, v, dx, dy)
        x0, _, x1, _ = bb[v]
        msp.add_text(labels[v], height=3.5, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            ((x0 + x1) / 2 + dx, full[v][1] + dy + 4), align=TextEntityAlignment.TOP_CENTER)
    for i, n in enumerate(notes):
        msp.add_text(n, height=3.5, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            (ax0 + 5, ay0 - 6 - 6 * i))
    W, H = KAGIT[paper]
    doc.set_modelspace_vport(height=H + 10, center=(W / 2, H / 2))
    path = os.path.join(outdir, f"{name}.dxf")
    doc.saveas(path)
    return path


PARCALAR = [
    ("ParcaA_Catal", "ÇATALLI BAĞLANTI", parca_a, ("ON", "UST"), 17.5, olcu_a, None, ()),
    ("ParcaB_Flansli_Burc", "FLANŞLI BURÇ", parca_b, ("ON", "UST"), 0.0, olcu_b, None, ()),
    ("ParcaC_Pabuc", "PABUÇ", parca_c, ("ON", "SOL"), 25.0, olcu_c, None,
     ("Belirtilmeyen köşe kavisleri R3",)),
    ("ParcaD_Yatak_Govdesi", "YATAK GÖVDESİ", parca_d, ("ON", "UST"), 30.0, olcu_d,
     lambda: parca_d(with_ribs=False), ("Belirtilmeyen köşe kavisleri R2",)),
]

if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    for name, title, fn, views, c, ol, norib, notes in PARCALAR:
        kw = {"gap": 8.0, "label_gap": 8.0} if name.startswith("ParcaB") else {}
        p = build(name, title, fn(), views, c, ol(), outdir,
                  norib_shape=norib() if norib else None, notes=notes, **kw)
        print("yazıldı:", p)
