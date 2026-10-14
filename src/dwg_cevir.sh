#!/bin/sh
# DXF -> DWG donusumu (GNU LibreDWG ile)
#
# AutoCAD'in kendi DWG yazicisi olmadigi icin donusum GNU LibreDWG'nin
# "dwgwrite" aracıyla yapilir. Iki onemli nokta:
#   1) LibreDWG yalnizca R2000 formatinda DWG yazabilir (AutoCAD 2000 ve
#      sonrasi acar).
#   2) LibreDWG, R2010 ve ustu DXF dosyalarinin metinlerini bozuyor; bu yuzden
#      donusum icin ara dosya R2004 surumunde uretilir.
#
# Kurulum:
#   git clone --depth 1 https://github.com/LibreDWG/libredwg
#   cd libredwg && git submodule update --init --depth 1
#   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
#   export PATH=$PWD/build:$PATH LD_LIBRARY_PATH=$PWD/build
#
# Kullanim:  sh src/dwg_cevir.sh
set -e
KOK=$(cd "$(dirname "$0")/.." && pwd)
ARA=$(mktemp -d)
trap 'rm -rf "$ARA"' EXIT

python3 "$KOK/src/build_dxf.py" --surum R2004 --cikti "$ARA/m.dxf"
python3 "$KOK/src/build_dxf.py" --surum R2004 --birim mm --cikti "$ARA/mm.dxf"

dwgwrite -I DXF --as r2000 -y -o "$KOK/output/toyota_boyahane_cati_3d.dwg"    "$ARA/m.dxf"
dwgwrite -I DXF --as r2000 -y -o "$KOK/output/toyota_boyahane_cati_3d_mm.dwg" "$ARA/mm.dxf"

echo "DWG dosyalari uretildi:"
ls -la "$KOK/output"/*.dwg
