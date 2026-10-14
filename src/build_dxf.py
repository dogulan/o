# -*- coding: utf-8 -*-
"""
Toyota Boyahane Catisi - 3B AutoCAD (DXF) model ureteci
=======================================================

Girdi : data/cati_geometri.json  (cati bloklari, kotlar, kalibrasyon)
        data/ekipman.csv         (fotograftan okunan tum ekipman etiketleri)
Cikti : output/toyota_boyahane_cati_3d.dxf

Kullanim:
    python3 src/build_dxf.py                 # metre biriminde
    python3 src/build_dxf.py --birim mm      # milimetre biriminde
    python3 src/build_dxf.py --cikti baska.dxf

Modelin tamami parametriktir: olcek, kot veya ekipman konumu degistirmek icin
sadece data/ klasorundeki dosyalari duzenleyip betigi tekrar calistirmak yeterlidir.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import Counter, OrderedDict

import ezdxf
from ezdxf.render import MeshVertexMerger

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOMETRI = os.path.join(KOK, "data", "cati_geometri.json")
EKIPMAN = os.path.join(KOK, "data", "ekipman.csv")

# ----------------------------------------------------------------------------
# Katman tanimlari:  ad -> (ACI renk, aciklama)
# ----------------------------------------------------------------------------
KATMANLAR = OrderedDict([
    ("00-SINIR",            (8,   "Bina sinirlari - 2B referans (z=0)")),
    ("01-EKSEN",            (8,   "Yardimci eksenler")),
    ("05-CEPHE",            (253, "Cepheler (zeminden cati altina kadar kabuk)")),
    ("10-CATI-DOSEME",      (254, "Cati dosemeleri (3B kati)")),
    ("11-PARAPET",          (9,   "Parapet duvarlari")),
    ("12-CELIK-PLATFORM",   (30,  "Celik teknik platformlar ve ayaklar")),
    ("13-KORKULUK",         (31,  "Korkuluklar")),
    ("14-SED-CATI",         (150, "Sed (kuzey isik) catilari")),
    ("15-SED-CAM",          (140, "Sed cati cam yuzeyleri")),
    ("16-KOPRU-BORU-HATTI", (33,  "Koprüler / boru hatti bantlari")),
    ("20-EKIPMAN-FAN",      (1,   "Cati aspiratorleri")),
    ("21-EKIPMAN-AHU",      (5,   "Klima santralleri / galeri uniteleri")),
    ("22-EKIPMAN-BACA",     (2,   "Bacalar ve P serisi cikislar")),
    ("23-EKIPMAN-RTO",      (6,   "RTO uniteleri (W/B - SB R70)")),
    ("24-EKIPMAN-YIKAYICI", (4,   "330 serisi yikayici/kule uniteleri")),
    ("30-ETIKET",           (7,   "Ekipman etiketleri")),
    ("31-KILAVUZ-CIZGI",    (8,   "Etiket kilavuz cizgileri")),
    ("90-PAFTA",            (7,   "Pafta cercevesi ve antet")),
])

TIP_KATMAN = {
    "FAN": "20-EKIPMAN-FAN",
    "AHU": "21-EKIPMAN-AHU",
    "BACA": "22-EKIPMAN-BACA",
    "RTO": "23-EKIPMAN-RTO",
    "YIKAYICI": "24-EKIPMAN-YIKAYICI",
}

TIP_ACIKLAMA = {
    "FAN": "CATI ASPIRATORU",
    "AHU": "KLIMA SANTRALI",
    "BACA": "BACA / CIKIS",
    "RTO": "RTO UNITESI",
    "YIKAYICI": "YIKAYICI KULE",
}


# ----------------------------------------------------------------------------
# Yardimci geometri uretecleri (hepsi POLYFACE MESH olarak yazilir -> her
# AutoCAD surumunde ve her DXF goruntuleyicide sorunsuz acilir)
# ----------------------------------------------------------------------------
def kutu_yuzleri(x0, y0, z0, x1, y1, z1):
    """Eksenlere paralel bir prizmanin 6 yuzunu dondurur."""
    a = (x0, y0, z0); b = (x1, y0, z0); c = (x1, y1, z0); d = (x0, y1, z0)
    e = (x0, y0, z1); f = (x1, y0, z1); g = (x1, y1, z1); h = (x0, y1, z1)
    return [
        [a, b, c, d],   # alt
        [e, f, g, h],   # ust
        [a, b, f, e],   # on
        [b, c, g, f],   # sag
        [c, d, h, g],   # arka
        [d, a, e, h],   # sol
    ]


def silindir_yuzleri(cx, cy, z0, z1, r, n=16):
    """Dusey eksenli silindir (kapakli)."""
    pts = [(cx + r * math.cos(2 * math.pi * i / n),
            cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    yuzler = []
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        yuzler.append([(x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)])
    # kapaklar ucgenlenerek
    for i in range(1, n - 1):
        yuzler.append([(pts[0][0], pts[0][1], z0), (pts[i][0], pts[i][1], z0),
                       (pts[i + 1][0], pts[i + 1][1], z0)])
        yuzler.append([(pts[0][0], pts[0][1], z1), (pts[i][0], pts[i][1], z1),
                       (pts[i + 1][0], pts[i + 1][1], z1)])
    return yuzler


def koni_yuzleri(cx, cy, z0, z1, r0, r1, n=16):
    """Kesik koni - fan sapkasi / baca cikisi icin."""
    yuzler = []
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        p0 = (cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z0)
        p1 = (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1), z0)
        q1 = (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1)
        q0 = (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z1)
        yuzler.append([p0, p1, q1, q0])
    return yuzler


def prizma_yuzleri(profil_yz, x0, x1):
    """(y,z) profilini x ekseni boyunca supurur - sed cati makasi icin."""
    n = len(profil_yz)
    yuzler = []
    for i in range(n):
        y0, z0 = profil_yz[i]
        y1, z1 = profil_yz[(i + 1) % n]
        yuzler.append([(x0, y0, z0), (x0, y1, z1), (x1, y1, z1), (x1, y0, z0)])
    if n == 3:
        yuzler.append([(x0, profil_yz[0][0], profil_yz[0][1]),
                       (x0, profil_yz[1][0], profil_yz[1][1]),
                       (x0, profil_yz[2][0], profil_yz[2][1])])
        yuzler.append([(x1, profil_yz[0][0], profil_yz[0][1]),
                       (x1, profil_yz[1][0], profil_yz[1][1]),
                       (x1, profil_yz[2][0], profil_yz[2][1])])
    return yuzler


def mesh_ekle(hedef, yuzler, katman):
    """Yuz listesini tek bir POLYFACE MESH olarak layout/blok icine yazar."""
    mb = MeshVertexMerger()
    for f in yuzler:
        mb.add_face(f)
    return mb.render_polyface(hedef, dxfattribs={"layer": katman})


# ----------------------------------------------------------------------------
# Model kurucu
# ----------------------------------------------------------------------------
class CatiModeli:
    def __init__(self, geometri, ekipmanlar, birim="m"):
        self.g = geometri
        self.ekipmanlar = ekipmanlar
        self.birim = birim
        self.F = 1000.0 if birim == "mm" else 1.0          # metre -> cizim birimi
        kal = geometri["kalibrasyon"]
        self.mpx = float(kal["metre_bolu_piksel"])
        self.ox, self.oy = kal["orijin_px"]
        self.blok_kot = {b["ad"]: float(b["kot"]) for b in geometri["bloklar"]}
        for p in geometri["celik_platformlar"]:
            self.blok_kot[p["ad"]] = float(p["kot"])
        self.blok_cache = {}

        self.doc = ezdxf.new("R2018", setup=True)
        self.doc.units = ezdxf.units.MM if birim == "mm" else ezdxf.units.M
        self.doc.header["$INSUNITS"] = 4 if birim == "mm" else 6
        self.msp = self.doc.modelspace()
        self._katmanlari_kur()
        self._stil_kur()

    # -- birim / koordinat donusumleri ---------------------------------------
    def u(self, metre):
        return metre * self.F

    def xy(self, px, py):
        """Fotograf pikseli -> model koordinati (X dogu, Y kuzey)."""
        X = (px - self.ox) * self.mpx
        Y = (self.oy - py) * self.mpx
        return self.u(X), self.u(Y)

    def dikdortgen(self, px_kutu):
        x0, y0 = self.xy(px_kutu[0], px_kutu[3])   # sol-alt (guney-bati)
        x1, y1 = self.xy(px_kutu[2], px_kutu[1])   # sag-ust (kuzey-dogu)
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    # -- kurulum -------------------------------------------------------------
    def _katmanlari_kur(self):
        for ad, (renk, acik) in KATMANLAR.items():
            lay = self.doc.layers.add(ad, color=renk)
            lay.description = acik

    def _stil_kur(self):
        if "ANNOT" not in self.doc.styles:
            self.doc.styles.add("ANNOT", font="isocp.shx")

    # -- cati bloklari -------------------------------------------------------
    def cati_bloklari(self):
        for b in self.g["bloklar"]:
            x0, y0, x1, y1 = self.dikdortgen(b["px"])
            kot = self.u(float(b["kot"]))
            kal = self.u(float(b["kalinlik"]))
            mesh_ekle(self.msp, kutu_yuzleri(x0, y0, kot - kal, x1, y1, kot),
                      "10-CATI-DOSEME")
            # 2B referans sinir
            self.msp.add_lwpolyline(
                [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                dxfattribs={"layer": "00-SINIR"})
            # cephe kabugu (zeminden cati altina)
            taban = self.u(float(b.get("taban_kot", 0.0)))
            if kot - kal > taban:
                self.cephe(x0, y0, x1, y1, taban, kot - kal, self.u(0.40))
            # parapet
            p = float(b.get("parapet", 0.0))
            if p > 0:
                self.parapet(x0, y0, x1, y1, kot, self.u(p), self.u(0.30))
            # blok adi yazisi
            self.msp.add_text(
                b["ad"], height=self.u(3.0),
                dxfattribs={"layer": "30-ETIKET", "style": "ANNOT", "color": 8}
            ).set_placement(((x0 + x1) / 2, (y0 + y1) / 2, kot + self.u(0.2)),
                            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    def cephe(self, x0, y0, x1, y1, z0, z1, t):
        yuzler = []
        yuzler += kutu_yuzleri(x0, y0, z0, x1, y0 + t, z1)
        yuzler += kutu_yuzleri(x0, y1 - t, z0, x1, y1, z1)
        yuzler += kutu_yuzleri(x0, y0 + t, z0, x0 + t, y1 - t, z1)
        yuzler += kutu_yuzleri(x1 - t, y0 + t, z0, x1, y1 - t, z1)
        mesh_ekle(self.msp, yuzler, "05-CEPHE")

    def parapet(self, x0, y0, x1, y1, kot, h, t):
        yuzler = []
        yuzler += kutu_yuzleri(x0, y0, kot, x1, y0 + t, kot + h)
        yuzler += kutu_yuzleri(x0, y1 - t, kot, x1, y1, kot + h)
        yuzler += kutu_yuzleri(x0, y0 + t, kot, x0 + t, y1 - t, kot + h)
        yuzler += kutu_yuzleri(x1 - t, y0 + t, kot, x1, y1 - t, kot + h)
        mesh_ekle(self.msp, yuzler, "11-PARAPET")

    # -- celik platformlar ---------------------------------------------------
    def celik_platformlar(self):
        for p in self.g["celik_platformlar"]:
            x0, y0, x1, y1 = self.dikdortgen(p["px"])
            kot = self.u(float(p["kot"]))
            taban = self.u(float(p["taban_kot"]))
            d = self.u(0.25)
            yuzler = kutu_yuzleri(x0, y0, kot - d, x1, y1, kot)
            # ayaklar
            a = self.u(0.35)
            nx = max(2, int(round((x1 - x0) / self.u(6.0))) + 1)
            ny = max(2, int(round((y1 - y0) / self.u(6.0))) + 1)
            for i in range(nx):
                for j in range(ny):
                    cx = x0 + (x1 - x0) * i / (nx - 1)
                    cy = y0 + (y1 - y0) * j / (ny - 1)
                    cx = min(max(cx, x0 + a), x1 - a)
                    cy = min(max(cy, y0 + a), y1 - a)
                    yuzler += kutu_yuzleri(cx - a / 2, cy - a / 2, taban,
                                           cx + a / 2, cy + a / 2, kot - d)
            mesh_ekle(self.msp, yuzler, "12-CELIK-PLATFORM")
            self.korkuluk(x0, y0, x1, y1, kot, self.u(float(p.get("korkuluk", 1.1))))

    def korkuluk(self, x0, y0, x1, y1, kot, h):
        kose = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        for seviye in (h, h * 0.5):
            self.msp.add_polyline3d(
                [(x, y, kot + seviye) for x, y in kose],
                dxfattribs={"layer": "13-KORKULUK"})
        adim = self.u(3.0)
        for i in range(len(kose) - 1):
            (ax, ay), (bx, by) = kose[i], kose[i + 1]
            uz = math.hypot(bx - ax, by - ay)
            n = max(1, int(uz / adim))
            for k in range(n + 1):
                t = k / n
                px_, py_ = ax + (bx - ax) * t, ay + (by - ay) * t
                self.msp.add_line((px_, py_, kot), (px_, py_, kot + h),
                                  dxfattribs={"layer": "13-KORKULUK"})

    # -- sed catilar ---------------------------------------------------------
    def sed_catilar(self):
        for s in self.g["sed_catilar"]:
            x0, y0, x1, y1 = self.dikdortgen(s["px"])
            z0 = self.u(float(s["taban_kot"]))
            h = self.u(float(s["tepe_yuksekligi"]))
            n = int(s["bolme_sayisi"])
            genislik = (x1 - x0) / n
            for i in range(n):
                bx0 = x0 + i * genislik + genislik * 0.08
                bx1 = x0 + (i + 1) * genislik - genislik * 0.08
                profil = [(y0, z0), (y1, z0), (y1, z0 + h)]
                mesh_ekle(self.msp, prizma_yuzleri(profil, bx0, bx1), "14-SED-CATI")
                # kuzeye bakan cam yuzey
                mesh_ekle(self.msp, [[(bx0, y1, z0), (bx1, y1, z0),
                                      (bx1, y1, z0 + h), (bx0, y1, z0 + h)]],
                          "15-SED-CAM")

    # -- koprüler / boru hatlari ---------------------------------------------
    def koprular(self):
        for k in self.g["koprular"]:
            x0, y0, x1, y1 = self.dikdortgen(k["px"])
            kot = self.u(float(k["kot"]))
            h = self.u(float(k["yukseklik"]))
            mesh_ekle(self.msp, kutu_yuzleri(x0, y0, kot, x1, y1, kot + h),
                      "16-KOPRU-BORU-HATTI")
            # capraz celik dolgu gorunumu
            adim = self.u(6.0)
            uz = x1 - x0 if (x1 - x0) > (y1 - y0) else y1 - y0
            n = max(1, int(uz / adim))
            for i in range(n):
                t0, t1 = i / n, (i + 1) / n
                if (x1 - x0) > (y1 - y0):
                    a = (x0 + (x1 - x0) * t0, y0, kot)
                    b = (x0 + (x1 - x0) * t1, y0, kot + h)
                else:
                    a = (x0, y0 + (y1 - y0) * t0, kot)
                    b = (x0, y0 + (y1 - y0) * t1, kot + h)
                self.msp.add_line(a, b, dxfattribs={"layer": "16-KOPRU-BORU-HATTI"})

    # -- ekipman blok tanimlari ---------------------------------------------
    def ekipman_blogu(self, tip, boyut):
        """Ayni geometriye sahip ekipmanlar icin tek bir AutoCAD blogu uretir."""
        if tip in ("FAN", "BACA", "YIKAYICI"):
            cap, yuk = boyut
            ad = "{}_D{:d}_H{:d}".format(tip, int(round(cap * 1000)),
                                         int(round(yuk * 1000)))
        else:
            en, boy, yuk = boyut
            ad = "{}_{:d}x{:d}x{:d}".format(tip, int(round(en * 1000)),
                                            int(round(boy * 1000)),
                                            int(round(yuk * 1000)))
        if ad in self.blok_cache:
            return ad
        katman = TIP_KATMAN[tip]
        blk = self.doc.blocks.new(ad)
        if tip == "FAN":
            cap, yuk = boyut
            r = self.u(cap / 2.0)
            k = self.u(0.20)                              # kaide yuksekligi
            yuzler = kutu_yuzleri(-r * 1.25, -r * 1.25, 0, r * 1.25, r * 1.25, k)
            yuzler += silindir_yuzleri(0, 0, k, self.u(yuk) * 0.7, r)
            yuzler += koni_yuzleri(0, 0, self.u(yuk) * 0.7, self.u(yuk),
                                   r, r * 1.35)
            mesh_ekle(blk, yuzler, katman)
        elif tip == "BACA":
            cap, yuk = boyut
            r = self.u(cap / 2.0)
            yuzler = kutu_yuzleri(-r * 1.6, -r * 1.6, 0, r * 1.6, r * 1.6, self.u(0.30))
            yuzler += silindir_yuzleri(0, 0, self.u(0.30), self.u(yuk), r)
            yuzler += koni_yuzleri(0, 0, self.u(yuk), self.u(yuk) + self.u(0.35),
                                   r, r * 0.75)
            mesh_ekle(blk, yuzler, katman)
        elif tip == "YIKAYICI":
            cap, yuk = boyut
            r = self.u(cap / 2.0)
            yuzler = silindir_yuzleri(0, 0, 0, self.u(yuk), r)
            yuzler += koni_yuzleri(0, 0, self.u(yuk), self.u(yuk) + self.u(0.6),
                                   r, r * 0.45)
            mesh_ekle(blk, yuzler, katman)
        elif tip == "AHU":
            en, boy, yuk = boyut
            ex, by, h = self.u(en) / 2, self.u(boy) / 2, self.u(yuk)
            yuzler = kutu_yuzleri(-ex, -by, 0, ex, by, self.u(0.25))     # kaide
            yuzler += kutu_yuzleri(-ex * 0.95, -by * 0.95, self.u(0.25),
                                   ex * 0.95, by * 0.95, h)
            mesh_ekle(blk, yuzler, katman)
        elif tip == "RTO":
            en, boy, yuk = boyut
            ex, by, h = self.u(en) / 2, self.u(boy) / 2, self.u(yuk)
            yuzler = kutu_yuzleri(-ex, -by, 0, ex, by, h * 0.72)
            yuzler += silindir_yuzleri(ex * 0.62, 0, h * 0.72, h, self.u(0.90))
            yuzler += koni_yuzleri(ex * 0.62, 0, h, h + self.u(0.4),
                                   self.u(0.90), self.u(0.70))
            mesh_ekle(blk, yuzler, katman)
        # oznitelikler (ATTDEF) - AutoCAD'de veri cikarmak icin
        th = self.u(1.2)
        ust = self.u(boyut[-1]) + self.u(0.6)
        a1 = blk.add_attdef("ETIKET", (0, 0, ust), height=th,
                            dxfattribs={"layer": "30-ETIKET", "style": "ANNOT"})
        a1.dxf.invisible = 1
        a2 = blk.add_attdef("TIP", (0, 0, ust + th * 1.4), height=th,
                            dxfattribs={"layer": "30-ETIKET", "style": "ANNOT"})
        a2.dxf.invisible = 1
        a3 = blk.add_attdef("KOT", (0, 0, ust + th * 2.8), height=th,
                            dxfattribs={"layer": "30-ETIKET", "style": "ANNOT"})
        a3.dxf.invisible = 1
        self.blok_cache[ad] = True
        return ad

    # -- ekipman yerlesimi ---------------------------------------------------
    def ekipmanlari_yerlestir(self):
        sayac = Counter()
        self.koordinatlar = []
        for e in self.ekipmanlar:
            tip = e["tip"]
            x, y = self.xy(float(e["px_x"]), float(e["px_y"]))
            kot_m = self.blok_kot.get(e["blok"])
            if kot_m is None:
                raise SystemExit("Bilinmeyen blok: {} (etiket {})".format(
                    e["blok"], e["etiket"]))
            z = self.u(kot_m)
            yuk = float(e["yukseklik_m"])
            if tip in ("FAN", "BACA", "YIKAYICI"):
                boyut = (float(e["cap_m"]), yuk)
            else:
                boyut = (float(e["en_m"]), float(e["boy_m"]), yuk)
            blok_adi = self.ekipman_blogu(tip, boyut)
            ref = self.msp.add_blockref(blok_adi, (x, y, z),
                                        dxfattribs={"layer": TIP_KATMAN[tip]})
            ref.add_auto_attribs({
                "ETIKET": e["etiket"],
                "TIP": TIP_ACIKLAMA[tip],
                "KOT": "+{:.2f}".format(kot_m),
            })
            self.etiket_yaz(x, y, z + self.u(yuk), e["etiket"], kot_m)
            self.koordinatlar.append({
                "etiket": e["etiket"], "grup": e["grup"], "tip": tip,
                "blok": e["blok"], "blok_adi_dxf": blok_adi,
                "X_m": round(x / self.F, 2), "Y_m": round(y / self.F, 2),
                "Z_m": round(kot_m, 2),
                "yukseklik_m": round(yuk, 2), "aciklama": e["aciklama"]})
            sayac[tip] += 1
        return sayac

    def etiket_yaz(self, x, y, z_ust, metin, kot_m):
        dx, dy, dz = self.u(5.0), self.u(5.0), self.u(3.0)
        tz = z_ust + dz
        self.msp.add_polyline3d(
            [(x, y, z_ust), (x, y, tz), (x + dx, y + dy, tz)],
            dxfattribs={"layer": "31-KILAVUZ-CIZGI"})
        t = self.msp.add_text(
            metin, height=self.u(2.2),
            dxfattribs={"layer": "30-ETIKET", "style": "ANNOT"})
        t.set_placement((x + dx, y + dy + self.u(0.6), tz),
                        align=ezdxf.enums.TextEntityAlignment.LEFT)
        t2 = self.msp.add_text(
            "+{:.2f}".format(kot_m), height=self.u(1.4),
            dxfattribs={"layer": "30-ETIKET", "style": "ANNOT", "color": 8})
        t2.set_placement((x + dx, y + dy - self.u(1.8), tz),
                         align=ezdxf.enums.TextEntityAlignment.LEFT)

    # -- kuzey oku -----------------------------------------------------------
    def kuzey_oku(self):
        x0, y0, x1, y1 = self.dikdortgen([140, 160, 1950, 1250])
        x = x1 + self.u(18.0)
        y = y1 - self.u(10.0)
        L = self.u(14.0)
        self.msp.add_polyline3d([(x, y, 0), (x, y + L, 0)],
                                dxfattribs={"layer": "01-EKSEN"})
        self.msp.add_polyline3d(
            [(x - L * 0.12, y + L * 0.75, 0), (x, y + L, 0),
             (x + L * 0.12, y + L * 0.75, 0)],
            dxfattribs={"layer": "01-EKSEN"})
        self.msp.add_text("K", height=self.u(6.0),
                          dxfattribs={"layer": "01-EKSEN", "style": "ANNOT"}
                          ).set_placement((x, y + L + self.u(4.0), 0),
                                          align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    # -- pafta (kagit alani) -------------------------------------------------
    def pafta(self, sayac):
        lay = self.doc.layouts.new("CATI-PLANI-A1")
        lay.page_setup(size=(841, 594), margins=(10, 10, 10, 10), units="mm")
        W, H = 821, 574
        kenar = [(0, 0), (W, 0), (W, H), (0, H)]
        lay.add_lwpolyline(kenar, close=True, dxfattribs={"layer": "90-PAFTA"})
        # antet
        ax, ay, aw, ah = W - 250, 0, 250, 90
        lay.add_lwpolyline([(ax, ay), (ax + aw, ay), (ax + aw, ay + ah), (ax, ay + ah)],
                           close=True, dxfattribs={"layer": "90-PAFTA"})
        satirlar = [
            ("TOYOTA BOYAHANE - CATI 3B MODELI", 6.0, 72),
            ("Cati ekipman yerlesimi / roof equipment layout", 3.2, 62),
            ("Olcek (model): 1 birim = 1 {}".format(self.birim), 3.2, 52),
            ("Toplam ekipman: {} adet".format(sum(sayac.values())), 3.2, 42),
            ("Kaynak: isaretli havadan gorunus fotografi", 3.0, 32),
            ("Uretim: data/*.csv + src/build_dxf.py", 3.0, 22),
            ("Konumlar fotograftan sayisallastirilmistir - saha teyidi gerekir", 2.6, 12),
        ]
        for metin, h, dy in satirlar:
            lay.add_text(metin, height=h,
                         dxfattribs={"layer": "90-PAFTA", "style": "ANNOT"}
                         ).set_placement((ax + 6, ay + dy),
                                         align=ezdxf.enums.TextEntityAlignment.LEFT)
        # lejant
        lx, ly = 8, 8
        lay.add_text("LEJANT", height=4.5,
                     dxfattribs={"layer": "90-PAFTA", "style": "ANNOT"}
                     ).set_placement((lx, ly + 58),
                                     align=ezdxf.enums.TextEntityAlignment.LEFT)
        for i, (tip, ad) in enumerate(TIP_ACIKLAMA.items()):
            y = ly + 48 - i * 9
            renk = KATMANLAR[TIP_KATMAN[tip]][0]
            lay.add_lwpolyline([(lx, y), (lx + 7, y), (lx + 7, y + 5), (lx, y + 5)],
                               close=True,
                               dxfattribs={"layer": "90-PAFTA", "color": renk})
            lay.add_text("{}  ({} adet)".format(ad, sayac.get(tip, 0)), height=3.2,
                         dxfattribs={"layer": "90-PAFTA", "style": "ANNOT"}
                         ).set_placement((lx + 11, y + 0.6),
                                         align=ezdxf.enums.TextEntityAlignment.LEFT)
        # ustten gorunus viewport
        x0, y0, x1, y1 = self.dikdortgen([140, 160, 1950, 1250])
        mw, mh = x1 - x0, y1 - y0
        vp_w, vp_h = W - 20, H - 110
        olcek = min(vp_w / mw, vp_h / mh) * 0.95
        lay.add_viewport(
            center=(W / 2, H - 10 - vp_h / 2), size=(vp_w, vp_h),
            view_center_point=((x0 + x1) / 2, (y0 + y1) / 2),
            view_height=vp_h / olcek)

    # -- kaydet --------------------------------------------------------------
    def koordinat_listesi_yaz(self, yol):
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        alanlar = ["etiket", "grup", "tip", "blok", "blok_adi_dxf",
                   "X_m", "Y_m", "Z_m", "yukseklik_m", "aciklama"]
        with open(yol, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=alanlar)
            w.writeheader()
            for r in sorted(self.koordinatlar, key=lambda r: r["etiket"]):
                w.writerow(r)

    def kaydet(self, yol):
        if "Layout1" in self.doc.layouts.names():
            self.doc.layouts.delete("Layout1")
        x0, y0, x1, y1 = self.dikdortgen([140, 160, 1950, 1250])
        self.doc.set_modelspace_vport(height=(y1 - y0) * 1.15,
                                      center=((x0 + x1) / 2, (y0 + y1) / 2))
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        self.doc.saveas(yol)


def ekipmanlari_oku(yol):
    with open(yol, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("etiket")]


def main():
    ap = argparse.ArgumentParser(description="Toyota boyahane cati 3B DXF ureteci")
    ap.add_argument("--birim", choices=["m", "mm"], default="m",
                    help="Cizim birimi (varsayilan: m)")
    ap.add_argument("--cikti", default=os.path.join(KOK, "output",
                                                    "toyota_boyahane_cati_3d.dxf"))
    args = ap.parse_args()

    with open(GEOMETRI, encoding="utf-8") as f:
        geometri = json.load(f)
    ekipmanlar = ekipmanlari_oku(EKIPMAN)

    m = CatiModeli(geometri, ekipmanlar, birim=args.birim)
    m.cati_bloklari()
    m.celik_platformlar()
    m.sed_catilar()
    m.koprular()
    sayac = m.ekipmanlari_yerlestir()
    m.kuzey_oku()
    m.pafta(sayac)
    m.kaydet(args.cikti)
    liste = os.path.join(KOK, "output", "ekipman_koordinat_listesi.csv")
    m.koordinat_listesi_yaz(liste)

    print("DXF yazildi : {}".format(args.cikti))
    print("Birim       : 1 birim = 1 {}".format(args.birim))
    print("Cati blogu  : {} adet".format(len(geometri["bloklar"])))
    print("Ekipman     : {} adet -> {}".format(sum(sayac.values()), dict(sayac)))
    print("Koordinatlar: {}".format(liste))


if __name__ == "__main__":
    main()
