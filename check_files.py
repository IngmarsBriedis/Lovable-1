#!/usr/bin/env python3
"""
Pārbauda lejupielādēto failu atrašanās vietu
"""

import os
from pathlib import Path
import json

def check_downloaded_files():
    """Pārbauda kur atrodas lejupielādētie faili"""
    
    print("🔍 Pārbaudu lejupielādēto failu atrašanās vietas...\n")
    
    # Pašreizējā direktorija
    current_dir = Path.cwd()
    print(f"📍 Pašreizējā direktorija: {current_dir}")
    
    # Meklē EIS-Automatic-Download un EIS-XML-Files mapes
    possible_locations = [
        (Path('EIS-Automatic-Download'), Path('EIS-XML-Files')),
        (current_dir / 'EIS-Automatic-Download', current_dir / 'EIS-XML-Files'),
        (current_dir.parent / 'EIS-Automatic-Download', current_dir.parent / 'EIS-XML-Files'),
        (Path.home() / 'Desktop' / 'Ingmars-EIS' / 'EIS-Automatic-Download', 
         Path.home() / 'Desktop' / 'Ingmars-EIS' / 'EIS-XML-Files'),
        (Path.home() / 'Desktop' / 'Ingmars-EIS' / 'python' / 'EIS-Automatic-Download',
         Path.home() / 'Desktop' / 'Ingmars-EIS' / 'python' / 'EIS-XML-Files')
    ]
    
    found = False
    for download_loc, xml_loc in possible_locations:
        if download_loc.exists():
            print(f"\n✅ Atrasta arhīvu direktorija: {download_loc.absolute()}")
            found = True
            
            # Skaita failus
            tar_files = list(download_loc.rglob('*.tar.gz'))
            print(f"   📦 .tar.gz faili: {len(tar_files)}")
            
            # Parāda dažus failus
            if tar_files:
                print("\n   Pirmie arhīva faili:")
                for f in tar_files[:5]:
                    print(f"   - {f.relative_to(download_loc)} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
                    
        if xml_loc.exists():
            print(f"\n✅ Atrasta XML direktorija: {xml_loc.absolute()}")
            
            # Skaita XML failus
            total_xml = 0
            date_dirs = []
            for date_dir in xml_loc.iterdir():
                if date_dir.is_dir():
                    xml_files = list(date_dir.glob('*.xml'))
                    if xml_files:
                        total_xml += len(xml_files)
                        date_dirs.append((date_dir.name, len(xml_files)))
                        
            print(f"   📄 Kopā XML faili: {total_xml}")
            
            if date_dirs:
                print("\n   Datumu mapes:")
                for dir_name, count in sorted(date_dirs, reverse=True)[:10]:
                    print(f"   - {dir_name}: {count} XML faili")
                    
            # Pārbauda metadatus
            metadata_file = download_loc / 'download_metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                print(f"\n   📊 Metadati:")
                print(f"   - Pēdējā atjaunošana: {metadata.get('last_update', 'Nav')}")
                print(f"   - Kopā reģistrēti faili: {metadata.get('total_files', 0)}")
            break
    
    if not found:
        print("\n❌ EIS-Automatic-Download direktorija nav atrasta!")
        print("\nMeklēju šajās vietās:")
        for loc in possible_locations:
            print(f"  - {loc.absolute()}")
            
    # Pārbauda python failu atrašanās vietu
    print(f"\n📂 Python faili atrodas: {current_dir}")
    python_files = ['ftp_downloader_scheduler.py', 'local_procurement_searcher.py', 'app.py']
    for pf in python_files:
        if Path(pf).exists():
            print(f"  ✓ {pf}")
        else:
            print(f"  ✗ {pf} - NAV ATRASTS!")

if __name__ == "__main__":
    check_downloaded_files()
