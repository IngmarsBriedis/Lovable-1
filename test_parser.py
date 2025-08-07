#!/usr/bin/env python3
"""
Tests XML parsētājam ar reālu failu
"""

import xml.etree.ElementTree as ET

def test_xml_parser():
    """Testē XML parsēšanu ar 768142.xml"""
    
    try:
        # Parsē XML failu
        tree = ET.parse('768142.xml')
        root = tree.getroot()
        
        print("=== XML STRUKTŪRAS ANALĪZE ===\n")
        
        # Pamatinformācija
        print("1. PAMATINFORMĀCIJA:")
        elements_to_find = [
            'procurement_code',
            'procurement_id', 
            'name',
            'contract_name',
            'pub_date',
            'publication_date',
            'id',
            'price',
            'currency',
            'authority_name',
            'address'
        ]
        
        for elem_name in elements_to_find:
            elem = root.find('.//' + elem_name)
            if elem is not None and elem.text:
                print(f"  {elem_name}: {elem.text.strip()}")
                
        # CPV kodi
        print("\n2. CPV KODI:")
        for elem in root.iter():
            if elem.tag == 'code' and elem.text:
                print(f"  code: {elem.text}")
                # Meklē parent elementu
                parent = elem
                for _ in range(3):  # Meklē 3 līmeņus augšup
                    parent_map = {c: p for p in tree.iter() for c in p}
                    if parent in parent_map:
                        parent = parent_map[parent]
                        if 'cpv' in parent.tag.lower():
                            print(f"    (parent: {parent.tag})")
                            break
                            
        # Datumi
        print("\n3. DATUMI:")
        date_elements = ['pub_date', 'approval_date', 'publication_date', 'decision_date']
        for date_elem in date_elements:
            elem = root.find('.//' + date_elem)
            if elem is not None and elem.text:
                print(f"  {date_elem}: {elem.text}")
                
        # Uzvarētājs
        print("\n4. UZVARĒTĀJA INFORMĀCIJA:")
        winner_list = root.find('.//winner_list')
        if winner_list is not None:
            for winner in winner_list.findall('.//winner'):
                winner_name = winner.find('.//winner_name')
                winner_reg = winner.find('.//winner_reg_num')
                winner_addr = winner.find('.//winner_address')
                
                if winner_name is not None:
                    print(f"  Nosaukums: {winner_name.text}")
                if winner_reg is not None:
                    print(f"  Reģ. nr.: {winner_reg.text}")
                if winner_addr is not None:
                    print(f"  Adrese: {winner_addr.text}")
                    
        # Visa XML struktūra (pirmie 2 līmeņi)
        print("\n5. XML STRUKTŪRA (pirmie 2 līmeņi):")
        def print_structure(elem, level=0, max_level=2):
            if level <= max_level:
                indent = "  " * level
                text_preview = elem.text[:30] + "..." if elem.text and len(elem.text) > 30 else elem.text
                print(f"{indent}{elem.tag}: {text_preview if text_preview else ''}")
                for child in elem:
                    print_structure(child, level + 1, max_level)
                    
        print_structure(root)
        
    except Exception as e:
        print(f"Kļūda: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_xml_parser()
