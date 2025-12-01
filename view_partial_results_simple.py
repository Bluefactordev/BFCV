"""
Script semplice per visualizzare una volta i risultati parziali.
Esegui: python view_partial_results_simple.py
"""
import json
import pandas as pd
from pathlib import Path
import os

def get_latest_partial_results():
    """Recupera i risultati parziali più recenti."""
    try:
        partial_dir = Path(os.path.abspath(os.getcwd())) / "partial_results"
        if not partial_dir.exists():
            return None
        
        latest_file = partial_dir / "partial_results_latest.json"
        if not latest_file.exists():
            partial_files = list(partial_dir.glob("partial_results_*.json"))
            if not partial_files:
                return None
            partial_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest_file = partial_files[0]
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        print(f"Errore: {str(e)}")
        return None

def main():
    partial_data = get_latest_partial_results()
    
    if not partial_data or not partial_data.get("results"):
        print("[!] Nessun risultato parziale trovato.")
        return
    
    results = partial_data["results"]
    fields = partial_data.get("fields", [])
    timestamp = partial_data.get("timestamp", "N/A")
    
    print("=" * 80)
    print(f"RISULTATI PARZIALI - {len(results)} CV ANALIZZATI")
    print(f"Ultimo aggiornamento: {timestamp}")
    print("=" * 80)
    print()
    
    data_list = []
    for result in results:
        row = {"File_PDF": result.get("filename", "")}
        
        if "result" in result and "composite_score" in result["result"]:
            try:
                raw_score = result["result"]["composite_score"]
                row["Punteggio"] = int(float(raw_score) if raw_score is not None else 0)
            except:
                row["Punteggio"] = 0
        else:
            row["Punteggio"] = 0
        
        for field in fields:
            if "result" in result and "extraction" in result["result"] and field in result["result"]["extraction"]:
                value = result["result"]["extraction"][field]
                row[field] = ", ".join(map(str, value)) if isinstance(value, list) else value
        
        data_list.append(row)
    
    if data_list:
        df = pd.DataFrame(data_list)
        if "Punteggio" in df.columns:
            df = df.sort_values("Punteggio", ascending=False)
        
        # Mostra solo le colonne principali per non sovraccaricare
        cols_to_show = ["File_PDF", "Punteggio"] + [f for f in fields[:5] if f in df.columns]
        print(df[cols_to_show].to_string(index=False))
        print()
        print(f"[OK] Totale: {len(df)} CV | Media: {df['Punteggio'].mean():.1f} | Max: {df['Punteggio'].max()}")
    else:
        print("[!] Nessun dato disponibile.")

if __name__ == "__main__":
    main()

