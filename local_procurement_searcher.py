#!/usr/bin/env python3
"""
Lokālo iepirkumu failu meklētājs ar uzlabotu veiktspēju un XML parsēšanu
FAILS: local_procurement_searcher.py - Atjaunināta versija
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import tempfile
import shutil
import logging
import json
from pathlib import Path
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing
from typing import Dict, List, Tuple, Optional
import traceback

# Mēģina importēt lxml, ja nav - izmanto standarta ET
try:
    from lxml import etree as lxml_ET
    USE_LXML = True
except ImportError:
    USE_LXML = False

# Logging konfigurācija
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Procedūras tipu kartēšana
PROCEDURE_TYPE_MAPPING = {
    # PIL procedūras virs ES sliekšņiem
    'open': 'Atklāts konkurss virs ES sliekšņiem',
    'restricted': 'Slēgts konkurss virs ES sliekšņiem',
    'negotiated': 'Sarunu procedūra virs ES sliekšņiem',
    'competitive_dialogue': 'Konkursa dialogs virs ES sliekšņiem',
    'competitive_negotiation': 'Konkursa procedūra ar sarunām virs ES sliekšņiem',
    'innovation': 'Inovāciju partnerības procedūra virs ES sliekšņiem',
    
    # PIL procedūras zem ES sliekšņiem
    'open_below': 'Atklāts konkurss zem ES sliekšņiem',
    'restricted_below': 'Slēgts konkurss zem ES sliekšņiem',
    'negotiated_below': 'Sarunu procedūra zem ES sliekšņiem',
    
    # SPSIL procedūras
    'sps_open': 'SPSIL atklāts konkurss',
    'sps_restricted': 'SPSIL slēgts konkurss',
    'sps_negotiated': 'SPSIL sarunu procedūra',
    
    # Citi
    'price_survey': 'Cenu aptauja',
    'small_purchase': 'Mazie iepirkumi',
    'design_contest': 'Metu konkurss',
    'framework': 'Vispārīgā vienošanās',
    
    # Noklusējuma
    'unknown': 'Nav norādīts'
}

class XMLNamespaceHandler:
    """Apstrādā XML namespace problēmas"""
    def __init__(self):
        self.namespaces = {}
        
    def extract_namespaces(self, root):
        """Izvelk visus namespace no XML"""
        if USE_LXML:
            self.namespaces = {k: v for k, v in root.nsmap.items() if k}
        else:
            # Standarta ET - meklē namespace manuāli
            for elem in root.iter():
                if '}' in elem.tag:
                    ns = elem.tag.split('}')[0][1:]
                    prefix = elem.tag.split('}')[0].split('/')[-1]
                    if ns and ns not in self.namespaces.values():
                        self.namespaces[prefix] = ns
        return self.namespaces
        
    def find_element(self, root, tag_names, with_namespace=True):
        """Meklē elementu ar vai bez namespace"""
        for tag in tag_names:
            # Mēģina ar namespace
            if with_namespace:
                for prefix, ns in self.namespaces.items():
                    ns_tag = f"{{{ns}}}{tag}"
                    elem = root.find(f".//{ns_tag}")
                    if elem is not None:
                        return elem
            
            # Mēģina bez namespace
            elem = root.find(f".//{tag}")
            if elem is not None:
                return elem
                
            # Mēģina ar daļēju atbilstību
            for elem in root.iter():
                if tag.lower() in elem.tag.lower():
                    return elem
        
        return None

class ImprovedXMLParser:
    """Uzlabots XML parsētājs ar pilnīgāku lauku atpazīšanu"""
    
    def __init__(self):
        self.ns_handler = XMLNamespaceHandler()
        
    def parse_xml_comprehensive(self, xml_path):
        """Visaptveroša XML parsēšana"""
        try:
            if USE_LXML:
                parser = lxml_ET.XMLParser(recover=True, encoding='utf-8')
                tree = lxml_ET.parse(xml_path, parser=parser)
                root = tree.getroot()
            else:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
            # Izvelk namespaces
            self.ns_handler.extract_namespaces(root)
            
            info = {
                'title': '',
                'contracting_authority': '',
                'authority_address': '',
                'authority_contact': {},
                'cpv_codes': [],
                'cpv_descriptions': {},
                'value': '',
                'value_min': '',
                'value_max': '',
                'currency': '',
                'deadline': '',  # Iesniegšanas termiņš
                'appeal_date': '',  # Pārsūdzības termiņš
                'submission_deadline': '',
                'notice_type': '',
                'procedure_type': '',
                'procedure_category': '',  # Virs/zem ES sliekšņiem
                'id': '',
                'ted_id': '',
                'publication_date': '',
                'submission_date': '',
                'identification_number': '',
                'procurement_id': '',
                'status': '',
                'description': '',
                'place_of_performance': '',
                'nuts_codes': [],
                'duration': '',
                'criteria': [],
                'lots': [],
                'documents': [],
                'modifications': [],
                'award_info': {},
                'type': '',  # Paziņojuma tips no XML
                'proc_type': ''  # Procedūras tips no XML
            }
            
            # Parsē pamatinformāciju
            self._parse_basic_info(root, info)
            
            # Parsē pasūtītāja informāciju
            self._parse_authority_info(root, info)
            
            # Parsē CPV kodus
            self._parse_cpv_codes(root, info)
            
            # Parsē finansiālo informāciju
            self._parse_financial_info(root, info)
            
            # Parsē datumus
            self._parse_dates(root, info)
            
            # Parsē procedūras informāciju
            self._parse_procedure_info(root, info)
            
            # Parsē lotes (ja ir)
            self._parse_lots(root, info)
            
            # Parsē piešķiršanas informāciju
            self._parse_award_info(root, info)
            
            # Nosaka procedūras kategoriju
            self._determine_procedure_category(info)
            
            return info
            
        except Exception as e:
            logging.error(f"Kļūda parsējot {xml_path}: {e}")
            return None
            
    def _parse_basic_info(self, root, info):
        """Parsē pamatinformāciju"""
        # Nosaukums - pievienots 'name' tags
        title_tags = ['name', 'TITLE', 'CONTRACT_NAME', 'OBJECT_DESCR', 'SHORT_DESCR', 'title', 'contract_name']
        title_elem = self.ns_handler.find_element(root, title_tags)
        if title_elem is not None and title_elem.text:
            info['title'] = title_elem.text.strip()
            
        # Apraksts
        desc_tags = ['DESCRIPTION', 'OBJECT_DESCRIPTION', 'SHORT_DESC', 'AC_PROCUREMENT_DOC', 'description']
        desc_elem = self.ns_handler.find_element(root, desc_tags)
        if desc_elem is not None and desc_elem.text:
            info['description'] = desc_elem.text.strip()
            
        # ID / Identifikācijas numurs - meklē procurement_code
        id_tags = ['procurement_code', 'procurement_id', 'NOTICE_NUMBER', 'TED_NOTICE_NUMBER', 'ID', 'NO_DOC_OJS']
        id_elem = self.ns_handler.find_element(root, id_tags)
        if id_elem is not None and id_elem.text:
            info['id'] = id_elem.text.strip()
            info['identification_number'] = id_elem.text.strip()
            
        # Procurement ID - vairs nav vajadzīgs, jo procurement_code jau ir ID
        if not info['procurement_id']:
            proc_id_tags = ['FILE_REFERENCE_NUMBER', 'REFERENCE_NUMBER', 'REF_NOTICE']
            proc_elem = self.ns_handler.find_element(root, proc_id_tags)
            if proc_elem is not None and proc_elem.text:
                info['procurement_id'] = proc_elem.text.strip()
                
        # Type un proc_type
        type_elem = self.ns_handler.find_element(root, ['type'])
        if type_elem is not None and type_elem.text:
            info['type'] = type_elem.text.strip()
            
        proc_type_elem = self.ns_handler.find_element(root, ['proc_type'])
        if proc_type_elem is not None and proc_type_elem.text:
            info['proc_type'] = proc_type_elem.text.strip()
                
    def _parse_authority_info(self, root, info):
        """Parsē pasūtītāja informāciju"""
        # Meklē pasūtītāja nosaukumu
        auth_name_tags = ['authority_name', 'OFFICIALNAME', 'NAME']
        for tag in auth_name_tags:
            elem = self.ns_handler.find_element(root, [tag])
            if elem is not None and elem.text:
                info['contracting_authority'] = elem.text.strip()
                break
                
        # Meklē adresi
        addr_elem = self.ns_handler.find_element(root, ['address', 'ADDRESS'])
        if addr_elem is not None and addr_elem.text:
            info['authority_address'] = addr_elem.text.strip()
            
        # Meklē pasūtītāja sekciju
        auth_sections = ['CONTRACTING_AUTHORITY', 'CONTRACTING_BODY', 'CA_CE', 'ADDR_CONTRACTING_BODY']
        
        for section_name in auth_sections:
            auth_elem = self.ns_handler.find_element(root, [section_name])
            if auth_elem is not None:
                # Nosaukums
                if not info['contracting_authority']:
                    name_elem = auth_elem.find('.//OFFICIALNAME') or auth_elem.find('.//NAME')
                    if name_elem is not None and name_elem.text:
                        info['contracting_authority'] = name_elem.text.strip()
                    
                # Adrese
                if not info['authority_address']:
                    addr_parts = []
                    for addr_tag in ['ADDRESS', 'STREET', 'TOWN', 'POSTAL_CODE', 'COUNTRY']:
                        addr_elem = auth_elem.find(f'.//{addr_tag}')
                        if addr_elem is not None and addr_elem.text:
                            addr_parts.append(addr_elem.text.strip())
                    if addr_parts:
                        info['authority_address'] = ', '.join(addr_parts)
                    
                # Kontaktinformācija
                contact_info = {}
                contact_tags = {
                    'CONTACT_POINT': 'contact_point',
                    'PHONE': 'phone',
                    'E_MAIL': 'email',
                    'FAX': 'fax',
                    'URL': 'url',
                    'URL_BUYER': 'buyer_profile'
                }
                
                for tag, key in contact_tags.items():
                    elem = auth_elem.find(f'.//{tag}')
                    if elem is not None and elem.text:
                        contact_info[key] = elem.text.strip()
                        
                if contact_info:
                    info['authority_contact'] = contact_info
                    
                break
                
    def _parse_cpv_codes(self, root, info):
        """Parsē CPV kodus ar aprakstiem"""
        # Meklē vienkāršos <code> tagus
        for elem in root.iter():
            if elem.tag.lower() == 'code' and elem.text:
                code_text = elem.text.strip()
                # Pārbauda vai ir CPV formāts (8 cipari ar vai bez defises)
                if re.match(r'^\d{8}(-\d)?$', code_text):
                    # Noņem defisi un ciparu aiz tās, ja ir
                    clean_code = code_text.split('-')[0]
                    if clean_code not in info['cpv_codes']:
                        info['cpv_codes'].append(clean_code)
                        
                        # Meklē aprakstu blakus
                        parent = elem.getparent() if hasattr(elem, 'getparent') else None
                        if parent is not None:
                            desc_elem = parent.find('.//description') or parent.find('.//DESCRIPTION')
                            if desc_elem is not None and desc_elem.text:
                                info['cpv_descriptions'][clean_code] = desc_elem.text.strip()
        
        # Meklē arī CPV sekcijās
        cpv_sections = ['CPV_MAIN', 'CPV_ADDITIONAL', 'CPV_CODE', 'ORIGINAL_CPV', 'main_cpv']
        for section in cpv_sections:
            for cpv_elem in root.iter():
                if section.lower() in cpv_elem.tag.lower():
                    # Meklē CPV kodu
                    code_elem = cpv_elem.find('.//CODE') or cpv_elem.find('.//code')
                    if code_elem is not None and code_elem.text:
                        code = code_elem.text.strip().split('-')[0]  # Noņem -X daļu
                        if re.match(r'^\d{8}$', code) and code not in info['cpv_codes']:
                            info['cpv_codes'].append(code)
                            
                            # Meklē aprakstu
                            desc_elem = cpv_elem.find('.//DESCRIPTION') or cpv_elem.find('.//description')
                            if desc_elem is not None and desc_elem.text:
                                info['cpv_descriptions'][code] = desc_elem.text.strip()
                                
    def _parse_financial_info(self, root, info):
        """Parsē finansiālo informāciju"""
        # Vērtība - pievienots 'price' tags
        value_tags = ['price', 'VAL_TOTAL', 'VALUE', 'VAL_ESTIMATED_TOTAL', 'COSTS_RANGE_AND_CURRENCY']
        
        for val_tag in value_tags:
            val_elem = self.ns_handler.find_element(root, [val_tag])
            if val_elem is not None:
                # Meklē valūtu
                curr_attr = val_elem.get('CURRENCY') or val_elem.get('currency')
                if curr_attr:
                    info['currency'] = curr_attr
                else:
                    # Meklē currency elementu
                    curr_elem = self.ns_handler.find_element(root, ['currency', 'CURRENCY'])
                    if curr_elem is not None and curr_elem.text:
                        info['currency'] = curr_elem.text.strip()
                    
                # Meklē summu
                if val_elem.text:
                    info['value'] = val_elem.text.strip()
                else:
                    # Meklē bērnos
                    for child in val_elem:
                        if child.text and re.search(r'\d', child.text):
                            info['value'] = child.text.strip()
                            break
                            
        # Diapazons
        min_elem = self.ns_handler.find_element(root, ['VAL_RANGE_TOTAL_MIN', 'LOWEST_OFFER'])
        max_elem = self.ns_handler.find_element(root, ['VAL_RANGE_TOTAL_MAX', 'HIGHEST_OFFER'])
        
        if min_elem is not None and min_elem.text:
            info['value_min'] = min_elem.text.strip()
        if max_elem is not None and max_elem.text:
            info['value_max'] = max_elem.text.strip()
            
    def _parse_dates(self, root, info):
        """Parsē datumus"""
        # Publicēšanas datums - pievienots pub_date un publication_date
        pub_tags = ['pub_date', 'publication_date', 'DATE_DISPATCH_NOTICE', 'DATEPUB', 'DATE_PUB']
        pub_elem = self.ns_handler.find_element(root, pub_tags)
        if pub_elem is not None and pub_elem.text:
            info['publication_date'] = self._format_date(pub_elem.text.strip())
            
        # Iesniegšanas termiņš - PIEVIENOTS appeal_date
        deadline_tags = ['appeal_date', 'DEADLINE_RECEIPT_TENDERS', 'DATE_TENDER_VALID', 'TIME_LIMIT', 'deadline', 'submit_date']
        deadline_elem = self.ns_handler.find_element(root, deadline_tags)
        if deadline_elem is not None:
            date_text = deadline_elem.text or ''
            # Meklē laiku
            time_elem = deadline_elem.find('.//TIME')
            if time_elem is not None and time_elem.text:
                date_text += ' ' + time_elem.text.strip()
            if date_text.strip():
                info['deadline'] = self._format_date(date_text.strip())
                
        # Atsevišķi meklē appeal_date
        appeal_elem = self.ns_handler.find_element(root, ['appeal_date'])
        if appeal_elem is not None and appeal_elem.text:
            info['appeal_date'] = self._format_date(appeal_elem.text.strip())
            # Ja nav deadline, izmanto appeal_date
            if not info['deadline']:
                info['deadline'] = info['appeal_date']
                
        # Līguma ilgums
        duration_tags = ['DURATION', 'DATE_START', 'DATE_END']
        duration_info = []
        for tag in duration_tags:
            elem = self.ns_handler.find_element(root, [tag])
            if elem is not None and elem.text:
                duration_info.append(f"{tag}: {elem.text.strip()}")
        if duration_info:
            info['duration'] = '; '.join(duration_info)
            
    def _parse_procedure_info(self, root, info):
        """Parsē procedūras informāciju"""
        # Procedūras tips no proc_type
        if info['proc_type']:
            proc_type_num = info['proc_type']
            # Kartē proc_type numurus uz aprakstiem
            proc_type_mapping = {
                '1': 'open',
                '2': 'restricted',
                '3': 'negotiated',
                '4': 'competitive_dialogue',
                '5': 'competitive_negotiation',
                '6': 'innovation',
                '7': 'negotiated_below',
                '8': 'design_contest',
                '101': 'open_below',
                '102': 'restricted_below',
                '201': 'sps_open',
                '202': 'sps_restricted',
                '203': 'sps_negotiated',
                '301': 'price_survey',
                '302': 'small_purchase'
            }
            
            mapped_type = proc_type_mapping.get(proc_type_num, 'unknown')
            info['procedure_type'] = PROCEDURE_TYPE_MAPPING.get(mapped_type, 'Nav norādīts')
        else:
            # Meklē citos veidos
            proc_tags = ['TYPE_PROCEDURE', 'PT_OPEN', 'PT_RESTRICTED', 'PT_NEGOTIATED']
            for tag in proc_tags:
                proc_elem = self.ns_handler.find_element(root, [tag])
                if proc_elem is not None:
                    if proc_elem.text:
                        info['procedure_type'] = proc_elem.text.strip()
                    else:
                        # Ja tas ir marķiera elements
                        info['procedure_type'] = tag.replace('PT_', '').replace('_', ' ').title()
                    break
                
        # Paziņojuma tips no type
        if info['type']:
            notice_type_mapping = {
                'general': 'Paziņojums par līgumu',
                'general_planning': 'Iepriekšējs informatīvs paziņojums',
                'general_result': 'Paziņojums par līguma slēgšanas tiesību piešķiršanu',
                'general_change': 'Paziņojums par grozījumiem',
                'general_cancel': 'Paziņojums par procedūras izbeigšanu',
                'utilities': 'Sabiedrisko pakalpojumu paziņojums',
                'utilities_planning': 'Sabiedrisko pakalpojumu iepriekšējs informatīvs paziņojums',
                'utilities_result': 'Sabiedrisko pakalpojumu rezultātu paziņojums',
                'defence': 'Aizsardzības un drošības paziņojums',
                'concession': 'Koncesijas paziņojums',
                'design_contest': 'Paziņojums par metu konkursu',
                'voluntary': 'Brīvprātīgs ex ante caurspīdīguma paziņojums',
                'qualification': 'Paziņojums par kvalifikācijas sistēmu'
            }
            
            info['notice_type'] = notice_type_mapping.get(info['type'], info['type'])
        else:
            # Meklē citos elementos
            notice_tags = ['NOTICE_TYPE', 'TD_DOCUMENT_TYPE', 'FORM_SECTION']
            notice_elem = self.ns_handler.find_element(root, notice_tags)
            if notice_elem is not None and notice_elem.text:
                info['notice_type'] = notice_elem.text.strip()
            
        # Kritēriji
        criteria_elem = self.ns_handler.find_element(root, ['AWARD_CRITERIA', 'AC_CRITERIA'])
        if criteria_elem is not None:
            criteria_list = []
            for crit in criteria_elem.iter():
                if crit.text and len(crit.text.strip()) > 3:
                    criteria_list.append(crit.text.strip())
            if criteria_list:
                info['criteria'] = criteria_list
                
    def _determine_procedure_category(self, info):
        """Nosaka vai procedūra ir virs vai zem ES sliekšņiem"""
        proc_type = info.get('procedure_type', '')
        
        if 'virs ES sliekšņiem' in proc_type:
            info['procedure_category'] = 'virs_es'
        elif 'zem ES sliekšņiem' in proc_type:
            info['procedure_category'] = 'zem_es'
        elif 'SPSIL' in proc_type:
            info['procedure_category'] = 'spsil'
        else:
            info['procedure_category'] = 'cits'
                
    def _parse_lots(self, root, info):
        """Parsē lotes/daļas"""
        lots = []
        lot_sections = root.findall('.//LOT') or root.findall('.//OBJECT_DESCR')
        
        for i, lot_elem in enumerate(lot_sections):
            lot_info = {
                'number': str(i + 1),
                'title': '',
                'description': '',
                'cpv_codes': [],
                'value': ''
            }
            
            # Lotes numurs
            num_elem = lot_elem.find('.//LOT_NUMBER') or lot_elem.find('.//LOT_NO')
            if num_elem is not None and num_elem.text:
                lot_info['number'] = num_elem.text.strip()
                
            # Nosaukums
            title_elem = lot_elem.find('.//TITLE') or lot_elem.find('.//LOT_TITLE')
            if title_elem is not None and title_elem.text:
                lot_info['title'] = title_elem.text.strip()
                
            # CPV kodi
            for cpv_elem in lot_elem.findall('.//CPV_CODE'):
                code_elem = cpv_elem.find('.//CODE')
                if code_elem is not None and code_elem.text:
                    lot_info['cpv_codes'].append(code_elem.text.strip())
                    
            if lot_info['title'] or lot_info['cpv_codes']:
                lots.append(lot_info)
                
        if lots:
            info['lots'] = lots
            
    def _parse_award_info(self, root, info):
        """Parsē līguma piešķiršanas informāciju"""
        # Meklē uzvarētāju winner_list struktūrā
        winner_list = self.ns_handler.find_element(root, ['winner_list'])
        if winner_list is not None:
            winner = winner_list.find('.//winner')
            if winner is not None:
                award_data = {}
                
                # Uzvarētāja nosaukums
                winner_name = winner.find('.//winner_name')
                if winner_name is not None and winner_name.text:
                    award_data['contractor'] = winner_name.text.strip()
                    
                # Uzvarētāja reģ. numurs
                winner_reg = winner.find('.//winner_reg_num')
                if winner_reg is not None and winner_reg.text:
                    award_data['contractor_reg'] = winner_reg.text.strip()
                    
                # Uzvarētāja adrese
                winner_addr = winner.find('.//winner_address')
                if winner_addr is not None and winner_addr.text:
                    award_data['contractor_address'] = winner_addr.text.strip()
                    
                if award_data:
                    info['award_info'] = award_data
        
        # Meklē arī citos variantos
        award_sections = ['AWARD_CONTRACT', 'AWARDED_CONTRACT', 'AWARD']
        
        for section in award_sections:
            award_elem = self.ns_handler.find_element(root, [section])
            if award_elem is not None:
                if not info['award_info']:
                    info['award_info'] = {}
                    
                # Uzvarētājs
                if 'contractor' not in info['award_info']:
                    contractor_elem = award_elem.find('.//CONTRACTOR') or award_elem.find('.//AWARDED_TO')
                    if contractor_elem is not None:
                        name_elem = contractor_elem.find('.//OFFICIALNAME') or contractor_elem.find('.//NAME')
                        if name_elem is not None and name_elem.text:
                            info['award_info']['contractor'] = name_elem.text.strip()
                        
                # Piešķiršanas datums
                date_elem = award_elem.find('.//DATE_CONCLUSION_CONTRACT') or award_elem.find('.//DATE_AWARD')
                if date_elem is not None and date_elem.text:
                    info['award_info']['award_date'] = self._format_date(date_elem.text.strip())
                    
                # Līguma vērtība
                val_elem = award_elem.find('.//VAL_TOTAL') or award_elem.find('.//VALUE')
                if val_elem is not None and val_elem.text:
                    info['award_info']['contract_value'] = val_elem.text.strip()
                    
                break
                
    def _format_date(self, date_str):
        """Formatē datumu vienotā formātā"""
        if not date_str:
            return ''
            
        # Mēģina dažādus datuma formātus
        formats = ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except:
                continue
                
        return date_str  # Atgriež oriģinālo, ja nevar parsēt

class OptimizedLocalSearcher:
    """Optimizēts lokālais meklētājs ar paralēlo apstrādi"""
    
    def __init__(self, config_file='config.json'):
        self.xml_dir = Path('EIS-XML-Files')
        self.results_dir = Path('rezultati')
        self.results_dir.mkdir(exist_ok=True)
        self.processed_ids = set()
        self.procurement_ids = {}
        
        # Paralēlās apstrādes parametri
        self.num_workers = multiprocessing.cpu_count()
        self.batch_size = 50  # XML failu skaits vienā paketē
        
        # XML parsētājs
        self.parser = ImprovedXMLParser()
        
        # Ielādē konfigurāciju
        self.load_config(config_file)
        
    def load_config(self, config_file):
        """Ielādē meklēšanas kritērijus"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                self.search_criteria = self.config.get('search_criteria', {})
        except FileNotFoundError:
            logging.warning(f"Konfigurācijas fails {config_file} nav atrasts")
            self.search_criteria = {}
            
    def process_xml_batch(self, xml_files: List[Path], date_str: str) -> List[Dict]:
        """Apstrādā XML failu paketi"""
        results = []
        
        for xml_file in xml_files:
            try:
                # Parsē XML
                parsed_info = self.parser.parse_xml_comprehensive(str(xml_file))
                if not parsed_info:
                    continue
                    
                # Pārbauda atbilstību kritērijiem
                if self._matches_criteria(parsed_info, str(xml_file)):
                    parsed_info['date'] = date_str
                    parsed_info['xml_file'] = xml_file.name
                    results.append(parsed_info)
                    
            except Exception as e:
                logging.error(f"Kļūda apstrādājot {xml_file}: {e}")
                
        return results
        
    def _matches_criteria(self, info: Dict, xml_path: str) -> bool:
        """Pārbauda vai XML atbilst meklēšanas kritērijiem"""
        # Pārbauda aktualitāti
        if 'deadline_status' in self.search_criteria:
            deadline_status = self.search_criteria['deadline_status']
            is_active = self._is_active(info.get('deadline', ''))
            
            if deadline_status == 'active' and not is_active:
                return False
            elif deadline_status == 'expired' and is_active:
                return False
        
        # Pārbauda procedūras tipus
        if 'procedure_types' in self.search_criteria:
            allowed_types = self.search_criteria['procedure_types']
            if info.get('procedure_type') not in allowed_types:
                return False
        
        # Pārbauda statusu
        status = info.get('status', 'IZSLUDINĀTS')
        allowed_statuses = self.search_criteria.get('statuses', ['IZSLUDINĀTS'])
        
        if status and status not in allowed_statuses:
            return False
        
        # Ja nav kritēriju, parāda visu
        if self.search_criteria.get('show_all', False):
            return True
            
        # Pārbauda atslēgvārdus
        text_content = ' '.join([
            info.get('title', ''),
            info.get('description', ''),
            info.get('contracting_authority', '')
        ])
        
        keyword_found = False
        matched_keywords = []
        
        for kw in self.search_criteria.get('keywords', []):
            if self._text_contains_keyword(text_content, kw):
                keyword_found = True
                matched_keywords.append(kw)
                
        # Pārbauda CPV kodus
        cpv_found = False
        found_cpv_codes = []
        
        # Attīra CPV kodus
        cleaned_cpv_codes = []
        for cpv in info.get('cpv_codes', []):
            cleaned = cpv.split('-')[0] if '-' in cpv else cpv
            if cleaned not in cleaned_cpv_codes:
                cleaned_cpv_codes.append(cleaned)
        info['cpv_codes'] = cleaned_cpv_codes
        
        for cpv in self.search_criteria.get('cpv_codes', []):
            cleaned_search_cpv = cpv.split('-')[0] if '-' in cpv else cpv
            if cleaned_search_cpv in info.get('cpv_codes', []):
                cpv_found = True
                found_cpv_codes.append(cleaned_search_cpv)
                
        # Pārbauda izslēgtos vārdus
        excluded = False
        for ex in self.search_criteria.get('exclude_keywords', []):
            if self._text_contains_keyword(text_content, ex):
                excluded = True
                break
                
        # Saglabā atrastos atslēgvārdus
        if keyword_found or cpv_found:
            info['matched_keywords'] = matched_keywords
            info['found_cpv_codes'] = found_cpv_codes
            
        return (keyword_found or cpv_found) and not excluded
        
    def _is_active(self, deadline_str: str) -> bool:
        """Pārbauda vai iepirkums ir aktīvs (termiņš nav beidzies)"""
        if not deadline_str:
            return True  # Ja nav termiņa, pieņem ka aktīvs
            
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            return deadline >= datetime.now()
        except:
            return True  # Ja nevar parsēt, pieņem ka aktīvs
        
    def _text_contains_keyword(self, text: str, keyword: str) -> bool:
        """Pārbauda vai tekstā ir atslēgvārds ar locījumu atbalstu"""
        text_lower = text.lower()
        text_normalized = self.normalize_latvian_text(text)
        
        # Ja atslēgvārds ir vairāku vārdu frāze
        if ' ' in keyword:
            words = keyword.split()
            # Pārbauda vai visi vārdi ir tekstā
            all_found = True
            for word in words:
                word_variations = self.create_word_variations(word)
                word_found = False
                for variation in word_variations:
                    pattern = r'\b' + re.escape(variation) + r'\b'
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        word_found = True
                        break
                if not word_found:
                    all_found = False
                    break
            return all_found
        else:
            # Viena vārda meklēšana
            keyword_variations = self.create_word_variations(keyword)
            
            for variation in keyword_variations:
                pattern = r'\b' + re.escape(variation) + r'\b'
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return True
                    
                pattern_norm = r'\b' + re.escape(self.normalize_latvian_text(variation)) + r'\b'
                if re.search(pattern_norm, text_normalized, re.IGNORECASE):
                    return True
                    
        return False
        
    def normalize_latvian_text(self, text):
        """Normalizē latviešu tekstu meklēšanai"""
        if not text:
            return ""
            
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
        """Izveido vārda variācijas ar locījumiem"""
        word_lower = word.lower()
        variations = {word_lower}
        
        endings = ['s', 'a', 'as', 'am', 'ā', 'ām', 'i', 'u', 'us', 'os', 'es', 
                  'em', 'ēm', 'is', 'im', 'ī', 'iem', 'ēs', 'e', 'ē', 'ei',
                  'ai', 'ais', 'ās', 'ajā', 'ajam', 'ajai', 'ajo', 'ajās',
                  'ajiem', 'ajām', 'ajos', 'ums', 'umam', 'umu', 'umos',
                  'šana', 'šanas', 'šanu', 'šanai', 'tājs', 'tāja', 'tāju',
                  'nieks', 'nieka', 'nieku', 'niekiem', 'ība', 'ības', 'ību']
        
        for ending in endings:
            variations.add(word_lower + ending)
            
            for e in endings:
                if word_lower.endswith(e) and len(word_lower) > len(e) + 2:
                    base = word_lower[:-len(e)]
                    variations.add(base)
                    variations.add(base + ending)
        
        normalized = self.normalize_latvian_text(word)
        variations.add(normalized)
        
        return variations
        
    def search_date_range_parallel(self, start_date: str, end_date: str) -> List[Dict]:
        """Meklē datumu diapazonā ar paralēlo apstrādi"""
        all_results = []
        self.processed_ids.clear()
        self.procurement_ids.clear()
        
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Savāc visus XML failus pa datumiem
        files_by_date = []
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            date_folder = current_date.strftime('%d_%m_%Y')
            xml_date_dir = self.xml_dir / date_folder
            
            if xml_date_dir.exists():
                xml_files = list(xml_date_dir.glob('*.xml'))
                if xml_files:
                    files_by_date.append((date_str, xml_files))
                    logging.info(f"Datumam {date_str} atrasti {len(xml_files)} XML faili")
                    
            current_date += timedelta(days=1)
            
        # Apstrādā ar ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            
            for date_str, xml_files in files_by_date:
                # Sadala failos pa paketēm
                for i in range(0, len(xml_files), self.batch_size):
                    batch = xml_files[i:i + self.batch_size]
                    future = executor.submit(self.process_xml_batch, batch, date_str)
                    futures.append(future)
                    
            # Savāc rezultātus
            for future in futures:
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                except Exception as e:
                    logging.error(f"Kļūda apstrādājot paketi: {e}")
                    
        # Noņem dublikātus
        unique_results = self._remove_duplicates(all_results)
        
        logging.info(f"Kopā atrasti {len(unique_results)} unikāli rezultāti")
        return unique_results
        
    def _remove_duplicates(self, results: List[Dict]) -> List[Dict]:
        """Noņem dublikātus pēc procurement_id vai citas unikālas vērtības"""
        seen = set()
        unique = []
        
        for result in results:
            # Izveido unikālu atslēgu
            key = None
            if result.get('procurement_id'):
                key = f"proc_{result['procurement_id']}"
            elif result.get('identification_number'):
                key = f"id_{result['identification_number']}"
            elif result.get('id'):
                key = f"id_{result['id']}"
            elif result.get('title'):
                key = f"title_{hash(result['title'])}"
                
            if key and key not in seen:
                seen.add(key)
                unique.append(result)
                
        return unique

# Integrācija ar esošo sistēmu
class LokalaisMekletajs(OptimizedLocalSearcher):
    """Wrapper klase saderībai ar esošo kodu"""
    
    def extract_xml_id(self, root):
        """Izvelk unikālo XML identifikatoru"""
        # Meklē dažādos iespējamos ID elementos
        id_tags = ['id', 'notice_id', 'ted_id', 'document_id', 'reference', 'identifier']
        
        for elem in root.iter():
            elem_tag = elem.tag.lower()
            # Izslēdz authority_id
            if elem_tag == 'authority_id':
                continue
                
            for id_tag in id_tags:
                if id_tag in elem_tag and elem.text and elem.text.strip():
                    return elem.text.strip()
                    
        # Mēģina atrast ID atribūtos
        for elem in root.iter():
            if 'id' in elem.attrib and elem.tag.lower() != 'authority_id':
                return elem.attrib['id']
                
        # Ja nav ID, ģenerē no satura hash
        text_content = ''.join([elem.text for elem in root.iter() if elem.text])
        if text_content:
            return hashlib.md5(text_content.encode()).hexdigest()[:16]
            
        return None
        
    def extract_status(self, root):
        """Izvelk iepirkuma statusu no XML"""
        status_mapping = {
            'IZSLUDINĀTS': ['IZSLUDINĀTS', 'PUBLISHED', 'ACTIVE'],
            'PIEDĀVĀJUMI ATVĒRTI': ['PIEDĀVĀJUMI ATVĒRTI', 'OFFERS_OPENED'],
            'LĪGUMS NOSLĒGTS': ['LĪGUMS NOSLĒGTS', 'CONTRACT_AWARDED', 'AWARDED'],
            'IZBEIGTS-PĀRTRAUKTS': ['IZBEIGTS', 'PĀRTRAUKTS', 'CANCELLED', 'TERMINATED']
        }
        
        for elem in root.iter():
            if 'status' in elem.tag.lower() and elem.text:
                text_upper = elem.text.strip().upper()
                for status_key, variations in status_mapping.items():
                    if any(var in text_upper for var in variations):
                        return status_key
                        
        # Mēģina atrast citos elementos
        text_content = ' '.join([elem.text for elem in root.iter() if elem.text])
        for status_key, variations in status_mapping.items():
            if any(var in text_content.upper() for var in variations):
                return status_key
                
        return 'IZSLUDINĀTS'  # Noklusējuma statuss
    
    def search_xml(self, xml_path):
        """Meklē XML failā pēc kritērijiem (vecā metode saderībai)"""
        matches = []
        
        try:
            # Izmanto atbilstošo parseri
            if USE_LXML:
                tree = lxml_ET.parse(xml_path)
                root = tree.getroot()
            else:
                tree = ET.parse(xml_path)
                root = tree.getroot()
            
            # Izvelk unikālo ID
            xml_id = self.extract_xml_id(root)
            if xml_id and xml_id in self.processed_ids:
                # Jau apstrādāts šis paziņojums
                return matches
                
            # Vispirms pārbauda iepirkuma statusu
            status = self.extract_status(root)
            allowed_statuses = self.search_criteria.get('statuses', ['IZSLUDINĀTS'])
            
            if status and status not in allowed_statuses:
                return matches  # Neatbilst statusa filtram
            
            # Ja nav meklēšanas kritēriju, parāda visus
            show_all = self.search_criteria.get('show_all', False)
            
            if show_all:
                # Parāda visus iepirkumus (tikai pārbauda izslēgtos vārdus)
                excluded = False
                for ex in self.search_criteria.get('exclude_keywords', []):
                    text_parts = []
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            text_parts.append(elem.text.strip())
                    text_content = ' '.join(text_parts)
                    
                    if self._text_contains_keyword(text_content, ex):
                        excluded = True
                        break
                        
                if not excluded:
                    notice_info = self.parser.parse_xml_comprehensive(xml_path)
                    if notice_info:
                        notice_info['file'] = os.path.basename(xml_path)
                        notice_info['matched_keywords'] = []
                        notice_info['found_cpv_codes'] = []
                        notice_info['context_snippets'] = []
                        notice_info['status'] = status
                        notice_info['xml_id'] = xml_id
                        
                        # Atzīmē kā apstrādātu
                        if xml_id:
                            self.processed_ids.add(xml_id)
                        
                        matches.append(notice_info)
                    
            else:
                # Standarta meklēšana ar kritērijiem
                text_parts = []
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_parts.append(elem.text.strip())
                    if elem.tail and elem.tail.strip():
                        text_parts.append(elem.tail.strip())
                        
                text_content = ' '.join(text_parts)
                
                matched_keywords = []
                for kw in self.search_criteria.get('keywords', []):
                    if self._text_contains_keyword(text_content, kw):
                        matched_keywords.append(kw)
                        
                keyword_found = len(matched_keywords) > 0
                
                excluded = False
                for ex in self.search_criteria.get('exclude_keywords', []):
                    if self._text_contains_keyword(text_content, ex):
                        excluded = True
                        break
                
                cpv_found = False
                found_cpv_codes = []
                
                # Meklē CPV kodus XML
                for elem in root.iter():
                    if elem.text:
                        # Pārbauda vai ir CPV formātā (8 cipari ar vai bez defises)
                        if re.match(r'^\d{8}(-\d)?, elem.text.strip()):
                            clean_cpv = elem.text.strip().split('-')[0]
                            
                            # Pārbauda pret meklēšanas kritērijiem
                            for search_cpv in self.search_criteria.get('cpv_codes', []):
                                clean_search_cpv = search_cpv.split('-')[0]
                                if clean_cpv == clean_search_cpv:
                                    cpv_found = True
                                    if clean_cpv not in found_cpv_codes:
                                        found_cpv_codes.append(clean_cpv)
                                
                if (keyword_found or cpv_found) and not excluded:
                    notice_info = self.parser.parse_xml_comprehensive(xml_path)
                    if notice_info:
                        notice_info['file'] = os.path.basename(xml_path)
                        notice_info['matched_keywords'] = matched_keywords
                        notice_info['found_cpv_codes'] = found_cpv_codes
                        notice_info['context_snippets'] = self.extract_context_snippets(text_content, matched_keywords)
                        notice_info['status'] = status
                        notice_info['xml_id'] = xml_id
                        
                        # Atzīmē kā apstrādātu
                        if xml_id:
                            self.processed_ids.add(xml_id)
                        
                        matches.append(notice_info)
                
        except Exception as e:
            logging.error(f"Kļūda lasot XML {xml_path}: {e}")
            
        return matches
        
    def extract_context_snippets(self, text, keywords, context_length=100):
        """Izvelk konteksta fragmentus"""
        snippets = []
        text_lower = text.lower()
        
        for kw in keywords[:3]:  # Tikai pirmie 3 atslēgvārdi
            kw_variations = self.create_word_variations(kw)
            
            for variation in list(kw_variations)[:2]:  # Tikai 2 variācijas
                pattern = r'\b' + re.escape(variation) + r'\b'
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
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
                    break
                        
        return snippets
    
    def search_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Saderības metode"""
        return self.search_date_range_parallel(start_date, end_date)
        
    def check_local_files_status(self):
        """Pārbauda lokālo failu statusu"""
        metadata_file = Path('EIS-Automatic-Download/download_metadata.json')
        
        if not metadata_file.exists():
            return {
                'status': 'error',
                'message': 'Nav atrasti lejupielādēti faili. Palaidiet lejupielādētāju vispirms.'
            }
            
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            
        # Skaita XML failus
        total_xml = 0
        if self.xml_dir.exists():
            for date_dir in self.xml_dir.iterdir():
                if date_dir.is_dir():
                    xml_count = len(list(date_dir.glob('*.xml')))
                    total_xml += xml_count
            
        return {
            'status': 'ok',
            'last_update': metadata.get('last_update'),
            'total_files': metadata.get('total_files', 0),
            'total_xml_files': total_xml,
            'message': f"Pieejami {metadata.get('total_files', 0)} arhīvi ar {total_xml} XML failiem"
        }

class IepirkumuMekletajs:
    """Wrapper klase pilnai saderībai"""
    
    def __init__(self, config_file='config.json'):
        self.local_searcher = LokalaisMekletajs(config_file)
        self.config = self.local_searcher.config
        self.search_criteria = self.local_searcher.search_criteria
        
    def search_date_range(self, start_date, end_date):
        """Meklē norādītajā datumu diapazonā"""
        status = self.local_searcher.check_local_files_status()
        
        if status['status'] != 'ok':
            logging.error(status['message'])
            return []
            
        logging.info(f"Lokālie faili: {status['message']}")
        logging.info(f"Pēdējā atjaunošana: {status['last_update']}")
        
        return self.local_searcher.search_date_range(start_date, end_date)
