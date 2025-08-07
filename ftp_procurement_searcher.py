#!/usr/bin/env python3
"""
FTP Iepirkumu datu meklētājs
Pieslēdzas open.iub.gov.lv FTP serverim un meklē iepirkumu datus
"""

import ftplib
import os
import tarfile
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import tempfile
import shutil
import logging
import json
from pathlib import Path
import schedule
import time
import re

# Logging konfigurācija
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iepirkumi_search.log'),
        logging.StreamHandler()
    ]
)

class IepirkumuMekletajs:
    def __init__(self, config_file='config.json'):
        """Inicializē meklētāju ar konfigurāciju"""
        self.ftp_host = 'open.iub.gov.lv'
        self.ftp_user = 'anonymous'
        self.ftp_pass = ''
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = Path('rezultati')
        self.results_dir.mkdir(exist_ok=True)
        
        # Ielādē meklēšanas kritērijus
        self.load_config(config_file)
        
    def load_config(self, config_file):
        """Ielādē meklēšanas kritērijus no konfigurācijas faila"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                self.search_criteria = self.config.get('search_criteria', {})
                self.days_to_check = self.config.get('days_to_check', 1)
        except FileNotFoundError:
            logging.warning(f"Konfigurācijas fails {config_file} nav atrasts. Izmantoju noklusējuma kritērijus.")
            self.create_default_config(config_file)
            
    def create_default_config(self, config_file):
        """Izveido noklusējuma konfigurāciju"""
        default_config = {
            "search_criteria": {
                "keywords": [
                    "sporta inventārs",
                    "sporta preces",
                    "treniņ",
                    "nometn",
                    "sporta pakalpojum",
                    "fitness",
                    "vingrošan",
                    "basketbol",
                    "volejbol",
                    "futbol",
		    "iegāde",
		    "paleš"
                ],
                "cpv_codes": [
                    "37400000",  # Sporta preces un inventārs
                    "37410000",  # Āra sporta inventārs
                    "37420000",  # Fitnesa inventārs
                    "92600000",  # Sporta pakalpojumi
                    "92610000",  # Sporta objektu darbības pakalpojumi
                    "92620000"   # Ar sportu saistīti pakalpojumi
                ],
                "exclude_keywords": [
                    "ēdināšan"
                ]
            },
            "days_to_check": 7,
            "check_time": "09:00"
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        self.config = default_config
        self.search_criteria = default_config['search_criteria']
        self.days_to_check = default_config['days_to_check']
        
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
            
    def get_recent_dates(self):
        """Atgriež pēdējo dienu datumus pārbaudei"""
        dates = []
        today = datetime.now()
        
        for i in range(self.days_to_check):
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
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {remote_path}', f.write)
            return True
        except Exception as e:
            logging.error(f"Kļūda lejupielādējot {remote_path}: {e}")
            return False
            
    def extract_and_search_tar_gz(self, tar_gz_path):
        """Atarhivē tar.gz failu un meklē XML datos"""
        results = []
        
        try:
            # Atarhivē tar.gz
            with tarfile.open(tar_gz_path, 'r:gz') as tar:
                tar.extractall(self.temp_dir)
                
            # Meklē XML failus
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    if file.endswith('.xml'):
                        xml_path = os.path.join(root, file)
                        matches = self.search_xml(xml_path)
                        if matches:
                            results.extend(matches)
                            
        except Exception as e:
            logging.error(f"Kļūda apstrādājot {tar_gz_path}: {e}")
            
        return results
        
    def normalize_latvian_text(self, text):
        """Normalizē latviešu tekstu meklēšanai (noņem locījumus, diakritiskās zīmes)"""
        if not text:
            return ""
            
        # Aizstāj latviešu diakritiskās zīmes ar pamatvarianti
        replacements = {
            'ā': 'a', 'č': 'c', 'ē': 'e', 'ģ': 'g', 
            'ī': 'i', 'ķ': 'k', 'ļ': 'l', 'ņ': 'n', 
            'š': 's', 'ū': 'u', 'ž': 'z',
            'Ā': 'A', 'Č': 'C', 'Ē': 'E', 'Ģ': 'G',
            'Ī': 'I', 'Ķ': 'K', 'Ļ': 'L', 'Ņ': 'N',
            'Š': 'S', 'Ū': 'U', 'Ž': 'Z'
        }
        
        for latvian, ascii in replacements.items():
            text = text.replace(latvian, ascii)
            
        return text.lower()
        
    def create_word_variations(self, word):
        """Izveido vārda variācijas ar dažādiem locījumiem"""
        word_lower = word.lower()
        variations = {word_lower}
        
        # Latviešu valodas tipiskās galotnes
        endings = ['s', 'a', 'as', 'am', 'ā', 'ām', 'i', 'u', 'us', 'os', 'es', 
                  'em', 'ēm', 'is', 'im', 'ī', 'iem', 'ēs', 'e', 'ē', 'ei',
                  'ai', 'ais', 'ās', 'ajā', 'ajam', 'ajai', 'ajo', 'ajās',
                  'ajiem', 'ajām', 'ajos', 'ums', 'umam', 'umu', 'umos',
                  'šana', 'šanas', 'šanu', 'šanai', 'tājs', 'tāja', 'tāju',
                  'nieks', 'nieka', 'nieku', 'niekiem', 'ība', 'ības', 'ību']
        
        # Ģenerē variācijas
        for ending in endings:
            # Pievieno galotni
            variations.add(word_lower + ending)
            
            # Ja vārds beidzas ar kādu galotni, mēģina to nomainīt
            for e in endings:
                if word_lower.endswith(e) and len(word_lower) > len(e) + 2:
                    base = word_lower[:-len(e)]
                    variations.add(base)
                    variations.add(base + ending)
        
        # Pievieno normalizēto versiju
        normalized = self.normalize_latvian_text(word)
        variations.add(normalized)
        
        return variations
        
    def text_contains_keyword(self, text, keyword):
        """Pārbauda vai tekstā ir atslēgvārds ar locījumu atbalstu"""
        text_lower = text.lower()
        text_normalized = self.normalize_latvian_text(text)
        
        # Izveido atslēgvārda variācijas
        keyword_variations = self.create_word_variations(keyword)
        
        # Pārbauda katru variāciju
        for variation in keyword_variations:
            # Meklē kā atsevišķu vārdu (ar robežām)
            import re
            pattern = r'\b' + re.escape(variation) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
                
            # Meklē arī normalizētajā tekstā
            pattern_norm = r'\b' + re.escape(self.normalize_latvian_text(variation)) + r'\b'
            if re.search(pattern_norm, text_normalized, re.IGNORECASE):
                return True
                
        # Ja atslēgvārds ir vairāku vārdu frāze
        if ' ' in keyword:
            words = keyword.split()
            # Pārbauda vai visi vārdi ir tekstā (jebkurā secībā un locījumā)
            all_found = True
            for word in words:
                word_found = False
                word_variations = self.create_word_variations(word)
                for variation in word_variations:
                    pattern = r'\b' + re.escape(variation) + r'\b'
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        word_found = True
                        break
                if not word_found:
                    all_found = False
                    break
            if all_found:
                return True
                
        return False
        
    def search_xml(self, xml_path):
        """Meklē XML failā pēc kritērijiem"""
        matches = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Savāc visu teksta saturu
            text_parts = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    text_parts.append(elem.text.strip())
                if elem.tail and elem.tail.strip():
                    text_parts.append(elem.tail.strip())
                    
            text_content = ' '.join(text_parts)
            
            # Pārbauda atslēgvārdus ar locījumu atbalstu
            matched_keywords = []
            for kw in self.search_criteria.get('keywords', []):
                if self.text_contains_keyword(text_content, kw):
                    matched_keywords.append(kw)
                    
            keyword_found = len(matched_keywords) > 0
            
            # Pārbauda izslēgtos vārdus
            excluded = False
            for ex in self.search_criteria.get('exclude_keywords', []):
                if self.text_contains_keyword(text_content, ex):
                    excluded = True
                    logging.debug(f"Izslēgts {xml_path} - atrasts '{ex}'")
                    break
            
            # Meklē CPV kodus (tie parasti nav ar locījumiem)
            cpv_found = False
            found_cpv_codes = []
            for elem in root.iter():
                if elem.text:
                    for cpv in self.search_criteria.get('cpv_codes', []):
                        if cpv in elem.text:
                            cpv_found = True
                            found_cpv_codes.append(cpv)
                            
            if (keyword_found or cpv_found) and not excluded:
                # Izvelk pamatinformāciju
                notice_info = self.extract_notice_info(root)
                notice_info['file'] = os.path.basename(xml_path)
                notice_info['matched_keywords'] = matched_keywords
                notice_info['found_cpv_codes'] = found_cpv_codes
                
                # Saglabā kontekstu
                notice_info['context_snippets'] = self.extract_context_snippets(text_content, matched_keywords)
                
                matches.append(notice_info)
                logging.info(f"Atrasts: {xml_path} - atslēgvārdi: {matched_keywords}, CPV: {found_cpv_codes}")
                
        except Exception as e:
            logging.error(f"Kļūda lasot XML {xml_path}: {e}")
            
        return matches
        
    def extract_context_snippets(self, text, keywords, context_length=100):
        """Izvelk teksta fragmentus ap atrastajiem atslēgvārdiem"""
        snippets = []
        text_lower = text.lower()
        
        for kw in keywords:
            # Meklē visas atslēgvārda pozīcijas tekstā
            kw_variations = self.create_word_variations(kw)
            
            for variation in kw_variations:
                import re
                pattern = r'\b' + re.escape(variation) + r'\b'
                for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                    start = max(0, match.start() - context_length)
                    end = min(len(text), match.end() + context_length)
                    snippet = text[start:end]
                    
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(text):
                        snippet = snippet + "..."
                        
                    snippets.append({
                        'keyword': kw,
                        'variation': variation,
                        'context': snippet
                    })
                    
                    # Pievieno tikai dažus piemērus katram atslēgvārdam
                    if len([s for s in snippets if s['keyword'] == kw]) >= 2:
                        break
                        
        return snippets
        
    def extract_notice_info(self, root):
        """Izvelk pamatinformāciju no paziņojuma"""
        info = {
            'title': '',
            'contracting_authority': '',
            'cpv_codes': [],
            'value': '',
            'deadline': '',
            'notice_type': '',
            'id': ''
        }
        
        # Šeit jāpielāgo atbilstoši faktiskajai XML struktūrai
        # Pagaidām izmantoju vispārīgu pieeju
        for elem in root.iter():
            if 'title' in elem.tag.lower() and elem.text:
                info['title'] = elem.text
            elif 'authority' in elem.tag.lower() and elem.text:
                info['contracting_authority'] = elem.text
            elif 'cpv' in elem.tag.lower() and elem.text:
                info['cpv_codes'].append(elem.text)
            elif 'value' in elem.tag.lower() and elem.text:
                info['value'] = elem.text
            elif 'deadline' in elem.tag.lower() and elem.text:
                info['deadline'] = elem.text
            elif 'notice' in elem.tag.lower() and 'type' in elem.tag.lower() and elem.text:
                info['notice_type'] = elem.text
            elif 'id' in elem.tag.lower() and elem.text and not info['id']:
                info['id'] = elem.text
                
        return info
        
    def check_ftp_structure(self):
        """Pārbauda un izpēta FTP struktūru"""
        logging.info("Pārbaudu FTP servera struktūru...")
        
        try:
            # Parāda root direktoriju
            self.ftp.cwd('/')
            files = []
            self.ftp.retrlines('LIST', lambda x: files.append(x))
            
            logging.info("Root direktorijā:")
            for f in files[:10]:  # Parāda pirmos 10
                logging.info(f"  {f}")
            
            # Mēģina atrast jaunākos gada folderus
            year_folders = []
            self.ftp.retrlines('NLST', lambda x: year_folders.append(x))
            
            years = [f for f in year_folders if f.isdigit() and len(f) == 4]
            years.sort(reverse=True)
            
            if years:
                latest_year = years[0]
                logging.info(f"\nPārbaudu {latest_year} gada struktūru:")
                
                self.ftp.cwd(f'/{latest_year}')
                month_folders = []
                self.ftp.retrlines('NLST', lambda x: month_folders.append(x))
                
                logging.info(f"Mēneša mapes: {month_folders[:5]}")  # Parāda pirmos 5
                
                if month_folders:
                    # Pārbauda pirmo mēnesi
                    self.ftp.cwd(month_folders[0])
                    tar_files = []
                    self.ftp.retrlines('NLST', lambda x: tar_files.append(x))
                    
                    logging.info(f"Faili {month_folders[0]} mapē: {tar_files[:5]}")
                    
            self.ftp.cwd('/')
            
        except Exception as e:
            logging.error(f"Kļūda pārbaudot struktūru: {e}")
            
    def process_date(self, date_info):
        """Apstrādā vienas dienas datus"""
        results = []
        # Struktūra: /2025/07_2025/01_07_2025.tar.gz
        year_path = f"/{date_info['year']}"
        month_folder = f"{date_info['month']}_{date_info['year']}"
        tar_filename = f"{date_info['day']}_{date_info['month']}_{date_info['year']}.tar.gz"
        
        try:
            # Navigē uz gada mapi
            self.ftp.cwd(year_path)
            
            # Navigē uz mēneša mapi
            self.ftp.cwd(month_folder)
            
            # Pārbauda vai fails eksistē
            files = []
            self.ftp.retrlines('LIST', lambda x: files.append(x.split()[-1]))
            
            if tar_filename in files:
                logging.info(f"Apstrādāju {tar_filename}")
                local_path = os.path.join(self.temp_dir, tar_filename)
                
                if self.download_file(tar_filename, local_path):
                    file_results = self.extract_and_search_tar_gz(local_path)
                    if file_results:
                        for result in file_results:
                            result['date'] = date_info['full']
                            result['archive'] = tar_filename
                        results.extend(file_results)
                    
                    # Dzēš pagaidu failus
                    try:
                        os.remove(local_path)
                    except:
                        pass
            else:
                logging.info(f"Fails {tar_filename} nav atrasts")
                
            # Atgriežas uz root direktoriju
            self.ftp.cwd('/')
                        
        except Exception as e:
            logging.warning(f"Nevarēju apstrādāt {year_path}/{month_folder}/{tar_filename}: {e}")
            try:
                self.ftp.cwd('/')
            except:
                pass
            
        return results
        
    def save_results(self, results):
        """Saglabā rezultātus"""
        if not results:
            logging.info("Nav atrasti atbilstoši ieraksti")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Saglabā JSON formātā
        json_file = self.results_dir / f'rezultati_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        # Saglabā arī cilvēkiem lasāmā formātā
        txt_file = self.results_dir / f'rezultati_{timestamp}.txt'
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Iepirkumu meklēšanas rezultāti - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("="*80 + "\n\n")
            
            for r in results:
                f.write(f"Datums: {r.get('date', 'N/A')}\n")
                f.write(f"Nosaukums: {r.get('title', 'N/A')}\n")
                f.write(f"Pasūtītājs: {r.get('contracting_authority', 'N/A')}\n")
                f.write(f"CPV kodi: {', '.join(r.get('cpv_codes', []))}\n")
                f.write(f"Atrasti CPV: {', '.join(r.get('found_cpv_codes', []))}\n")
                f.write(f"Vērtība: {r.get('value', 'N/A')}\n")
                f.write(f"Termiņš: {r.get('deadline', 'N/A')}\n")
                f.write(f"Atrastie atslēgvārdi: {', '.join(r.get('matched_keywords', []))}\n")
                f.write(f"Fails: {r.get('archive', 'N/A')} -> {r.get('file', 'N/A')}\n")
                
                # Pievieno konteksta fragmentus
                if 'context_snippets' in r and r['context_snippets']:
                    f.write("\nKonteksts:\n")
                    for snippet in r['context_snippets'][:3]:  # Parāda pirmos 3
                        f.write(f"  [{snippet['keyword']} -> {snippet['variation']}]:\n")
                        f.write(f"  {snippet['context']}\n\n")
                        
                f.write("-"*80 + "\n\n")
                
        logging.info(f"Saglabāti {len(results)} rezultāti failos {json_file} un {txt_file}")
        
    def run_search(self):
        """Galvenā meklēšanas funkcija"""
        logging.info("Sāku iepirkumu meklēšanu...")
        
        if not self.connect_ftp():
            return
        
        # Vispirms pārbauda struktūru (var izslēgt pēc pirmās reizes)
        if hasattr(self, 'check_structure') and self.check_structure:
            self.check_ftp_structure()
            
        all_results = []
        dates = self.get_recent_dates()
        
        for date in dates:
            logging.info(f"Pārbaudu {date['full']}...")
            results = self.process_date(date)
            all_results.extend(results)
            
        self.disconnect_ftp()
        
        # Saglabā rezultātus
        self.save_results(all_results)
        
        # Tīra pagaidu direktoriju
        try:
            shutil.rmtree(self.temp_dir)
            self.temp_dir = tempfile.mkdtemp()
        except:
            pass
            
        logging.info(f"Meklēšana pabeigta. Atrasti {len(all_results)} atbilstoši ieraksti.")
        
    def schedule_daily_run(self):
        """Ieplāno ikdienas palaišanu"""
        run_time = self.config.get('check_time', '09:00')
        schedule.every().day.at(run_time).do(self.run_search)
        
        logging.info(f"Ieplānota ikdienas palaišana plkst. {run_time}")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Pārbauda katru minūti


if __name__ == "__main__":
    import sys
    
    mekletajs = IepirkumuMekletajs()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # Palaiž plānotāju
        mekletajs.schedule_daily_run()
    else:
        # Veic vienreizēju meklēšanu
        mekletajs.run_search()
