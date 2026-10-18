# 3. Ödev – Kesit Görünüşler (AutoCAD)

Her parça ayrı bir çizim dosyası (`dxf/`), antetli çerçeve içinde, ölçek 1:1, ölçüler mm.
Ön görünüş **A-A tam kesit** olarak çizildi; kesit düzlemi diğer görünüşte oklarla ve "A" harfleriyle gösterildi.
Görünüşler hizalı yerleştirildi (ISO-E): üst görünüş ön görünüşün altında, sol yan görünüş sağında.

| Dosya | Parça | Görünüşler | Kağıt |
|-------|-------|------------|-------|
| ParcaA_Catal | Çatallı bağlantı (sayfa 1) | A-A kesiti + Üst | A3 |
| ParcaB_Flansli_Burc | Flanşlı burç (sayfa 2) | A-A kesiti + Üst | A4 |
| ParcaC_Pabuc | Pabuç | A-A kesiti + Sol yan | A4 |
| ParcaD_Yatak_Govdesi | Yatak gövdesi | A-A kesiti + Üst | A3 |

## Katmanlar
GORUNEN (0.5) · GIZLI (kesik) · EKSEN (noktalı-çizgi) · TARAMA (ANSI31, 45°) · OLCU · YAZI ·
KESIT (kesit düzlemi uçları) · CERCEVE

## DWG'ye çevirme
AutoCAD'de dosyayı açın → `SAVEAS` → **AutoCAD 2018 Çizimi (*.dwg)**.

## Notlar / yorumlar
- **Parça A:** perspektifteki "26" ölçüsü, uçtaki R4 kavsinin bittiği yerden alınmış; parça simetrik
  (ayaklar 40-40-40, çatal kolları 30–50 ve 70–90). Çizimde uçtan ölçülen **30** verildi.
  Ø13 delik ekseni tabandan 50; Ø10 deliklerin ağzında 2x45° pah var; deliklerin ayak ortasında olduğu kabul edildi (15 ve 17,5).
- **Parça C (Pabuç):** üst görünüş gerekmediği için ön kesit + sol yan görünüş verildi (en az görünüş).
  Kulak deliği ekseni tabandan 40, kulak R15 ve deliğe eş merkezli. Belirtilmeyen kavisler R3 (not olarak yazıldı).
- **Parça D (Yatak gövdesi):** kesit düzlemi kaburgaları boyuna kestiği için kaburgalar **taranmadı** (kural gereği).
  R50 merkezi küçük göbek ekseninden 20 sağda. 4 adet Ø8 delik (35 x 28 aralıklı, arka-sol delik perspektifte göbeğin
  arkasında kaldığı için görünmüyor). Belirtilmeyen kavisler R2.

`kaynak/kesitli.py` çizimleri 3B modelden üretir (`python3 kaynak/kesitli.py dxf`).
