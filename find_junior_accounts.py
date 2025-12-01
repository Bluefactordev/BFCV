"""
Script per trovare candidati < 30 anni interessanti per Junior Account in digital agency.
Legge direttamente i file di cache JSON.
"""
import json
import os
import re
from pathlib import Path
import pandas as pd
from datetime import datetime

def extract_age(eta_str):
    """Estrae l'età numerica da una stringa."""
    if not eta_str or pd.isna(eta_str):
        return None
    
    try:
        # Prova conversione diretta
        age = int(float(str(eta_str)))
        if 18 <= age <= 35:
            return age
    except:
        pass
    
    # Cerca pattern numerici
    match = re.search(r'(\d{1,2})', str(eta_str))
    if match:
        try:
            age = int(match.group(1))
            if 18 <= age <= 35:
                return age
        except:
            pass
    
    return None

def is_interesting_for_junior_account(data):
    """Valuta interesse per Junior Account in digital agency."""
    score = 0
    reasons = []
    
    keywords_digital = ['digital', 'social media', 'marketing digitale', 'advertising', 
                       'agenzia', 'account', 'client', 'campagna', 'web', 'online',
                       'seo', 'sem', 'content', 'social', 'facebook', 'instagram',
                       'google ads', 'adwords', 'analytics', 'e-commerce', 'ecommerce']
    
    keywords_account = ['account', 'client', 'cliente', 'relationship', 'relazione',
                       'gestione clienti', 'customer', 'vendita', 'commerciale']
    
    # Combina tutti i dati
    all_text = " ".join([
        str(data.get('Nome', '')),
        str(data.get('Cognome', '')),
        str(data.get('Posizione attuale', '')),
        str(data.get('Datori di lavoro precedenti', '')),
        str(data.get('Formazione più alta', '')),
        str(data.get('Soft skills', '')),
    ]).lower()
    
    # Conta keyword
    digital_count = sum(1 for kw in keywords_digital if kw in all_text)
    account_count = sum(1 for kw in keywords_account if kw in all_text)
    
    if digital_count > 0:
        score += digital_count * 2
        reasons.append(f"Digital ({digital_count})")
    
    if account_count > 0:
        score += account_count * 3
        reasons.append(f"Account ({account_count})")
    
    # Verifica esperienza
    esperienza = str(data.get('Anni di esperienza lavorativa', '')).lower()
    if '0' in esperienza or 'junior' in all_text or 'trainee' in all_text:
        score += 5
        reasons.append("Junior/Trainee")
    
    if 'account' in all_text:
        score += 10
        reasons.append("Esperienza Account")
    
    if 'digital' in all_text or 'agenzia' in all_text:
        score += 8
        reasons.append("Digital/Agenzia")
    
    return score, reasons

def read_cache_files():
    """Legge tutti i file di cache e estrae i dati dei CV."""
    cache_dir = Path("ai_cache")
    all_cv_data = []
    
    if not cache_dir.exists():
        return all_cv_data
    
    # Cerca file che contengono dati di estrazione (hash bcf2e466 indica estrazione principale)
    cache_files = list(cache_dir.glob("openai-gpt-4o-mini-*.txt"))
    
    print(f"Trovati {len(cache_files)} file di cache, analizzando...")
    
    for cache_file in cache_files:
        try:
            with open(cache_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # I file di cache possono contenere JSON direttamente o come stringa JSON
            try:
                # Prova prima a leggere come JSON diretto
                data = json.loads(content)
                # Se è una stringa, prova a parsarla di nuovo
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and 'Nome' in data and 'Età' in data:
                    all_cv_data.append(data)
            except json.JSONDecodeError:
                # Prova a cercare JSON nel contenuto
                json_match = re.search(r'\{[^{}]*"Nome"[^{}]*\}', content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                        if isinstance(data, dict) and 'Nome' in data and 'Età' in data:
                            all_cv_data.append(data)
                    except:
                        pass
        except Exception as e:
            continue
    
    return all_cv_data

def main():
    print("=" * 80)
    print("RICERCA CANDIDATI < 30 ANNI PER JUNIOR ACCOUNT DIGITAL AGENCY")
    print("=" * 80)
    print()
    
    # Leggi i file di cache
    all_cv_data = read_cache_files()
    
    if not all_cv_data:
        print("[!] Nessun CV trovato nei file di cache.")
        return
    
    print(f"[OK] Analizzati {len(all_cv_data)} CV")
    print()
    
    # Carica CSV esistente se presente
    existing_candidates = {}
    try:
        df_existing = pd.read_csv('candidati_junior_account.csv')
        for _, row in df_existing.iterrows():
            key = f"{row['Nome']}_{row['Cognome']}_{row['Email']}"
            existing_candidates[key] = row.to_dict()
        print(f"[OK] Trovati {len(existing_candidates)} candidati già nel CSV")
    except:
        print("[!] Nessun CSV esistente trovato, creo nuovo file")
    
    # Filtra e analizza
    candidates = []
    new_candidates = []
    for cv in all_cv_data:
        # Estrai età
        age = extract_age(cv.get('Età', ''))
        
        if age is None or age >= 30:
            continue
        
        # Crea chiave univoca
        nome = cv.get('Nome', 'N/A')
        cognome = cv.get('Cognome', 'N/A')
        email = cv.get('Email', 'N/A')
        key = f"{nome}_{cognome}_{email}"
        
        # Valuta interesse
        interest_score, reasons = is_interesting_for_junior_account(cv)
        
        candidate_data = {
            'Nome': nome,
            'Cognome': cognome,
            'Età': age,
            'Email': email,
            'Città': cv.get('Città di residenza', 'N/A'),
            'Esperienza_anni': cv.get('Anni di esperienza lavorativa', 'N/A'),
            'Posizione_attuale': cv.get('Posizione attuale', 'N/A')[:50] if cv.get('Posizione attuale') else 'N/A',
            'Aziende_precedenti': cv.get('Datori di lavoro precedenti', 'N/A')[:80] if cv.get('Datori di lavoro precedenti') else 'N/A',
            'Formazione': cv.get('Formazione più alta', 'N/A')[:50] if cv.get('Formazione più alta') else 'N/A',
            'Lingue': cv.get('Lingue conosciute', 'N/A')[:30] if cv.get('Lingue conosciute') else 'N/A',
            'Punteggio_interesse': interest_score,
            'Motivi': "; ".join(reasons) if reasons else "Nessuno specifico",
        }
        
        # Aggiungi se nuovo o aggiorna se esistente
        if key not in existing_candidates:
            new_candidates.append(candidate_data)
            candidates.append(candidate_data)
        else:
            # Mantieni quello esistente ma aggiorna se necessario
            candidates.append(existing_candidates[key])
    
    if not candidates:
        print("[!] Nessun candidato < 30 anni trovato.")
        return
    
    print(f"[OK] Trovati {len(new_candidates)} nuovi candidati da aggiungere")
    print()
    
    # Ordina per punteggio
    candidates.sort(key=lambda x: x['Punteggio_interesse'], reverse=True)
    
    # Mostra risultati
    print("=" * 80)
    print(f"TOTALE CANDIDATI: {len(candidates)} ({len(new_candidates)} nuovi)")
    print("=" * 80)
    print()
    
    if new_candidates:
        print("NUOVI CANDIDATI AGGIUNTI:")
        for i, cand in enumerate(new_candidates, 1):
            print(f"  {i}. {cand['Nome']} {cand['Cognome']} - {cand['Età']} anni ({cand['Email']})")
        print()
    
    # Salva in CSV
    df = pd.DataFrame(candidates)
    output_file = "candidati_junior_account.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"[OK] CSV aggiornato: {output_file}")
    print(f"     Totale candidati: {len(candidates)}")
    print(f"     Nuovi aggiunti: {len(new_candidates)}")
    print()
    print(f"Top 3 candidati più interessanti:")
    for i, cand in enumerate(candidates[:3], 1):
        print(f"  {i}. {cand['Nome']} {cand['Cognome']} ({cand['Età']} anni) - Punteggio: {cand['Punteggio_interesse']}")

if __name__ == "__main__":
    main()

