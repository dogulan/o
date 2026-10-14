# -*- coding: utf-8 -*-
"""
Uretilen DXF dosyasindan PNG onizleme goruntuleri cikarir.
AutoCAD'e girmeden modelin dogrulugunu kontrol etmek icindir.

    python3 src/onizleme.py [dxf_yolu]
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

import ezdxf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# katman -> (yuz rengi, kenar rengi, saydamlik)
GORUNUM = {
    "05-CEPHE":            ("#e6e2d8", "#9b968a", 1.00),
    "10-CATI-DOSEME":      ("#cfcabd", "#8f8a7e", 1.00),
    "11-PARAPET":          ("#b4afa2", "#7d786d", 1.00),
    "12-CELIK-PLATFORM":   ("#d59b53", "#8c5f28", 1.00),
    "14-SED-CATI":         ("#9fb0bd", "#5d6d79", 1.00),
    "15-SED-CAM":          ("#8fd0e8", "#3f7f94", 0.55),
    "16-KOPRU-BORU-HATTI": ("#c08a5a", "#7a5430", 1.00),
    "20-EKIPMAN-FAN":      ("#d23b2f", "#7d1c15", 1.00),
    "21-EKIPMAN-AHU":      ("#2f6fd2", "#17407d", 1.00),
    "22-EKIPMAN-BACA":     ("#e3c541", "#8e7a12", 1.00),
    "23-EKIPMAN-RTO":      ("#b43bd2", "#6c1c7d", 1.00),
    "24-EKIPMAN-YIKAYICI": ("#2fb0a8", "#176862", 1.00),
}
CIZGI = {
    "13-KORKULUK": "#8c5f28",
    "16-KOPRU-BORU-HATTI": "#7a5430",
}


def yuzleri_topla(msp):
    yuzler = defaultdict(list)
    cizgiler = defaultdict(list)

    def polyface_ekle(e, katman):
        for f in e.faces():
            pts = [tuple(v.dxf.location) for v in f[:-1]]
            if len(pts) >= 3:
                yuzler[katman].append(pts)

    for e in msp:
        tip = e.dxftype()
        if tip == "POLYLINE" and e.get_mode() == "AcDbPolyFaceMesh":
            polyface_ekle(e, e.dxf.layer)
        elif tip == "POLYLINE" and e.get_mode() == "AcDb3dPolyline":
            pts = [tuple(v.dxf.location) for v in e.vertices]
            if e.dxf.layer in CIZGI:
                cizgiler[e.dxf.layer].append(pts)
        elif tip == "LINE" and e.dxf.layer in CIZGI:
            cizgiler[e.dxf.layer].append([tuple(e.dxf.start), tuple(e.dxf.end)])
        elif tip == "INSERT":
            for v in e.virtual_entities():
                if v.dxftype() == "POLYLINE" and v.get_mode() == "AcDbPolyFaceMesh":
                    polyface_ekle(v, v.dxf.layer)
    return yuzler, cizgiler


def etiketleri_topla(msp):
    """Ekipman blok referanslarindan etiket metni + konum listesi."""
    sonuc = []
    for e in msp.query("INSERT"):
        tag = None
        for a in e.attribs:
            if a.dxf.tag == "ETIKET":
                tag = a.dxf.text
        if tag:
            x, y, z = e.dxf.insert
            sonuc.append((x, y, z, tag))
    return sonuc


def ciz(yuzler, cizgiler, yol, elev, azim, baslik, sinir=None, etiketler=None):
    fig = plt.figure(figsize=(19.2, 11.5), dpi=110)
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    hepsi = []
    for katman, fl in yuzler.items():
        if katman not in GORUNUM:
            continue
        yuz, kenar, alfa = GORUNUM[katman]
        if sinir:
            fl = [f for f in fl if sinir[0] <= sum(p[0] for p in f) / len(f) <= sinir[1]
                  and sinir[2] <= sum(p[1] for p in f) / len(f) <= sinir[3]]
        if not fl:
            continue
        hepsi.extend([p for f in fl for p in f])
        pc = Poly3DCollection(fl, facecolor=yuz, edgecolor=kenar,
                              linewidths=0.18, alpha=alfa)
        ax.add_collection3d(pc)
    for katman, ll in cizgiler.items():
        if sinir:
            ll = [l for l in ll if all(sinir[0] <= p[0] <= sinir[1]
                                       and sinir[2] <= p[1] <= sinir[3] for p in l)]
        if ll:
            ax.add_collection3d(Line3DCollection(ll, colors=CIZGI[katman],
                                                 linewidths=0.35))
    xs = [p[0] for p in hepsi]; ys = [p[1] for p in hepsi]; zs = [p[2] for p in hepsi]
    x_min, x_max = (sinir[0], sinir[1]) if sinir else (min(xs), max(xs))
    y_min, y_max = (sinir[2], sinir[3]) if sinir else (min(ys), max(ys))
    dx, dy = x_max - x_min, y_max - y_min
    dz = max(zs) * 1.05
    ax.set_xlim(x_min, x_max); ax.set_ylim(y_min, y_max); ax.set_zlim(0, dz)
    # yukseklikler 2.2 kat abartilarak okunurluk artirilir
    ax.set_box_aspect((dx, dy, dz * 2.2))
    if etiketler:
        for x, y, z, t in etiketler:
            if sinir and not (sinir[0] <= x <= sinir[1] and sinir[2] <= y <= sinir[3]):
                continue
            ax.text(x + 2, y + 2, dz, t, fontsize=(6.5 if sinir else 4.6), color="#10243d",
                    ha="left", va="bottom", zorder=10)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_position([0.0, 0.0, 1.0, 0.97])
    ax.set_title(baslik, fontsize=16, color="#333333")
    fig.savefig(yol, facecolor="white", bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print("yazildi:", yol)


def main():
    dxf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        KOK, "output", "toyota_boyahane_cati_3d.dxf")
    doc = ezdxf.readfile(dxf)
    yuzler, cizgiler = yuzleri_topla(doc.modelspace())
    etiketler = etiketleri_topla(doc.modelspace())
    print("etiket sayisi:", len(etiketler))
    print("yuz sayisi:", sum(len(v) for v in yuzler.values()))
    cik = os.path.join(KOK, "output")
    ciz(yuzler, cizgiler, os.path.join(cik, "onizleme_izometrik.png"),
        32, -118, "Toyota Boyahane Catisi - 3B model (GB izometrik)")
    ciz(yuzler, cizgiler, os.path.join(cik, "onizleme_izometrik_2.png"),
        28, 42, "Toyota Boyahane Catisi - 3B model (KD izometrik)")
    ciz(yuzler, cizgiler, os.path.join(cik, "onizleme_detay_dogu_blok.png"),
        26, -120, "Dogu blok (firin / RTO bolgesi) - detay",
        sinir=(190, 302, 45, 130), etiketler=etiketler)
    ciz(yuzler, cizgiler, os.path.join(cik, "onizleme_ustten.png"),
        89.9, -90, "Toyota Boyahane Catisi - ustten gorunus ve ekipman etiketleri",
        etiketler=etiketler)


if __name__ == "__main__":
    main()
