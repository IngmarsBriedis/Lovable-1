#!/bin/bash

# Iepirkumu meklētāja sistēmas palaišanas skripts

echo "🚀 Iepirkumu meklētāja sistēma"
echo "============================="
echo ""

# Pārbauda Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nav atrasts!"
    exit 1
fi

# Izveido virtuālo vidi
if [ ! -d "venv" ]; then
    echo "📦 Izveidoju virtuālo vidi..."
    python3 -m venv venv
fi

# Aktivizē virtuālo vidi
source venv/bin/activate

# Instalē atkarības
echo "📦 Pārbaudu atkarības..."
pip install -q flask flask-cors schedule

# Izveido nepieciešamās mapes
mkdir -p EIS-Automatic-Download
mkdir -p EIS-XML-Files
mkdir -p rezultati

# Pārbauda konfigurāciju
if [ ! -f "config.json" ]; then
    echo "📝 Izveidoju noklusējuma konfigurāciju..."
    cat > config.json << EOF
{
  "search_criteria": {
    "keywords": ["sporta inventārs", "treniņ", "nometn"],
    "cpv_codes": ["37400000", "92600000"],
    "exclude_keywords": ["ēdināšan"]
  }
}
EOF
fi

# Izvēlas darbību
echo ""
echo "Izvēlieties darbību:"
echo "1) 🌐 Palaist Web UI (meklē lokālajos failos)"
echo "2) 📥 Lejupielādēt jaunākos failus no FTP"
echo "3) 🔄 Palaist automātisko lejupielādētāju (katru dienu 5:00)"
echo "4) 📊 Parādīt sistēmas statusu"
echo "5) 🧪 Testēt lokālo failu meklēšanu"
echo ""

read -p "Izvēle (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🌐 Palaižu Web UI..."
        echo "📍 Atveriet pārlūku: http://127.0.0.1:5050"
        echo ""
        
        # Pārbauda vai ir lokālie faili
        if [ ! -f "EIS-Automatic-Download/download_metadata.json" ]; then
            echo "⚠️  BRĪDINĀJUMS: Nav atrasti lokālie faili!"
            echo "   Vispirms palaidiet lejupielādētāju (opcija 2)"
            echo ""
        fi
        
        # Atver pārlūku Mac
        if [[ "$OSTYPE" == "darwin"* ]]; then
            (sleep 3 && open http://127.0.0.1:5050) &
        fi
        
        python3 app.py
        ;;
        
    2)
        echo ""
        echo "📥 Lejupielādēju jaunākos failus..."
        python3 ftp_downloader_scheduler.py
        ;;
        
    3)
        echo ""
        echo "🔄 Palaižu automātisko lejupielādētāju..."
        echo "   Lejupielāde notiks katru dienu plkst. 5:00"
        echo "   Lai apturētu, spiediet Ctrl+C"
        echo ""
        python3 ftp_downloader_scheduler.py --schedule
        ;;
        
    4)
        echo ""
        echo "📊 Sistēmas statuss:"
        echo ""
        python3 ftp_downloader_scheduler.py --status
        
        # Parāda arī citu informāciju
        echo ""
        if [ -d "EIS-Automatic-Download" ]; then
            echo "📁 Lokālo arhīvu mape: EIS-Automatic-Download"
            file_count=$(find EIS-Automatic-Download -name "*.tar.gz" 2>/dev/null | wc -l)
            echo "   Kopā .tar.gz faili: $file_count"
        fi
        
        if [ -d "EIS-XML-Files" ]; then
            echo "📁 XML failu mape: EIS-XML-Files"
            xml_count=$(find EIS-XML-Files -name "*.xml" 2>/dev/null | wc -l)
            echo "   Kopā XML faili: $xml_count"
            
            # Parāda pēdējās dienas
            echo "   Pieejamie datumi:"
            for dir in $(ls -d EIS-XML-Files/*/ 2>/dev/null | sort -r | head -5); do
                dir_name=$(basename "$dir")
                file_count=$(find "$dir" -name "*.xml" 2>/dev/null | wc -l)
                echo "     - $dir_name: $file_count XML faili"
            done
        fi
        
        if [ -d "rezultati" ]; then
            result_count=$(find rezultati -name "*.json" 2>/dev/null | wc -l)
            echo "📋 Saglabātie rezultāti: $result_count"
        fi
        ;;
        
    5)
        echo ""
        echo "🧪 Testēju lokālo failu meklēšanu..."
        
        # Izveido testa skriptu
        cat > test_local_search.py << 'EOF'
#!/usr/bin/env python3
from local_procurement_searcher import IepirkumuMekletajs
from datetime import datetime, timedelta

# Izveido meklētāju
searcher = IepirkumuMekletajs()

# Meklē pēdējās 3 dienās
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

print(f"Meklēju no {start_date} līdz {end_date}...")
results = searcher.search_date_range(start_date, end_date)

print(f"\nAtrasti {len(results)} rezultāti")
for i, r in enumerate(results[:5]):
    print(f"\n{i+1}. {r.get('title', 'Nav nosaukuma')}")
    print(f"   Datums: {r.get('date')}")
    print(f"   Atslēgvārdi: {', '.join(r.get('matched_keywords', []))}")
EOF
        
        python3 test_local_search.py
        rm test_local_search.py
        ;;
        
    *)
        echo "❌ Nepareiza izvēle!"
        exit 1
        ;;
esac
