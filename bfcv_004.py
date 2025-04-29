''' versione funzionante con cui ho fatto la prima analisi'''


import streamlit as st
import os
import json
import pandas as pd
import requests
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Modifica il percorso se necessario
from datetime import datetime
import base64
import time
from io import BytesIO
import tempfile
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import hashlib
import pathlib

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Ottieni la chiave API di OpenAI dall'ambiente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configurazione pagina
st.set_page_config(
    page_title="CV Analyzer Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato
st.markdown("""
<style>
    .main {
        background-color: #f9f9f9;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stButton>button {
        background-color: #3498db;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2980b9;
    }
    .status-box {
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeeba;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    .sidebar .sidebar-content {
        background-color: #fff;
    }
    .stDataFrame {
        padding: 1rem;
        border-radius: 5px;
        background-color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    footer {
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Inizializzazione delle variabili di sessione
if 'cv_dir' not in st.session_state:
    st.session_state.cv_dir = None
if 'job_description' not in st.session_state:
    st.session_state.job_description = ""
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = OPENAI_API_KEY
if 'model' not in st.session_state:
    st.session_state.model = "gpt-4o-mini"
if 'use_ollama' not in st.session_state:
    st.session_state.use_ollama = False
if 'ollama_model' not in st.session_state:
    st.session_state.ollama_model = None
if 'ollama_models' not in st.session_state:
    st.session_state.ollama_models = []

# Criteri di valutazione e campi da estrarre
EVALUATION_CRITERIA = [
    ("criteri_base", "Valuta principalmente la corrispondenza tra requisiti del lavoro e competenze/esperienze del candidato, considerando il livello di esperienza, la formazione e le competenze tecniche."),
    ("criteri_estesi", "Criteri di valutazione: Top 10 università nazionali +3 punti, università prestigiose +2 punti, esperienza in aziende leader +2 punti, esperienza in aziende di fama +1 punto, background all'estero +3 punti, background in aziende straniere +1 punto."),
    ("intuito", "Criteri di valutazione: Usa solo il tuo intuito considerando che la tua risposta non rappresenta una valutazione del candidato come persona, ma solo una valutazione tecnica della rispondenza delle caratteristiche del candidato rispetto alle caratteristiche della posizione e sarà usata solo come criterio per la schedulazione dei colloqui personali."),
]

CV_FIELDS = [
    "Nome", 
    "Numero di contatto", 
    "Email",
    "Età",
    "Città di residenza",
    "Anni di esperienza lavorativa", 
    "Formazione più alta", 
    "Università/Istituto", 
    "Posizione attuale", 
    "Datori di lavoro precedenti",
    "Competenze tecniche", 
    "Lingue conosciute",
    "Competenze specializzate"
]

DEFAULT_JOB_DESCRIPTION = """Account Manager di agenzia di digital marketing. 
Si preferisce un candidato che:
- Abbia esperienza in agenzia di pubblicità o di digital marketing. 
- Abbia una predisposizione o esperienza nella generazione di new business o come commerciale di agenzie di digital marketing
- Abbia già un qualche legame con la città di lavoro, cioè Firenze, ovvero o abiti vicino, o ci abbia almeno studiato o lavorato, e quindi possa volerci tornare
- Possibilmente sotto i 30 anni. 
- Preferibilmente con un master in marketing o comunicazione.

Compiti: 
- Gestione e sviluppo dei rapporti con i clienti
- Pianificazione e gestione di progetti digitali
- Analisi delle performance delle campagne
- Preparazione di presentazioni e reportistica
- Sviluppo di strategie di content marketing
- Ricerca di nuove opportunità di business
- Presentazione dell'agenzia ai clienti
"""

# Funzioni di utilità
def create_cache_dir():
    """Crea la directory per la cache se non esiste"""
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def get_cache_path(model_name, prompt):
    """Genera il percorso del file di cache basato sul modello e sul prompt"""
    # Crea un hash dal prompt
    prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
    
    # Crea il nome del file
    cache_filename = f"{model_name}-{prompt_hash}.txt"
    
    # Restituisci il percorso completo
    cache_dir = create_cache_dir()
    return os.path.join(cache_dir, cache_filename)

def get_cached_response(model_name, prompt):
    """Cerca una risposta nella cache"""
    cache_path = get_cache_path(model_name, prompt)
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            st.warning(f"Errore nel leggere dalla cache: {e}")
    
    return None

def save_to_cache(model_name, prompt, response):
    """Salva una risposta nella cache"""
    cache_path = get_cache_path(model_name, prompt)
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(response)
    except Exception as e:
        st.warning(f"Errore nel salvare nella cache: {e}")

def get_ollama_models():
    """Recupera la lista di modelli disponibili da Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [model['name'] for model in models]
        return []
    except:
        return []

def extract_text_from_pdf(pdf_path):
    """Estrae il testo da un PDF usando sia PyMuPDF che OCR"""
    # Estrazione diretta
    text_direct = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text_direct += page.get_text()
        doc.close()
    except Exception as e:
        st.error(f"Errore nell'estrazione diretta del testo: {e}")
        text_direct = ""
    
    # Estrazione OCR
    text_ocr = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img = img.convert('L')
            img = img.point(lambda x: 0 if x < 140 else 255, '1')
            img = img.filter(ImageFilter.SHARPEN)
            
            custom_config = r'--oem 3 --psm 6'
            page_text = pytesseract.image_to_string(img, lang='ita+eng', config=custom_config)
            text_ocr += page_text
        doc.close()
    except Exception as e:
        st.error(f"Errore nell'OCR: {e}")
        text_ocr = ""
    
    return text_direct, text_ocr

def clean_cv_text(text_direct, text_ocr):
    """Pulisce e combina il testo estratto dal CV"""
    # Se entrambi i metodi di estrazione hanno fallito
    if not text_direct and not text_ocr:
        return ""
    
    # Se uno dei due metodi ha fallito, restituisci l'altro
    if not text_direct:
        return text_ocr
    if not text_ocr:
        return text_direct
    
    # Altrimenti, chiedi all'AI di combinare i risultati
    if st.session_state.use_ollama:
        return combine_texts_ollama(text_direct, text_ocr)
    else:
        return combine_texts_openai(text_direct, text_ocr)

def combine_texts_openai(text_direct, text_ocr):
    """Usa OpenAI per combinare e pulire i testi estratti"""
    try:
        # Crea il prompt
        prompt_template = (
            "Ecco due versioni del testo estratto da un CV:"
            "\n\n---Estrazione Diretta---\n{text_direct}"
            "\n\n---Estrazione OCR---\n{text_ocr}"
            "\n\nCrea una versione pulita e completa combinando le due versioni. "
            "Assicurati di includere tutti i dettagli importanti come nome, contatti, esperienze, "
            "formazione, competenze, ecc. Non aggiungere commenti o spiegazioni."
        )
        
        prompt = prompt_template.format(text_direct=text_direct, text_ocr=text_ocr)
        
        # Cerca nella cache
        model_name = f"openai-{st.session_state.model}"
        cached_response = get_cached_response(model_name, prompt)
        
        if cached_response:
            return cached_response
        
        # Se non c'è in cache, chiama l'API
        model = ChatOpenAI(model=st.session_state.model, api_key=st.session_state.api_key)
        prompt_obj = ChatPromptTemplate.from_template("{text}")
        chain = prompt_obj | model | StrOutputParser()
        result = chain.invoke({"text": prompt})
        
        # Salva nella cache
        save_to_cache(model_name, prompt, result)
        
        return result
    except Exception as e:
        st.error(f"Errore nella combinazione dei testi con OpenAI: {e}")
        # In caso di errore, restituisci la versione più lunga
        return text_direct if len(text_direct) > len(text_ocr) else text_ocr

def combine_texts_ollama(text_direct, text_ocr):
    """Usa Ollama per combinare e pulire i testi estratti"""
    try:
        # Crea il prompt
        prompt = (
            "Ecco due versioni del testo estratto da un CV:"
            "\n\n---Estrazione Diretta---\n" + text_direct +
            "\n\n---Estrazione OCR---\n" + text_ocr +
            "\n\nCrea una versione pulita e completa combinando le due versioni. "
            "Assicurati di includere tutti i dettagli importanti come nome, contatti, esperienze, "
            "formazione, competenze, ecc. Non aggiungere commenti o spiegazioni."
        )
        
        # Cerca nella cache
        model_name = f"ollama-{st.session_state.ollama_model}"
        cached_response = get_cached_response(model_name, prompt)
        
        if cached_response:
            return cached_response
        
        # Se non c'è in cache, chiama l'API
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": st.session_state.ollama_model,
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            result = response.json().get("response", "")
            
            # Salva nella cache
            save_to_cache(model_name, prompt, result)
            
            return result
        else:
            st.error(f"Errore nella richiesta a Ollama: {response.status_code}")
            return text_direct if len(text_direct) > len(text_ocr) else text_ocr
    except Exception as e:
        st.error(f"Errore nella combinazione dei testi con Ollama: {e}")
        return text_direct if len(text_direct) > len(text_ocr) else text_ocr

def analyze_cv_openai(cv_text, job_description, fields):
    """Analizza un CV con OpenAI"""
    try:
        # Crea il prompt per l'estrazione dei campi
        fields_prompt = "\n".join([f"- {field}" for field in fields])
        extraction_prompt = f"""
        Analizza il seguente CV in relazione alla descrizione del lavoro.
        
        Job Description:
        {job_description}
        
        CV:
        {cv_text}
        
        Estrai le seguenti informazioni (se non disponibili, scrivi "Non specificato"):
        {fields_prompt}
        
        Restituisci i risultati in formato JSON, con ogni campo come chiave e il valore estratto.
        """
        
        # Cerca nella cache per l'estrazione
        model_name = f"openai-{st.session_state.model}"
        cached_extraction = get_cached_response(model_name, extraction_prompt)
        
        if cached_extraction:
            try:
                extraction_result = json.loads(cached_extraction)
            except:
                import re
                json_match = re.search(r'\{.*\}', cached_extraction, re.DOTALL)
                if json_match:
                    extraction_result = json.loads(json_match.group(0))
                else:
                    st.warning("Cache corrotta per l'estrazione, richiamo l'API")
                    cached_extraction = None
        
        if not cached_extraction:
            model = ChatOpenAI(model=st.session_state.model, api_key=st.session_state.api_key)
            prompt = ChatPromptTemplate.from_template("{text}")
            chain = prompt | model | StrOutputParser()
            result = chain.invoke({"text": extraction_prompt})
            
            # Salva nella cache
            save_to_cache(model_name, extraction_prompt, result)
            
            # Cerca di estrarre la parte JSON dalla risposta
            try:
                extraction_result = json.loads(result)
            except:
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    extraction_result = json.loads(json_match.group(0))
                else:
                    st.error("Non è stato possibile estrarre JSON dalla risposta")
                    extraction_result = {field: "Errore di estrazione" for field in fields}
        
        # Analisi delle corrispondenze per ogni criterio
        criteria_results = {}
        
        for criteria_id, criteria_desc in EVALUATION_CRITERIA:
            criteria_prompt = f"""
            Analizza il seguente CV in relazione alla descrizione del lavoro.
            
            Job Description:
            {job_description}
            
            CV:
            {cv_text}
            
            {criteria_desc}
            
            Restituisci un JSON con due campi:
            - "score": un punteggio da 0 a 100 che indica quanto il candidato è adatto alla posizione
            - "motivazione": una breve spiegazione (max 150 parole) del perché hai assegnato questo punteggio
            """
            
            # Cerca nella cache per ciascun criterio
            cached_criteria = get_cached_response(model_name, criteria_prompt)
            
            if cached_criteria:
                try:
                    criteria_results[criteria_id] = json.loads(cached_criteria)
                    continue
                except:
                    import re
                    json_match = re.search(r'\{.*\}', cached_criteria, re.DOTALL)
                    if json_match:
                        criteria_results[criteria_id] = json.loads(json_match.group(0))
                        continue
                    else:
                        st.warning(f"Cache corrotta per il criterio {criteria_id}, richiamo l'API")
            
            # Se non trovato in cache, chiama l'API
            criteria_result = chain.invoke({"text": criteria_prompt})
            
            # Salva nella cache
            save_to_cache(model_name, criteria_prompt, criteria_result)
            
            try:
                result_json = json.loads(criteria_result)
                criteria_results[criteria_id] = result_json
            except:
                import re
                json_match = re.search(r'\{.*\}', criteria_result, re.DOTALL)
                if json_match:
                    criteria_results[criteria_id] = json.loads(json_match.group(0))
                else:
                    criteria_results[criteria_id] = {
                        "score": 0,
                        "motivazione": "Errore nell'analisi"
                    }
        
        return {
            "extraction": extraction_result,
            "criteria": criteria_results
        }
        
    except Exception as e:
        st.error(f"Errore nell'analisi con OpenAI: {e}")
        return None

def analyze_cv_ollama(cv_text, job_description, fields):
    """Analizza un CV con Ollama"""
    try:
        # Crea il prompt per l'estrazione dei campi
        fields_prompt = "\n".join([f"- {field}" for field in fields])
        extraction_prompt = f"""
        Analizza il seguente CV in relazione alla descrizione del lavoro.
        
        Job Description:
        {job_description}
        
        CV:
        {cv_text}
        
        Estrai le seguenti informazioni (se non disponibili, scrivi "Non specificato"):
        {fields_prompt}
        
        Restituisci i risultati SOLO in formato JSON, con ogni campo come chiave e il valore estratto.
        Il JSON deve essere valido e parsabile.
        """
        
        # Cerca nella cache per l'estrazione
        model_name = f"ollama-{st.session_state.ollama_model}"
        cached_extraction = get_cached_response(model_name, extraction_prompt)
        
        if cached_extraction:
            try:
                extraction_result = json.loads(cached_extraction)
            except:
                st.warning("Cache corrotta per l'estrazione, richiamo l'API")
                cached_extraction = None
        
        if not cached_extraction:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": st.session_state.ollama_model,
                    "prompt": extraction_prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            
            if response.status_code != 200:
                st.error(f"Errore nella richiesta a Ollama: {response.status_code}")
                return None
                
            result = response.json().get("response", "{}")
            
            # Salva nella cache
            save_to_cache(model_name, extraction_prompt, result)
            
            try:
                extraction_result = json.loads(result)
            except:
                st.error("Non è stato possibile estrarre JSON dalla risposta di Ollama")
                extraction_result = {field: "Errore di estrazione" for field in fields}
        
        # Analisi delle corrispondenze per ogni criterio
        criteria_results = {}
        
        for criteria_id, criteria_desc in EVALUATION_CRITERIA:
            criteria_prompt = f"""
            Analizza il seguente CV in relazione alla descrizione del lavoro.
            
            Job Description:
            {job_description}
            
            CV:
            {cv_text}
            
            {criteria_desc}
            
            Restituisci SOLO un JSON con due campi:
            - "score": un punteggio da 0 a 100 che indica quanto il candidato è adatto alla posizione
            - "motivazione": una breve spiegazione (max 150 parole) del perché hai assegnato questo punteggio
            
            Il JSON deve essere valido e parsabile.
            """
            
            # Cerca nella cache per ciascun criterio
            cached_criteria = get_cached_response(model_name, criteria_prompt)
            
            if cached_criteria:
                try:
                    criteria_results[criteria_id] = json.loads(cached_criteria)
                    continue
                except:
                    st.warning(f"Cache corrotta per il criterio {criteria_id}, richiamo l'API")
            
            # Se non trovato in cache, chiama l'API
            criteria_response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": st.session_state.ollama_model,
                    "prompt": criteria_prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            
            if criteria_response.status_code != 200:
                criteria_results[criteria_id] = {
                    "score": 0,
                    "motivazione": f"Errore nella richiesta a Ollama: {criteria_response.status_code}"
                }
                continue
                
            criteria_result = criteria_response.json().get("response", "{}")
            
            # Salva nella cache
            save_to_cache(model_name, criteria_prompt, criteria_result)
            
            try:
                criteria_results[criteria_id] = json.loads(criteria_result)
            except:
                criteria_results[criteria_id] = {
                    "score": 0,
                    "motivazione": "Errore nell'analisi"
                }
        
        return {
            "extraction": extraction_result,
            "criteria": criteria_results
        }
        
    except Exception as e:
        st.error(f"Errore nell'analisi con Ollama: {e}")
        return None

def create_download_link(df):
    """Crea un link per scaricare il dataframe come file Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Analisi CV')
    processed_data = output.getvalue()
    b64 = base64.b64encode(processed_data).decode()
    href = f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}'
    return href

def process_cvs(cv_dir, job_description, fields):
    """Processa tutti i CV nella directory specificata"""
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Ottieni la lista di tutti i file PDF nella directory
    pdf_files = [f for f in os.listdir(cv_dir) if f.lower().endswith('.pdf')]
    
    for i, pdf_file in enumerate(pdf_files):
        status_text.text(f"Elaborazione di {pdf_file}... ({i+1}/{len(pdf_files)})")
        
        full_path = os.path.join(cv_dir, pdf_file)
        
        # Estrai il testo dal PDF
        text_direct, text_ocr = extract_text_from_pdf(full_path)
        
        # Pulisci e combina i testi
        clean_text = clean_cv_text(text_direct, text_ocr)
        
        # Analizza il CV
        if st.session_state.use_ollama:
            analysis = analyze_cv_ollama(clean_text, job_description, fields)
        else:
            analysis = analyze_cv_openai(clean_text, job_description, fields)
        
        if analysis:
            # Crea un dizionario con i risultati
            result = {
                "Filename": pdf_file,
                **analysis["extraction"]
            }
            
            # Aggiungi i punteggi e le motivazioni per ogni criterio
            for criteria_id, _ in EVALUATION_CRITERIA:
                if criteria_id in analysis["criteria"]:
                    result[f"Score_{criteria_id}"] = analysis["criteria"][criteria_id].get("score", 0)
                    result[f"Motivazione_{criteria_id}"] = analysis["criteria"][criteria_id].get("motivazione", "")
            
            results.append(result)
        
        # Aggiorna la barra di avanzamento
        progress_bar.progress((i + 1) / len(pdf_files))
    
    status_text.text("Analisi completata!")
    
    return pd.DataFrame(results)

# Interfaccia sidebar per le configurazioni
with st.sidebar:
    st.image("https://via.placeholder.com/150x80?text=CV+Analyzer", width=150)
    st.title("Configurazione")
    
    # Selezione del motore di AI
    ai_engine = st.radio("Seleziona il motore di AI", ["OpenAI", "Ollama"])
    st.session_state.use_ollama = (ai_engine == "Ollama")
    
    # Opzioni di cache
    st.subheader("Opzioni cache")
    cache_enabled = st.checkbox("Usa cache per le richieste AI", value=True)
    
    if cache_enabled and st.button("Svuota cache"):
        try:
            cache_dir = create_cache_dir()
            files = os.listdir(cache_dir)
            for file in files:
                os.remove(os.path.join(cache_dir, file))
            st.success(f"Cache svuotata! ({len(files)} file rimossi)")
        except Exception as e:
            st.error(f"Errore nello svuotamento della cache: {e}")
    
    # Configurazione OpenAI
    if not st.session_state.use_ollama:
        api_key_input = st.text_input(
            "OpenAI API Key (lascia vuoto per usare quella in .env)", 
            value="" if st.session_state.api_key == OPENAI_API_KEY else st.session_state.api_key, 
            type="password",
            placeholder="Inserisci la tua chiave API o lascia vuoto per usare quella in .env"
        )
        
        # Se l'utente ha inserito una chiave, usala, altrimenti usa quella di default
        if api_key_input:
            st.session_state.api_key = api_key_input
        else:
            st.session_state.api_key = OPENAI_API_KEY
            
        st.session_state.model = st.selectbox(
            "Modello OpenAI",
            ["gpt-4o-mini"],
            index=0
        )
        
        # Mostra un messaggio che indica se si sta usando la chiave dal file .env
        if st.session_state.api_key == OPENAI_API_KEY:
            st.info("Usando la chiave API dal file .env")
    
    # Configurazione Ollama
    else:
        # Aggiorna la lista dei modelli Ollama
        if st.button("Aggiorna lista modelli Ollama"):
            with st.spinner("Recupero dei modelli in corso..."):
                st.session_state.ollama_models = get_ollama_models()
        
        if not st.session_state.ollama_models:
            st.session_state.ollama_models = get_ollama_models()
        
        if st.session_state.ollama_models:
            st.session_state.ollama_model = st.selectbox(
                "Modello Ollama",
                st.session_state.ollama_models,
                index=0 if st.session_state.ollama_model is None else st.session_state.ollama_models.index(st.session_state.ollama_model) if st.session_state.ollama_model in st.session_state.ollama_models else 0
            )
        else:
            st.error("Nessun modello Ollama trovato. Assicurati che Ollama sia in esecuzione.")
    
    # Campi da estrarre dal CV
    st.subheader("Campi da estrarre")
    selected_fields = st.multiselect(
        "Seleziona i campi da estrarre",
        CV_FIELDS,
        default=CV_FIELDS[:8]
    )
    
    # Informazioni sull'app
    st.markdown("---")
    st.markdown("### Informazioni")
    st.markdown("CV Analyzer Pro v1.0")
    st.markdown("Sviluppato con ❤️ da Claude 3")

# Corpo principale dell'app
st.title("📊 CV Analyzer Pro")
st.markdown("#### Analisi intelligente dei curriculum vitae")

# Selezione della cartella CV
cv_dir_input = st.text_input(
    "Seleziona la cartella contenente i CV (percorso completo)",
    value=st.session_state.cv_dir if st.session_state.cv_dir else "",
    placeholder="Es. C:/Utenti/Nome/Documents/CV"
)

if cv_dir_input and cv_dir_input != st.session_state.cv_dir:
    if os.path.isdir(cv_dir_input):
        st.session_state.cv_dir = cv_dir_input
        st.success(f"Cartella selezionata: {cv_dir_input}")
        
        # Conta i file PDF nella cartella
        pdf_files = [f for f in os.listdir(cv_dir_input) if f.lower().endswith('.pdf')]
        st.info(f"Trovati {len(pdf_files)} file PDF nella cartella.")
    else:
        st.error("La cartella specificata non esiste.")

# Descrizione del lavoro
st.subheader("Descrizione della posizione")
job_desc = st.text_area(
    "Inserisci la descrizione del lavoro",
    value=st.session_state.job_description if st.session_state.job_description else DEFAULT_JOB_DESCRIPTION,
    height=200
)
if job_desc != st.session_state.job_description:
    st.session_state.job_description = job_desc

# Pulsante per avviare l'analisi
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("Analizza CV", use_container_width=True):
        if not st.session_state.cv_dir:
            st.error("Devi selezionare una cartella contenente i CV.")
        elif not job_desc:
            st.error("Devi inserire una descrizione del lavoro.")
        elif st.session_state.use_ollama and not st.session_state.ollama_model:
            st.error("Devi selezionare un modello Ollama.")
        elif not st.session_state.use_ollama and not st.session_state.api_key:
            st.error("Devi inserire una API key di OpenAI o configurarla nel file .env.")
        else:
            with st.spinner("Analisi in corso..."):
                results_df = process_cvs(
                    st.session_state.cv_dir,
                    job_desc,
                    selected_fields
                )
                st.session_state.analysis_results = results_df
                
                # Notifica con suono e visualizza un messaggio di successo
                st.balloons()
                st.success("Analisi completata con successo!")

# Visualizzazione dei risultati
if st.session_state.analysis_results is not None:
    st.subheader("Risultati dell'analisi")
    
    # Aggiunta del link per il download
    excel_link = create_download_link(st.session_state.analysis_results)
    st.markdown(f'<a href="{excel_link}" download="analisi_cv.xlsx">📥 Scarica risultati come Excel</a>', unsafe_allow_html=True)
    
    # Visualizza la tabella dei risultati
    st.dataframe(st.session_state.analysis_results, use_container_width=True)
    
    # Dashboard con visualizzazioni
    st.subheader("Dashboard")
    
    # Se ci sono risultati con punteggi
    if "Score_criteri_base" in st.session_state.analysis_results.columns:
        # Visualizza la classifica dei candidati
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Top candidati per punteggio di base")
            top_candidates = st.session_state.analysis_results.sort_values(
                "Score_criteri_base", 
                ascending=False
            )[["Nome", "Score_criteri_base"]].head(5)
            
            st.bar_chart(
                top_candidates.set_index("Nome")
            )
        
        with col2:
            st.markdown("##### Distribuzione punteggi")
            
            # Crea una tabella per la distribuzione dei punteggi
            score_ranges = ["0-25", "26-50", "51-75", "76-100"]
            score_counts = []
            
            for col in [c for c in st.session_state.analysis_results.columns if c.startswith("Score_")]:
                scores = st.session_state.analysis_results[col].astype(float)
                counts = [
                    len(scores[(scores >= 0) & (scores <= 25)]),
                    len(scores[(scores > 25) & (scores <= 50)]),
                    len(scores[(scores > 50) & (scores <= 75)]),
                    len(scores[(scores > 75) & (scores <= 100)])
                ]
                score_counts.append(counts)
            
            score_df = pd.DataFrame(
                score_counts, 
                columns=score_ranges,
                index=[c.replace("Score_", "") for c in st.session_state.analysis_results.columns if c.startswith("Score_")]
            )
            
            st.bar_chart(score_df)
else:
    # Messaggio informativo
    st.info("Seleziona una cartella, definisci la descrizione del lavoro e clicca su 'Analizza CV' per iniziare.")
    
    # Esempio di risultati attesi (solo per la UI)
    st.subheader("Esempio di risultati")
    example_data = {
        "Filename": ["esempio_1.pdf", "esempio_2.pdf"],
        "Nome": ["Mario Rossi", "Giulia Bianchi"],
        "Età": ["28", "32"],
        "Formazione più alta": ["Laurea Magistrale in Marketing", "Master in Digital Communication"],
        "Score_criteri_base": [85, 72],
        "Score_criteri_estesi": [78, 64]
    }
    st.dataframe(pd.DataFrame(example_data), use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Sviluppato con Streamlit • Powered by AI • 2024")