# -*- coding: utf-8 -*-
"""
Toyota Boyahane Catisi - 3B AutoCAD (DXF) BACA modeli
=====================================================

Fotografta kirmizi ile isaretlenmis noktalarin tamami CATI BACASIDIR; yanlarindaki
el yazisi numaralar da baca kodlaridir. Bu betik, her bacayi 3B kati model olarak
cati uzerine yerlestirir ve kodunu hem yazi hem de AutoCAD ozniteligi olarak isler.

Girdi : data/cati_geometri.json  (cati bloklari, kotlar, kalibrasyon)
        data/bacalar.csv         (fotograftan okunan tum baca kodlari ve konumlari)
Cikti : output/toyota_boyahane_cati_3d.dxf
        output/baca_koordinat_listesi.csv

Kullanim:
    python3 src/build_dxf.py                 # metre biriminde
    python3 src/build_dxf.py --birim mm      # milimetre biriminde
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
BACALAR = os.path.join(KOK, "data", "bacalar.csv")

# ----------------------------------------------------------------------------
# Yapi katmanlari:  ad -> (ACI renk, aciklama)
# ----------------------------------------------------------------------------
YAPI_KATMANLARI = OrderedDict([
    ("00-SINIR",            (8,   "Bina sinirlari - 2B referans (z=0)")),
    ("01-EKSEN",            (8,   "Kuzey oku ve yardimci eksenler")),
    ("05-CEPHE",            (253, "Cepheler (zeminden cati altina kabuk)")),
    ("10-CATI-DOSEME",      (254, "Cati dosemeleri (3B kati)")),
    ("11-PARAPET",          (9,   "Parapet duvarlari")),
    ("12-CELIK-PLATFORM",   (30,  "Celik teknik platformlar ve ayaklar")),
    ("13-KORKULUK",         (31,  "Korkuluklar")),
    ("14-SED-CATI",         (150, "Sed (kuzey isik) catilari")),
    ("15-SED-CAM",          (140, "Sed cati cam yuzeyleri")),
    ("16-KOPRU-BORU-HATTI", (33,  "Koprüler / boru hatti bantlari")),
    ("30-BACA-KODU",        (7,   "Baca kodu yazilari")),
    ("31-KILAVUZ-CIZGI",    (8,   "Baca kodu kilavuz cizgileri")),
    ("90-PAFTA",            (7,   "Pafta cercevesi ve antet")),
])

# Baca serileri icin renk paleti (her seri ayri katman -> AutoCAD'de izole edilebilir)
SERI_RENKLERI = [1, 3, 4, 5, 6, 30, 40, 50, 70, 90, 110, 130, 150, 170, 190, 210,
                 230, 12, 22, 92]

SINIF_ACIKLAMA = OrderedDict([
    ("STANDART", "STANDART CATI BACASI"),
    ("BUYUK",    "BUYUK KESITLI BACA"),
    ("RTO",      "RTO BACASI (R70)"),
])


# ----------------------------------------------------------------------------
# Geometri uretecleri (hepsi POLYFACE MESH -> her AutoCAD surumunde acilir)
# ----------------------------------------------------------------------------
def kutu_yuzleri(x0, y0, z0, x1, y1, z1):
    a = (x0, y0, z0); b = (x1, y0, z0); c = (x1, y1, z0); d = (x0, y1, z0)
    e = (x0, y0, z1); f = (x1, y0, z1); g = (x1, y1, z1); h = (x0, y1, z1)
    return [[a, b, c, d], [e, f, g, h], [a, b, f, e],
            [b, c, g, f], [c, d, h, g], [d, a, e, h]]


def silindir_yuzleri(cx, cy, z0, z1, r, n=20, kapak=True):
    pts = [(cx + r * math.cos(2 * math.pi * i / n),
            cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    yuzler = []
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        yuzler.append([(x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)])
    if kapak:
        for i in range(1, n - 1):
            yuzler.append([(pts[0][0], pts[0][1], z0), (pts[i][0], pts[i][1], z0),
                           (pts[i + 1][0], pts[i + 1][1], z0)])
            yuzler.append([(pts[0][0], pts[0][1], z1), (pts[i][0], pts[i][1], z1),
                           (pts[i + 1][0], pts[i + 1][1], z1)])
    return yuzler


def koni_yuzleri(cx, cy, z0, z1, r0, r1, n=20):
    yuzler = []
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        yuzler.append([
            (cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z0),
            (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1), z0),
            (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1),
            (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z1)])
    return yuzler


def prizma_yuzleri(profil_yz, x0, x1):
    n = len(profil_yz)
    yuzler = []
    for i in range(n):
        y0, z0 = profil_yz[i]
        y1, z1 = profil_yz[(i + 1) % n]
        yuzler.append([(x0, y0, z0), (x0, y1, z1), (x1, y1, z1), (x1, y0, z0)])
    if n == 3:
        for x in (x0, x1):
            yuzler.append([(x, profil_yz[0][0], profil_yz[0][1]),
                           (x, profil_yz[1][0], profil_yz[1][1]),
                           (x, profil_yz[2][0], profil_yz[2][1])])
    return yuzler


def mesh_ekle(hedef, yuzler, katman):
    mb = MeshVertexMerger()
    for f in yuzler:
        mb.add_face(f)
    return mb.render_polyface(hedef, dxfattribs={"layer": katman})


# ----------------------------------------------------------------------------
class CatiModeli:
    def __init__(self, geometri, bacalar, birim="m"):
        self.g = geometri
        self.bacalar = bacalar
        self.birim = birim
        self.F = 1000.0 if birim == "mm" else 1.0
        kal = geometri["kalibrasyon"]
        self.mpx = float(kal["metre_bolu_piksel"])
        self.ox, self.oy = kal["orijin_px"]
        self.blok_kot = {b["ad"]: float(b["kot"]) for b in geometri["bloklar"]}
        for p in geometri["celik_platformlar"]:
            self.blok_kot[p["ad"]] = float(p["kot"])
        self.blok_cache = {}
        self.koordinatlar = []

        self.seriler = sorted({b["seri"] for b in bacalar})
        self.seri_katman = {s: "20-BACA-{}".format(s) for s in self.seriler}
        self.seri_renk = {s: SERI_RENKLERI[i % len(SERI_RENKLERI)]
                          for i, s in enumerate(self.seriler)}

        self.doc = ezdxf.new("R2018", setup=True)
        self.doc.units = ezdxf.units.MM if birim == "mm" else ezdxf.units.M
        self.doc.header["$INSUNITS"] = 4 if birim == "mm" else 6
        self.msp = self.doc.modelspace()
        self._katmanlari_kur()
        if "ANNOT" not in self.doc.styles:
            self.doc.styles.add("ANNOT", font="isocp.shx")

    # -- birim / koordinat --------------------------------------------------
    def u(self, metre):
        return metre * self.F

    def xy(self, px, py):
        return self.u((px - self.ox) * self.mpx), self.u((self.oy - py) * self.mpx)

    def dikdortgen(self, px_kutu):
        x0, y0 = self.xy(px_kutu[0], px_kutu[3])
        x1, y1 = self.xy(px_kutu[2], px_kutu[1])
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def _katmanlari_kur(self):
        for ad, (renk, acik) in YAPI_KATMANLARI.items():
            self.doc.layers.add(ad, color=renk).description = acik
        for s in self.seriler:
            self.doc.layers.add(
                self.seri_katman[s], color=self.seri_renk[s]
            ).description = "{} serisi bacalar".format(s)

    # -- cati bloklari ------------------------------------------------------
    def cati_bloklari(self):
        for b in self.g["bloklar"]:
            x0, y0, x1, y1 = self.dikdortgen(b["px"])
            kot = self.u(float(b["kot"]))
            kal = self.u(float(b["kalinlik"]))
            mesh_ekle(self.msp, kutu_yuzleri(x0, y0, kot - kal, x1, y1, kot),
                      "10-CATI-DOSEME")
            self.msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                                    close=True, dxfattribs={"layer": "00-SINIR"})
            taban = self.u(float(b.get("taban_kot", 0.0)))
            if kot - kal > taban:
                self.kabuk(x0, y0, x1, y1, taban, kot - kal, self.u(0.40), "05-CEPHE")
            p = float(b.get("parapet", 0.0))
            if p > 0:
                self.kabuk(x0, y0, x1, y1, kot, kot + self.u(p), self.u(0.30),
                           "11-PARAPET")
            self.msp.add_text(
                b["ad"], height=self.u(3.0),
                dxfattribs={"layer": "30-BACA-KODU", "style": "ANNOT", "color": 8}
            ).set_placement(((x0 + x1) / 2, (y0 + y1) / 2, kot + self.u(0.2)),
                            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    def kabuk(self, x0, y0, x1, y1, z0, z1, t, katman):
        yuzler = []
        yuzler += kutu_yuzleri(x0, y0, z0, x1, y0 + t, z1)
        yuzler += kutu_yuzleri(x0, y1 - t, z0, x1, y1, z1)
        yuzler += kutu_yuzleri(x0, y0 + t, z0, x0 + t, y1 - t, z1)
        yuzler += kutu_yuzleri(x1 - t, y0 + t, z0, x1, y1 - t, z1)
        mesh_ekle(self.msp, yuzler, katman)

    # -- celik platformlar --------------------------------------------------
    def celik_platformlar(self):
        for p in self.g["celik_platformlar"]:
            x0, y0, x1, y1 = self.dikdortgen(p["px"])
            kot = self.u(float(p["kot"]))
            taban = self.u(float(p["taban_kot"]))
            d = self.u(0.25)
            yuzler = kutu_yuzleri(x0, y0, kot - d, x1, y1, kot)
            a = self.u(0.35)
            nx = max(2, int(round((x1 - x0) / self.u(6.0))) + 1)
            ny = max(2, int(round((y1 - y0) / self.u(6.0))) + 1)
            for i in range(nx):
                for j in range(ny):
                    cx = min(max(x0 + (x1 - x0) * i / (nx - 1), x0 + a), x1 - a)
                    cy = min(max(y0 + (y1 - y0) * j / (ny - 1), y0 + a), y1 - a)
                    yuzler += kutu_yuzleri(cx - a / 2, cy - a / 2, taban,
                                           cx + a / 2, cy + a / 2, kot - d)
            mesh_ekle(self.msp, yuzler, "12-CELIK-PLATFORM")
            self.korkuluk(x0, y0, x1, y1, kot,
                          self.u(float(p.get("korkuluk", 1.1))))

    def korkuluk(self, x0, y0, x1, y1, kot, h):
        kose = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        for seviye in (h, h * 0.5):
            self.msp.add_polyline3d([(x, y, kot + seviye) for x, y in kose],
                                    dxfattribs={"layer": "13-KORKULUK"})
        adim = self.u(3.0)
        for i in range(len(kose) - 1):
            (ax, ay), (bx, by) = kose[i], kose[i + 1]
            n = max(1, int(math.hypot(bx - ax, by - ay) / adim))
            for k in range(n + 1):
                t = k / n
                px_, py_ = ax + (bx - ax) * t, ay + (by - ay) * t
                self.msp.add_line((px_, py_, kot), (px_, py_, kot + h),
                                  dxfattribs={"layer": "13-KORKULUK"})

    # -- sed catilar / koprüler ---------------------------------------------
    def sed_catilar(self):
        for s in self.g["sed_catilar"]:
            x0, y0, x1, y1 = self.dikdortgen(s["px"])
            z0 = self.u(float(s["taban_kot"]))
            h = self.u(float(s["tepe_yuksekligi"]))
            n = int(s["bolme_sayisi"])
            gen = (x1 - x0) / n
            for i in range(n):
                bx0 = x0 + i * gen + gen * 0.08
                bx1 = x0 + (i + 1) * gen - gen * 0.08
                mesh_ekle(self.msp, prizma_yuzleri(
                    [(y0, z0), (y1, z0), (y1, z0 + h)], bx0, bx1), "14-SED-CATI")
                mesh_ekle(self.msp, [[(bx0, y1, z0), (bx1, y1, z0),
                                      (bx1, y1, z0 + h), (bx0, y1, z0 + h)]],
                          "15-SED-CAM")

    def koprular(self):
        for k in self.g["koprular"]:
            x0, y0, x1, y1 = self.dikdortgen(k["px"])
            kot = self.u(float(k["kot"]))
            h = self.u(float(k["yukseklik"]))
            mesh_ekle(self.msp, kutu_yuzleri(x0, y0, kot, x1, y1, kot + h),
                      "16-KOPRU-BORU-HATTI")
            uzun_x = (x1 - x0) > (y1 - y0)
            uz = (x1 - x0) if uzun_x else (y1 - y0)
            n = max(1, int(uz / self.u(6.0)))
            for i in range(n):
                t0, t1 = i / n, (i + 1) / n
                if uzun_x:
                    a = (x0 + (x1 - x0) * t0, y0, kot)
                    b = (x0 + (x1 - x0) * t1, y0, kot + h)
                else:
                    a = (x0, y0 + (y1 - y0) * t0, kot)
                    b = (x0, y0 + (y1 - y0) * t1, kot + h)
                self.msp.add_line(a, b, dxfattribs={"layer": "16-KOPRU-BORU-HATTI"})

    # -- BACA blok tanimi ----------------------------------------------------
    def baca_blogu(self, seri, cap, yuk):
        """Seri + olcu basina tek bir AutoCAD blogu uretir ve yeniden kullanir."""
        ad = "BACA_{}_D{:d}_H{:d}".format(seri, int(round(cap * 1000)),
                                          int(round(yuk * 1000)))
        if ad in self.blok_cache:
            return ad
        katman = self.seri_katman[seri]
        blk = self.doc.blocks.new(ad)
        r = self.u(cap / 2.0)
        H = self.u(yuk)
        kaide_h = self.u(0.40)
        kaide_y = r * 1.70                       # kare kaide yari kenari

        yuzler = []
        # 1) betonarme/celik kaide (cati gecis bileziği)
        yuzler += kutu_yuzleri(-kaide_y, -kaide_y, 0, kaide_y, kaide_y, kaide_h)
        # 2) govde
        yuzler += silindir_yuzleri(0, 0, kaide_h, H - self.u(0.45), r)
        # 3) orta flans bilezigi
        fz = kaide_h + (H - kaide_h) * 0.5
        yuzler += silindir_yuzleri(0, 0, fz - self.u(0.07), fz + self.u(0.07),
                                   r * 1.22, kapak=False)
        # 4) tepe konisi + agiz bilezigi
        yuzler += koni_yuzleri(0, 0, H - self.u(0.45), H - self.u(0.15), r, r * 0.88)
        yuzler += silindir_yuzleri(0, 0, H - self.u(0.15), H, r * 0.95)
        mesh_ekle(blk, yuzler, katman)

        # 5) yuksek bacalarda celik destek ayaklari
        if yuk >= 8.0:
            d = r * 2.6
            tepe = H * 0.55
            for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                mesh_ekle(blk, kutu_yuzleri(
                    min(sx * d, sx * r * 0.9) if sx else -self.u(0.09),
                    min(sy * d, sy * r * 0.9) if sy else -self.u(0.09),
                    0,
                    max(sx * d, sx * r * 0.9) if sx else self.u(0.09),
                    max(sy * d, sy * r * 0.9) if sy else self.u(0.09),
                    self.u(0.18)), katman)
                blk.add_line((sx * d, sy * d, self.u(0.18)),
                             (sx * r, sy * r, tepe), dxfattribs={"layer": katman})

        # 6) oznitelikler -> AutoCAD DATAEXTRACTION ile baca listesi cikarilabilir
        th = self.u(1.2)
        ust = H + self.u(0.8)
        for i, etiket in enumerate(("BACA_KODU", "SERI", "KOT", "YUKSEKLIK", "CAP")):
            a = blk.add_attdef(etiket, (0, 0, ust + i * th * 1.4), height=th,
                               dxfattribs={"layer": "30-BACA-KODU", "style": "ANNOT"})
            a.dxf.invisible = 1
        self.blok_cache[ad] = True
        return ad

    # -- baca yerlesimi ------------------------------------------------------
    def bacalari_yerlestir(self):
        sayac = Counter()
        for b in self.bacalar:
            seri = b["seri"]
            cap = float(b["cap_m"])
            yuk = float(b["yukseklik_m"])
            x, y = self.xy(float(b["px_x"]), float(b["px_y"]))
            kot_m = self.blok_kot.get(b["blok"])
            if kot_m is None:
                raise SystemExit("Bilinmeyen blok: {} (baca {})".format(
                    b["blok"], b["baca_kodu"]))
            z = self.u(kot_m)
            blok_adi = self.baca_blogu(seri, cap, yuk)
            ref = self.msp.add_blockref(blok_adi, (x, y, z),
                                        dxfattribs={"layer": self.seri_katman[seri]})
            ref.add_auto_attribs({
                "BACA_KODU": b["baca_kodu"],
                "SERI": seri,
                "KOT": "+{:.2f}".format(kot_m),
                "YUKSEKLIK": "{:.2f} m".format(yuk),
                "CAP": "DN{:d}".format(int(round(cap * 1000))),
            })
            self.kod_yaz(x, y, z + self.u(yuk), b["baca_kodu"], kot_m, yuk,
                         self.seri_renk[seri])
            self.koordinatlar.append({
                "baca_kodu": b["baca_kodu"], "seri": seri, "sinif": b["sinif"],
                "blok": b["blok"], "dxf_blok_adi": blok_adi,
                "X_m": round(x / self.F, 2), "Y_m": round(y / self.F, 2),
                "cati_kotu_m": round(kot_m, 2),
                "baca_yuksekligi_m": round(yuk, 2),
                "baca_tepe_kotu_m": round(kot_m + yuk, 2),
                "cap_m": round(cap, 2), "aciklama": b["aciklama"]})
            sayac[seri] += 1
        return sayac

    def kod_yaz(self, x, y, z_ust, kod, kot_m, yuk, renk):
        dx, dy, dz = self.u(5.0), self.u(5.0), self.u(2.5)
        tz = z_ust + dz
        self.msp.add_polyline3d([(x, y, z_ust), (x, y, tz), (x + dx, y + dy, tz)],
                                dxfattribs={"layer": "31-KILAVUZ-CIZGI"})
        self.msp.add_text(
            kod, height=self.u(2.4),
            dxfattribs={"layer": "30-BACA-KODU", "style": "ANNOT", "color": renk}
        ).set_placement((x + dx, y + dy + self.u(0.7), tz),
                        align=ezdxf.enums.TextEntityAlignment.LEFT)
        self.msp.add_text(
            "h={:.2f}  tepe +{:.2f}".format(yuk, kot_m + yuk), height=self.u(1.3),
            dxfattribs={"layer": "30-BACA-KODU", "style": "ANNOT", "color": 8}
        ).set_placement((x + dx, y + dy - self.u(1.9), tz),
                        align=ezdxf.enums.TextEntityAlignment.LEFT)

    # -- kuzey oku -----------------------------------------------------------
    def kuzey_oku(self):
        x0, y0, x1, y1 = self.dikdortgen([140, 160, 1950, 1250])
        x, y, L = x1 + self.u(18.0), y1 - self.u(10.0), self.u(14.0)
        self.msp.add_polyline3d([(x, y, 0), (x, y + L, 0)],
                                dxfattribs={"layer": "01-EKSEN"})
        self.msp.add_polyline3d([(x - L * 0.12, y + L * 0.75, 0), (x, y + L, 0),
                                 (x + L * 0.12, y + L * 0.75, 0)],
                                dxfattribs={"layer": "01-EKSEN"})
        self.msp.add_text("K", height=self.u(6.0),
                          dxfattribs={"layer": "01-EKSEN", "style": "ANNOT"}
                          ).set_placement((x, y + L + self.u(4.0), 0),
                                          align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    # -- pafta ---------------------------------------------------------------
    def pafta(self, sayac):
        lay = self.doc.layouts.new("BACA-YERLESIM-PLANI-A1")
        lay.page_setup(size=(841, 594), margins=(10, 10, 10, 10), units="mm")
        W, H = 821, 574
        lay.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True,
                           dxfattribs={"layer": "90-PAFTA"})
        ax, aw, ah = W - 250, 250, 90
        lay.add_lwpolyline([(ax, 0), (ax + aw, 0), (ax + aw, ah), (ax, ah)],
                           close=True, dxfattribs={"layer": "90-PAFTA"})
        for metin, h, dy in [
                ("TOYOTA BOYAHANE - CATI BACALARI 3B MODELI", 6.0, 72),
                ("Baca yerlesim plani / stack layout", 3.2, 62),
                ("Olcek (model): 1 birim = 1 {}".format(self.birim), 3.2, 52),
                ("Toplam baca: {} adet / {} seri".format(
                    sum(sayac.values()), len(sayac)), 3.2, 42),
                ("Kaynak: isaretli havadan gorunus fotografi", 3.0, 32),
                ("Uretim: data/bacalar.csv + src/build_dxf.py", 3.0, 22),
                ("Konumlar fotograftan sayisallastirilmistir - saha teyidi gerekir",
                 2.6, 12)]:
            lay.add_text(metin, height=h,
                         dxfattribs={"layer": "90-PAFTA", "style": "ANNOT"}
                         ).set_placement((ax + 6, dy),
                                         align=ezdxf.enums.TextEntityAlignment.LEFT)
        # seri lejandi
        lx, ly = 8, 8
        lay.add_text("BACA SERILERI", height=4.5,
                     dxfattribs={"layer": "90-PAFTA", "style": "ANNOT"}
                     ).set_placement((lx, ly + 86),
                                     align=ezdxf.enums.TextEntityAlignment.LEFT)
        for i, s in enumerate(self.seriler):
            sut, sat = divmod(i, 10)
            x = lx + sut * 78
            y = ly + 76 - sat * 8
            lay.add_lwpolyline([(x, y), (x + 6, y), (x + 6, y + 4.5), (x, y + 4.5)],
                               close=True, dxfattribs={"layer": "90-PAFTA",
                                                       "color": self.seri_renk[s]})
            lay.add_text("{}  ({} adet)".format(s, sayac.get(s, 0)), height=3.0,
                         dxfattribs={"layer": "90-PAFTA", "style": "ANNOT"}
                         ).set_placement((x + 9, y + 0.6),
                                         align=ezdxf.enums.TextEntityAlignment.LEFT)
        x0, y0, x1, y1 = self.dikdortgen([140, 160, 1950, 1250])
        vp_w, vp_h = W - 20, H - 110
        olcek = min(vp_w / (x1 - x0), vp_h / (y1 - y0)) * 0.95
        lay.add_viewport(center=(W / 2, H - 10 - vp_h / 2), size=(vp_w, vp_h),
                         view_center_point=((x0 + x1) / 2, (y0 + y1) / 2),
                         view_height=vp_h / olcek)

    # -- cikti ---------------------------------------------------------------
    def koordinat_listesi_yaz(self, yol):
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        alanlar = ["baca_kodu", "seri", "sinif", "blok", "dxf_blok_adi", "X_m",
                   "Y_m", "cati_kotu_m", "baca_yuksekligi_m", "baca_tepe_kotu_m",
                   "cap_m", "aciklama"]
        with open(yol, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=alanlar)
            w.writeheader()
            for r in sorted(self.koordinatlar, key=lambda r: r["baca_kodu"]):
                w.writerow(r)

    def kaydet(self, yol):
        if "Layout1" in self.doc.layouts.names():
            self.doc.layouts.delete("Layout1")
        x0, y0, x1, y1 = self.dikdortgen([140, 160, 1950, 1250])
        self.doc.set_modelspace_vport(height=(y1 - y0) * 1.15,
                                      center=((x0 + x1) / 2, (y0 + y1) / 2))
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        self.doc.saveas(yol)


def bacalari_oku(yol):
    with open(yol, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("baca_kodu")]


def main():
    ap = argparse.ArgumentParser(description="Toyota boyahane cati bacalari 3B DXF")
    ap.add_argument("--birim", choices=["m", "mm"], default="m")
    ap.add_argument("--cikti", default=os.path.join(
        KOK, "output", "toyota_boyahane_cati_3d.dxf"))
    args = ap.parse_args()

    with open(GEOMETRI, encoding="utf-8") as f:
        geometri = json.load(f)
    bacalar = bacalari_oku(BACALAR)

    m = CatiModeli(geometri, bacalar, birim=args.birim)
    m.cati_bloklari()
    m.celik_platformlar()
    m.sed_catilar()
    m.koprular()
    sayac = m.bacalari_yerlestir()
    m.kuzey_oku()
    m.pafta(sayac)
    m.kaydet(args.cikti)
    liste = os.path.join(KOK, "output", "baca_koordinat_listesi.csv")
    m.koordinat_listesi_yaz(liste)

    print("DXF yazildi : {}".format(args.cikti))
    print("Birim       : 1 birim = 1 {}".format(args.birim))
    print("Baca        : {} adet / {} seri".format(sum(sayac.values()), len(sayac)))
    print("Seriler     : {}".format(dict(sorted(sayac.items()))))
    print("Liste       : {}".format(liste))


if __name__ == "__main__":
    main()
