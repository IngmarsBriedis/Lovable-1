#!/usr/bin/env python3
"""
Skripts FTP servera struktūras pārbaudei
"""

import ftplib
from datetime import datetime

def test_ftp_structure():
    """Pārbauda FTP servera struktūru"""
    ftp_host = 'open.iub.gov.lv'
    
    try:
        # Pieslēdzas serverim
        ftp = ftplib.FTP(ftp_host)
        ftp.login('anonymous', '')
        ftp.encoding = 'utf-8'
        print(f"✓ Veiksmīgi pieslēdzos {ftp_host}")
        
        # Pārbauda root
        print("\n=== ROOT DIREKTORIJA ===")
        ftp.cwd('/')
        files = []
        ftp.retrlines('LIST', lambda x: files.append(x))
        
        print("Atrasti objekti:")
        for f in files[:20]:
            print(f"  {f}")
        
        # Meklē gada mapes
        year_folders = []
        ftp.retrlines('NLST', lambda x: year_folders.append(x))
        years = [f for f in year_folders if f.isdigit() and len(f) == 4]
        years.sort(reverse=True)
        
        if years:
            print(f"\nAtrasti gadi: {years[:5]}")
            
            # Pārbauda 2025. gadu
            test_year = '2025'
            if test_year in years:
                print(f"\n=== {test_year}. GADA STRUKTŪRA ===")
                ftp.cwd(f'/{test_year}')
                
                month_folders = []
                ftp.retrlines('NLST', lambda x: month_folders.append(x))
                print(f"Mēneša mapes: {month_folders[:12]}")
                
                # Pārbauda jūliju
                july_folder = '07_2025'
                if july_folder in month_folders:
                    print(f"\n=== {july_folder} MAPES SATURS ===")
                    ftp.cwd(july_folder)
                    
                    tar_files = []
                    ftp.retrlines('LIST', lambda x: tar_files.append(x))
                    
                    print("Faili:")
                    for f in tar_files[:10]:
                        print(f"  {f}")
                    
                    # Meklē konkrētu datumu
                    test_file = '01_07_2025.tar.gz'
                    file_names = []
                    ftp.retrlines('NLST', lambda x: file_names.append(x))
                    
                    if test_file in file_names:
                        print(f"\n✓ Fails {test_file} atrasts!")
                        
                        # Parāda faila izmēru
                        try:
                            size = ftp.size(test_file)
                            print(f"  Izmērs: {size:,} baiti ({size/1024/1024:.2f} MB)")
                        except:
                            pass
                    else:
                        print(f"\n✗ Fails {test_file} NAV atrasts")
                        print(f"Pieejamie .tar.gz faili:")
                        tar_gz_files = [f for f in file_names if f.endswith('.tar.gz')]
                        for f in tar_gz_files[:5]:
                            print(f"  - {f}")
        
        ftp.quit()
        print("\n✓ Pārbaude pabeigta veiksmīgi")
        
    except Exception as e:
        print(f"\n✗ Kļūda: {e}")
        print("\nIespējamie iemesli:")
        print("- Nepareiza servera adrese")
        print("- Nav interneta savienojuma")
        print("- Servera struktūra ir mainījusies")

if __name__ == "__main__":
    test_ftp_structure()
