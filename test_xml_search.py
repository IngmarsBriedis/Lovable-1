#!/usr/bin/env python3
"""
Testē XML failu meklēšanu
"""

from local_procurement_searcher import LokalaisMekletajs
from pathlib import Path
import logging

# Logging
logging.basicConfig(level=logging.INFO)

def test_xml_search():
    """Testē XML meklēšanu"""
    print("🔍 Testēju XML meklēšanu...\n")
    
    # Izveido meklētāju
    searcher = LokalaisMekletajs()
    
    # Pārbauda vai ir XML faili
    xml_dir = Path('EIS-XML-Files')
    if not xml_dir.exists():
        print("❌ Nav atrasta EIS-XML-Files direktorija!")
        return
        
    # Atrod pirmo XML failu testēšanai
    xml_files = list(xml_dir.rglob('*.xml'))
    if not xml_files:
        print("❌ Nav atrasti XML faili!")
        return
        
    print(f"✅ Atrasti {len(xml_files)} XML faili\n")
    
    # Testē pirmo failu
    test_file = xml_files[0]
    print(f"Testēju failu: {test_file}")
    
    try:
        # Iestatām, lai parādītu visus
        searcher.search_criteria = {
            'keywords': [],
            'cpv_codes': [],
            'exclude_keywords': [],
            'statuses': ['IZSLUDINĀTS'],
            'show_all': True
        }
        
        results = searcher.search_xml(test_file)
        
        if results:
            print(f"\n✅ Veiksmīgi apstrādāts!")
            result = results[0]
            print(f"  Nosaukums: {result.get('title', 'Nav')}")
            print(f"  Statuss: {result.get('status', 'Nav')}")
            print(f"  ID: {result.get('xml_id', 'Nav')}")
        else:
            print("\n⚠️ Fails apstrādāts, bet neatbilst kritērijiem")
            
    except Exception as e:
        print(f"\n❌ Kļūda: {e}")
        import traceback
        traceback.print_exc()
        
    # Testē datumu diapazonu
    print("\n\nTestēju datumu diapazonu...")
    try:
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"Meklēju no {start_date} līdz {end_date}")
        results = searcher.search_date_range(start_date, end_date)
        
        print(f"\n✅ Atrasti {len(results)} rezultāti")
        if results:
            print("\nPirmie 3 rezultāti:")
            for i, r in enumerate(results[:3]):
                print(f"\n{i+1}. {r.get('title', 'Nav nosaukuma')}")
                print(f"   Statuss: {r.get('status')}")
                print(f"   Datums: {r.get('date')}")
                
    except Exception as e:
        print(f"\n❌ Kļūda datumu meklēšanā: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_xml_search()
