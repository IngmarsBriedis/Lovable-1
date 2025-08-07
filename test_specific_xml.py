#!/usr/bin/env python3
"""
Testē specifisku XML failu, lai redzētu kāda informācija tiek izvilkta
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import sys

def analyze_xml_structure(xml_file):
    """Analizē XML faila struktūru"""
    print(f"Analizēju failu: {xml_file}\n")
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Izveidojam parent karti
        parent_map = {}
        for parent in root.iter():
            for child in parent:
                parent_map[child] = parent
        
        print("=== XML STRUKTŪRA ===\n")
        
        # Meklē specifiskos elementus
        elements_to_find = {
            'contract_name': [],
            'name': [],
            'code': [],
            'procurement_id': [],
            'cpv': [],
            'authority': [],
            'contracting': []
        }
        
        for elem in root.iter():
            elem_tag = elem.tag.lower()
            parent = parent_map.get(elem, None)
            parent_tag = parent.tag if parent is not None else 'root'
            
            # Meklē contract_name
            if elem_tag == 'contract_name' and elem.text:
                elements_to_find['contract_name'].append({
                    'tag': elem.tag,
                    'text': elem.text.strip(),
                    'parent': parent_tag
                })
                
            # Meklē name tagus
            elif elem_tag == 'name' and elem.text:
                elements_to_find['name'].append({
                    'tag': elem.tag,
                    'text': elem.text.strip()[:100],  # Pirmās 100 rakstzīmes
                    'parent': parent_tag
                })
                
            # Meklē code tagus (CPV)
            elif elem_tag == 'code' and elem.text:
                elements_to_find['code'].append({
                    'tag': elem.tag,
                    'text': elem.text.strip(),
                    'parent': parent_tag
                })
                
            # Meklē procurement_id
            elif elem_tag == 'procurement_id' and elem.text:
                elements_to_find['procurement_id'].append({
                    'tag': elem.tag,
                    'text': elem.text.strip(),
                    'parent': parent_tag
                })
                
            # Meklē CPV saistītus
            elif 'cpv' in elem_tag and elem.text:
                elements_to_find['cpv'].append({
                    'tag': elem.tag,
                    'text': elem.text.strip(),
                    'parent': parent_tag
                })
                
            # Meklē authority
            elif 'authority' in elem_tag and elem.text:
                # Izslēdz authority_id
                if elem_tag != 'authority_id':
                    elements_to_find['authority'].append({
                        'tag': elem.tag,
                        'text': elem.text.strip()[:100],
                        'parent': parent_tag
                    })
                
            # Meklē contracting
            elif 'contracting' in elem_tag and elem.text:
                elements_to_find['contracting'].append({
                    'tag': elem.tag,
                    'text': elem.text.strip()[:100],
                    'parent': parent_tag
                })
        
        # Izvada rezultātus
        print("1. CONTRACT_NAME elementi:")
        if elements_to_find['contract_name']:
            for item in elements_to_find['contract_name']:
                print(f"   <{item['tag']}> (parent: {item['parent']}): {item['text']}")
        else:
            print("   Nav atrasti")
            
        print("\n2. NAME elementi:")
        if elements_to_find['name']:
            for item in elements_to_find['name'][:10]:  # Pirmie 10
                print(f"   <{item['tag']}> (parent: {item['parent']}): {item['text']}")
            if len(elements_to_find['name']) > 10:
                print(f"   ... un vēl {len(elements_to_find['name']) - 10} elementi")
        else:
            print("   Nav atrasti")
            
        print("\n3. CODE elementi (CPV):")
        if elements_to_find['code']:
            for item in elements_to_find['code']:
                if 'cpv' in item['parent'].lower() or len(item['text']) == 8:
                    print(f"   <{item['tag']}> (parent: {item['parent']}): {item['text']}")
        else:
            print("   Nav atrasti")
            
        print("\n4. PROCUREMENT_ID elementi:")
        if elements_to_find['procurement_id']:
            for item in elements_to_find['procurement_id']:
                print(f"   <{item['tag']}> (parent: {item['parent']}): {item['text']}")
        else:
            print("   Nav atrasti")
            
        print("\n5. CPV saistītie elementi:")
        if elements_to_find['cpv']:
            for item in elements_to_find['cpv']:
                print(f"   <{item['tag']}> (parent: {item['parent']}): {item['text']}")
        else:
            print("   Nav atrasti")
            
        print("\n6. AUTHORITY elementi (bez authority_id):")
        if elements_to_find['authority']:
            for item in elements_to_find['authority']:
                # Pārbauda vai nav authority_id
                if item['tag'].lower() != 'authority_id' and item['parent'].lower() != 'authority_id':
                    print(f"   <{item['tag']}> (parent: {item['parent']}): {item['text']}")
        else:
            print("   Nav atrasti")
            
        print("\n7. CONTRACTING elementi:")
        if elements_to_find['contracting']:
            for item in elements_to_find['contracting']:
                print(f"   <{item['tag']}> (parent: {item['parent']}): {item['text']}")
        else:
            print("   Nav atrasti")
            
        # Meklē name pēc type
        print("\n8. NAME elementi pēc TYPE:")
        type_elem_found = False
        names_after_type = []
        for elem in root.iter():
            if elem.tag.lower() == 'type':
                type_elem_found = True
            elif type_elem_found and elem.tag.lower() == 'name' and elem.text:
                names_after_type.append({
                    'tag': elem.tag,
                    'text': elem.text.strip()[:100]
                })
                type_elem_found = False  # Reset lai atrastu nākamo
            elif type_elem_found and elem.tag.lower() == 'short_name' and elem.text:
                names_after_type.append({
                    'tag': elem.tag,
                    'text': elem.text.strip()[:100]
                })
                
        if names_after_type:
            for item in names_after_type:
                print(f"   <{item['tag']}>: {item['text']}")
        else:
            print("   Nav atrasti")
            
        # Testē jaunās funkcijas
        print("\n\n=== TESTĒJU JAUNO EXTRACT_NOTICE_INFO ===\n")
        from local_procurement_searcher import LokalaisMekletajs
        
        searcher = LokalaisMekletajs()
        info = searcher.extract_notice_info(root)
        
        print(f"Nosaukums: {info.get('title', 'NAV ATRASTS')}")
        print(f"Pasūtītājs: {info.get('contracting_authority', 'NAV ATRASTS')}")
        
        # Pārbauda vai nav authority_id
        if 'authority_id' in str(info.get('contracting_authority', '')).lower():
            print("❌ KĻŪDA: Pasūtītājs satur authority_id!")
        elif not info.get('contracting_authority'):
            print("⚠️ BRĪDINĀJUMS: Nav atrasts pasūtītājs!")
        else:
            print("✅ Pasūtītājs atrasts pareizi")
            
        print(f"\nCPV kodi: {', '.join(info.get('cpv_codes', [])) if info.get('cpv_codes') else 'NAV ATRASTI'}")
        print(f"Iepirkuma ID: {info.get('procurement_id', 'NAV ATRASTS')}")
        print(f"Identifikācijas Nr: {info.get('identification_number', 'NAV ATRASTS')}")
        print(f"Vērtība: {info.get('value', 'NAV ATRASTA')}")
        print(f"Termiņš: {info.get('deadline', 'NAV ATRASTS')}")
        
    except Exception as e:
        print(f"Kļūda: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        # Mēģina atrast 768132.xml
        possible_paths = [
            'EIS-XML-Files/*/768132.xml',
            'EIS-XML-Files/29_07_2025/768132.xml',
            '768132.xml'
        ]
        
        xml_file = None
        for pattern in possible_paths:
            files = list(Path('.').glob(pattern))
            if files:
                xml_file = files[0]
                break
                
        if not xml_file:
            print("Lietošana: python3 test_specific_xml.py [ceļš/uz/xml_failu]")
            print("\nVai norādiet konkrētu XML failu, piemēram:")
            print("python3 test_specific_xml.py EIS-XML-Files/29_07_2025/768132.xml")
            sys.exit(1)
            
    analyze_xml_structure(xml_file)
