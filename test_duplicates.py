#!/usr/bin/env python3
"""
Testē dublikātu apstrādi
"""

from local_procurement_searcher import IepirkumuMekletajs
from datetime import datetime, timedelta
import logging

# Logging
logging.basicConfig(level=logging.INFO)

def test_duplicate_handling():
    """Testē dublikātu apstrādi"""
    print("🔍 Testēju dublikātu apstrādi...\n")
    
    # Izveido meklētāju
    searcher = IepirkumuMekletajs()
    
    # Iestatām, lai parādītu visus
    searcher.local_searcher.search_criteria = {
        'keywords': [],
        'cpv_codes': [],
        'exclude_keywords': [],
        'statuses': ['IZSLUDINĀTS'],
        'show_all': True
    }
    
    # Meklē pēdējās 7 dienās
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"Meklēju no {start_date} līdz {end_date}")
    results = searcher.search_date_range(start_date, end_date)
    
    print(f"\n✅ Atrasti {len(results)} unikāli rezultāti\n")
    
    # Analizē dublikātus
    procurement_ids = {}
    identification_numbers = {}
    duplicates_found = 0
    
    for i, result in enumerate(results):
        proc_id = result.get('procurement_id', '')
        ident_num = result.get('identification_number', '')
        
        # Pārbauda procurement_id
        if proc_id:
            if proc_id in procurement_ids:
                duplicates_found += 1
                print(f"❌ DUBLIKĀTS pēc procurement_id: {proc_id}")
                print(f"   Pirmais: {procurement_ids[proc_id]['date']} - {procurement_ids[proc_id]['file']}")
                print(f"   Otrais: {result['date']} - {result.get('file', 'nav')}")
            else:
                procurement_ids[proc_id] = {
                    'index': i,
                    'date': result['date'],
                    'file': result.get('file', 'nav')
                }
                
        # Pārbauda identification_number
        if ident_num and ident_num != proc_id:
            if ident_num in identification_numbers:
                duplicates_found += 1
                print(f"❌ DUBLIKĀTS pēc identification_number: {ident_num}")
                print(f"   Pirmais: {identification_numbers[ident_num]['date']} - {identification_numbers[ident_num]['file']}")
                print(f"   Otrais: {result['date']} - {result.get('file', 'nav')}")
            else:
                identification_numbers[ident_num] = {
                    'index': i,
                    'date': result['date'],
                    'file': result.get('file', 'nav')
                }
    
    if duplicates_found == 0:
        print("✅ Nav atrasti dublikāti - sistēma strādā pareizi!")
    else:
        print(f"\n⚠️ Atrasti {duplicates_found} dublikāti")
        
    # Parāda dažus rezultātus
    print("\n📋 Pirmie 5 rezultāti:")
    for i, r in enumerate(results[:5]):
        print(f"\n{i+1}. {r.get('title', 'Nav nosaukuma')}")
        print(f"   Datums: {r['date']}")
        print(f"   Iepirkuma ID: {r.get('procurement_id', 'nav')}")
        print(f"   Identifikācijas Nr: {r.get('identification_number', 'nav')}")
        print(f"   Fails: {r.get('file', 'nav')}")
        
    # Pārbauda authority_id
    print("\n\n🔍 Pārbaudu authority_id izslēgšanu...")
    authority_ids_found = 0
    for r in results:
        if r.get('id', '').lower() == 'authority_id' or 'authority_id' in str(r.get('id', '')).lower():
            authority_ids_found += 1
            print(f"❌ Atrasts authority_id: {r.get('id')} failā {r.get('file')}")
            
    if authority_ids_found == 0:
        print("✅ Nav atrasti authority_id - sistēma strādā pareizi!")

if __name__ == "__main__":
    test_duplicate_handling()
