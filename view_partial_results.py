"""
Script per visualizzare i risultati parziali dell'analisi CV in corso.
Può essere eseguito mentre bfcv_008.py è in esecuzione.
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

def get_latest_partial_results():
    """Recupera i risultati parziali più recenti."""
    try:
        partial_dir = Path(os.path.abspath(os.getcwd())) / "partial_results"
        if not partial_dir.exists():
            return None
        
        # Cerca il file latest
        latest_file = partial_dir / "partial_results_latest.json"
        if not latest_file.exists():
            # Fallback: trova il file più recente
            partial_files = list(partial_dir.glob("partial_results_*.json"))
            if not partial_files:
                return None
            partial_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest_file = partial_files[0]
        
        # Leggi il file
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        print(f"Errore nel recupero dei risultati parziali: {str(e)}")
        return None

def display_partial_results():
    """Mostra i risultati parziali in formato tabellare."""
    partial_data = get_latest_partial_results()
    
    if not partial_data or not partial_data.get("results"):
        print("[!] Nessun risultato parziale trovato.")
        print("   Avvia un'analisi per generare risultati parziali.")
        return
    
    results = partial_data["results"]
    fields = partial_data.get("fields", [])
    timestamp = partial_data.get("timestamp", "N/A")
    
    print("=" * 80)
    print(f"RISULTATI PARZIALI - {len(results)} CV ANALIZZATI")
    print(f"Ultimo aggiornamento: {timestamp}")
    print("=" * 80)
    print()
    
    # Prepara il DataFrame
    data_list = []
    for result in results:
        row = {
            "File_PDF": result.get("filename", ""),
            "file_path": result.get("path", "")
        }
        
        # Aggiungi il punteggio composito
        if "result" in result and "composite_score" in result["result"]:
            try:
                raw_score = result["result"]["composite_score"]
                row["Punteggio_composito"] = int(float(raw_score) if raw_score is not None else 0)
            except (ValueError, TypeError):
                row["Punteggio_composito"] = 0
        else:
            row["Punteggio_composito"] = 0
        
        # Aggiungi le informazioni estratte
        for field in fields:
            if "result" in result and "extraction" in result["result"] and field in result["result"]["extraction"]:
                value = result["result"]["extraction"][field]
                if isinstance(value, list):
                    row[field] = ", ".join(map(str, value))
                else:
                    row[field] = value
        
        data_list.append(row)
    
    if not data_list:
        print("[!] Nessun dato disponibile nei risultati parziali.")
        return
    
    # Crea DataFrame e mostra
    df = pd.DataFrame(data_list)
    
    # Ordina per punteggio composito (decrescente)
    if "Punteggio_composito" in df.columns:
        df = df.sort_values("Punteggio_composito", ascending=False)
    
    # Mostra la tabella
    print(df.to_string(index=False))
    print()
    print("=" * 80)
    print(f"[OK] Totale: {len(df)} CV analizzati")
    
    # Statistiche rapide
    if "Punteggio_composito" in df.columns:
        print(f"Punteggio medio: {df['Punteggio_composito'].mean():.1f}")
        print(f"Punteggio max: {df['Punteggio_composito'].max()}")
        print(f"Punteggio min: {df['Punteggio_composito'].min()}")
    
    print("=" * 80)
    print()
    print("Suggerimento: Esegui questo script periodicamente per vedere i progressi!")
    print("   (Premi Ctrl+C per uscire)")

if __name__ == "__main__":
    import time
    import sys
    
    print("Monitoraggio risultati parziali...")
    print("   (Premi Ctrl+C per uscire)")
    print()
    
    try:
        while True:
            # Pulisci lo schermo (funziona su Windows e Linux/Mac)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            display_partial_results()
            
            print()
            print("Aggiornamento automatico tra 5 secondi...")
            time.sleep(5)
    except KeyboardInterrupt:
        print()
        print("Uscita dal monitoraggio.")

