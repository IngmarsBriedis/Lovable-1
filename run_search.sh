#!/bin/bash

# Iepirkumu meklētāja palaišanas skripts

# Pārbauda vai Python ir instalēts
if ! command -v python3 &> /dev/null; then
    echo "Python3 nav atrasts. Lūdzu instalējiet Python 3.7 vai jaunāku versiju."
    exit 1
fi

# Izveido virtuālo vidi, ja tā neeksistē
if [ ! -d "venv" ]; then
    echo "Izveidoju virtuālo vidi..."
    python3 -m venv venv
fi

# Aktivizē virtuālo vidi
source venv/bin/activate

# Instalē nepieciešamās bibliotēkas
echo "Instalēju nepieciešamās bibliotēkas..."
pip install schedule

# Izvēlas darbības režīmu
if [ "$1" == "--schedule" ]; then
    echo "Palaižu plānotāju - meklēšana notiks katru dienu norādītajā laikā..."
    python3 ftp_procurement_searcher.py --schedule
elif [ "$1" == "--help" ]; then
    echo "Lietošana:"
    echo "  ./run_search.sh           - Veic vienreizēju meklēšanu"
    echo "  ./run_search.sh --schedule - Palaiž ikdienas plānotāju"
    echo "  ./run_search.sh --help     - Parāda šo palīdzību"
else
    echo "Veicu vienreizēju meklēšanu..."
    python3 ftp_procurement_searcher.py
fi

# Deaktivizē virtuālo vidi
deactivate
