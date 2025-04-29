"""
Script per migliorare il logging nell'applicazione BFCV
"""
import os
import shutil
import datetime
import re

def backup_file(file_path):
    """Crea una copia di backup del file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_logging_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Backup creato: {backup_path}")
    return backup_path

def enhance_scores_logger(content):
    """Migliora il logger dedicato ai punteggi per registrare maggiori informazioni"""
    print("Miglioramento del logger dei punteggi...")
    
    # Nuovo formato per il logger con più dettagli
    pattern = r'formatter = logging\.Formatter\(\'%\(asctime\)s - %\(levelname\)s - %\(message\)s\'\)'
    replacement = "formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s')"
    
    # Applica la modifica
    modified_content = content.replace(pattern, replacement)
    
    # Aggiunge ulteriori log all'avvio
    init_pattern = r'scores_logger\.info\(f"================ AVVIO DEBUGGING PUNTEGGI ================"\)'
    init_replacement = 'scores_logger.info(f"================ AVVIO DEBUGGING PUNTEGGI ================")' + '''
        scores_logger.info(f"Python version: {sys.version}")
        scores_logger.info(f"Directory di lavoro: {os.getcwd()}")
        scores_logger.info(f"Log file: {log_file_path}")
        if 'model' in st.session_state:
            scores_logger.info(f"Modello OpenAI configurato: {st.session_state.model}")
        if 'ollama_model' in st.session_state:
            scores_logger.info(f"Modello Ollama configurato: {st.session_state.ollama_model}")
        if 'use_ollama' in st.session_state:
            scores_logger.info(f"Uso Ollama: {st.session_state.use_ollama}")
        if 'use_cache' in st.session_state:
            scores_logger.info(f"Cache abilitata: {st.session_state.use_cache}")'''
    
    modified_content = modified_content.replace(init_pattern, init_replacement)
    
    return modified_content

def add_logging_to_api_calls(content):
    """Aggiunge logging ai punti in cui vengono chiamate le API AI"""
    print("Aggiunta logging alle chiamate API...")
    
    # Aggiunge logging prima della chiamata a OpenAI
    openai_call_pattern = r'response = client\.chat\.completions\.create\('
    openai_call_replacement = '''scores_logger.info(f"CHIAMATA OPENAI - Modello: {st.session_state.model}")
                scores_logger.info(f"PROMPT: {prompt[:500]}..." if len(prompt) > 500 else f"PROMPT: {prompt}")
                response = client.chat.completions.create('''
    
    modified_content = content.replace(openai_call_pattern, openai_call_replacement)
    
    # Aggiunge logging prima della chiamata a Ollama
    ollama_call_pattern = r'response = requests\.post\(\s+"http://localhost:11434/api/generate",'
    ollama_call_replacement = '''scores_logger.info(f"CHIAMATA OLLAMA - Modello: {st.session_state.ollama_model}")
                scores_logger.info(f"PROMPT: {prompt[:500]}..." if len(prompt) > 500 else f"PROMPT: {prompt}")
                response = requests.post(
                    "http://localhost:11434/api/generate",'''
    
    modified_content = modified_content.replace(ollama_call_pattern, ollama_call_replacement)
    
    # Aggiunge logging per le risposte
    response_pattern = r'(save_to_cache\(model_name, prompt, result\))'
    response_replacement = r'''scores_logger.info(f"RISPOSTA (troncata): {str(result)[:500]}..." if len(str(result)) > 500 else f"RISPOSTA: {result}")
                \1'''
    
    modified_content = re.sub(response_pattern, response_replacement, modified_content)
    
    return modified_content

def enhance_cache_logging(content):
    """Migliora il logging relativo alla cache"""
    print("Miglioramento del logging della cache...")
    
    # Miglior logging per cache hit
    cache_hit_pattern = r'logger\.info\(f"Trovata risposta nella cache per {model_name}"\)'
    cache_hit_replacement = '''logger.info(f"Trovata risposta nella cache per {model_name}")
                scores_logger.info(f"CACHE HIT: {model_name}, hash={hashlib.md5(prompt.encode('utf-8')).hexdigest()[:8]}...")
                # Log della risposta troncata per debug
                result_str = cached_result if isinstance(cached_result, str) else json.dumps(cached_result)
                truncated_result = result_str[:300] + "..." if len(result_str) > 300 else result_str
                scores_logger.debug(f"CACHE RESPONSE (troncato): {truncated_result}")'''
    
    modified_content = content.replace(cache_hit_pattern, cache_hit_replacement)
    
    # Miglior logging per cache miss
    cache_miss_pattern = r'logger\.info\(f"Nessuna cache trovata per {model_name} con hash {.*}"\)'
    cache_miss_replacement = '''logger.info(f"Nessuna cache trovata per {model_name} con hash {hashlib.md5(prompt.encode('utf-8')).hexdigest()}")
            scores_logger.info(f"CACHE MISS: Modello={model_name}, Hash={hashlib.md5(prompt.encode('utf-8')).hexdigest()[:8]}...")'''
    
    modified_content = re.sub(cache_miss_pattern, cache_miss_replacement, modified_content)
    
    return modified_content

def fix_logging(file_path):
    """Applica tutte le migliorie al logging"""
    print(f"Miglioramento del logging in {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Applica le modifiche in sequenza
    modified_content = enhance_scores_logger(content)
    modified_content = add_logging_to_api_calls(modified_content)
    modified_content = enhance_cache_logging(modified_content)
    
    # Scrivi il contenuto modificato
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("✅ Miglioramenti al logging applicati!")
    return True

def main():
    """Funzione principale"""
    print("Inizio miglioramento del logging...")
    
    file_path = "bfcv_007.py"
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} non trovato!")
        return False
    
    # Crea un backup
    backup_file(file_path)
    
    # Applica i miglioramenti
    success = fix_logging(file_path)
    
    if success:
        print("\n✅ Miglioramenti al logging completati con successo!")
        print("Ora avrai log più dettagliati con le seguenti informazioni:")
        print("  - Prompt e risposte delle chiamate AI")
        print("  - Operazioni di cache")
        print("  - Dettagli sui calcoli dei punteggi")
        print("  - Informazioni di sistema")
        print("Per vedere i risultati, esegui launcher.py e controlla i file nella cartella logs/")
    else:
        print("\n❌ Si sono verificati errori durante il miglioramento del logging.")
    
    return success

if __name__ == "__main__":
    main() 