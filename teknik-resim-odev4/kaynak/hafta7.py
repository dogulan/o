"""7. hafta antetli resim ödevi: 4 parça, bir görünüşü tam kesit olmak üzere görünüşler.

Model ekseni: X = derinlik (ÖN görünüş oku +X tarafından bakar), Y = sağa, Z = yukarı
Görünüş düzlemleri: ON (Y, Z)   SOL (X, Z)   UST (Y, -X)
Kesit:  ("ON", c)  -> X = c düzlemi, +X tarafı kaldırılır, önden bakılır
        ("SOL", c) -> Y = c düzlemi, -Y tarafı kaldırılır, soldan bakılır
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "teknik-resim-odev2", "kaynak"))

import ezdxf  # noqa: E402
from ezdxf.enums import TextEntityAlignment  # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface  # noqa: E402
from OCP.GCPnts import GCPnts_QuasiUniformDeflection  # noqa: E402
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Plane  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE  # noqa: E402
from OCP.TopExp import TopExp_Explorer  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402

from olculer import Olcu  # noqa: E402
from uc_gorunus import (VIEWS, X, Y, Z, add_prims, bbox, box, clean, cut, cyl,  # noqa: E402
                        cylinder_axes, fuse, hlr, merge_lines, new_doc, prism, project,
                        remove_hidden_under_visible)


def stadium(c1, c2, r, plane, w0, w1):
    """İki merkez arası kanal (uçları yarım daire) prizması. Merkezler aynı u veya aynı v'de."""
    (u1, v1), (u2, v2) = c1, c2
    if abs(v1 - v2) < 1e-9:
        body = prism([(u1, v1 - r), (u2, v1 - r), (u2, v1 + r), (u1, v1 + r)], plane, w0, w1)
    else:
        body = prism([(u1 - r, v1), (u1 + r, v1), (u1 + r, v2), (u1 - r, v2)], plane, w0, w1)
    m = {"XY": lambda u, v: ((u, v, w0), Z), "YZ": lambda u, v: ((w0, u, v), X),
         "XZ": lambda u, v: ((u, w0, v), Y)}[plane]
    p1, d = m(u1, v1)
    p2, _ = m(u2, v2)
    return fuse(body, cyl(p1, d, r, w1 - w0), cyl(p2, d, r, w1 - w0))


# ====================================================================== PARÇALAR


def parca1():
    """Halkalı dikme: 50x40x10 taban, 10'luk duvar (80), üstte 15'lik kanallı başlık, Ø32/Ø24 halka."""
    base = box(0, 40, 0, 50, 0, 10)
    wall = prism([(0, 0), (50, 0), (50, 80, 5), (0, 80, 5)], "YZ", 0, 10)
    bar = prism([(0, 60), (50, 60), (50, 80, 5), (0, 80, 5)], "YZ", 0, 15)
    ring = cyl((10, 25, 40), X, 16, 10)
    stem = box(10, 20, 21, 29, 10, 40)
    s = fuse(base, wall, bar, ring, stem)
    s = cut(s,
            stadium((10, 70), (40, 70), 5, "YZ", -1, 16),     # 30 x 10 kanal
            cyl((-1, 25, 40), X, 12, 22),                      # Ø24 delik
            cyl((30, 10, -1), Z, 5, 12), cyl((30, 40, -1), Z, 5, 12))   # 2x Ø10
    return s


P2_HOLES = [(35 + dx * 15 / math.sqrt(2), 25 + dy * 15 / math.sqrt(2)) for dx in (-1, 1) for dy in (-1, 1)]


def parca2():
    """Çatallı L parça: 10'luk duvar (50), 25'lik blok, çatallı taban (90), R20 flanş, R10/4xR3 delikler."""
    wall = prism([(0, 0), (50, 0), (50, 50, 10), (0, 50, 10)], "YZ", 0, 10)
    block = box(0, 35, 0, 50, 0, 20)
    plate = prism([(35, 0), (90, 0, 10), (90, 50, 10), (35, 50)], "XY", 0, 10)
    boss = cyl((35, 25, 0), Z, 20, 15)
    s = fuse(wall, block, plate, boss)
    s = cut(s,
            stadium((10, 40), (40, 40), 5, "YZ", -1, 11),          # duvardaki kanal
            cyl((35, 25, 15), Z, 20, 6),                            # R20 x 5 havşa
            cyl((35, 25, -1), Z, 10, 22),                           # R10 delik
            *[cyl((x, y, -1), Z, 3, 22) for x, y in P2_HOLES],      # 4x R3
            box(70, 91, 18, 32, -1, 11), cyl((70, 25, -1), Z, 7, 12))   # R7 çatal
    return s


def parca3():
    """Kanallı gövde: 96x50x40, uçlar eğik, altta 40/20x15 kanal, Ø35 göbek (24x12 yarıklı), cep, 2x Ø10."""
    prof = [(0, 0), (28, 0), (38, 15), (58, 15), (68, 0), (96, 0), (96, 10), (78, 40), (18, 40), (0, 10)]
    body = prism(prof, "YZ", 0, 50)
    s = fuse(body, cyl((25, 48, 40), Z, 17.5, 20))
    s = cut(s,
            box(10, 40, -1, 25.5, 22, 41),           # 30 genişlik cep, taban 22
            box(-1, 51, 36, 60, 48, 61),             # göbekte 24 x 12 yarık
            cyl((25, 14, -1), Z, 5, 25), cyl((25, 82, -1), Z, 5, 45))
    return s


def parca4():
    """Dikme: 75x65x25 taban (R20, 20'lik kanal), 140 boy, Ø50 delik, 5x45° pah, V kanal, R10."""
    base = prism([(0, 0), (65, 0, 20), (65, 75, 20), (0, 75)], "XY", 0, 25)
    col = prism([(0, 0), (15, 0), (20, 5), (20, 70), (15, 75), (0, 75)], "XY", 0, 110)
    top = prism([(0, 0), (20, 0), (25, 5), (25, 70), (20, 75), (0, 75)], "XY", 110, 140)
    top = cut(top, cut(box(-1, 10, -1, 76, 130, 141), cyl((10, -1, 130), Y, 10, 77)))   # R10 sırt
    s = fuse(base, col, top)
    s = cut(s,
            stadium((45, 20), (45, 55), 10, "XY", -1, 26),                    # 20'lik kanal
            box(12, 21, -1, 76, 25, 35),                                       # 8x10 boşaltma
            cyl((-1, 37.5, 75), X, 25, 30),                                    # Ø50
            prism([(22.5, 141), (37.5, 125), (52.5, 141)], "YZ", -1, 26))     # V kanal 30x15
    return s


# ====================================================================== ÖLÇÜLER


def olcu1():
    D = Olcu()
    # ÖN (Y, Z)
    D.h("ON", (0, 0), (50, 0), -22)
    D.v("ON", (0, 0), (0, 10), -10)
    D.v("ON", (0, 10), (0, 60), -10)
    D.v("ON", (0, 60), (5, 80), -10)
    D.v("ON", (50, 10), (25, 40), 60)
    D.h("ON", (10, 70), (40, 70), 98)
    D.v("ON", (25, 65), (25, 75), 25)
    D.h("ON", (21, 10), (29, 10), 17)
    D.dia("ON", (25, 40), 16, 35, dist=27)
    D.dia("ON", (25, 40), 12, 145, dist=27)
    D.rad("ON", (5, 75), 5, 135)
    # SOL (X, Z)  A-A kesiti
    D.h("SOL", (0, 0), (10, 10), -10)
    D.h("SOL", (10, 10), (40, 0), -10)
    D.h("SOL", (0, 0), (40, 0), -18)
    D.h("SOL", (0, 80), (15, 80), 88)
    D.h("SOL", (10, 28), (20, 28), 40)
    # ÜST (Y, -X)
    D.dia("UST", (10, -30), 5, 205, text="2x<>", dist=17)
    D.h("UST", (0, -40), (10, -30), -50)
    D.v("UST", (50, -40), (40, -30), 60)
    return D


def olcu2():
    D = Olcu()
    # ÖN (Y, Z)  A-A kesiti (X = 35)
    D.h("ON", (15, 0), (35, 0), -10, text="%%c20")
    D.h("ON", (0, 0), (50, 0), -18)
    D.v("ON", (0, 0), (10, 50), -12)
    D.v("ON", (50, 0), (45, 15), 60)
    D.v("ON", (45, 15), (50, 20), 60)
    D.v("ON", (50, 20), (40, 40), 60)
    D.v("ON", (40, 40), (40, 50), 60)
    D.h("ON", (0, 40), (10, 40), 58)
    D.h("ON", (10, 40), (40, 40), 58)
    D.rad("ON", (40, 40), 5, 30, text="2x<>")
    D.rad("ON", (10, 40), 10, 135)
    # ÜST (Y, -X)
    D.v("UST", (50, 0), (50, -10), 66)
    D.v("UST", (50, -10), (50, -35), 66)
    D.v("UST", (50, -35), (25, -70), 66)
    D.v("UST", (25, -70), (40, -90), 66)
    D.v("UST", (50, 0), (40, -90), 74)
    D.circle("UST", (25, -35), 15)
    D.rad("UST", (25, -35), 20, 200)
    D.rad("UST", (25, -35), 15, 160)
    D.rad("UST", (25 + 15 / math.sqrt(2), -35 - 15 / math.sqrt(2)), 3, -45, text="4x<>")
    D.rad("UST", (25, -70), 7, 225)
    D.rad("UST", (10, -80), 10, 215, text="4x<>")
    return D


def olcu3():
    D = Olcu()
    # ÖN (Y, Z)  A-A kesiti (X = 25)
    D.h("ON", (9, 0), (19, 0), -10, text="%%c10")
    D.h("ON", (28, 0), (68, 0), -10)
    D.h("ON", (14, 0), (82, 0), -18)
    D.h("ON", (0, 0), (96, 0), -26)
    D.h("ON", (38, 15), (58, 15), 10)
    D.v("ON", (28, 0), (38, 15), 46)
    D.v("ON", (0, 0), (0, 10), -10)
    D.v("ON", (0, 0), (7.2, 22), -18)
    D.v("ON", (96, 0), (96, 10), 106)
    D.v("ON", (96, 10), (78, 40), 106)
    D.v("ON", (78, 40), (65.5, 60), 106)
    D.v("ON", (96, 0), (78, 40), 114)
    D.v("ON", (42, 48), (42, 60), 42)
    D.h("ON", (0, 10), (18, 40), 50)
    D.h("ON", (25.5, 40), (30.5, 60), 50)
    D.h("ON", (36, 60), (60, 60), 66)
    D.h("ON", (30.5, 60), (65.5, 60), 73, text="%%c35")
    D.h("ON", (18, 40), (78, 40), 80)
    # ÜST (Y, -X)
    D.v("UST", (96, 0), (96, -50), 112)
    D.v("UST", (0, -10), (0, -40), -18)
    return D


def olcu4():
    k = 2.0
    D = Olcu(k)
    # ÖN (Y, Z)
    D.h("ON", (0, 0), (75, 0), -34)
    D.v("ON", (0, 0), (0, 25), -20)
    D.v("ON", (0, 25), (37.5, 75), -20)
    D.v("ON", (37.5, 75), (0, 110), -20)
    D.v("ON", (0, 110), (0, 140), -20)
    D.v("ON", (0, 0), (0, 140), -36)
    D.dia("ON", (37.5, 75), 25, 40, dist=45)
    D.h("ON", (22.5, 140), (52.5, 140), 168)
    D.v("ON", (37.5, 125), (52.5, 140), 37.5)
    D.lead("ON", (72.5, 120), (90, 150), "5x45%%d")
    # SOL (X, Z)  A-A kesiti (Y = 37.5)
    D.h("SOL", (35, 0), (55, 0), -20)
    D.h("SOL", (0, 0), (65, 0), -36)
    D.h("SOL", (0, 100), (20, 100), 75)
    D.h("SOL", (12, 35), (20, 35), 30)
    D.v("SOL", (20, 25), (20, 35), 38)
    D.h("SOL", (0, 140), (25, 140), 156)
    D.rad("SOL", (10, 130), 10, 135)
    # ÜST (Y, -X)
    D.h("UST", (20, -45), (55, -45), -85)
    D.rad("UST", (55, -45), 20, -40)
    return D


# ====================================================================== KESİT + ÇİZİM


def section_faces(shape, axis, c):
    """axis (0=X, 1=Y) düzlemi = c üzerindeki yüzeyler."""
    out = []
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        f = TopoDS.Face(exp.Current())
        s = BRepAdaptor_Surface(f)
        if s.GetType() == GeomAbs_Plane:
            pl = s.Plane()
            n = pl.Axis().Direction()
            nv = (n.X(), n.Y(), n.Z())
            loc = pl.Location()
            lv = (loc.X(), loc.Y(), loc.Z())
            if abs(abs(nv[axis]) - 1) < 1e-6 and abs(lv[axis] - c) < 1e-6:
                out.append(f)
        exp.Next()
    return out


def face_loops(face, view):
    segs = []
    exp = TopExp_Explorer(face, TopAbs_EDGE)
    while exp.More():
        e = TopoDS.Edge(exp.Current())
        c = BRepAdaptor_Curve(e)
        if c.GetType() == GeomAbs_Line:
            ps = [c.Value(c.FirstParameter()), c.Value(c.LastParameter())]
        else:
            d = GCPnts_QuasiUniformDeflection(c, 0.01)
            ps = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
        segs.append([project((p.X(), p.Y(), p.Z()), view) for p in ps])
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


KAGIT = {"A4Y": (297.0, 210.0), "A4D": (210.0, 297.0)}   # yatay / dikey


def drawing_area(paper, k):
    W, H = KAGIT[paper]
    return (24 * k, 42 * k, (W - 14) * k, (H - 14) * k)


def frame(msp, title, paper, k, scale_txt):
    W, H = KAGIT[paper]
    S = lambda *p: tuple(v * k for v in p)
    msp.add_lwpolyline([S(0, 0), S(W, 0), S(W, H), S(0, H)], close=True, dxfattribs={"layer": "CERCEVE_INCE"})
    x0, y0, x1, y1 = 20, 10, W - 10, H - 10
    msp.add_lwpolyline([S(x0, y0), S(x1, y0), S(x1, y1), S(x0, y1)], close=True, dxfattribs={"layer": "CERCEVE"})
    ax0 = x1 - 180
    rows = [y0 + 7 * i for i in range(5)]
    msp.add_lwpolyline([S(ax0, y0), S(x1, y0), S(x1, rows[4]), S(ax0, rows[4])], close=True,
                       dxfattribs={"layer": "CERCEVE"})
    ince = {"layer": "CERCEVE_INCE"}
    for r in rows[1:4]:
        msp.add_line(S(ax0, r), S(ax0 + 60, r), dxfattribs=ince)
    c1, c2, c3, c4 = ax0 + 20, ax0 + 60, ax0 + 75, ax0 + 125
    for cx in (c1, c2, c3, c4):
        msp.add_line(S(cx, y0), S(cx, rows[4]), dxfattribs=ince)
    msp.add_line(S(c2, rows[3]), S(c3, rows[3]), dxfattribs=ince)
    msp.add_line(S(c4, rows[1]), S(x1, rows[1]), dxfattribs=ince)

    def t(s, p, h=2.5, al=TextEntityAlignment.MIDDLE_LEFT):
        msp.add_text(s, height=h * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(S(*p), align=al)

    for i, s in enumerate(["Kontrol", "Tarih", "Sınıf - No", "Çizen"]):
        t(s, (ax0 + 1.5, rows[i] + 3.5))
    t("Ölçek", ((c2 + c3) / 2, rows[3] + 3.5), al=TextEntityAlignment.MIDDLE_CENTER)
    t(scale_txt, ((c2 + c3) / 2, rows[1] + 3.5), h=3.5, al=TextEntityAlignment.MIDDLE_CENTER)
    t(title, ((c3 + c4) / 2, rows[2]), h=3.5, al=TextEntityAlignment.MIDDLE_CENTER)
    t("Resim Numarası", ((c4 + x1) / 2, rows[1] + 3.5), al=TextEntityAlignment.MIDDLE_CENTER)
    t("A4", (x1 - 2, rows[4] + 3), al=TextEntityAlignment.MIDDLE_RIGHT)


def section_line(msp, view, axis, c, view_dir, bbv, k, dx, dy, letter="A"):
    """Kesit düzlemini 'view' görünüşünde çiz (çizgi, kalın uçlar, oklar, harfler)."""
    P = lambda p: (p[0] + dx, p[1] + dy)
    pt = [0.0, 0.0, 0.0]
    pt[axis] = c
    q = project(tuple(pt), view)
    n3 = [0.0, 0.0, 0.0]
    n3[axis] = 1.0
    nproj = project(tuple(n3), view)
    m = 8 * k
    if abs(nproj[0]) > 0.5:            # düzlem görünüşte düşey çizgi (u = sabit)
        u = q[0]
        a, b = (u, bbv[1] - m), (u, bbv[3] + m)
        d = (0, 1)
    else:                              # yatay çizgi (v = sabit)
        v = q[1]
        a, b = (bbv[0] - m, v), (bbv[2] + m, v)
        d = (1, 0)
    arrow = project(view_dir, view)
    L = math.hypot(*arrow)
    arrow = (arrow[0] / L, arrow[1] / L)
    msp.add_line(P(a), P(b), dxfattribs={"layer": "EKSEN"})
    for end, s in ((a, 1), (b, -1)):
        e2 = (end[0] + s * d[0] * 6 * k, end[1] + s * d[1] * 6 * k)
        msp.add_line(P(end), P(e2), dxfattribs={"layer": "KESIT"})
        tail = (end[0] + s * d[0] * k, end[1] + s * d[1] * k)
        tip = (tail[0] + arrow[0] * 8 * k, tail[1] + arrow[1] * 8 * k)
        msp.add_line(P(tail), P(tip), dxfattribs={"layer": "OLCU"})
        nn = (-arrow[1], arrow[0])
        base = (tip[0] - arrow[0] * 3 * k, tip[1] - arrow[1] * 3 * k)
        msp.add_solid([P(tip), P((base[0] + nn[0] * 0.9 * k, base[1] + nn[1] * 0.9 * k)),
                       P((base[0] - nn[0] * 0.9 * k, base[1] - nn[1] * 0.9 * k))], dxfattribs={"layer": "OLCU"})
        lp = (tip[0] + arrow[0] * 3 * k - s * d[0] * 2 * k, tip[1] + arrow[1] * 3 * k - s * d[1] * 2 * k)
        msp.add_text(letter, height=5 * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            P(lp), align=TextEntityAlignment.MIDDLE_CENTER)


def build(name, title, shape, views, section, olcu, outdir, k=1.0, gap=12.0, line_view="UST", notes=()):
    sec_view, c = section
    axis = 0 if sec_view == "ON" else 1
    shape = clean(shape)
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    def vol(s_):
        g = GProp_GProps()
        BRepGProp.VolumeProperties_s(s_, g)
        return g.Mass()

    def halve(cc):
        if axis == 0:
            return clean(cut(shape, box(cc, 1000, -1000, 1000, -1000, 1000)))
        return clean(cut(shape, box(-1000, 1000, -1000, cc, -1000, 1000)))

    view_dir = (-1.0, 0.0, 0.0) if axis == 0 else (0.0, 1.0, 0.0)
    cc = c
    half = halve(cc)
    if vol(half) > 0.999 * vol(shape):
        # düzlem tam bir delik ekseninden geçince OCC kesimi bazen başarısız olur:
        # düzlemi 0.0001 mm kaydırıp tekrar dene (çizimde fark yok)
        cc = c + 1e-4 * (1 if axis == 0 else -1)
        half = halve(cc)
    sfaces = section_faces(half, axis, cc)

    data = {}
    for v in views:
        if v == sec_view:
            vv, _ = hlr(half, v)
            keep = [a for a in cylinder_axes(half) if a[0] == axis or abs(a[1][axis] - c) <= a[2] + 1e-6]
            cls = []
            nk = [abs(t) for t in VIEWS[v][0]].index(1)
            for kk, base, r, lo, hi in keep:
                if kk == nk:
                    continue
                p0, p1 = list(base), list(base)
                p0[kk], p1[kk] = lo, hi
                a2, b2 = project(tuple(p0), v), project(tuple(p1), v)
                Lx = math.hypot(b2[0] - a2[0], b2[1] - a2[1])
                ux, uy = (b2[0] - a2[0]) / Lx, (b2[1] - a2[1]) / Lx
                cls.append(((a2[0] - 3 * ux, a2[1] - 3 * uy), (b2[0] + 3 * ux, b2[1] + 3 * uy)))
            data[v] = (merge_lines(vv), [], cls)
        else:
            from uc_gorunus import centerlines
            vv, hh = hlr(shape, v)
            vv = merge_lines(vv)
            hh = merge_lines(remove_hidden_under_visible(vv, merge_lines(hh)))
            data[v] = (vv, hh, centerlines(shape, v))

    bb = {v: bbox(data[v][0]) for v in views}
    lg = 9 * k
    full = {}
    for v in views:
        e = olcu.extents(v)
        x0, y0, x1, y1 = bb[v]
        if e:
            x0, y0, x1, y1 = min(x0, e[0]), min(y0, e[1]), max(x1, e[2]), max(y1, e[3])
        if v == line_view:
            bx0, by0, bx1, by1 = bb[v]
            m = 14 * k
            x0, y0, x1, y1 = min(x0, bx0 - m), min(y0, by0 - m), max(x1, bx1 + m), max(y1, by1 + m)
        full[v] = [x0, y0 - lg, x1, y1]
    off = {"ON": (0.0, 0.0)}
    if "SOL" in views:
        off["SOL"] = (full["ON"][2] + gap * k - full["SOL"][0], 0.0)
        full["ON"][1] = full["SOL"][1] = min(full["ON"][1], full["SOL"][1])
    if "UST" in views:
        off["UST"] = (0.0, full["ON"][1] - gap * k - full["UST"][3])
    gx0 = min(full[v][0] + off[v][0] for v in views)
    gy0 = min(full[v][1] + off[v][1] for v in views)
    gx1 = max(full[v][2] + off[v][0] for v in views)
    gy1 = max(full[v][3] + off[v][1] for v in views)

    paper = None
    for p in ("A4Y", "A4D"):
        ax0, ay0, ax1, ay1 = drawing_area(p, k)
        if gx1 - gx0 <= ax1 - ax0 and gy1 - gy0 <= ay1 - ay0:
            paper = p
            break
    if paper is None:
        paper = "A4D"
        print(f"UYARI {name}: A4'e sığmıyor {gx1 - gx0:.0f} x {gy1 - gy0:.0f}")
    print("  alan", [round(t / k) for t in drawing_area(paper or "A4D", k)])
    ax0, ay0, ax1, ay1 = drawing_area(paper, k)
    print(f"{name}: {paper} ölçek 1:{k:g}  yerleşim {(gx1 - gx0) / k:.0f} x {(gy1 - gy0) / k:.0f} (kağıtta)")

    doc = new_doc()
    doc.header["$LTSCALE"] = k
    doc.dimstyles.get("OLCU").dxf.dimscale = k
    L = doc.layers
    L.add("TARAMA", color=8, linetype="Continuous", lineweight=18)
    L.add("KESIT", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE_INCE", color=7, linetype="Continuous", lineweight=25)
    msp = doc.modelspace()
    frame(msp, title, paper, k, "1:1" if k == 1 else f"1:{k:g}")
    sx = (ax0 + ax1) / 2 - (gx0 + gx1) / 2
    sy = (ay0 + ay1) / 2 - (gy0 + gy1) / 2

    labels = {"ON": "ÖN GÖRÜNÜŞ", "UST": "ÜST GÖRÜNÜŞ", "SOL": "SOL YAN GÖRÜNÜŞ"}
    labels[sec_view] = "A-A KESİTİ"
    for v in views:
        vis, hid, cls = data[v]
        dx, dy = off[v][0] + sx, off[v][1] + sy
        add_prims(msp, vis, "GORUNEN", dx, dy)
        add_prims(msp, hid, "GIZLI", dx, dy)
        for a, b in cls:
            msp.add_line((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy), dxfattribs={"layer": "EKSEN"})
        if v == sec_view:
            h = msp.add_hatch(dxfattribs={"layer": "TARAMA"})
            h.set_pattern_fill("ANSI31", scale=0.8 * k)
            for f in sfaces:
                for loop in face_loops(f, v):
                    h.paths.add_polyline_path([(p[0] + dx, p[1] + dy) for p in loop], is_closed=True)
        if v == line_view:
            section_line(msp, v, axis, c, view_dir, bb[v], k, dx, dy)
        olcu.render(msp, v, dx, dy)
        x0, _, x1, _ = bb[v]
        msp.add_text(labels[v], height=3.5 * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            ((x0 + x1) / 2 + dx, full[v][1] + dy + 4 * k), align=TextEntityAlignment.TOP_CENTER)
    for i, n in enumerate(notes):      # antetin hemen üstüne
        msp.add_text(n, height=3.5 * k, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            (ax0, (38 + 3 + 6 * i) * k))
    W, H = KAGIT[paper]
    doc.set_modelspace_vport(height=(H + 10) * k, center=(W * k / 2, H * k / 2))
    path = os.path.join(outdir, f"{name}.dxf")
    doc.saveas(path)
    return path


PARCALAR = [
    # ad, başlık, model, görünüşler, kesit, ölçüler, ölçek çarpanı, kesit çizgisinin gösterildiği görünüş, notlar
    ("Parca1_Halkali_Dikme", "HALKALI DİKME", parca1, ("ON", "SOL", "UST"), ("SOL", 25.0), olcu1, 1.0, "ON",
     ("Tüm radüsler R5",)),
    ("Parca2_Catalli_Kosebent", "ÇATALLI KÖŞEBENT", parca2, ("ON", "UST"), ("ON", 35.0), olcu2, 1.0, "UST", ()),
    ("Parca3_Kanalli_Govde", "KANALLI GÖVDE", parca3, ("ON", "UST"), ("ON", 25.0), olcu3, 1.0, "UST",
     ("Kanal ve delikler boydan boya",)),
    ("Parca4_Dikme", "DİKME", parca4, ("ON", "SOL", "UST"), ("SOL", 37.5), olcu4, 2.0, "ON",
     ("Delikler boydan boya",)),
]

if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    only = sys.argv[2:]
    for name, title, fn, views, sec, ol, k, lv, notes in PARCALAR:
        if only and not any(o in name for o in only):
            continue
        build(name, title, fn(), views, sec, ol(), outdir, k=k, line_view=lv, notes=notes)
