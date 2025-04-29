"""
Script per garantire che la cache funzioni correttamente nel progetto BFCV
"""
import os
import shutil
import datetime

def backup_file(file_path):
    """Crea una copia di backup del file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_cache_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Backup creato: {backup_path}")
    return backup_path

def fix_cache_variable():
    """Aggiunge l'inizializzazione della variabile use_cache nella session_state"""
    file_path = "bfcv_007.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Cerca il blocco dove vengono inizializzate le variabili di sessione
    init_block = "# Inizializzazione di use_ollama se non presente\n    if 'use_ollama' not in st.session_state:\n        st.session_state.use_ollama = False"
    
    # Aggiungi l'inizializzazione di use_cache
    replacement = init_block + "\n\n    # Inizializzazione di use_cache se non presente\n    if 'use_cache' not in st.session_state:\n        st.session_state.use_cache = True"
    
    new_content = content.replace(init_block, replacement)
    
    # Aggiungi controllo use_cache nei checkbox
    checkbox_pattern = "cache_enabled = st.checkbox(\"Usa cache per le richieste AI\", value=True)"
    checkbox_replacement = "cache_enabled = st.checkbox(\"Usa cache per le richieste AI\", value=st.session_state.use_cache)\n        st.session_state.use_cache = cache_enabled"
    
    new_content = new_content.replace(checkbox_pattern, checkbox_replacement)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Variabile cache inizializzata correttamente nella session_state")
    
def main():
    """Funzione principale"""
    print("⚙️ Fixing cache in BFCV...")
    
    # Verifica la presenza del file
    file_path = "bfcv_007.py"
    if not os.path.exists(file_path):
        print(f"❌ Errore: File {file_path} non trovato!")
        return

    # Backup del file originale
    backup_file(file_path)
    
    # Correggi il problema della cache
    fix_cache_variable()
    
    print("\n✅ Cache fixing completato con successo!")
    print("Riavvia l'applicazione per applicare le modifiche.")

if __name__ == "__main__":
    main() 