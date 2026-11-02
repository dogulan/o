"""1. Kısa sınav – çözüm çizimleri (kontrol amaçlı).

Soru 1: Kanallı gövde – ÖN görünüş tam kesit (A-A), YAN ve ÜST görünüş izdüşüm, ölçülü.
Soru 2: 100x100 levha, Ø70 delik dairesi üzerinde 6 x Ø8 delik, ölçülü.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "teknik-resim-odev4", "kaynak"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "teknik-resim-odev2", "kaynak"))

from ezdxf.enums import TextEntityAlignment  # noqa: E402

import hafta7 as h7  # noqa: E402
from olculer import Olcu  # noqa: E402
from uc_gorunus import new_doc  # noqa: E402


def olcu_s1():
    D = h7.olcu3()
    # ödevdeki üst görünüş ölçüleri yerine: yan görünüşte 50, üstte cep konumu
    D.items = [it for it in D.items if it[0] != "UST"]
    # YAN (SOL) görünüş (X, Z)
    D.h("SOL", (0, 0), (50, 0), -10)
    # ÜST (Y, -X)
    D.v("UST", (0, 0), (0, -10), -18)
    D.v("UST", (0, -10), (0, -40), -18)
    return D


def soru2(outdir):
    doc = new_doc()
    L = doc.layers
    L.add("CERCEVE", color=7, linetype="Continuous", lineweight=70)
    L.add("CERCEVE_INCE", color=7, linetype="Continuous", lineweight=25)
    msp = doc.modelspace()
    paper = "A4D"
    h7.frame(msp, "DELİKLİ LEVHA", paper, 1.0, "1:1")
    ax0, ay0, ax1, ay1 = h7.drawing_area(paper, 1.0)
    ox = (ax0 + ax1) / 2 - 50
    oy = (ay0 + ay1) / 2 - 50
    P = lambda x, y: (x + ox, y + oy)
    g = {"layer": "GORUNEN"}
    e = {"layer": "EKSEN"}
    msp.add_lwpolyline([P(0, 0), P(100, 0), P(100, 100), P(0, 100)], close=True, dxfattribs=g)
    c = (50, 50)
    R = 35
    msp.add_circle(P(*c), R, dxfattribs=e)                       # Ø70 delik dairesi
    msp.add_line(P(5, 50), P(95, 50), dxfattribs=e)               # yatay eksen
    msp.add_line(P(50, 5), P(50, 95), dxfattribs=e)               # düşey eksen
    for i in range(6):
        a = math.radians(30 + 60 * i)
        hx, hy = c[0] + R * math.cos(a), c[1] + R * math.sin(a)
        msp.add_circle(P(hx, hy), 4, dxfattribs=g)                 # Ø8
        if i not in (1, 4):                                       # 90° ve 270° zaten düşey eksende
            msp.add_line(P(c[0] + 6 * math.cos(a), c[1] + 6 * math.sin(a)),
                         P(c[0] + (R + 7) * math.cos(a), c[1] + (R + 7) * math.sin(a)), dxfattribs=e)
        tx, ty = -math.sin(a), math.cos(a)                         # deliğe teğet kısa eksen
        msp.add_line(P(hx - 7 * tx, hy - 7 * ty), P(hx + 7 * tx, hy + 7 * ty), dxfattribs=e)

    D = Olcu()
    D.h("ON", (0, 0), (100, 0), -12)
    D.v("ON", (0, 0), (0, 100), -12)
    D.h("ON", (0, 100), (50, 100), 112)
    D.v("ON", (100, 0), (50, 50), 112)
    D.dia("ON", c, R, 45, dist=52)
    a = math.radians(90)
    D.dia("ON", (c[0] + R * math.cos(a), c[1] + R * math.sin(a)), 4, 60, text="6x<>", dist=14)
    D.ang("ON", c, (c[0] + 20 * math.cos(math.radians(30)), c[1] + 20 * math.sin(math.radians(30))),
          (c[0], c[1] + 20), 22)
    D.render(msp, "ON", ox, oy)
    msp.add_text("SORU 2", height=3.5, dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement(
        P(50, -28), align=TextEntityAlignment.TOP_CENTER)
    msp.add_text("6 delik Ø70 daire üzerinde eşit aralıklı (60°)", height=3.5,
                 dxfattribs={"layer": "YAZI", "style": "TR"}).set_placement((ax0, 41))
    doc.set_modelspace_vport(height=307, center=(105, 148.5))
    path = os.path.join(outdir, "Soru2_Delikli_Levha.dxf")
    doc.saveas(path)
    print("yazıldı:", path)


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    p = h7.build("Soru1_Kanalli_Govde", "KANALLI GÖVDE", h7.parca3(), ("ON", "SOL", "UST"), ("ON", 25.0),
                 olcu_s1(), outdir, k=1.0, line_view="UST", notes=("Kanal ve delikler boydan boya",),
                 papers=("A4Y", "A4D", "A3Y"))
    print("yazıldı:", p)
    soru2(outdir)
