#!/usr/bin/env python3
"""
FTP failu automātiskais lejupielādētājs
Pieslēdzas FTP serverim katru dienu plkst. 5:00 un lejupielādē jaunākos failus
"""

import ftplib
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import time
import shutil
import tarfile
import hashlib

# Logging konfigurācija
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ftp_downloader.log'),
        logging.StreamHandler()
    ]
)

class FTPDownloader:
    def __init__(self):
        self.ftp_host = 'open.iub.gov.lv'
        self.ftp_user = 'anonymous'
        self.ftp_pass = ''
        self.download_dir = Path('EIS-Automatic-Download')
        self.download_dir.mkdir(exist_ok=True)
        self.xml_dir = Path('EIS-XML-Files')  # Direktorija atarhivētiem XML failiem
        self.xml_dir.mkdir(exist_ok=True)
        self.metadata_file = self.download_dir / 'download_metadata.json'
        self.days_to_download = 90  # Lejupielādē pēdējo 90 dienu failus
        self.days_to_keep = 90  # Glabā failus 90 dienas
        
    def connect_ftp(self):
        """Pieslēdzas FTP serverim"""
        try:
            self.ftp = ftplib.FTP(self.ftp_host)
            self.ftp.login(self.ftp_user, self.ftp_pass)
            self.ftp.encoding = 'utf-8'
            logging.info(f"Veiksmīgi pieslēdzos {self.ftp_host}")
            return True
        except Exception as e:
            logging.error(f"Kļūda pieslēdzoties FTP: {e}")
            return False
            
    def disconnect_ftp(self):
        """Atvieno FTP savienojumu"""
        try:
            self.ftp.quit()
        except:
            pass
            
    def get_dates_to_download(self):
        """Atgriež datumus, kuriem jālejupielādē faili"""
        dates = []
        today = datetime.now()
        
        for i in range(self.days_to_download):
            date = today - timedelta(days=i)
            dates.append({
                'year': date.strftime('%Y'),
                'month': date.strftime('%m'),
                'day': date.strftime('%d'),
                'full': date.strftime('%Y-%m-%d')
            })
            
        return dates
        
    def download_file(self, remote_path, local_path):
        """Lejupielādē failu no FTP"""
        try:
            # Izveido direktoriju, ja neeksistē
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {remote_path}', f.write)
            
            # Saglabā faila metadata
            file_size = os.path.getsize(local_path)
            logging.info(f"Lejupielādēts: {remote_path} ({file_size:,} baiti)")
            return True
            
        except Exception as e:
            logging.error(f"Kļūda lejupielādējot {remote_path}: {e}")
            return False
            
    def load_metadata(self):
        """Ielādē lejupielāžu metadatus"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {'downloads': {}, 'last_update': None}
        
    def save_metadata(self, metadata):
        """Saglabā lejupielāžu metadatus"""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            
    def is_file_downloaded(self, file_key, metadata):
        """Pārbauda vai fails jau ir lejupielādēts"""
        if file_key in metadata['downloads']:
            # Pārbauda vai lokālais fails eksistē
            local_path = Path(metadata['downloads'][file_key]['local_path'])
            if local_path.exists():
                return True
        return False
        
    def extract_tar_gz_files(self, tar_path, date_folder):
        """Atarhivē tar.gz failu un saglabā XML failus datuma mapē"""
        xml_date_dir = self.xml_dir / date_folder
        xml_date_dir.mkdir(exist_ok=True)
        
        try:
            with tarfile.open(tar_path, 'r:gz') as tar:
                # Izvelk tikai XML failus
                xml_members = [m for m in tar.getmembers() if m.name.endswith('.xml')]
                
                for member in xml_members:
                    # Drošības pārbaude - izvairās no path traversal
                    if os.path.isabs(member.name) or ".." in member.name:
                        logging.warning(f"Izlaižu potenciāli bīstamu failu: {member.name}")
                        continue
                        
                    # Izvelk XML failu ar drošības filtru (Python 3.12+)
                    try:
                        # Mēģina izmantot jauno filter parametru
                        tar.extract(member, xml_date_dir, filter='data')
                    except TypeError:
                        # Vecākās Python versijās filter nav pieejams
                        tar.extract(member, xml_date_dir)
                    
                    # Pārvieto uz pareizo vietu (ja ir subdirektorijas)
                    extracted_path = xml_date_dir / member.name
                    if extracted_path.exists() and extracted_path.parent != xml_date_dir:
                        final_path = xml_date_dir / os.path.basename(member.name)
                        shutil.move(str(extracted_path), str(final_path))
                        
                logging.info(f"Atarhivēti {len(xml_members)} XML faili no {os.path.basename(tar_path)}")
                return len(xml_members)
                
        except Exception as e:
            logging.error(f"Kļūda atarhivējot {tar_path}: {e}")
            return 0
            
    def download_date_files(self, date_info, metadata):
        """Lejupielādē visus failus konkrētam datumam"""
        downloaded_count = 0
        extracted_count = 0
        year_path = f"/{date_info['year']}"
        month_folder = f"{date_info['month']}_{date_info['year']}"
        date_folder = f"{date_info['day']}_{date_info['month']}_{date_info['year']}"
        
        try:
            # Navigē uz mēneša mapi
            self.ftp.cwd(year_path)
            self.ftp.cwd(month_folder)
            
            # Iegūst failu sarakstu
            files = []
            self.ftp.retrlines('NLST', lambda x: files.append(x))
            
            # Filtrē tikai .tar.gz failus
            tar_files = [f for f in files if f.endswith('.tar.gz')]
            
            logging.info(f"Datumam {date_info['full']} atrasti {len(tar_files)} arhīva faili")
            
            for tar_file in tar_files:
                # Nosaka lokālo ceļu
                local_path = self.download_dir / date_info['year'] / month_folder / tar_file
                
                # Pārbauda vai fails jau eksistē
                if local_path.exists():
                    logging.debug(f"Fails {tar_file} jau eksistē, izlaižu lejupielādi")
                    
                    # Pārbauda vai XML faili ir atarhivēti
                    xml_date_dir = self.xml_dir / date_folder
                    if not xml_date_dir.exists() or len(list(xml_date_dir.glob('*.xml'))) == 0:
                        # Atarhivē esošo failu
                        logging.info(f"Atarhivēju esošo failu {tar_file}")
                        extracted = self.extract_tar_gz_files(local_path, date_folder)
                        extracted_count += extracted
                        
                        # Atjaunina metadatus
                        file_key = f"{date_info['full']}/{tar_file}"
                        if file_key not in metadata['downloads']:
                            metadata['downloads'][file_key] = {
                                'local_path': str(local_path),
                                'download_time': datetime.now().isoformat(),
                                'date': date_info['full'],
                                'size': os.path.getsize(local_path),
                                'xml_extracted': extracted,
                                'xml_folder': str(self.xml_dir / date_folder)
                            }
                    continue
                
                # Lejupielādē failu
                if self.download_file(tar_file, local_path):
                    downloaded_count += 1
                    
                    # Uzreiz atarhivē XML failus
                    extracted = self.extract_tar_gz_files(local_path, date_folder)
                    extracted_count += extracted
                    
                    # Atjaunina metadatus
                    file_key = f"{date_info['full']}/{tar_file}"
                    metadata['downloads'][file_key] = {
                        'local_path': str(local_path),
                        'download_time': datetime.now().isoformat(),
                        'date': date_info['full'],
                        'size': os.path.getsize(local_path),
                        'xml_extracted': extracted,
                        'xml_folder': str(self.xml_dir / date_folder)
                    }
                    
            # Atgriežas uz root
            self.ftp.cwd('/')
            
        except Exception as e:
            logging.warning(f"Kļūda apstrādājot {date_info['full']}: {e}")
            
        logging.info(f"Lejupielādēti {downloaded_count} jauni faili, atarhivēti {extracted_count} XML faili")
        return downloaded_count
        
    def cleanup_old_files(self, metadata, days_to_keep=90):
        """Dzēš vecos failus (vecākus par 90 dienām)"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        files_to_remove = []
        
        for file_key, file_info in metadata['downloads'].items():
            download_time = datetime.fromisoformat(file_info['download_time'])
            if download_time < cutoff_date:
                # Dzēš lokālo tar.gz failu
                local_path = Path(file_info['local_path'])
                if local_path.exists():
                    local_path.unlink()
                    logging.info(f"Dzēsts vecs tar.gz: {local_path}")
                    
                # Dzēš XML mapi
                xml_folder = file_info.get('xml_folder')
                if xml_folder and Path(xml_folder).exists():
                    shutil.rmtree(xml_folder)
                    logging.info(f"Dzēsta XML mape: {xml_folder}")
                    
                files_to_remove.append(file_key)
                
        # Noņem no metadatiem
        for file_key in files_to_remove:
            del metadata['downloads'][file_key]
            
        logging.info(f"Dzēsti {len(files_to_remove)} veci faili (vecāki par {days_to_keep} dienām)")
        return len(files_to_remove)
        
    def run_download(self):
        """Galvenā lejupielādes funkcija"""
        logging.info("=== Sāku automātisko lejupielādi ===")
        logging.info(f"Lokālo failu direktorija: {self.download_dir.absolute()}")
        
        # Ielādē metadatus
        metadata = self.load_metadata()
        
        if not self.connect_ftp():
            return
            
        total_downloaded = 0
        dates = self.get_dates_to_download()
        
        for date in dates:
            logging.info(f"Pārbaudu {date['full']}...")
            downloaded = self.download_date_files(date, metadata)
            total_downloaded += downloaded
            
        self.disconnect_ftp()
        
        # Tīra vecos failus
        deleted_count = self.cleanup_old_files(metadata)
        
        # Atjaunina pēdējās lejupielādes laiku
        metadata['last_update'] = datetime.now().isoformat()
        metadata['total_files'] = len(metadata['downloads'])
        
        # Saglabā metadatus
        self.save_metadata(metadata)
        
        logging.info(f"=== Lejupielāde pabeigta ===")
        logging.info(f"Lejupielādēti jauni faili: {total_downloaded}")
        logging.info(f"Dzēsti veci faili: {deleted_count}")
        logging.info(f"Kopā lokāli: {metadata['total_files']} faili")
        
    def schedule_daily_download(self, run_time="05:00"):
        """Ieplāno ikdienas lejupielādi"""
        logging.info(f"Ieplānoju ikdienas lejupielādi plkst. {run_time}")
        
        # Veic pirmo lejupielādi uzreiz
        self.run_download()
        
        # Ieplāno ikdienas lejupielādi
        schedule.every().day.at(run_time).do(self.run_download)
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Pārbauda katru minūti
            
    def get_download_status(self):
        """Atgriež lejupielādes statusu"""
        metadata = self.load_metadata()
        
        status = {
            'last_update': metadata.get('last_update'),
            'total_files': metadata.get('total_files', 0),
            'files_by_date': {}
        }
        
        # Grupē failus pēc datuma
        for file_info in metadata['downloads'].values():
            date = file_info['date']
            if date not in status['files_by_date']:
                status['files_by_date'][date] = 0
            status['files_by_date'][date] += 1
            
        return status


if __name__ == "__main__":
    import sys
    
    downloader = FTPDownloader()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # Palaiž plānotāju
        downloader.schedule_daily_download()
    elif len(sys.argv) > 1 and sys.argv[1] == '--status':
        # Parāda statusu
        status = downloader.get_download_status()
        print(f"\nLejupielādes statuss:")
        print(f"Pēdējā atjaunošana: {status['last_update']}")
        print(f"Kopā faili: {status['total_files']}")
        print(f"\nFaili pa datumiem:")
        for date, count in sorted(status['files_by_date'].items(), reverse=True):
            print(f"  {date}: {count} faili")
    else:
        # Veic vienreizēju lejupielādi
        downloader.run_download()
