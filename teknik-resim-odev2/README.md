# 2. Hafta Ödevi – 3 Görünüş (ÖN / SOL YAN / ÜST)

Her parça ayrı bir çizim dosyası olarak hazırlandı (`dxf/Parca1.dxf` … `dxf/Parca6.dxf`).
Görünüşler ISO-E (Avrupa) metoduna göre yerleştirildi: **ÖN** sol üstte, **SOL YAN** ön görünüşün
sağında, **ÜST** ön görünüşün altında. Ölçek 1:1, birim mm.

| Dosya  | Parça (ödev sayfasındaki yeri)                       |
|--------|------------------------------------------------------|
| Parca1 | Sol üst – Ø36/Ø24 göbekli L dirsek                    |
| Parca2 | Orta üst – 70×80×60 kanallı, eğik ayaklı blok         |
| Parca3 | Sol alt – 100×68×50, 45° pahlı blok                   |
| Parca4 | Orta alt – 100 boyunda çatal uçlu parça               |
| Parca5 | Sağ – Ø40/Ø26 göbekli A gövdeli yatak (75×112 taban)  |
| Parca6 | Sağ – Ø50 göbekli, R25 köşeli köşebent (76×126 taban) |

**Bakış yönü:** ÖN görünüş = izometrik resimde sağ-alt yüze bakış; SOL YAN = sol-alt yüze bakış.

## DWG'ye çevirme
1. AutoCAD'de `ParcaX.dxf` dosyasını açın.
2. `SAVEAS` (Farklı Kaydet) → Dosya türü **AutoCAD 2018 Çizimi (*.dwg)** → Kaydet.
3. Altı dosyayı da kaydettikten sonra DWG'leri seçip sağ tık → *Sıkıştırılmış klasöre gönder*.

## Katmanlar
| Katman  | Çizgi        | Kalınlık |
|---------|--------------|----------|
| GORUNEN | Sürekli      | 0.50     |
| GIZLI   | Kesik (gizli)| 0.25     |
| EKSEN   | Noktalı-çizgi| 0.18     |
| YAZI    | –            | 0.25     |

## Resimde ölçüsü verilmeyen yerler için yapılan kabuller
- **Parça 1:** plaka kalınlığı 10, taban kalınlığı 10, plaka–duvar arası boşluk 20, göbek boyu 16, Ø24 delik plakayı da deler.
- **Parça 4:** eğimli geçişler 10 mm (100 − 46 − 44).
- **Parça 5:** taban yüksekliği 25 (125 ölçüsü taban üstünden), gövde kalınlığı 25, gövde üst yayı R23 (R20 + 3),
  tabandaki dikey delik Ø26 kabul edildi.
- **Parça 6:** göbek ekseni taban üstünden 38 (Ø50 göbek tabandan 13 yukarıda), göbek ön yüzü duvardan 38 ileride,
  Ø14 delikler kenarlardan 19 ve ön kenardan 25, kaburga 10 kalınlıkta ve göbek önünden taban ön kenarına iner.

`kaynak/uc_gorunus.py` görünüşleri 3B modelden (OpenCascade gizli çizgi hesabı) üretir; ölçü değiştirmek
gerekirse ilgili `parcaX()` fonksiyonu düzenlenip `python3 kaynak/uc_gorunus.py dxf` çalıştırılır.
