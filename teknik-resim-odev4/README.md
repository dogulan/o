# 7. Hafta Antetli Resim Ödevi – Kesit Görünüşler

Her parça ayrı bir DXF dosyası; **A4 dikey antetli kağıt**, ölçülü, bir görünüşü **A-A tam kesit**.
Görünüşler ISO-E (Avrupa) metoduna göre hizalı: üst görünüş ön görünüşün altında, sol yan görünüş sağında.
Kesit düzlemi ilgili görünüşte oklar ve "A" harfleriyle gösterildi.

| Dosya | Görünüşler | Kesit düzlemi | Ölçek |
|-------|------------|---------------|-------|
| Parca1_Halkali_Dikme | Ön + A-A (sol yan) + Üst | Simetri düzlemi (halka, kanal, gövde) | 1:1 |
| Parca2_Catalli_Kosebent | A-A (ön) + Üst | Flanş / delik ekseni | 1:1 |
| Parca3_Kanalli_Govde | A-A (ön) + Üst | Orta düzlem (2 delik, göbek, kanal) | 1:1 |
| Parca4_Dikme | Ön + A-A (sol yan) + Üst | Simetri düzlemi (Ø50, kanal, V oluk) | 1:2 (140 boy A4'e 1:1 sığmaz) |

DWG için: AutoCAD'de aç → `SAVEAS` → AutoCAD 2018 Çizimi (*.dwg). 1:2 çizim, model alanında 1:2 ölçekli çerçeve ile
hazırlandı (yazdırırken ölçek 1:2).

## Yorumlar / kabuller
- **Parça 1:** halka ve gövdesi (8 genişlik) 10 derinlikte; Ø24 delik duvarı da deler; kanal merkezleri 30 aralıklı
  (uçlar R5); delikler kenardan 10. Üst görünüş, taban deliklerinin yerini göstermek için gerekli.
- **Parça 2:** R20 flanş merkezi bloğun ön yüzünde (duvardan 35); flanş tabandan 5 yüksek, blok içinde 5 derin havşa
  ("5 5" ölçüsü). 4xR3 delikler R15 daire üzerinde 45°'de.
- **Parça 3:** üst yüz 60, uçlar 10 yükseklikten eğimli; delikler arası 68 göbeğe simetrik (14 ve 82); cep 30 genişlik,
  tabanı 22'de, göbekten 5 geride bitiyor.
- **Parça 4:** resimde en belirsiz parça. Dikme 20 kalınlık (12 + 8), ön dikey kenarları 5x45° pahlı; altta 8x10 boşaltma
  kanalı; üst başlık 25 derinlik, arkası R10; üstte 30 genişlik 15 derinlik V oluk; Ø50 delik ekseni tabandan 50;
  taban ön köşeleri R20, 20 genişlik kanal (merkezler 35 aralık).

`kaynak/hafta7.py` çizimleri 3B modelden üretir: `python3 kaynak/hafta7.py dxf`
