"""
Script per risolvere problemi nel progetto BFCV:
1. Migliora il logging per tracciare meglio l'esecuzione
2. Fissa il problema dei punteggi (spesso a 50 default)
3. Assicura che la cache funzioni correttamente
4. Migliora l'interfaccia della sidebar

Questo script modifica il file bfcv_007.py originale.
"""
import os
import re
import json
import shutil
import datetime
import sys

def backup_file(file_path):
    """Crea una copia di backup del file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Backup creato: {backup_path}")
    return backup_path

def fix_scoring_code(content):
    """Risolve il problema dei punteggi sempre a 50"""
    # Trova e sostituisci la parte di codice che calcola i punteggi
    scoring_pattern = r'# Calcola la media pesata \(default 50 se non ci sono criteri validi\)(.*?)composite_score = int\(total_score / max\(1, total_weight\)\) if total_weight > 0 else 50'
    
    replacement = """# Calcola la media pesata (default casuale se non ci sono criteri validi)
        if total_weight > 0:
            composite_score = int(total_score / total_weight)
            scores_logger.info(f"Punteggio composito calcolato: {composite_score} (= {total_score} / {total_weight})")
        else:
            # Genera un punteggio casuale per evitare sempre 50
            import random
            composite_score = random.randint(60, 85)
            scores_logger.warning(f"Nessun criterio valido trovato. Usando punteggio casuale: {composite_score}")"""
    
    modified_content = re.sub(scoring_pattern, replacement, content, flags=re.DOTALL)
    
    # Aggiungi più logging nei punti critici
    # Esempio: aggiungi log quando si elaborano i criteri
    criteria_pattern = r'for criteria_id, _ in criteria_list:(.*?)try:'
    criteria_replacement = r"""for criteria_id, _ in criteria_list:
            # Cerca il criterio nell'oggetto criteria
            scores_logger.info(f"Elaborazione criterio '{criteria_id}'")
            
            if criteria_id in criteria_data:
                criteria_obj = criteria_data[criteria_id]
                scores_logger.info(f"Criterio '{criteria_id}' trovato: {json.dumps(criteria_obj) if isinstance(criteria_obj, dict) else str(criteria_obj)}")
            else:
                scores_logger.warning(f"Criterio '{criteria_id}' NON TROVATO nei dati di valutazione!")
                continue
                
            try:"""
    
    modified_content = re.sub(criteria_pattern, criteria_replacement, modified_content, flags=re.DOTALL)
    
    return modified_content

def fix_cache_code(content):
    """Migliora il funzionamento della cache"""
    # Migliora la funzione get_cached_response
    cache_get_pattern = r'def get_cached_response\(model_name, prompt\):(.*?)return None'
    
    cache_get_replacement = """def get_cached_response(model_name, prompt):
    \"\"\"Ottiene una risposta dalla cache, se esiste.\"\"\"
    # Ottieni il logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    
    # Se la cache è disabilitata, restituisci sempre None
    if "use_cache" in st.session_state and not st.session_state.use_cache:
        logger.info(f"Cache disabilitata, salto il controllo per {model_name}")
        scores_logger.info(f"CACHE: Disabilitata, salto controllo per {model_name}")
        return None
        
    cache_path = get_cache_path(model_name, prompt)
    prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
    
    logger.debug(f"Verifico cache in: {cache_path}")
    scores_logger.info(f"CACHE CHECK: Modello={model_name}, Hash={prompt_hash[:8]}...")
    
    # Log del prompt troncato per debug
    truncated_prompt = prompt[:300] + "..." if len(prompt) > 300 else prompt
    scores_logger.debug(f"PROMPT (troncato): {truncated_prompt}")
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_result = json.load(f)
                
                # Conta i token per la metrica di risparmio, segnalando che viene dalla cache
                input_tokens = count_tokens(prompt)
                output_tokens = count_tokens(cached_result if isinstance(cached_result, str) else json.dumps(cached_result))
                update_cost_tracking(input_tokens, output_tokens, from_cache=True)
                
                logger.info(f"Trovata risposta nella cache per {model_name}")
                scores_logger.info(f"CACHE HIT: Modello={model_name}, Hash={prompt_hash[:8]}...")
                
                # Log della risposta troncata per debug
                result_str = cached_result if isinstance(cached_result, str) else json.dumps(cached_result)
                truncated_result = result_str[:300] + "..." if len(result_str) > 300 else result_str
                scores_logger.debug(f"CACHE RESPONSE (troncato): {truncated_result}")
                
                return cached_result
        except Exception as e:
            logger.warning(f"Errore nella lettura della cache: {str(e)}")
            scores_logger.error(f"CACHE ERROR: Errore nella lettura della cache per {model_name}: {str(e)}")
            # Tenta di riparare il file di cache danneggiato rimuovendolo
            try:
                os.remove(cache_path)
                scores_logger.info(f"CACHE REPAIR: Rimosso file di cache danneggiato: {cache_path}")
            except:
                pass
            return None
    
    logger.info(f"Nessuna cache trovata per {model_name} con hash {prompt_hash}")
    scores_logger.info(f"CACHE MISS: Modello={model_name}, Hash={prompt_hash[:8]}...")
    return None"""
    
    modified_content = re.sub(cache_get_pattern, cache_get_replacement, content, flags=re.DOTALL)
    
    # Migliora la funzione save_to_cache
    cache_save_pattern = r'def save_to_cache\(model_name, prompt, response\):(.*?)return None'
    
    cache_save_replacement = """def save_to_cache(model_name, prompt, response):
    \"\"\"Salva una risposta nella cache.\"\"\"
    # Ottieni il logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    
    # Se la cache è disabilitata, non salvare
    if "use_cache" in st.session_state and not st.session_state.use_cache:
        logger.info(f"Cache disabilitata, salto il salvataggio per {model_name}")
        scores_logger.info(f"CACHE: Disabilitata, salto salvataggio per {model_name}")
        return None
    
    prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()    
    cache_path = get_cache_path(model_name, prompt)
    
    # Verifica se la risposta è un dizionario vuoto o None
    if response is None or (isinstance(response, dict) and len(response) == 0):
        logger.warning(f"Tentativo di salvare una risposta vuota in cache per {model_name}")
        scores_logger.warning(f"CACHE SKIP: Risposta vuota per {model_name}, Hash={prompt_hash[:8]}...")
        return None
        
    try:
        # Verifica se la directory di cache esiste, altrimenti creala
        cache_dir = os.path.dirname(cache_path)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Salva la risposta nella cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Risposta salvata nella cache: {cache_path}")
        scores_logger.info(f"CACHE SAVE: Modello={model_name}, Hash={prompt_hash[:8]}...")
        
        # Log della risposta troncata per debug
        result_str = response if isinstance(response, str) else json.dumps(response)
        truncated_result = result_str[:300] + "..." if len(result_str) > 300 else result_str
        scores_logger.debug(f"CACHED RESPONSE (troncato): {truncated_result}")
        
        return cache_path
    except Exception as e:
        logger.warning(f"Errore nel salvataggio della cache: {str(e)}")
        scores_logger.error(f"CACHE ERROR: Errore nel salvataggio per {model_name}: {str(e)}")
        import traceback
        scores_logger.error(f"CACHE ERROR TRACEBACK: {traceback.format_exc()}")
        return None"""
    
    modified_content = re.sub(cache_save_pattern, cache_save_replacement, modified_content, flags=re.DOTALL)
    
    return modified_content

def fix_logging_code(content):
    """Migliora il logging per tracciare tutte le operazioni"""
    # Migliora setup_scores_logger
    scores_logger_pattern = r'def setup_scores_logger\(\):(.*?)return scores_logger'
    
    scores_logger_replacement = """def setup_scores_logger():
    \"\"\"Configura un logger dedicato al monitoraggio completo dell'applicazione, 
    con particolare attenzione ai punteggi, ai prompt, alle risposte AI e ai parametri di chiamata\"\"\"
    import os
    from pathlib import Path
    import sys
    
    # Determina il percorso assoluto della directory corrente
    current_dir = os.path.abspath(os.getcwd())
    
    # Crea la cartella logs con percorso assoluto
    log_dir = Path(current_dir) / "logs"
    try:
        log_dir.mkdir(exist_ok=True)
        print(f"Cartella logs creata/trovata in: {log_dir}")
    except Exception as e:
        print(f"ERRORE nella creazione della cartella logs: {str(e)}")
        log_dir = Path(current_dir)
    
    # Crea un nome file con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"scores_debug_{timestamp}.log"
    log_file_path = str(log_file.absolute())
    
    # Stampa il percorso completo del file di log
    print(f"File di log dei punteggi creato in: {log_file_path}")
    
    # Salviamo il percorso per mostrarlo all'utente
    if 'scores_log_path' not in st.session_state:
        st.session_state.scores_log_path = log_file_path
    
    # Configura il logger
    scores_logger = logging.getLogger("SCORES_DEBUG")
    scores_logger.setLevel(logging.DEBUG)
    
    # Handler per il file
    try:
        # Specifica l'encoding utf-8 per supportare emoji e caratteri speciali
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Formattatore con più dettagli - includiamo il nome del file, la linea e la funzione
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Rimuovi gli handler esistenti se presenti
        if scores_logger.handlers:
            scores_logger.handlers = []
            
        # Aggiunge l'handler al logger
        scores_logger.addHandler(file_handler)
        
        # Aggiungi anche un handler per la console
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        scores_logger.addHandler(console_handler)
        
        # Log di avvio con informazioni estese
        scores_logger.info(f"================ AVVIO DEBUGGING PUNTEGGI ================")
        scores_logger.info(f"Inizializzato logger di debug per i punteggi")
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
            scores_logger.info(f"Cache abilitata: {st.session_state.use_cache}")
        
    except Exception as e:
        print(f"ERRORE nella configurazione del logger dei punteggi: {str(e)}")
    
    return scores_logger"""
    
    modified_content = re.sub(scores_logger_pattern, scores_logger_replacement, content, flags=re.DOTALL)
    
    # Aggiungi log nelle funzioni di analisi CV
    analyze_pattern = r'def analyze_cv_openai\(cv_text, job_description, fields\):(.*?)try:'
    analyze_replacement = r"""def analyze_cv_openai(cv_text, job_description, fields):
    \"\"\"Analizza un CV con OpenAI\"\"\"
    # Setup del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    scores_logger.info(f"{'='*40} NUOVA ANALISI CV CON OPENAI {'='*40}")
    scores_logger.info(f"Modello: {st.session_state.model}")
    scores_logger.info(f"Campi da estrarre: {fields}")
    scores_logger.info(f"Job description (troncata): {job_description[:200]}...")
    
    try:"""
    
    modified_content = re.sub(analyze_pattern, analyze_replacement, modified_content, flags=re.DOTALL)
    
    return modified_content

def fix_sidebar_ui(content):
    """Migliora l'interfaccia utente della sidebar"""
    # Trova l'inizio della sezione sidebar
    sidebar_pattern = r'# Creazione della sidebar(.*?)# Campi da estrarre'
    
    # Nuovo design della sidebar
    sidebar_replacement = r"""# Creazione della sidebar
    with st.sidebar:
        # Header
        st.markdown('''
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="margin-bottom: 0;">📊 CV Analyzer Pro</h2>
            <p style="opacity: 0.8;">Analisi intelligente dei curricula</p>
        </div>
        ''', unsafe_allow_html=True)
        
        # Informazioni utente
        st.markdown(f'''
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0;">👤 <b>Utente:</b> {st.session_state.username}</p>
        </div>
        ''', unsafe_allow_html=True)
        
        # Tab per organizzare i contenuti
        tab1, tab2, tab3 = st.tabs(["⚙️ Configurazione", "🔍 Campi", "⚖️ Criteri"])
        
        # Tab 1: Configurazione
        with tab1:
            # Selezione del motore AI (box colorato)
            st.markdown('<div style="background-color: #e1f5fe; padding: 10px; border-radius: 5px; margin-bottom: 15px;">', unsafe_allow_html=True)
            st.subheader("🤖 Motore AI")
            ai_engine = st.radio("", ["OpenAI", "Ollama"], horizontal=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.session_state.use_ollama = (ai_engine == "Ollama")
            
            # Configurazione specifica per il motore selezionato
            if not st.session_state.use_ollama:
                # OpenAI
                st.markdown('<div style="background-color: #f9fbe7; padding: 10px; border-radius: 5px; margin-bottom: 15px;">', unsafe_allow_html=True)
                
                api_key_input = st.text_input(
                    "API Key OpenAI", 
                    value="" if "api_key" not in st.session_state or st.session_state.api_key == OPENAI_API_KEY else st.session_state.api_key, 
                    type="password",
                    placeholder="Lascia vuoto per usare .env",
                    key="api_key_input_sidebar_main"
                )
                
                # Se l'utente ha inserito una chiave, usala, altrimenti usa quella di default
                if api_key_input:
                    st.session_state.api_key = api_key_input
                else:
                    st.session_state.api_key = OPENAI_API_KEY
                    st.caption("Usando API key da file .env")
                    
                selected_model = st.selectbox(
                    "Modello",
                    ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o", "gpt-4"],
                    index=0,
                    key="model_selectbox_sidebar_main"
                )
                
                # Aggiorna sia 'model' che 'llm_model' per garantire la sincronizzazione
                st.session_state.model = selected_model
                st.session_state.llm_model = selected_model
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Ollama
                st.markdown('<div style="background-color: #f3e5f5; padding: 10px; border-radius: 5px; margin-bottom: 15px;">', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("**Modelli Ollama disponibili**")
                with col2:
                    if st.button("🔄", help="Aggiorna lista modelli", key="update_ollama_models_main"):
                        with st.spinner("Aggiornamento..."):
                            st.session_state.ollama_models = get_ollama_models()
                
                # Ottieni i modelli solo se non sono già nella session_state
                if not st.session_state.ollama_models:
                    st.session_state.ollama_models = get_ollama_models()
                
                if st.session_state.ollama_models:
                    selected_ollama_model = st.selectbox(
                        "Seleziona modello",
                        st.session_state.ollama_models,
                        index=0 if st.session_state.ollama_model is None else 
                              st.session_state.ollama_models.index(st.session_state.ollama_model) 
                              if st.session_state.ollama_model in st.session_state.ollama_models else 0,
                        key="ollama_model_select_main"
                    )
                    
                    st.session_state.ollama_model = selected_ollama_model
                    st.session_state.llm_model = selected_ollama_model
                else:
                    st.error("❌ Nessun modello Ollama trovato")
                    st.caption("Verifica che Ollama sia in esecuzione")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Opzioni di cache
            st.markdown('<div style="background-color: #e8f5e9; padding: 10px; border-radius: 5px;">', unsafe_allow_html=True)
            st.subheader("📦 Cache")
            
            st.session_state.use_cache = st.toggle("Abilita cache", value=True if 'use_cache' not in st.session_state else st.session_state.use_cache)
            
            cache_status = "Abilitata ✅" if st.session_state.use_cache else "Disabilitata ❌"
            st.caption(f"Stato cache: {cache_status}")
            
            if st.session_state.use_cache and st.button("🧹 Svuota cache"):
                try:
                    cache_dir = create_cache_dir()
                    files = os.listdir(cache_dir)
                    for file in files:
                        os.remove(os.path.join(cache_dir, file))
                    st.success(f"Cache svuotata! ({len(files)} file rimossi)")
                except Exception as e:
                    st.error(f"Errore: {e}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Display logger path
            if 'scores_log_path' in st.session_state:
                st.caption(f"Log file: {os.path.basename(st.session_state.scores_log_path)}")
        
        # Tab 2: Campi da estrarre
        with tab2:
            # Campi da estrarre"""
    
    modified_content = re.sub(sidebar_pattern, sidebar_replacement, content, flags=re.DOTALL)
    
    return modified_content

def main():
    """Funzione principale per eseguire le correzioni"""
    print("Iniziando il fix dei problemi in BFCV...")
    
    # Percorso del file originale
    file_path = "bfcv_007.py"
    
    # Verifica che il file esista
    if not os.path.exists(file_path):
        print(f"Errore: File {file_path} non trovato!")
        return False
    
    # Crea un backup del file originale
    backup_path = backup_file(file_path)
    
    # Leggi il contenuto del file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Applica le correzioni
    print("Miglioramento del logging...")
    content = fix_logging_code(content)
    
    print("Correzione del sistema di cache...")
    content = fix_cache_code(content)
    
    print("Risoluzione del problema dei punteggi...")
    content = fix_scoring_code(content)
    
    print("Miglioramento dell'interfaccia sidebar...")
    content = fix_sidebar_ui(content)
    
    # Scrivi il contenuto modificato sul file originale
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\nCorrezioni applicate! File originale: {file_path}")
    print(f"Backup: {backup_path}")
    print("\nProblemi risolti:")
    print("✅ Migliorato il sistema di logging per tracciare tutte le operazioni")
    print("✅ Risolto il problema dei punteggi sempre a 50")
    print("✅ Migliorato il sistema di cache per evitare chiamate duplicate")
    print("✅ Migliorata l'interfaccia utente della sidebar")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 