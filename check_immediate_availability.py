"""
Script per identificare candidati < 30 anni potenzialmente disponibili subito
(senza preavviso o con preavviso molto breve)
"""
import pandas as pd
import re

def check_immediate_availability(row):
    """Valuta se un candidato potrebbe essere disponibile subito."""
    score = 0
    indicators = []
    
    posizione = str(row.get('Posizione_attuale', '')).lower()
    esperienza = str(row.get('Esperienza_anni', ''))
    
    # Indicatori di disponibilità immediata
    # 1. Stage/Internship/Tirocinio
    if any(term in posizione for term in ['internship', 'stage', 'tirocinio', 'trainee', 'stages']):
        score += 10
        indicators.append("STAGE/INTERNSHIP - Disponibilità immediata")
    
    # 2. Posizioni junior (spesso contratti più flessibili)
    if 'junior' in posizione:
        score += 5
        indicators.append("Posizione JUNIOR - Contratti più flessibili")
    
    # 3. Lavori stagionali/temporanei
    if any(term in posizione for term in ['cameriere', 'barista', 'stagionale', 'temporaneo', 'part-time']):
        score += 8
        indicators.append("Lavoro TEMPORANEO/STAGIONALE - Disponibilità immediata")
    
    # 4. Poca esperienza (1-2 anni) = contratti più brevi
    try:
        exp_years = float(re.search(r'[\d.]+', esperienza).group(0)) if re.search(r'[\d.]+', esperienza) else 0
        if exp_years <= 2:
            score += 3
            indicators.append(f"Esperienza limitata ({exp_years} anni) - Contratti più brevi")
    except:
        pass
    
    # 5. Età molto giovane (21-23) = spesso stage o primi lavori
    eta = row.get('Età', 0)
    if 21 <= eta <= 23:
        score += 2
        indicators.append("Età giovane - Maggiore flessibilità")
    
    # 6. Posizioni in università/ricerca (spesso stage)
    if any(term in posizione for term in ['research', 'università', 'university', 'scuola', 'department']):
        score += 6
        indicators.append("Posizione in UNIVERSITÀ/RICERCA - Spesso stage")
    
    return score, indicators

def main():
    print("=" * 80)
    print("ANALISI DISPONIBILITÀ IMMEDIATA - Candidati < 30 anni")
    print("=" * 80)
    print()
    
    # Leggi il CSV
    df = pd.read_csv('candidati_junior_account.csv')
    
    # Analizza disponibilità
    results = []
    for idx, row in df.iterrows():
        availability_score, indicators = check_immediate_availability(row)
        
        if availability_score > 0:  # Solo quelli con indicatori positivi
            results.append({
                'Nome': f"{row['Nome']} {row['Cognome']}",
                'Età': row['Età'],
                'Email': row['Email'],
                'Città': row['Città'],
                'Posizione_attuale': row['Posizione_attuale'],
                'Esperienza_anni': row['Esperienza_anni'],
                'Punteggio_disponibilità': availability_score,
                'Indicatori': "; ".join(indicators),
                'Punteggio_interesse': row['Punteggio_interesse'],
            })
    
    if not results:
        print("[!] Nessun candidato con indicatori di disponibilità immediata trovato.")
        return
    
    # Ordina per punteggio disponibilità (decrescente)
    results.sort(key=lambda x: x['Punteggio_disponibilità'], reverse=True)
    
    print(f"CANDIDATI POTENZIALMENTE DISPONIBILI SUBITO: {len(results)}")
    print("=" * 80)
    print()
    
    for i, cand in enumerate(results, 1):
        print(f"{i}. {cand['Nome']} - {cand['Età']} anni")
        print(f"   Email: {cand['Email']}")
        print(f"   Città: {cand['Città']}")
        print(f"   Posizione attuale: {cand['Posizione_attuale']}")
        print(f"   Esperienza: {cand['Esperienza_anni']} anni")
        print(f"   Punteggio disponibilità: {cand['Punteggio_disponibilità']}/20")
        print(f"   Punteggio interesse ruolo: {cand['Punteggio_interesse']}")
        print(f"   Indicatori: {cand['Indicatori']}")
        print()
    
    # Top candidati
    print("=" * 80)
    print("TOP CANDIDATI DISPONIBILI SUBITO:")
    print("=" * 80)
    for i, cand in enumerate(results[:5], 1):
        print(f"{i}. {cand['Nome']} ({cand['Età']} anni)")
        print(f"   {cand['Posizione_attuale']}")
        print(f"   Disponibilità: {cand['Punteggio_disponibilità']}/20 | Interesse: {cand['Punteggio_interesse']}")
        print()
    
    # Salva risultati
    df_results = pd.DataFrame(results)
    df_results.to_csv('candidati_disponibili_subito.csv', index=False, encoding='utf-8-sig')
    print(f"[OK] Risultati salvati in candidati_disponibili_subito.csv")

if __name__ == "__main__":
    main()




