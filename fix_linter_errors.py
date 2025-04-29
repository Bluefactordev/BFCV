"""
Script per correggere gli errori di linting in bfcv_007.py
1. Errore alla riga 1535: Carattere non valido "\u5c" nel token
2. Errore alla riga 2240: L'indentazione non corrisponde all'indentazione precedente
3. Errore alla riga 3292: Blocco indentato previsto
"""
import os
import shutil
import datetime

def backup_file(file_path):
    """Crea una copia di backup del file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_linter_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Backup creato: {backup_path}")
    return backup_path

def fix_linter_errors(file_path):
    """Corregge gli errori di linting specifici nel file"""
    print("Lettura del file...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Correggi l'errore alla riga 1535 (carattere non valido)
    print("Correzione carattere non valido alla riga 1535...")
    if len(lines) >= 1535:
        lines[1534] = '    """Analizza un CV con OpenAI"""\n'
    
    # Correggi l'errore alla riga 2240 (indentazione)
    print("Correzione indentazione alla riga 2240...")
    if len(lines) >= 2240:
        lines[2239] = '                    st.warning(f"Errore nel punteggio per {criteria_id}")\n'
    
    # Correggi l'errore alla riga 3292 (blocco indentato)
    print("Correzione blocco indentato alla riga 3292...")
    if len(lines) >= 3292:
        lines[3291] = '            st.subheader("Campi da estrarre")\n'
    
    # Scrivi le modifiche nel file
    print("Scrittura delle correzioni...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✅ Errori di linting corretti!")

def main():
    file_path = "bfcv_007.py"
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} non trovato!")
        return False
    
    # Backup del file originale
    backup_file(file_path)
    
    # Correggi gli errori
    fix_linter_errors(file_path)
    
    print("\n✅ Correzioni completate con successo!")
    print("Per verificare le correzioni, esegui il launcher.py")
    
    return True

if __name__ == "__main__":
    main() 