"""2. Hafta ödevi: 6 parçanın ÖN - SOL YAN - ÜST görünüşleri (ISO-E / Avrupa metodu).

Her parça 3B katı model olarak kurulur, OpenCascade HLR (gizli çizgi
hesaplama) ile üç görünüş çıkarılır ve AutoCAD'in açtığı DXF olarak yazılır.

Eksen kabulü (izometrik resme göre):
  X (a) : sağ-aşağı giden kenarlar   Y (b) : sağ-yukarı giden kenarlar   Z : yukarı
  ÖN görünüş      -> sağ-alt yüze (+X) bakılarak   (yatay: Y, düşey: Z)
  SOL YAN görünüş -> sol-alt yüze (-Y) bakılarak   (yatay: X, düşey: Z) ön görünüşün SAĞINA
  ÜST görünüş     -> yukarıdan (+Z) bakılarak      (yatay: Y, düşey: -X) ön görünüşün ALTINA
"""
import math
import os
import sys

import ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepLib import BRepLib
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
                                BRepBuilderAPI_MakeWire)
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCP.GC import GC_MakeArcOfCircle
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Line
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

# ---------------------------------------------------------------- 3B yardımcılar


def box(x0, x1, y0, y1, z0, z1):
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()


def cyl(p, d, r, h):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*p), gp_Dir(*d)), r, h).Shape()


def fuse(*shapes):
    s = shapes[0]
    for t in shapes[1:]:
        s = BRepAlgoAPI_Fuse(s, t).Shape()
    return s


def cut(s, *tools):
    for t in tools:
        s = BRepAlgoAPI_Cut(s, t).Shape()
    return s


def clean(s):
    u = ShapeUpgrade_UnifySameDomain(s, True, True, True)
    u.Build()
    s = u.Shape()
    BRepLib.EncodeRegularity_s(s, 1e-3)  # teğet (yumuşak) kenarlar çizilmesin
    return s


# düzlem: (u, v, w) -> (x, y, z)
PLANES = {
    "XY": lambda u, v, w: (u, v, w),   # u=X, v=Y, kalınlık Z
    "YZ": lambda u, v, w: (w, u, v),   # u=Y, v=Z, kalınlık X
    "XZ": lambda u, v, w: (u, w, v),   # u=X, v=Z, kalınlık Y
}


def prism(pts, plane, w0, w1):
    """pts: [(u, v) veya (u, v, r)] köşe listesi; r>0 ise köşe r yarıçapla yuvarlatılır."""
    m = PLANES[plane]
    P = lambda u, v: gp_Pnt(*m(u, v, w0))
    n = len(pts)
    pts = [(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in pts]
    segs = []  # her köşe için (giriş noktası, çıkış noktası, yay orta noktası|None)
    for i in range(n):
        x, y, r = pts[i]
        if r <= 0:
            segs.append(((x, y), (x, y), None))
            continue
        px, py, _ = pts[i - 1]
        nx, ny, _ = pts[(i + 1) % n]
        d1 = (x - px, y - py)
        l1 = math.hypot(*d1)
        d1 = (d1[0] / l1, d1[1] / l1)
        d2 = (nx - x, ny - y)
        l2 = math.hypot(*d2)
        d2 = (d2[0] / l2, d2[1] / l2)
        cosang = -d1[0] * d2[0] - d1[1] * d2[1]
        th = math.acos(max(-1.0, min(1.0, cosang)))
        t = r / math.tan(th / 2)
        t1 = (x - d1[0] * t, y - d1[1] * t)
        t2 = (x + d2[0] * t, y + d2[1] * t)
        bis = (-d1[0] + d2[0], -d1[1] + d2[1])
        lb = math.hypot(*bis)
        bis = (bis[0] / lb, bis[1] / lb)
        dc = r / math.sin(th / 2)
        c = (x + bis[0] * dc, y + bis[1] * dc)
        mid = (c[0] - bis[0] * r, c[1] - bis[1] * r)
        segs.append((t1, t2, mid))
    wire = BRepBuilderAPI_MakeWire()
    for i in range(n):
        a_in, a_out, mid = segs[i]
        if mid is not None:
            arc = GC_MakeArcOfCircle(P(*a_in), P(*mid), P(*a_out)).Value()
            wire.Add(BRepBuilderAPI_MakeEdge(arc).Edge())
        nxt_in = segs[(i + 1) % n][0]
        if math.hypot(nxt_in[0] - a_out[0], nxt_in[1] - a_out[1]) > 1e-9:
            wire.Add(BRepBuilderAPI_MakeEdge(P(*a_out), P(*nxt_in)).Edge())
    face = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
    vec = gp_Vec(*m(0, 0, w1 - w0))
    return BRepPrimAPI_MakePrism(face, vec).Shape()


def tangent_point(p, c, r, side):
    """p noktasından (c, r) çemberine teğet noktası. side=+1 sol taraf, -1 sağ taraf."""
    dx, dy = c[0] - p[0], c[1] - p[1]
    d = math.hypot(dx, dy)
    base = math.atan2(dy, dx)
    alpha = math.asin(r / d)
    ang = base + side * alpha
    L = math.sqrt(d * d - r * r)
    return (p[0] + L * math.cos(ang), p[1] + L * math.sin(ang))


def line_intersect(p1, p2, p3, p4):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def offset_line(p1, p2, dist, toward):
    """p1-p2 doğrusunu 'toward' noktası tarafına dist kadar kaydır."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    if (toward[0] - p1[0]) * nx + (toward[1] - p1[1]) * ny < 0:
        nx, ny = -nx, -ny
    return (p1[0] + nx * dist, p1[1] + ny * dist), (p2[0] + nx * dist, p2[1] + ny * dist)


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

# ---------------------------------------------------------------- PARÇALAR


def parca1():
    """L-dirsek: arka plaka, yuvarlak uçlu taban, 8'lik duvar, Ø36/Ø24 göbek."""
    plate = box(0, 10, 0, 50, 0, 80)
    base = fuse(box(0, 63, 0, 50, 0, 10), cyl((63, 25, 0), Z, 25, 10))
    wall = box(30, 38, 0, 50, 10, 34)
    boss = cyl((10, 25, 56), X, 18, 16)
    s = fuse(plate, base, wall, boss)
    s = cut(s, cyl((-1, 25, 56), X, 12, 28), cyl((63, 25, -1), Z, 15, 12))
    return s


def parca2():
    """Kanallı, eğik iki ayaklı blok (80 x 70 x 60)."""
    s = box(0, 80, 0, 70, 0, 60)
    s = cut(s,
            box(14, 34, -1, 71, 46, 61),                                    # 20x14 kanal
            prism([(52, 60), (80, 14), (81, 14), (81, 61), (52, 61)], "XZ", -1, 71),  # eğik yüz
            box(40, 81, 24, 46, -1, 61))                                    # ayaklar arası boşluk
    return s


def parca3():
    """100 x 68 x 50, iki ucu 45° pahlı, ortası 40'lık kanallı, köşe blokları 16'lık yarıklı."""
    prof = [(0, 30), (30, 0), (70, 0), (100, 30), (100, 50), (70, 50), (70, 30),
            (30, 30), (30, 50), (0, 50)]
    s = prism(prof, "XZ", 0, 68)
    s = cut(s, box(-1, 31, 26, 42, 40, 51), box(69, 101, 26, 42, 40, 51))
    return s


def parca4():
    """Çatal uçlu, 100 boyunda parça."""
    arm = [(0, 0), (12, 0), (12, 12), (24, 12), (24, 46), (0, 46)]
    top_arm = prism(arm, "XY", 38, 50)
    bot_arm = prism(arm, "XY", 0, 12)
    web = box(0, 24, 28, 56, 12, 38)
    top_slope = prism([(46, 38), (56, 38), (46, 50)], "YZ", 0, 24)
    bot_slope = prism([(46, 0), (56, 12), (46, 12)], "YZ", 0, 24)
    right = cut(box(0, 24, 56, 100, 12, 38), box(18, 25, 80, 101, 11, 39))
    return fuse(top_arm, bot_arm, web, top_slope, bot_slope, right)


def parca5():
    """A gövdeli yatak: 75x112x25 taban (alt V kanallı), üçgen pencereli gövde, Ø40/Ø26 göbek."""
    base = box(0, 75, 0, 112, 0, 25)
    vgroove = prism([(45, -1), (67, -1), (56, 10)], "YZ", -1, 76)
    base = cut(base, vgroove, cyl((50, 56, -1), Z, 13, 27))

    c, R = (56.0, 150.0), 23.0
    p_l, p_r = (0.0, 25.0), (112.0, 25.0)
    t_l = tangent_point(p_l, c, R, +1)   # sol ayak dış kenarının teğet noktası
    t_r = tangent_point(p_r, c, R, -1)
    body = fuse(prism([p_l, p_r, t_r, t_l], "YZ", 0, 25), cyl((0, c[0], c[1]), X, R, 25))

    # pencere: ayaklardan 20 içeride, tabandan 12 yukarıda; üst köşe R20, alt köşeler R6
    inside = (56.0, 80.0)
    l1, l2 = offset_line(p_l, t_l, 20, inside)
    r1, r2 = offset_line(p_r, t_r, 20, inside)
    bot1, bot2 = (0.0, 37.0), (112.0, 37.0)
    v_bl = line_intersect(l1, l2, bot1, bot2)
    v_br = line_intersect(r1, r2, bot1, bot2)
    v_top = line_intersect(l1, l2, r1, r2)
    window = prism([(v_bl[0], v_bl[1], 6), (v_br[0], v_br[1], 6), (v_top[0], v_top[1], 20)],
                   "YZ", -1, 26)
    body = cut(body, window)

    boss = cyl((0, 56, 150), X, 20, 50)
    s = fuse(base, body, boss)
    s = cut(s, cyl((-1, 56, 150), X, 13, 52))
    return s


def parca6():
    """Taban + R25 köşeli arka duvar, üstte 18'lik kanallı konsol, Ø50/Ø32 göbek, 10'luk kaburga."""
    base = box(0, 76, 0, 126, 0, 13)
    wall = prism([(0, 0), (126, 0), (126, 90, 25), (0, 90, 25)], "YZ", 0, 13)
    bracket = box(13, 38, 44, 82, 51, 90)
    boss = cyl((13, 63, 51), X, 25, 38)
    rib = prism([(13, 13), (76, 13), (51, 26), (51, 51), (13, 51)], "XZ", 58, 68)
    s = fuse(base, wall, bracket, boss, rib)
    s = cut(s,
            box(-1, 39, 54, 72, 80, 91),          # üstteki 18 genişlik 10 derinlik kanal
            cyl((-1, 63, 51), X, 16, 53),         # R16 delik
            cyl((51, 19, -1), Z, 7, 15),          # Ø14 delikler
            cyl((51, 107, -1), Z, 7, 15))
    return s


PARCALAR = [
    ("Parca1", "L Dirsek (Ø36 göbekli)", parca1),
    ("Parca2", "Eğik Ayaklı Kanallı Blok", parca2),
    ("Parca3", "45° Pahlı Kanallı Blok", parca3),
    ("Parca4", "Çatal Uçlu Parça", parca4),
    ("Parca5", "A Gövdeli Yatak (Ø40)", parca5),
    ("Parca6", "Ø50 Göbekli Köşebent", parca6),
]

# ---------------------------------------------------------------- HLR ve görünüşler

# (bakış yönü N (izleyiciye doğru), ekran X yönü)  -> ekran Y = N x X
VIEWS = {
    "ON": ((1, 0, 0), (0, 1, 0)),
    "SOL": ((0, -1, 0), (1, 0, 0)),
    "UST": ((0, 0, 1), (0, 1, 0)),
}


def edges_of(shape):
    out = []
    if shape is None or shape.IsNull():
        return out
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    while exp.More():
        out.append(TopoDS.Edge(exp.Current()))
        exp.Next()
    return out


def edge_to_prims(e):
    c = BRepAdaptor_Curve(e)
    f, l = c.FirstParameter(), c.LastParameter()
    t = c.GetType()
    p0, p1 = c.Value(f), c.Value(l)
    if t == GeomAbs_Line:
        return [("L", (p0.X(), p0.Y()), (p1.X(), p1.Y()))]
    if t == GeomAbs_Circle:
        circ = c.Circle()
        ctr = circ.Location()
        r = circ.Radius()
        if abs(abs(l - f) - 2 * math.pi) < 1e-6:
            return [("C", (ctr.X(), ctr.Y()), r)]
        pm = c.Value((f + l) / 2)
        ang = lambda p: math.degrees(math.atan2(p.Y() - ctr.Y(), p.X() - ctr.X())) % 360
        a0, am, a1 = ang(p0), ang(pm), ang(p1)
        # CCW a0 -> a1 ortadan geçiyor mu?
        if (am - a0) % 360 < (a1 - a0) % 360:
            return [("A", (ctr.X(), ctr.Y()), r, a0, a1)]
        return [("A", (ctr.X(), ctr.Y()), r, a1, a0)]
    disc = GCPnts_QuasiUniformDeflection(c, 0.02)
    pts = [(disc.Value(i).X(), disc.Value(i).Y()) for i in range(1, disc.NbPoints() + 1)]
    return [("P", pts)]


def hlr(shape, view):
    n, xd = VIEWS[view]
    algo = HLRBRep_Algo()
    algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*n), gp_Dir(*xd))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis, hid = [], []
    for s in (h.VCompound(), h.OutLineVCompound()):
        for e in edges_of(s):
            vis += edge_to_prims(e)
    for s in (h.HCompound(), h.OutLineHCompound()):
        for e in edges_of(s):
            hid += edge_to_prims(e)
    return vis, hid


def merge_lines(prims, tol=1e-4):
    """Aynı doğru üzerindeki bitişik/örtüşen çizgileri birleştir (kesik çizgi deseni düzgün çıksın)."""
    lines = [p for p in prims if p[0] == "L"]
    others = [p for p in prims if p[0] != "L"]
    groups = {}
    for _, a, b in lines:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.01:
            continue
        ux, uy = dx / L, dy / L
        if ux < -tol or (abs(ux) <= tol and uy < 0):
            ux, uy = -ux, -uy
        off = -uy * a[0] + ux * a[1]
        key = (round(ux, 4), round(uy, 4), round(off, 3))
        s0, s1 = sorted((ux * a[0] + uy * a[1], ux * b[0] + uy * b[1]))
        groups.setdefault(key, (ux, uy, off, []))[3].append((s0, s1))
    out = []
    for ux, uy, off, ivs in groups.values():
        ivs.sort()
        cur = list(ivs[0])
        merged = []
        for s0, s1 in ivs[1:]:
            if s0 <= cur[1] + 1e-3:
                cur[1] = max(cur[1], s1)
            else:
                merged.append(cur)
                cur = [s0, s1]
        merged.append(cur)
        for s0, s1 in merged:
            p = lambda s: (ux * s - uy * off, uy * s + ux * off)
            out.append(("L", p(s0), p(s1)))
    return out + others


def remove_hidden_under_visible(vis, hid):
    """Görünen çizginin tam üstüne düşen gizli çizgi parçalarını at."""
    vkeys = {}
    for p in vis:
        if p[0] != "L":
            continue
        _, a, b = p
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        if ux < -1e-4 or (abs(ux) <= 1e-4 and uy < 0):
            ux, uy = -ux, -uy
        off = -uy * a[0] + ux * a[1]
        key = (round(ux, 4), round(uy, 4), round(off, 3))
        s0, s1 = sorted((ux * a[0] + uy * a[1], ux * b[0] + uy * b[1]))
        vkeys.setdefault(key, []).append((s0, s1))
    out = []
    for p in hid:
        if p[0] != "L":
            out.append(p)
            continue
        _, a, b = p
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        if ux < -1e-4 or (abs(ux) <= 1e-4 and uy < 0):
            ux, uy = -ux, -uy
        off = -uy * a[0] + ux * a[1]
        key = (round(ux, 4), round(uy, 4), round(off, 3))
        s0, s1 = sorted((ux * a[0] + uy * a[1], ux * b[0] + uy * b[1]))
        pieces = [(s0, s1)]
        for v0, v1 in vkeys.get(key, []):
            nxt = []
            for q0, q1 in pieces:
                if v1 <= q0 or v0 >= q1:
                    nxt.append((q0, q1))
                    continue
                if q0 < v0:
                    nxt.append((q0, v0))
                if v1 < q1:
                    nxt.append((v1, q1))
            pieces = nxt
        for q0, q1 in pieces:
            if q1 - q0 > 0.05:
                pt = lambda s: (ux * s - uy * off, uy * s + ux * off)
                out.append(("L", pt(q0), pt(q1)))
    return out


def project(pt, view):
    n, xd = VIEWS[view]
    yd = (n[1] * xd[2] - n[2] * xd[1], n[2] * xd[0] - n[0] * xd[2], n[0] * xd[1] - n[1] * xd[0])
    dot = lambda u, v: sum(i * j for i, j in zip(u, v))
    return dot(pt, xd), dot(pt, yd)


def cylinder_axes(shape):
    """Delik/göbek eksenleri: (konum, yön, yarıçap, eksen boyunca [s0, s1])  (≥180° yüzeyler)."""
    axes = {}
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        f = TopoDS.Face(exp.Current())
        s = BRepAdaptor_Surface(f)
        if s.GetType() == GeomAbs_Cylinder:
            span = s.LastUParameter() - s.FirstUParameter()
            if span >= math.pi - 1e-6:
                cy = s.Cylinder()
                ax = cy.Axis()
                d = ax.Direction()
                dv = (round(abs(d.X())), round(abs(d.Y())), round(abs(d.Z())))
                loc = ax.Location()
                lv = (loc.X(), loc.Y(), loc.Z())
                k = dv.index(1)
                sgn = 1 if (d.X(), d.Y(), d.Z())[k] > 0 else -1
                v0 = lv[k] + sgn * s.FirstVParameter()
                v1 = lv[k] + sgn * s.LastVParameter()
                perp = tuple(round(lv[i], 3) for i in range(3) if i != k)
                key = (k, perp)
                r = cy.Radius()
                lo, hi = min(v0, v1), max(v0, v1)
                if key in axes:
                    o = axes[key]
                    axes[key] = (max(o[0], r), min(o[1], lo), max(o[2], hi))
                else:
                    axes[key] = (r, lo, hi)
        exp.Next()
    out = []
    for (k, perp), (r, lo, hi) in axes.items():
        idx = [i for i in range(3) if i != k]
        base = [0.0, 0.0, 0.0]
        base[idx[0]], base[idx[1]] = perp
        out.append((k, tuple(base), r, lo, hi))
    return out


def centerlines(shape, view, ext=3.0):
    n, _ = VIEWS[view]
    nk = [abs(c) for c in n].index(1)
    res = []
    for k, base, r, lo, hi in cylinder_axes(shape):
        if k == nk:
            cx, cy = project(base, view)
            res.append(((cx - r - ext, cy), (cx + r + ext, cy)))
            res.append(((cx, cy - r - ext), (cx, cy + r + ext)))
        else:
            p0 = list(base)
            p1 = list(base)
            p0[k], p1[k] = lo, hi
            a, b = project(p0, view), project(p1, view)
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            res.append(((a[0] - ux * ext, a[1] - uy * ext), (b[0] + ux * ext, b[1] + uy * ext)))
    # aynı eksen çizgilerini tekilleştir
    uniq = []
    for ln in res:
        if not any(all(abs(ln[i][j] - u[i][j]) < 1e-3 for i in range(2) for j in range(2)) for u in uniq):
            uniq.append(ln)
    return uniq


def bbox(prims):
    xs, ys = [], []
    for p in prims:
        if p[0] == "L":
            xs += [p[1][0], p[2][0]]
            ys += [p[1][1], p[2][1]]
        elif p[0] in ("C", "A"):
            xs += [p[1][0] - p[2], p[1][0] + p[2]]
            ys += [p[1][1] - p[2], p[1][1] + p[2]]
        else:
            xs += [q[0] for q in p[1]]
            ys += [q[1] for q in p[1]]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- DXF


def new_doc():
    doc = ezdxf.new("R2010", setup=True, units=4)
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 1
    # ISO tarzı mm çizgi tipleri (LTSCALE=1)
    doc.linetypes.add("GIZLI_ISO", pattern=[4.5, 3.0, -1.5], description="Gizli ___ ___ ___")
    doc.linetypes.add("EKSEN_ISO", pattern=[16.0, 10.0, -2.0, 2.0, -2.0],
                      description="Eksen ______ _ ______ _")
    doc.header["$LWDISPLAY"] = 1
    doc.styles.add("TR", font="arial.ttf")
    L = doc.layers
    L.add("GORUNEN", color=7, linetype="Continuous", lineweight=50)
    L.add("GIZLI", color=2, linetype="GIZLI_ISO", lineweight=25)
    L.add("EKSEN", color=1, linetype="EKSEN_ISO", lineweight=18)
    L.add("YAZI", color=3, linetype="Continuous", lineweight=25)
    return doc


def add_prims(msp, prims, layer, dx, dy):
    for p in prims:
        if p[0] == "L":
            msp.add_line((p[1][0] + dx, p[1][1] + dy), (p[2][0] + dx, p[2][1] + dy),
                         dxfattribs={"layer": layer})
        elif p[0] == "C":
            msp.add_circle((p[1][0] + dx, p[1][1] + dy), p[2], dxfattribs={"layer": layer})
        elif p[0] == "A":
            if abs(((p[4] - p[3]) % 360)) < 1e-6:
                continue
            msp.add_arc((p[1][0] + dx, p[1][1] + dy), p[2], p[3], p[4], dxfattribs={"layer": layer})
        else:
            msp.add_lwpolyline([(x + dx, y + dy) for x, y in p[1]], dxfattribs={"layer": layer})


def build(name, title, shape, outdir, gap=30.0):
    shape = clean(shape)
    data = {}
    for v in VIEWS:
        vis, hid = hlr(shape, v)
        vis = merge_lines(vis)
        hid = merge_lines(remove_hidden_under_visible(vis, merge_lines(hid)))
        data[v] = (vis, hid, centerlines(shape, v))

    bb = {v: bbox(data[v][0]) for v in VIEWS}
    # yerleşim: ÖN (0,0) | SOL YAN sağında | ÜST altında
    off = {"ON": (0.0, 0.0)}
    off["SOL"] = (bb["ON"][2] + gap - bb["SOL"][0], 0.0)
    off["UST"] = (0.0, bb["ON"][1] - gap - bb["UST"][3])

    doc = new_doc()
    msp = doc.modelspace()
    labels = {"ON": "ÖN GÖRÜNÜŞ", "SOL": "SOL YAN GÖRÜNÜŞ", "UST": "ÜST GÖRÜNÜŞ"}
    for v in VIEWS:
        vis, hid, cls = data[v]
        dx, dy = off[v]
        add_prims(msp, vis, "GORUNEN", dx, dy)
        add_prims(msp, hid, "GIZLI", dx, dy)
        for a, b in cls:
            msp.add_line((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy), dxfattribs={"layer": "EKSEN"})
        x0, y0, x1, y1 = bb[v]
        msp.add_text(labels[v], height=3.5, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            ((x0 + x1) / 2 + dx, y0 + dy - 12), align=ezdxf.enums.TextEntityAlignment.TOP_CENTER)
    # başlık: sol yan görünüşün altına (üst görünüşle çakışmaz)
    xl = bb["SOL"][0] + off["SOL"][0]
    yt = bb["SOL"][1] + off["SOL"][1] - 35
    lines = [(f"{name.replace('Parca', 'PARÇA ')} - {title}", 5),
             ("ISO-E (Avrupa) metodu   Ölçek 1:1   Ölçüler mm", 3.5),
             ("Ad Soyad: ....................   No: ..........", 3.5)]
    for i, (txt, h) in enumerate(lines):
        msp.add_text(txt, height=h, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
            (xl, yt - i * 10))
    doc.set_modelspace_vport(height=300, center=(off["SOL"][0] / 2 + 40, -60))
    path = os.path.join(outdir, f"{name}.dxf")
    doc.saveas(path)
    return path


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    for name, title, fn in PARCALAR:
        print("yazıldı:", build(name, title, fn(), outdir))
