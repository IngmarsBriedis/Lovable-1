#!/usr/bin/env python3
"""
Testa skripts lokāla tar.gz faila apstrādei un XML satura meklēšanai
"""

import tarfile
import os
import xml.etree.ElementTree as ET
import tempfile
import shutil
import json
from pathlib import Path

def test_local_tar_file(tar_path):
    """Testē lokālu tar.gz failu"""
    print(f"=== Testēju failu: {tar_path} ===\n")
    
    # Pārbauda vai fails eksistē
    if not os.path.exists(tar_path):
        print(f"❌ Fails {tar_path} nav atrasts!")
        print(f"Meklēju šajās vietās:")
        print(f"  - {os.path.abspath(tar_path)}")
        print(f"  - ../EIS-Manual-Download/{os.path.basename(tar_path)}")
        
        # Mēģina atrast failu
        alt_path = f"../EIS-Manual-Download/{os.path.basename(tar_path)}"
        if os.path.exists(alt_path):
            tar_path = alt_path
            print(f"✓ Atradu failu: {os.path.abspath(tar_path)}")
        else:
            return
    
    print(f"✓ Fails atrasts: {os.path.abspath(tar_path)}")
    print(f"  Izmērs: {os.path.getsize(tar_path):,} baiti\n")
    
    # Izveido pagaidu direktoriju
    temp_dir = tempfile.mkdtemp()
    print(f"Pagaidu direktorija: {temp_dir}\n")
    
    try:
        # Atver un izpako tar.gz
        print("1. ATARHIVĒJU TAR.GZ FAILU...")
        with tarfile.open(tar_path, 'r:gz') as tar:
            # Parāda saturu
            print("Faili arhīvā:")
            members = tar.getmembers()
            for member in members:
                print(f"  - {member.name} ({member.size:,} baiti)")
            
            # Izpako visu
            tar.extractall(temp_dir)
            print(f"\n✓ Izpakoti {len(members)} faili\n")
        
        # Meklē XML failus
        print("2. MEKLĒJU XML FAILUS...")
        xml_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.xml'):
                    xml_path = os.path.join(root, file)
                    xml_files.append(xml_path)
                    print(f"  ✓ Atrasts XML: {file}")
                    print(f"    Ceļš: {xml_path}")
                    print(f"    Izmērs: {os.path.getsize(xml_path):,} baiti")
        
        if not xml_files:
            print("  ❌ Nav atrasti XML faili!")
            return
            
        print(f"\n✓ Atrasti {len(xml_files)} XML faili\n")
        
        # Apstrādā katru XML
        for xml_path in xml_files:
            print(f"3. ANALIZĒJU XML: {os.path.basename(xml_path)}")
            analyze_xml_content(xml_path)
            print("\n" + "="*80 + "\n")
            
            # Meklē ar kritērijiem
            print("4. MEKLĒJU PĒC KRITĒRIJIEM...")
            search_with_criteria(xml_path)
            
    except Exception as e:
        print(f"❌ Kļūda: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Tīra pagaidu failus
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n✓ Pagaidu faili iztīrīti")


def analyze_xml_content(xml_path):
    """Analizē XML faila saturu"""
    try:
        # Mēģina parsēt XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        print(f"  Root elements: {root.tag}")
        if root.attrib:
            print(f"  Root atribūti: {root.attrib}")
        
        # Parāda struktūru
        print("\n  XML struktūra (pirmie 5 līmeņi):")
        show_xml_structure(root, "", max_depth=5)
        
        # Savāc visu tekstu
        print("\n  TEKSTA SATURS:")
        all_text = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                all_text.append(elem.text.strip())
        
        # Parāda pirmos 10 teksta fragmentus
        print(f"  Atrasti {len(all_text)} teksta fragmenti")
        for i, text in enumerate(all_text[:10]):
            if len(text) > 100:
                text = text[:100] + "..."
            print(f"    [{i+1}] {text}")
        
        if len(all_text) > 10:
            print(f"    ... un vēl {len(all_text) - 10} fragmenti")
            
        # Meklē specifiskus elementus
        print("\n  SPECIFISKI ELEMENTI:")
        search_elements = ['title', 'name', 'description', 'cpv', 'value', 'authority']
        
        for search_tag in search_elements:
            found_elements = []
            for elem in root.iter():
                if search_tag.lower() in elem.tag.lower():
                    if elem.text and elem.text.strip():
                        found_elements.append((elem.tag, elem.text.strip()))
            
            if found_elements:
                print(f"\n  Elements '{search_tag}':")
                for tag, text in found_elements[:3]:
                    if len(text) > 80:
                        text = text[:80] + "..."
                    print(f"    <{tag}>: {text}")
                    
    except Exception as e:
        print(f"  ❌ Kļūda parsējot XML: {e}")


def show_xml_structure(elem, indent="", max_depth=5, current_depth=0):
    """Parāda XML struktūru"""
    if current_depth >= max_depth:
        return
        
    # Parāda elementu
    attrs = ""
    if elem.attrib:
        attrs = " " + str(elem.attrib)
    
    text = ""
    if elem.text and elem.text.strip():
        text = elem.text.strip()
        if len(text) > 50:
            text = text[:50] + "..."
        text = f" = '{text}'"
    
    print(f"{indent}<{elem.tag}>{attrs}{text}")
    
    # Parāda bērnus
    for child in elem:
        show_xml_structure(child, indent + "  ", max_depth, current_depth + 1)


def search_with_criteria(xml_path):
    """Meklē XML failā ar kritērijiem"""
    # Ielādē kritērijus no config.json
    criteria = {
        "keywords": [
            "sport", "sporta", "inventār", "treniņ", "fitness",
            "basketbol", "volejbol", "futbol", "stadion",
            "iepirkum", "piegād", "pakalp", "noma", "palešu"
        ],
        "cpv_codes": ["37400000", "37410000", "37420000", "92600000"]
    }
    
    print(f"\n  Meklēšanas kritēriji:")
    print(f"    Atslēgvārdi: {', '.join(criteria['keywords'][:5])}...")
    print(f"    CPV kodi: {', '.join(criteria['cpv_codes'])}")
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Savāc visu tekstu
        all_text = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                all_text.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                all_text.append(elem.tail.strip())
                
        full_text = ' '.join(all_text).lower()
        
        # Meklē atslēgvārdus
        print("\n  ATRASTI ATSLĒGVĀRDI:")
        found_keywords = []
        for kw in criteria['keywords']:
            if kw.lower() in full_text:
                found_keywords.append(kw)
                # Atrod kontekstu
                pos = full_text.find(kw.lower())
                start = max(0, pos - 50)
                end = min(len(full_text), pos + len(kw) + 50)
                context = full_text[start:end]
                print(f"    ✓ '{kw}' atrasts:")
                print(f"      ...{context}...")
        
        if not found_keywords:
            print("    ❌ Nav atrasti atslēgvārdi")
            
        # Meklē CPV kodus
        print("\n  ATRASTI CPV KODI:")
        found_cpv = []
        for elem in root.iter():
            if elem.text:
                for cpv in criteria['cpv_codes']:
                    if cpv in elem.text:
                        found_cpv.append(cpv)
                        print(f"    ✓ CPV {cpv} atrasts: <{elem.tag}> = {elem.text}")
                        
        if not found_cpv:
            print("    ❌ Nav atrasti CPV kodi")
            
        # Rezultāts
        print(f"\n  REZULTĀTS:")
        if found_keywords or found_cpv:
            print(f"    ✅ ATBILST KRITĒRIJIEM!")
            print(f"    Atrasti {len(found_keywords)} atslēgvārdi un {len(found_cpv)} CPV kodi")
        else:
            print(f"    ❌ NEATBILST kritērijiem")
            
    except Exception as e:
        print(f"  ❌ Kļūda meklējot: {e}")


if __name__ == "__main__":
    import sys
    
    # Noklusējuma fails
    default_file = "26_07_2025.tar.gz"
    
    # Ja norādīts cits fails
    if len(sys.argv) > 1:
        tar_file = sys.argv[1]
    else:
        tar_file = default_file
        
    print("Lokālā TAR.GZ faila testēšanas skripts")
    print("=====================================\n")
    
    # Mēģina dažādas vietas
    possible_paths = [
        tar_file,
        f"../EIS-Manual-Download/{tar_file}",
        f"EIS-Manual-Download/{tar_file}",
        f"./{tar_file}"
    ]
    
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            test_local_tar_file(path)
            found = True
            break
            
    if not found:
        print(f"❌ Nevarēju atrast failu '{tar_file}'")
        print("\nMēģināju šajās vietās:")
        for path in possible_paths:
            print(f"  - {os.path.abspath(path)}")
        print("\nLietošana:")
        print(f"  python3 {sys.argv[0]} [ceļš/uz/failu.tar.gz]")
