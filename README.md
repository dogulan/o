# Toyota Boyahane Çatısı — 3B AutoCAD Modeli

İşaretli havadan görünüş fotoğrafından üretilmiş, **parametrik 3B çatı modeli**.
Fotoğraftaki tüm el yazısı ekipman etiketleri (110.x, 250.x, 330.x, RTO'lar, bacalar…)
modele 3B nesne + AutoCAD özniteliği olarak işlenmiştir.

## Çıktılar (`output/`)

| Dosya | Açıklama |
|---|---|
| `toyota_boyahane_cati_3d.dxf` | **Ana dosya.** AutoCAD 2018 (R2018) DXF, 1 birim = 1 **metre** |
| `toyota_boyahane_cati_3d_mm.dxf` | Aynı model, 1 birim = 1 **milimetre** |
| `ekipman_koordinat_listesi.csv` | Her ekipmanın model koordinatı (X, Y, Z) ve blok adı |
| `onizleme_izometrik.png` / `_2.png` | İzometrik önizlemeler (AutoCAD açmadan kontrol için) |
| `onizleme_ustten.png` | Üstten görünüş + etiketler (fotoğrafla karşılaştırmak için) |
| `onizleme_detay_dogu_blok.png` | Doğu blok (fırın / RTO bölgesi) detayı |

DXF'i AutoCAD'de açtıktan sonra: `3DORBIT` ile döndürün, `VSCURRENT` → `Conceptual`
veya `Shaded` görsel stilini seçin, `ZOOM` → `E` ile modeli ekrana sığdırın.
`CATI-PLANI-A1` adlı hazır A1 paftası, üstten görünüş + lejant + antet içerir.

## Modelde ne var

- **10 çatı bloğu** (ayrı kotlarda döşeme + parapet + cephe kabuğu)
- **Çelik teknik platform** (330 serisi üniteler) + merdiven kulesi + korkuluklar
- **Sed (kuzey ışık) çatısı** — doğu blokta 12 gözlü, cam yüzeyleri ayrı katmanda
- **2 adet köprü / boru hattı bandı**
- **77 adet ekipman**: 45 çatı aspiratörü, 17 klima santrali, 7 yıkayıcı kule,
  6 baca, 2 RTO ünitesi (W/B R70 ve SB R70)

Her ekipman gerçek bir **AutoCAD bloğu** olarak yerleştirilmiştir ve şu öznitelikleri
taşır: `ETIKET`, `TIP`, `KOT`. Böylece AutoCAD'de `DATAEXTRACTION` (veri çıkarma)
komutuyla ekipman listesi doğrudan tabloya dökülebilir. Öznitelikler görünmez
ayarlıdır; ekranda görünen etiketler `30-ETIKET` katmanındaki yazılardır.

## Katmanlar

| Katman | İçerik |
|---|---|
| `00-SINIR` | Bina sınırları (2B referans, z=0) |
| `01-EKSEN` | Kuzey oku ve yardımcı eksenler |
| `05-CEPHE` | Cepheler (zeminden çatı altına) |
| `10-CATI-DOSEME` | Çatı döşemeleri |
| `11-PARAPET` | Parapet duvarları |
| `12-CELIK-PLATFORM` / `13-KORKULUK` | Çelik platform, ayaklar, korkuluklar |
| `14-SED-CATI` / `15-SED-CAM` | Sed çatı makasları ve cam yüzeyleri |
| `16-KOPRU-BORU-HATTI` | Köprü / boru hattı bantları |
| `20-EKIPMAN-FAN` | Çatı aspiratörleri (kırmızı) |
| `21-EKIPMAN-AHU` | Klima santralleri / galeri üniteleri (mavi) |
| `22-EKIPMAN-BACA` | Bacalar, P serisi çıkışlar (sarı) |
| `23-EKIPMAN-RTO` | RTO üniteleri (mor) |
| `24-EKIPMAN-YIKAYICI` | 330 serisi yıkayıcı kuleler (camgöbeği) |
| `30-ETIKET` / `31-KILAVUZ-CIZGI` | Etiketler ve kılavuz çizgileri |
| `90-PAFTA` | Pafta çerçevesi ve antet (kağıt alanı) |

## Modeli yeniden üretmek / düzeltmek

```bash
pip install ezdxf matplotlib
python3 src/build_dxf.py                    # metre birimli DXF
python3 src/build_dxf.py --birim mm --cikti output/toyota_boyahane_cati_3d_mm.dxf
python3 src/onizleme.py                     # PNG önizlemeler
```

Model tamamen `data/` klasöründeki iki dosyadan üretilir — DXF'i elle düzenlemek
yerine bu dosyaları düzeltip betiği tekrar çalıştırmak yeterlidir:

- **`data/ekipman.csv`** — her satır bir ekipman: etiket, konum (`px_x`, `px_y`),
  bulunduğu blok, tip (`FAN` / `AHU` / `BACA` / `RTO` / `YIKAYICI`) ve boyutlar.
  Yanlış okunmuş bir numarayı düzeltmek = o satırdaki `etiket` hücresini değiştirmek.
- **`data/cati_geometri.json`** — çatı blokları, kotlar, platformlar, sed çatı,
  köprüler ve **ölçek kalibrasyonu**.

### Ölçeği gerçek değere oturtmak (önemli)

`data/cati_geometri.json` → `kalibrasyon.metre_bolu_piksel` = **0.16575**

Bu değer, *ana bloğun doğu–batı genişliği 300.00 m* kabulüyle hesaplanmıştır.
Sahadan **tek bir gerçek ölçü** (örneğin bina genişliği veya iki aks arası)
geldiğinde sadece bu sayıyı güncelleyin — tüm model, tüm ekipman konumları ve
mesafeler birlikte ölçeklenir. Hesap: `yeni_değer = gerçek_uzunluk_m / o_uzunluğun_piksel_değeri`.

### Koordinat sistemi

- Model `(0,0)` = ana bloğun **güneybatı köşesi**; X ekseni doğu, Y ekseni kuzey, Z yukarı.
- `px_x` / `px_y` değerleri, fotoğrafın düzeltilmiş 2000×1500 piksellik çerçevesinden
  okunmuştur (y ekseni aşağı doğru). Dönüşüm `src/build_dxf.py` içindeki `xy()` fonksiyonundadır.

## Kabuller ve doğrulanması gerekenler

Bu model **tek bir el işaretli fotoğraftan** çıkarıldı; ölçülü mimari proje
kullanılmadı. Aşağıdakiler mühendislik kabulüdür, saha/proje teyidi gerekir:

1. **Ölçek** — yukarıda anlatıldığı gibi tek parametreyle düzeltilir.
2. **Kotlar** — çatı kotları (+10.00 … +17.50) fotoğraftaki gölge ve kademelerden
   tahmin edilmiştir; `data/cati_geometri.json` → `kot` alanlarından düzeltilir.
3. **Ekipman boyutları** — fan Ø1.10 m, klima santrali 4.00×2.50 m, baca Ø0.80 m,
   RTO 10.00×5.00 m tipik değerlerdir; gerçek ekipman kataloğuyla güncellenmelidir.
4. **Ekipman tipleri** — galeri üzerindeki 250/190/170/160 serisi klima santrali,
   diğerleri çatı aspiratörü kabul edilmiştir.
5. **Okunamayan / şüpheli etiketler** (CSV'de `aciklama` sütununda da işaretli):
   - `330.8` — fotoğrafta 330.7 de olabilir
   - `190.3` — fotoğrafta "20.3" gibi okunuyor, 190 serisine göre tamamlandı
   - `260.2B` — 260.2 veya 160.2; aynı numara iki yerde görünüyor
   - `280.1B` — ikinci bir "280.1" etiketi var
   - `130.1` — "130.1" ve "130.4" üst üste yazılmış
   - `P.260.X` — "P.?.?" okunamadı
   - `P.260.1` — fotoğrafta üzeri çizili
   - `ETIKETSIZ-D1…D3`, `ETIKETSIZ-E1…E3`, `ETIKETSIZ-G1` — işaretli ama numarasız 7 nokta
6. Fotoğraftaki **"Tozsuz/Tozunsuz"**, **"Charge X"** ve **"Fosfat eski sigara odası
   bacası"** notları, okunduğu gibi birer ekipman olarak modele alınmıştır.

Kaynak fotoğraflar tesise ait olduğu için depoya eklenmedi; istenirse
`data/referans_foto/` altına konulabilir.
