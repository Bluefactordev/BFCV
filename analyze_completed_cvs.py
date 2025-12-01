"""
Script per analizzare i CV già elaborati dai log e trovare candidati interessanti.
Cerca candidati < 30 anni interessanti per ruolo di Junior Account in digital agency.
"""
import json
import re
import os
from pathlib import Path
from datetime import datetime
import pandas as pd

def extract_age(text):
    """Estrae l'età da un testo."""
    if not text or pd.isna(text):
        return None
    
    text_str = str(text).lower()
    # Cerca pattern come "27 anni", "age: 28", "nato nel 1995", etc.
    patterns = [
        r'(\d+)\s*anni',
        r'et[àa]\s*:?\s*(\d+)',
        r'age\s*:?\s*(\d+)',
        r'nato\s+(?:nel\s+)?(\d{4})',
        r'(\d{2})\s*anni',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_str)
        if match:
            age_str = match.group(1)
            try:
                age = int(age_str)
                # Se è un anno (4 cifre), calcola l'età
                if len(age_str) == 4 and 1950 <= age <= 2010:
                    current_year = datetime.now().year
                    age = current_year - age
                return age
            except:
                pass
    
    # Cerca numeri che potrebbero essere età
    numbers = re.findall(r'\b(1[89]|2[0-9]|3[0-5])\b', text_str)
    if numbers:
        try:
            return int(numbers[0])
        except:
            pass
    
    return None

def is_interesting_for_junior_account(data):
    """Valuta se un CV è interessante per il ruolo di Junior Account in digital agency."""
    score = 0
    reasons = []
    
    # Cerca keyword rilevanti
    keywords_digital = ['digital', 'social media', 'marketing digitale', 'advertising', 
                       'agenzia', 'account', 'client', 'campagna', 'web', 'online',
                       'seo', 'sem', 'content', 'social', 'facebook', 'instagram',
                       'google ads', 'adwords', 'analytics', 'e-commerce', 'ecommerce']
    
    keywords_account = ['account', 'client', 'cliente', 'relationship', 'relazione',
                       'gestione clienti', 'customer', 'vendita', 'commerciale']
    
    keywords_communication = ['comunicazione', 'communication', 'pubblicità', 'advertising',
                            'marketing', 'brand', 'campagna', 'strategia']
    
    # Combina tutti i dati in un testo unico per la ricerca
    all_text = " ".join([
        str(data.get('Nome', '')),
        str(data.get('Cognome', '')),
        str(data.get('Esperienza', '')),
        str(data.get('Competenze', '')),
        str(data.get('Ruolo attuale', '')),
        str(data.get('Ruoli precedenti', '')),
        str(data.get('Formazione', '')),
    ]).lower()
    
    # Conta keyword digital
    digital_count = sum(1 for kw in keywords_digital if kw in all_text)
    if digital_count > 0:
        score += digital_count * 2
        reasons.append(f"Competenze digital ({digital_count} keyword)")
    
    # Conta keyword account
    account_count = sum(1 for kw in keywords_account if kw in all_text)
    if account_count > 0:
        score += account_count * 3
        reasons.append(f"Esperienza account/clienti ({account_count} keyword)")
    
    # Conta keyword comunicazione
    comm_count = sum(1 for kw in keywords_communication if kw in all_text)
    if comm_count > 0:
        score += comm_count * 1
        reasons.append(f"Competenze comunicazione ({comm_count} keyword)")
    
    # Verifica esperienza
    esperienza = str(data.get('Esperienza', '')).lower()
    if 'junior' in esperienza or 'trainee' in esperienza or 'stage' in esperienza:
        score += 5
        reasons.append("Esperienza junior/trainee")
    
    if 'account' in esperienza.lower():
        score += 10
        reasons.append("Esperienza diretta come Account")
    
    if 'digital' in esperienza.lower() or 'agenzia' in esperienza.lower():
        score += 8
        reasons.append("Esperienza in digital/agenzia")
    
    # Verifica formazione
    formazione = str(data.get('Formazione', '')).lower()
    if any(kw in formazione for kw in ['marketing', 'comunicazione', 'economia', 'management']):
        score += 3
        reasons.append("Formazione rilevante")
    
    return score, reasons

def parse_log_file(log_path):
    """Estrae i dati dei CV dal file di log."""
    cv_data = []
    current_cv = {}
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Cerca inizio di un nuovo CV
            if 'Analisi completata per' in line or 'CACHE RESPONSE' in line:
                # Se c'era un CV precedente, salvalo
                if current_cv and 'Nome' in current_cv:
                    cv_data.append(current_cv.copy())
                    current_cv = {}
                
                # Cerca il nome del file
                filename_match = re.search(r'Analisi completata per (.+\.pdf)', line)
                if filename_match:
                    current_cv['File_PDF'] = filename_match.group(1)
            
            # Cerca dati estratti (formato JSON nel log)
            if 'CACHE RESPONSE' in line or '"Nome"' in line:
                # Prova a estrarre JSON dalle righe successive
                json_lines = []
                j = i
                while j < min(i + 50, len(lines)) and ('}' not in lines[j] or len(json_lines) < 10):
                    json_lines.append(lines[j])
                    j += 1
                
                json_text = " ".join(json_lines)
                # Cerca JSON nel testo
                json_match = re.search(r'\{[^{}]*"Nome"[^{}]*\}', json_text)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                        current_cv.update(data)
                    except:
                        pass
            
            # Cerca pattern specifici nei log
            if 'Nome:' in line or '"Nome"' in line:
                nome_match = re.search(r'["\']?Nome["\']?\s*:?\s*["\']?([^"\',\n]+)', line)
                if nome_match:
                    current_cv['Nome'] = nome_match.group(1).strip()
            
            if 'Età' in line or 'eta' in line.lower():
                eta_match = re.search(r'["\']?Et[àa]["\']?\s*:?\s*["\']?([^"\',\n]+)', line, re.IGNORECASE)
                if eta_match:
                    current_cv['Età'] = eta_match.group(1).strip()
            
            i += 1
        
        # Aggiungi l'ultimo CV se presente
        if current_cv and 'Nome' in current_cv:
            cv_data.append(current_cv)
    
    except Exception as e:
        print(f"Errore nel parsing del log {log_path}: {str(e)}")
    
    return cv_data

def analyze_cache_files():
    """Analizza i file di cache per trovare CV già analizzati."""
    cache_dir = Path("ai_cache")
    cv_data = []
    
    if not cache_dir.exists():
        return cv_data
    
    # Cerca file JSON nella cache
    for cache_file in cache_dir.rglob("*.json"):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Se il file contiene dati di un CV
            if isinstance(data, dict) and ('Nome' in data or 'extraction' in data):
                if 'extraction' in data:
                    cv_data.append(data['extraction'])
                else:
                    cv_data.append(data)
        except:
            pass
    
    return cv_data

def main():
    print("=" * 80)
    print("ANALISI CV COMPLETATI - Candidati < 30 anni per Junior Account Digital Agency")
    print("=" * 80)
    print()
    
    all_cv_data = []
    
    # 1. Analizza i log più recenti
    logs_dir = Path("logs")
    if logs_dir.exists():
        log_files = sorted(logs_dir.glob("scores_debug_*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        print(f"Analizzando {len(log_files[:5])} log file più recenti...")
        for log_file in log_files[:5]:
            data = parse_log_file(log_file)
            all_cv_data.extend(data)
    
    # 2. Analizza i file di cache
    print("Analizzando file di cache...")
    cache_data = analyze_cache_files()
    all_cv_data.extend(cache_data)
    
    if not all_cv_data:
        print("[!] Nessun CV trovato nei log/cache.")
        return
    
    print(f"[OK] Trovati {len(all_cv_data)} CV da analizzare")
    print()
    
    # Filtra e analizza
    candidates = []
    for cv in all_cv_data:
        # Estrai età
        age = None
        if 'Età' in cv:
            age = extract_age(cv['Età'])
        elif 'Età_numero' in cv:
            age = cv['Età_numero']
        
        # Filtra per età < 30
        if age is None or age >= 30:
            continue
        
        # Valuta interesse per junior account
        interest_score, reasons = is_interesting_for_junior_account(cv)
        
        candidates.append({
            'Nome': cv.get('Nome', 'N/A'),
            'Cognome': cv.get('Cognome', 'N/A'),
            'Età': age,
            'File_PDF': cv.get('File_PDF', 'N/A'),
            'Punteggio_interesse': interest_score,
            'Motivi': "; ".join(reasons),
            'Esperienza': cv.get('Esperienza', 'N/A')[:100] if cv.get('Esperienza') else 'N/A',
            'Competenze': cv.get('Competenze', 'N/A')[:100] if cv.get('Competenze') else 'N/A',
            'Formazione': cv.get('Formazione', 'N/A')[:100] if cv.get('Formazione') else 'N/A',
        })
    
    if not candidates:
        print("[!] Nessun candidato < 30 anni trovato.")
        return
    
    # Ordina per punteggio di interesse
    candidates.sort(key=lambda x: x['Punteggio_interesse'], reverse=True)
    
    # Mostra risultati
    print("=" * 80)
    print(f"CANDIDATI TROVATI: {len(candidates)}")
    print("=" * 80)
    print()
    
    for i, cand in enumerate(candidates[:10], 1):  # Mostra top 10
        print(f"{i}. {cand['Nome']} {cand['Cognome']} - {cand['Età']} anni")
        print(f"   File: {cand['File_PDF']}")
        print(f"   Punteggio interesse: {cand['Punteggio_interesse']}")
        print(f"   Motivi: {cand['Motivi']}")
        print(f"   Esperienza: {cand['Esperienza']}")
        print(f"   Competenze: {cand['Competenze']}")
        print()
    
    # Salva in CSV
    df = pd.DataFrame(candidates)
    output_file = "candidati_junior_account.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"[OK] Risultati salvati in {output_file}")

if __name__ == "__main__":
    main()




