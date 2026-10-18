"""Görünüşlerin ölçülendirmesi (orijinal izometrik resimdeki ölçüler).

Koordinatlar görünüşün kendi düzlemindedir:
  ON : (Y, Z)    SOL : (X, Z)    UST : (Y, -X)
"""
import math

from uc_gorunus import line_intersect, offset_line, tangent_point


class Olcu:
    def __init__(self):
        self.items = []  # (görünüş, tür, parametreler)

    def h(self, view, p1, p2, at, text="<>"):
        """Yatay ölçü; ölçü çizgisi v=at hizasında."""
        self.items.append((view, "lin", dict(base=((p1[0] + p2[0]) / 2, at), p1=p1, p2=p2,
                                             angle=0, text=text)))

    def v(self, view, p1, p2, at, text="<>"):
        """Düşey ölçü; ölçü çizgisi u=at hizasında."""
        self.items.append((view, "lin", dict(base=(at, (p1[1] + p2[1]) / 2), p1=p1, p2=p2,
                                             angle=90, text=text)))

    def al(self, view, p1, p2, dist=0.0, text="<>"):
        self.items.append((view, "al", dict(p1=p1, p2=p2, distance=dist, text=text)))

    def dia(self, view, c, r, ang=45, text="<>", dist=None):
        self.items.append((view, "dia", dict(center=c, radius=r, angle=ang, text=text, dist=dist)))

    def rad(self, view, c, r, ang=45, text="<>", dist=None):
        self.items.append((view, "rad", dict(center=c, radius=r, angle=ang, text=text, dist=dist)))

    def mark(self, view, c, size=4):
        """Merkez işareti (ör. R50 merkezi)."""
        self.items.append((view, "mark", dict(center=c, size=size)))

    def lead(self, view, p_arrow, p_text, text):
        """Oklu açıklama çizgisi (ör. pah ölçüsü 2x45°)."""
        self.items.append((view, "lead", dict(p1=p_arrow, p2=p_text, text=text)))

    def ang(self, view, center, p1, p2, r, text="<>"):
        """p1 -> p2 saat tersi yönündeki açı, r yarıçaplı yay ile."""
        a1 = math.atan2(p1[1] - center[1], p1[0] - center[0])
        a2 = math.atan2(p2[1] - center[1], p2[0] - center[0])
        if a2 < a1:
            a2 += 2 * math.pi
        am = (a1 + a2) / 2
        base = (center[0] + r * math.cos(am), center[1] + r * math.sin(am))
        self.items.append((view, "ang", dict(base=base, center=center, p1=p1, p2=p2, text=text)))

    # -------------------------------------------------- yerleşim için kaba sınırlar
    def extents(self, view):
        xs, ys = [], []
        for v, kind, k in self.items:
            if v != view:
                continue
            if kind == "lin":
                pts = [k["p1"], k["p2"], k["base"]]
                bx, by = k["base"]
                pts += [(bx - 5, by - 5), (bx + 5, by + 5)]
            elif kind in ("dia", "rad"):
                c, r, a = k["center"], k["radius"], math.radians(k["angle"])
                L = max(r + 12, (k.get("dist") or 0) + 12)
                pts = [(c[0] + L * math.cos(a), c[1] + L * math.sin(a))]
                if kind == "dia":
                    pts.append((c[0] - L * math.cos(a), c[1] - L * math.sin(a)))
            elif kind == "ang":
                pts = [k["base"], k["p1"], k["p2"]]
            elif kind == "mark":
                c, m = k["center"], k["size"]
                pts = [(c[0] - m, c[1] - m), (c[0] + m, c[1] + m)]
            elif kind == "lead":
                pts = [k["p1"], k["p2"], (k["p2"][0] + 4 * len(k["text"]), k["p2"][1] + 4)]
            else:
                pts = [k["p1"], k["p2"]]
            xs += [p[0] for p in pts]
            ys += [p[1] for p in pts]
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys)

    # -------------------------------------------------- çizim
    def render(self, msp, view, dx, dy):
        sh = lambda p: (p[0] + dx, p[1] + dy)
        attr = {"layer": "OLCU"}
        for v, kind, k in self.items:
            if v != view:
                continue
            if kind == "lin":
                d = msp.add_linear_dim(base=sh(k["base"]), p1=sh(k["p1"]), p2=sh(k["p2"]),
                                       angle=k["angle"], text=k["text"], dimstyle="OLCU",
                                       dxfattribs=attr)
            elif kind == "mark":
                c, m = k["center"], k["size"]
                for d0, d1 in (((-m, 0), (m, 0)), ((0, -m), (0, m))):
                    msp.add_line(sh((c[0] + d0[0], c[1] + d0[1])), sh((c[0] + d1[0], c[1] + d1[1])),
                                 dxfattribs={"layer": "EKSEN"})
                continue
            elif kind == "lead":
                a, b = k["p1"], k["p2"]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                w = 2.6 * len(k["text"].replace("%%d", "°"))
                msp.add_line(sh(a), sh(b), dxfattribs=attr)
                msp.add_line(sh(b), sh((b[0] + w, b[1])), dxfattribs=attr)
                bs = (a[0] + ux * 3, a[1] + uy * 3)
                msp.add_solid([sh(a), sh((bs[0] - uy * 0.5, bs[1] + ux * 0.5)),
                               sh((bs[0] + uy * 0.5, bs[1] - ux * 0.5))], dxfattribs=attr)
                msp.add_text(k["text"], height=3.5, dxfattribs={"layer": "OLCU", "style": "TR"}
                             ).set_placement(sh((b[0] + 0.5, b[1] + 1)))
                continue
            elif kind == "al":
                d = msp.add_aligned_dim(p1=sh(k["p1"]), p2=sh(k["p2"]), distance=k["distance"],
                                        text=k["text"], dimstyle="OLCU", dxfattribs=attr)
            elif kind in ("dia", "rad"):
                loc = None
                if k["dist"]:
                    a = math.radians(k["angle"])
                    loc = sh((k["center"][0] + k["dist"] * math.cos(a),
                              k["center"][1] + k["dist"] * math.sin(a)))
                fn = msp.add_diameter_dim if kind == "dia" else msp.add_radius_dim
                d = fn(center=sh(k["center"]), radius=k["radius"], angle=k["angle"],
                       location=loc, text=k["text"], dimstyle="OLCU", dxfattribs=attr)
            else:
                d = msp.add_angular_dim_3p(base=sh(k["base"]), center=sh(k["center"]),
                                           p1=sh(k["p1"]), p2=sh(k["p2"]), text=k["text"],
                                           dimstyle="OLCU", dxfattribs=attr)
            d.render()


def fillet_center(prev, p, nxt, r):
    d1 = (p[0] - prev[0], p[1] - prev[1])
    l1 = math.hypot(*d1)
    d1 = (d1[0] / l1, d1[1] / l1)
    d2 = (nxt[0] - p[0], nxt[1] - p[1])
    l2 = math.hypot(*d2)
    d2 = (d2[0] / l2, d2[1] / l2)
    th = math.acos(max(-1.0, min(1.0, -d1[0] * d2[0] - d1[1] * d2[1])))
    bis = (-d1[0] + d2[0], -d1[1] + d2[1])
    lb = math.hypot(*bis)
    bis = (bis[0] / lb, bis[1] / lb)
    dc = r / math.sin(th / 2)
    return (p[0] + bis[0] * dc, p[1] + bis[1] * dc)


# ====================================================================== PARÇALAR

def olcu1():
    D = Olcu()
    # ÖN (Y, Z)
    D.h("ON", (0, 80), (50, 80), 90)
    D.v("ON", (0, 0), (0, 80), -10)
    D.v("ON", (50, 10), (25, 56), 60)
    D.dia("ON", (25, 56), 18, 40, dist=27)
    D.dia("ON", (25, 56), 12, 140, dist=26)
    # SOL YAN (X, Z)
    D.h("SOL", (0, 80), (10, 80), 90)
    D.h("SOL", (10, 74), (26, 74), 90)
    D.h("SOL", (10, 80), (30, 34), 100)
    D.h("SOL", (30, 34), (38, 34), 100)
    D.h("SOL", (38, 34), (63, 10), 100)
    D.v("SOL", (88, 0), (88, 10), 98)
    D.v("SOL", (88, 10), (38, 34), 98)
    # ÜST (Y, -X)
    D.rad("UST", (25, -63), 25, -35)
    D.dia("UST", (25, -63), 15, -145)
    return D


def olcu2():
    D = Olcu()
    # SOL YAN (X, Z): profil
    D.h("SOL", (0, 0), (80, 0), -10)
    D.h("SOL", (0, 60), (14, 60), 70)
    D.h("SOL", (14, 60), (34, 60), 70)
    D.h("SOL", (34, 60), (52, 60), 70)
    D.v("SOL", (24, 46), (24, 60), 24)
    D.v("SOL", (80, 0), (80, 14), 90)
    D.v("SOL", (80, 0), (52, 60), 100)
    # ÖN (Y, Z)
    D.h("ON", (0, 0), (24, 0), -10)
    D.h("ON", (46, 0), (70, 0), -10)
    D.h("ON", (0, 60), (70, 60), 70)
    # ÜST (Y, -X)
    D.v("UST", (35, -34), (35, -40), 35)
    return D


def olcu3():
    D = Olcu()
    # SOL YAN (X, Z): profil
    D.h("SOL", (0, 30), (100, 30), -10)
    D.h("SOL", (0, 50), (30, 50), 60)
    D.h("SOL", (30, 50), (70, 50), 60)
    D.h("SOL", (70, 50), (100, 50), 60)
    D.v("SOL", (70, 0), (100, 30), 110)
    D.v("SOL", (100, 30), (100, 50), 110)
    D.v("SOL", (70, 0), (100, 50), 120)
    D.ang("SOL", (30, 0), (0, 30), (0, 0), 18)
    D.ang("SOL", (70, 0), (100, 0), (100, 30), 18)
    # ÖN (Y, Z)
    D.h("ON", (0, 50), (26, 50), 60)
    D.h("ON", (26, 50), (42, 50), 60)
    D.h("ON", (42, 50), (68, 50), 60)
    D.h("ON", (0, 0), (68, 0), -10)
    D.v("ON", (34, 40), (34, 50), 34)
    return D


def olcu4():
    D = Olcu()
    # ÖN (Y, Z)
    D.h("ON", (0, 50), (46, 50), 60)
    D.h("ON", (56, 38), (100, 38), 60)
    D.h("ON", (0, 50), (100, 38), 68)
    D.v("ON", (0, 0), (0, 12), -10)
    D.v("ON", (0, 12), (0, 38), -10)
    D.v("ON", (0, 38), (0, 50), -10)
    D.v("ON", (0, 0), (0, 50), -18)
    D.h("ON", (0, 12), (28, 12), 25)
    D.v("ON", (46, 0), (100, 12), 110)
    D.v("ON", (100, 12), (100, 38), 110)
    # SOL YAN (X, Z)
    D.h("SOL", (0, 0), (12, 0), -10)
    D.h("SOL", (12, 0), (24, 0), -10)
    D.h("SOL", (0, 50), (24, 50), 60)
    # ÜST (Y, -X)
    D.h("UST", (0, -12), (12, -24), -34)
    D.h("UST", (80, -24), (100, -18), -34)
    D.v("UST", (100, 0), (100, -18), 110)
    return D


def olcu5():
    D = Olcu()
    c, R = (56.0, 150.0), 23.0
    p_l, p_r = (0.0, 25.0), (112.0, 25.0)
    t_l = tangent_point(p_l, c, R, +1)
    t_r = tangent_point(p_r, c, R, -1)
    inside = (56.0, 80.0)
    l1, l2 = offset_line(p_l, t_l, 20, inside)
    r1, r2 = offset_line(p_r, t_r, 20, inside)
    v_bl = line_intersect(l1, l2, (0, 37), (112, 37))
    v_br = line_intersect(r1, r2, (0, 37), (112, 37))
    v_top = line_intersect(l1, l2, r1, r2)
    c_top = fillet_center(v_br, v_top, v_bl, 20)
    c_bl = fillet_center(v_top, v_bl, v_br, 6)
    c_br = fillet_center(v_bl, v_br, v_top, 6)

    # ÖN (Y, Z)
    D.h("ON", (46, 0), (56, 0), -10)
    D.h("ON", (56, 0), (66, 0), -10)
    D.h("ON", (0, 0), (112, 0), -20)
    D.ang("ON", (56, 10), (46, 0), (66, 0), 6)
    D.v("ON", (112, 0), (112, 25), 122)
    D.v("ON", (112, 25), (56, 150), 122)
    D.dia("ON", c, 20, 40, dist=35)
    D.dia("ON", c, 13, 140, dist=35)
    D.rad("ON", c, R, 100)
    D.rad("ON", c_top, 20, 90)
    D.rad("ON", c_bl, 6, 225)
    D.rad("ON", c_br, 6, 315)
    D.v("ON", (56, 25), (56, 37), 56)
    # ayak genişlikleri (kenara dik 20)
    for p, t in ((p_l, t_l), (p_r, t_r)):
        k = (90 - p[1]) / (t[1] - p[1])
        P = (p[0] + k * (t[0] - p[0]), 90.0)
        q1, q2 = offset_line(p, t, 20, inside)
        n = ((q1[0] - p[0]) / 20, (q1[1] - p[1]) / 20)
        Q = (P[0] + 20 * n[0], P[1] + 20 * n[1])
        D.al("ON", *((P, Q) if P[0] < Q[0] else (Q, P)), 0)
    # SOL YAN (X, Z)
    D.h("SOL", (0, 0), (25, 25), -10)
    D.h("SOL", (0, 0), (75, 0), -18)
    D.h("SOL", (0, 170), (50, 170), 183)
    # ÜST (Y, -X)
    D.dia("UST", (56, -50), 13, -40)
    D.v("UST", (112, 0), (56, -50), 122)
    return D


def olcu6():
    D = Olcu()
    # ÖN (Y, Z)
    D.h("ON", (0, 0), (126, 0), -10)
    D.v("ON", (0, 0), (25, 90), -12)
    D.v("ON", (126, 0), (126, 13), 136)
    D.v("ON", (126, 13), (63, 51), 136)
    D.h("ON", (44, 90), (54, 90), 100)
    D.h("ON", (54, 90), (72, 90), 100)
    D.h("ON", (72, 90), (82, 90), 100)
    D.v("ON", (63, 80), (63, 90), 63)
    D.h("ON", (58, 13), (68, 13), 19)
    D.rad("ON", (25, 65), 25, 115)
    D.dia("ON", (63, 51), 25, 35, dist=38)
    D.rad("ON", (63, 51), 16, 145, dist=36)
    # SOL YAN (X, Z)
    D.h("SOL", (0, 0), (76, 0), -10)
    D.h("SOL", (0, 90), (13, 90), 100)
    D.h("SOL", (0, 90), (38, 90), 108)
    D.h("SOL", (13, 90), (51, 76), 116)
    # ÜST (Y, -X)
    D.h("UST", (0, -76), (19, -51), -86)
    D.h("UST", (107, -51), (126, -76), -86)
    D.v("UST", (126, -76), (107, -51), 136)
    D.dia("UST", (19, -51), 7, 135, text="2x<>")
    return D


OLCULER = {"Parca1": olcu1, "Parca2": olcu2, "Parca3": olcu3,
           "Parca4": olcu4, "Parca5": olcu5, "Parca6": olcu6}
