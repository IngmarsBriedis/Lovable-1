#!/usr/bin/env python3
"""
Atrod kur XML failā atrodas 95052
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import sys

def find_95052(xml_file):
    """Meklē kur atrodas 95052"""
    print(f"Meklēju '95052' failā: {xml_file}\n")
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Izveidojam parent karti
        parent_map = {}
        for parent in root.iter():
            for child in parent:
                parent_map[child] = parent
        
        found_count = 0
        
        for elem in root.iter():
            if elem.text and '95052' in elem.text:
                found_count += 1
                parent = parent_map.get(elem, None)
                parent_tag = parent.tag if parent is not None else 'root'
                
                # Atrod pilnu ceļu
                path = []
                current = elem
                while current is not None:
                    path.append(current.tag)
                    current = parent_map.get(current, None)
                path.reverse()
                
                print(f"ATRASTS #{found_count}:")
                print(f"  Tag: <{elem.tag}>")
                print(f"  Parent: <{parent_tag}>")
                print(f"  Pilns ceļš: {' -> '.join(path)}")
                print(f"  Vērtība: {elem.text.strip()}")
                
                # Parāda kontekstu - blakus elementus
                if parent is not None:
                    print(f"\n  Blakus elementi:")
                    for sibling in list(parent)[:5]:  # Pirmie 5 blakus elementi
                        sibling_text = sibling.text.strip() if sibling.text else '[tukšs]'
                        if len(sibling_text) > 50:
                            sibling_text = sibling_text[:50] + '...'
                        print(f"    <{sibling.tag}>: {sibling_text}")
                
                print("\n" + "="*60 + "\n")
                
        if found_count == 0:
            print("'95052' NAV atrasts šajā failā!")
        else:
            print(f"\nKOPĀ atrasti {found_count} gadījumi")
            
            # Testē extract_notice_info
            print("\n\nKā to redz extract_notice_info:")
            from local_procurement_searcher import LokalaisMekletajs
            
            searcher = LokalaisMekletajs()
            info = searcher.extract_notice_info(root)
            
            print(f"Pasūtītājs: '{info.get('contracting_authority', 'NAV ATRASTS')}'")
            
            if info.get('contracting_authority') == '95052':
                print("❌ PROBLĒMA: 95052 joprojām tiek izmantots kā pasūtītājs!")
                
    except Exception as e:
        print(f"Kļūda: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        # Mēģina atrast failu
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
            print("Lietošana: python3 find_95052.py [ceļš/uz/xml_failu]")
            sys.exit(1)
            
    find_95052(xml_file)
