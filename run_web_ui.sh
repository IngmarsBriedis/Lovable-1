#!/bin/bash

# Web UI palaišanas skripts

echo "🚀 Palaižu Iepirkumu meklētāja Web UI..."

# Pārbauda vai Python ir instalēts
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nav atrasts. Lūdzu instalējiet Python 3.7 vai jaunāku versiju."
    exit 1
fi

# Izveido virtuālo vidi, ja tā neeksistē
if [ ! -d "venv" ]; then
    echo "📦 Izveidoju virtuālo vidi..."
    python3 -m venv venv
fi

# Aktivizē virtuālo vidi
source venv/bin/activate

# Instalē nepieciešamās bibliotēkas
echo "📦 Instalēju nepieciešamās bibliotēkas..."
pip install flask flask-cors schedule

# Atver pārlūku (Mac specifisks)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Pagaida 3 sekundes un atver pārlūku
    (sleep 3 && open http://localhost:5050) &
fi

# Palaiž Flask serveri
echo "✅ Serveris gatavs!"
echo "📍 Atveriet pārlūku: http://localhost:5050"
echo "   Vai izmantojiet search_ui.html failu tieši"
echo ""
echo "⏹  Lai apturētu serveri, spiediet Ctrl+C"
echo ""

python3 app.py
