# Toyota Boyahane Çatısı — Bacalar 3B AutoCAD Modeli

İşaretli havadan görünüş fotoğrafından üretilmiş **parametrik 3B çatı + baca modeli**.
Fotoğrafta kırmızı ile işaretlenmiş noktaların **tamamı çatı bacasıdır**; yanlarındaki
el yazısı numaralar da **baca kodlarıdır**. Her baca 3B katı model olarak çatıya
yerleştirilmiş, kodu hem yazı hem de AutoCAD özniteliği olarak işlenmiştir.

**77 baca / 21 seri** modellenmiştir:

| Seri | Adet | Seri | Adet | Seri | Adet |
|---|---|---|---|---|---|
| 110 | 5 | 200 | 4 | 320 | 4 |
| 116 | 2 | 220 | 1 | 330 | 7 |
| 120 | 2 | 240 | 3 | 340 | 2 |
| 130 | 3 | 250 | 7 | P | 5 |
| 160 | 1 | 260 | 7 | RTO (R70) | 2 |
| 170 | 1 | 280 | 3 | DİĞER | 3 |
| 180 | 4 | 190 | 4 | ETİKETSİZ | 7 |

## Çıktılar (`output/`)

| Dosya | Açıklama |
|---|---|
| `toyota_boyahane_cati_3d.dxf` | **Ana dosya.** AutoCAD 2018 (R2018) DXF, 1 birim = 1 **metre** |
| `toyota_boyahane_cati_3d_mm.dxf` | Aynı model, 1 birim = 1 **milimetre** |
| `baca_koordinat_listesi.csv` | Her bacanın kodu, X/Y koordinatı, çatı kotu, yüksekliği, **tepe kotu**, çapı |
| `onizleme_izometrik.png` / `_2.png` | İzometrik önizlemeler |
| `onizleme_ustten.png` | Üstten baca yerleşim planı + kodlar (fotoğrafla karşılaştırmak için) |
| `onizleme_detay_dogu_blok.png` | Doğu blok / RTO bölgesi baca detayı |

AutoCAD'de: `3DORBIT` ile döndürün, `VSCURRENT` → `Conceptual`, `ZOOM` → `E`.
Hazır **`BACA-YERLESIM-PLANI-A1`** paftası üstten görünüş + seri lejantı + antet içerir.

## Baca modeli

Her baca şu parçalardan oluşur: çatı geçiş kaidesi (bilezik) → gövde silindiri →
orta flanş bileziği → konik daralma → ağız bileziği. 8 m ve üzeri bacalarda ayrıca
**çelik destek ayakları** modellenmiştir.

Her baca gerçek bir **AutoCAD bloğu** olarak yerleştirilmiştir ve şu öznitelikleri
taşır: `BACA_KODU`, `SERI`, `KOT`, `YUKSEKLIK`, `CAP`. Böylece AutoCAD'de
`DATAEXTRACTION` komutuyla **baca listesi doğrudan tabloya dökülebilir**.
Öznitelikler görünmez ayarlıdır; ekranda görünen kodlar `30-BACA-KODU`
katmanındaki yazılardır (her kodun yanında `h=` yüksekliği ve `tepe +` kotu yazar).

**Her seri ayrı katmandadır** (`20-BACA-110`, `20-BACA-250`, `20-BACA-330` …).
Böylece AutoCAD'de `LAYISO` / `LAYFRZ` ile tek bir seriyi izole edebilirsiniz.

## Katmanlar

| Katman | İçerik |
|---|---|
| `20-BACA-<seri>` | **Bacalar** — her seri ayrı katman ve ayrı renk (21 adet) |
| `30-BACA-KODU` / `31-KILAVUZ-CIZGI` | Baca kodu yazıları ve kılavuz çizgileri |
| `00-SINIR` / `01-EKSEN` | Bina sınırları (2B referans), kuzey oku |
| `05-CEPHE` / `10-CATI-DOSEME` / `11-PARAPET` | Bina kabuğu, çatı döşemeleri, parapetler |
| `12-CELIK-PLATFORM` / `13-KORKULUK` | 330 serisi çelik platformu, ayaklar, korkuluklar |
| `14-SED-CATI` / `15-SED-CAM` | Sed (kuzey ışık) çatısı ve camları |
| `16-KOPRU-BORU-HATTI` | Köprü / boru hattı bantları |
| `90-PAFTA` | Pafta çerçevesi ve antet (kağıt alanı) |

## Modeli yeniden üretmek / düzeltmek

```bash
pip install ezdxf matplotlib
python3 src/build_dxf.py                    # metre birimli DXF
python3 src/build_dxf.py --birim mm --cikti output/toyota_boyahane_cati_3d_mm.dxf
python3 src/onizleme.py                     # PNG önizlemeler
```

Model tamamen `data/` klasöründeki iki dosyadan üretilir — DXF'i elle düzeltmek
yerine bu dosyaları düzeltip betiği tekrar çalıştırın:

- **`data/bacalar.csv`** — her satır bir baca:
  `baca_kodu, seri, px_x, px_y, blok, sinif, cap_m, yukseklik_m, aciklama`.
  Bir bacanın **kodunu, çapını veya yüksekliğini** değiştirmek = o satırdaki
  hücreyi değiştirmek. Yeni baca eklemek = yeni satır eklemek.
- **`data/cati_geometri.json`** — çatı blokları, kotlar, platformlar, sed çatı,
  köprüler ve **ölçek kalibrasyonu**.

### Ölçeği gerçek değere oturtmak (önemli)

`data/cati_geometri.json` → `kalibrasyon.metre_bolu_piksel` = **0.16575**

Bu değer, *ana bloğun doğu–batı genişliği 300.00 m* kabulüyle hesaplanmıştır.
Sahadan **tek bir gerçek ölçü** geldiğinde sadece bu sayıyı güncelleyin — tüm model
ve tüm baca konumları birlikte ölçeklenir.
Hesap: `yeni_değer = gerçek_uzunluk_m / o_uzunluğun_piksel_değeri`.

### Koordinat sistemi

Model `(0,0)` = ana bloğun **güneybatı köşesi**; X doğu, Y kuzey, Z yukarı.
`px_x` / `px_y`, fotoğrafın düzeltilmiş 2000×1500 piksellik çerçevesinden okunmuştur.

## Kabuller ve doğrulanması gerekenler

Model **tek bir el işaretli fotoğraftan** çıkarıldı; ölçülü proje kullanılmadı.
Aşağıdakiler mühendislik kabulüdür, saha teyidi gerekir:

1. **Ölçek** — yukarıda anlatıldığı gibi tek parametreyle düzeltilir.
2. **Baca yükseklikleri ve çapları** — fotoğrafta bu bilgi yok. Üç sınıf kullanıldı:
   - `STANDART` — Ø0.80 m, çatıdan **6.00 m** yüksek (73 adet)
   - `BUYUK` — Ø1.10 m, **8.00 m** (fotoğrafta büyük işaretli 260.2 ve 260.5)
   - `RTO` — Ø1.60 m, **12.00 m** (W/B R70 ve SB R70)
   Gerçek değerler `data/bacalar.csv` → `cap_m` / `yukseklik_m` sütunlarından girilir.
3. **Çatı kotları** (+10.00 … +17.50) fotoğraftaki gölge ve kademelerden tahmindir;
   `data/cati_geometri.json` → `kot` alanlarından düzeltilir. Baca tepe kotu =
   çatı kotu + baca yüksekliği olarak hesaplanır (`baca_koordinat_listesi.csv`).
4. **Okunamayan / şüpheli baca kodları** (CSV'de `aciklama` sütununda işaretli):
   - `330.8` — fotoğrafta 330.7 de olabilir
   - `190.3` — fotoğrafta "20.3" gibi okunuyor, 190 serisine göre tamamlandı
   - `260.2B` — 260.2 veya 160.2; aynı numara iki yerde görünüyor
   - `280.1B` — ikinci bir "280.1" etiketi var
   - `130.1` — "130.1" ve "130.4" üst üste yazılmış
   - `P.260.X` — "P.?.?" okunamadı
   - `P.260.1` — fotoğrafta üzeri çizili
   - `ETIKETSIZ-D1…D3`, `ETIKETSIZ-E1…E3`, `ETIKETSIZ-G1` — işaretli ama kodu
     yazılmamış 7 baca
5. Fotoğraftaki **"Tozsuz/Tozunsuz"**, **"Charge X"** ve **"Fosfat eski sigara odası
   bacası"** notları, okunduğu gibi birer baca olarak modele alınmıştır (`DIGER` serisi).

Kaynak fotoğraflar tesise ait olduğu için depoya eklenmedi; istenirse
`data/referans_foto/` altına konulabilir.
