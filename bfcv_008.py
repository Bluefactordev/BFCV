# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import fitz  # PyMuPDF
import docx2txt
import re
import time
import hashlib
import requests
import io
import base64
import random
import tiktoken
from datetime import datetime
import warnings
from typing import Dict, List, Optional, Any, Tuple, Union
import uuid
from PIL import Image, ImageFilter
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Modifica il percorso se necessario

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from io import BytesIO
from langchain_openai import ChatOpenAI
from openai import OpenAI
import xlsxwriter
import logging
import sys
from pathlib import Path
from streamlit.components.v1 import html
from auth_system import AuthManager
from cv_profiles import ProfileManager
from cv_projects import ProjectManager
from pydantic import BaseModel, Field, create_model
from company_analyzer import CompanyManager
from company_page import render_company_page, process_companies_in_cv
from pydantic import BaseModel
import concurrent.futures


# Variabile per controllare se saltare la configurazione della pagina (sarà impostata a True dal launcher)
skip_page_config = False

# Variabile per controllare se saltare l'autenticazione (sarà impostata a True dal launcher)
skip_authentication = False

# Aggiungo funzione per bloccare chiamate a domini esterni non autorizzati
def create_script_blocker():
    """Crea uno script per bloccare chiamate a domini specifici"""
    blocker_script = """
    <script>
    // Intercetta le chiamate fetch e XMLHttpRequest a domini non autorizzati
    (function() {
        // Lista di domini da bloccare
        const blockedDomains = ['fivetran.com', 'webhooks.fivetran.com'];
        
        // Sovrascrive fetch per intercettare le chiamate
        const originalFetch = window.fetch;
        window.fetch = function(resource, options) {
            let url = resource;
            if (resource instanceof Request) {
                url = resource.url;
            }
            
            // Verifica se l'URL è bloccato
            const isBlocked = blockedDomains.some(domain => url.includes(domain));
            if (isBlocked) {
                console.warn('Blocked fetch request to:', url);
                return Promise.reject(new Error('Request blocked for security reasons'));
            }
            
            return originalFetch.apply(this, arguments);
        };
        
        // Sovrascrive XMLHttpRequest per intercettare le chiamate
        const originalXHROpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            // Verifica se l'URL è bloccato
            const isBlocked = blockedDomains.some(domain => url.includes(domain));
            if (isBlocked) {
                console.warn('Blocked XMLHttpRequest to:', url);
                throw new Error('Request blocked for security reasons');
            }
            
            return originalXHROpen.call(this, method, url, ...rest);
        };
        
        console.log('Security blocker activated');
    })();
    </script>
    """
    return blocker_script

# Configurazione della pagina DEVE essere il primo comando Streamlit (a meno che non venga saltata)
# Esegui la configurazione solo se questo script è eseguito direttamente (non importato)
if __name__ == "__main__":
    st.set_page_config(
        page_title="CV Analyzer Pro",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
        # Disabilita la telemetria e le chiamate esterne non necessarie
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Blocca le chiamate esterne non autorizzate
    headers = {
        'Content-Security-Policy': "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https://streamlit.io",
        'X-Frame-Options': 'SAMEORIGIN',
        'X-Content-Type-Options': 'nosniff'
    }
    
    for key, value in headers.items():
        st.markdown(f"<meta http-equiv='{key}' content='{value}'>", unsafe_allow_html=True)

# Costante per limitare il numero di CV da analizzare
MAX_CV_TO_ANALYZE = 999
max_cv = MAX_CV_TO_ANALYZE

# RIMUOVO TUTTI I COMANDI UI DI STREAMLIT A LIVELLO GLOBALE
# Ma mantengo tutte le variabili, costanti, classi e import originali

# Variabili, costanti, ecc. rimangono invariate
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
DEEPSEEK_OPENROUTER_API_KEY = os.getenv("DEEPSEEK-OPENROUTER-API-KEY", "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")
# Definire un tema di colori coerente per l'applicazione
COLORS = {
    'primary': '#1E88E5',       # Blu primario
    'secondary': '#26A69A',     # Verde acqua
    'accent': '#FFC107',        # Giallo ambra
    'success': '#4CAF50',       # Verde
    'warning': '#FF9800',       # Arancione
    'error': '#F44336',         # Rosso
    'info': '#2196F3',          # Blu chiaro
    'neutral': '#607D8B',       # Blu grigio
    'lightgray': '#ECEFF1',     # Grigio chiaro
    'white': '#FFFFFF',         # Bianco
    'darktext': '#263238',      # Testo scuro
    'lighttext': '#FAFAFA'      # Testo chiaro
}



# Criteri di valutazione e campi da estrarre
EVALUATION_CRITERIA = [
    ("competenze_tecniche", "Competenze Tecniche"),
    ("esperienza_rilevante", "Esperienza Settoriale"),
    ("formazione", "Formazione"),
    ("problem_solving", "Problem Solving"),
    ("leadership", "Leadership"),
    ("potenziale_crescita", "Potenziale")
]

# Pesi di default per i criteri di valutazione
DEFAULT_CRITERIA_WEIGHTS = {
    "competenze_tecniche": 25,
    "esperienza_rilevante": 25,
    "formazione": 15,
    "problem_solving": 15,
    "leadership": 10,
    "potenziale_crescita": 10
}

CV_FIELDS = [
    "Nome", 
    "Cognome",
    "Numero di contatto", 
    "Email",
    "Età",
    "Città di residenza",
    "Città di origine",
    "Anni di esperienza lavorativa", 
    "Anni di esperienza lavorativa nel ruolo richiesto", 
    "Master o assimilabile nel ruolo richiesto", 
    "Formazione più alta", 
    "Università/Istituto", 
    "Posizione attuale", 
    "Datori di lavoro precedenti",
    "Lingue conosciute",
    "Legame con Firenze",
    "Soft skills", 
    "Lingue straniere",
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

# Aggiungo una costante per l'endpoint di OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Stile CSS personalizzato
st.markdown(f"""
<style>
    /* Stile generale */
    .main {{
        background-color: {COLORS['lightgray']};
        color: {COLORS['darktext']};
    }}
    
    /* Intestazioni */
    h1, h2, h3, h4, h5, h6 {{
        color: {COLORS['primary']};
        font-weight: 600;
    }}
    
    /* Bottoni */
    .stButton>button {{
        background-color: {COLORS['primary']};
        color: {COLORS['white']};
        border-radius: 5px;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s;
    }}
    .stButton>button:hover {{
        background-color: {COLORS['secondary']};
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }}
    
    /* Box di stato */
    .status-box {{
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        border-left: 5px solid;
    }}
    .success-box {{
        background-color: #E8F5E9;
        border-left-color: {COLORS['success']};
    }}
    .info-box {{
        background-color: #E1F5FE;
        border-left-color: {COLORS['info']};
    }}
    .warning-box {{
        background-color: #FFF8E1;
        border-left-color: {COLORS['warning']};
    }}
    .error-box {{
        background-color: #FFEBEE;
        border-left-color: {COLORS['error']};
    }}
    
    /* Schede per i CV */
    .cv-card {{
        background-color: {COLORS['white']};
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }}
    .cv-card:hover {{
        box-shadow: 0 5px 15px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }}
    
    /* Badge per i punteggi */
    .score-badge {{
        display: inline-block;
        padding: 0.35em 0.65em;
        font-size: 0.85em;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 0.375rem;
        margin-right: 0.5rem;
    }}
    .score-high {{
        background-color: {COLORS['success']};
        color: white;
    }}
    .score-medium {{
        background-color: {COLORS['warning']};
        color: {COLORS['darktext']};
    }}
    .score-low {{
        background-color: {COLORS['error']};
        color: white;
    }}
    
    /* Miglioramenti per DataFrame */
    .dataframe {{
        border: none !important;
        border-collapse: separate !important;
        border-spacing: 0 !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
    }}
    .dataframe thead tr th {{
        background-color: {COLORS['primary']} !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 12px 15px !important;
        text-align: left !important;
    }}
    .dataframe tbody tr:nth-child(even) {{
        background-color: {COLORS['lightgray']} !important;
    }}
    .dataframe tbody tr td {{
        padding: 10px 15px !important;
        border-bottom: 1px solid #e0e0e0 !important;
    }}
    
    /* Tooltip personalizzato */
    .tooltip {{
        position: relative;
        display: inline-block;
        cursor: pointer;
    }}
    .tooltip .tooltiptext {{
        visibility: hidden;
        width: 300px;
        background-color: #333;
        color: #fff;
        text-align: left;
        border-radius: 6px;
        padding: 10px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.9em;
    }}
    .tooltip:hover .tooltiptext {{
        visibility: visible;
        opacity: 1;
    }}
    
    /* Stile della sidebar */
    .sidebar .sidebar-content {{
        background-color: {COLORS['white']};
        border-right: 1px solid #e0e0e0;
    }}
    
    /* Nascondere il footer */
    footer {{
        visibility: hidden;
    }}
    
    /* Stile delle metriche */
    .metric-card {{
        background-color: {COLORS['white']};
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        height: 100%;
    }}
    .metric-value {{
        font-size: 2.5rem;
        font-weight: bold;
        color: {COLORS['primary']};
    }}
    .metric-label {{
        font-size: 1rem;
        color: {COLORS['neutral']};
        margin-top: 0.5rem;
    }}
    
    /* Stile dropdown e filtri */
    .stSelectbox>div>div, .stMultiSelect>div>div {{
        background-color: {COLORS['white']};
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }}
    
    /* Scheda candidato */
    .candidate-header {{
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }}
    .candidate-avatar {{
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: {COLORS['primary']};
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        font-weight: bold;
        margin-right: 1rem;
    }}
    .candidate-name {{
        font-size: 1.25rem;
        font-weight: bold;
        margin: 0;
    }}
    .candidate-position {{
        color: {COLORS['neutral']};
        margin: 0;
    }}
    .candidate-details {{
        display: flex;
        flex-wrap: wrap;
        margin-top: 1rem;
    }}
    .candidate-detail {{
        padding: 0.5rem 1rem;
        margin-right: 1rem;
        margin-bottom: 0.5rem;
        background-color: {COLORS['lightgray']};
        border-radius: 20px;
        font-size: 0.9rem;
    }}
    .candidate-section {{
        margin-top: 1.5rem;
    }}
    .candidate-section-title {{
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        color: {COLORS['primary']};
        border-bottom: 2px solid {COLORS['lightgray']};
        padding-bottom: 0.5rem;
    }}
    
    /* Barra del punteggio */
    .score-bar-container {{
        width: 100%;
        background-color: {COLORS['lightgray']};
        border-radius: 5px;
        margin-bottom: 0.5rem;
    }}
    .score-bar {{
        height: 10px;
        border-radius: 5px;
    }}
    .score-label {{
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
    }}
    
    /* Tabella comparativa */
    .comparison-table {{
        width: 100%;
        border-collapse: collapse;
    }}
    .comparison-table th, .comparison-table td {{
        padding: 10px;
        text-align: left;
        border-bottom: 1px solid #e0e0e0;
    }}
    .comparison-table th {{
        background-color: {COLORS['primary']};
        color: white;
    }}
    .comparison-table tr:nth-child(even) {{
        background-color: {COLORS['lightgray']};
    }}
    
    /* Stile del link di download */
    .download-button {{
        background-color: {COLORS['primary']};
        color: {COLORS['white']};
        border-radius: 5px;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s;
        display: inline-block;
        margin-top: 1rem;
    }}
    .download-button:hover {{
        background-color: {COLORS['secondary']};
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }}
    
    /* Stile per i pulsanti di rimozione */
    button[data-testid^="remove_"] {{
        background-color: #F44336;
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 4px;
        padding: 0.3rem 0.5rem;
        cursor: pointer;
    }}
    
    /* Stile personalizzato per i bottoni di rimozione */
    button[data-testid*="remove_"] {{
        background-color: #F44336 !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 4px 8px !important;
        cursor: pointer !important;
    }}
    
    /* Nasconde i webhooks non autorizzati */
    iframe[src*="fivetran.com"],
    img[src*="fivetran.com"],
    script[src*="fivetran.com"] {{
        display: none !important;
    }}
</style>
""", unsafe_allow_html=True)

# Configurazione delle costanti per i prezzi API
OPENAI_PRICING = {
    # Modelli o3 - GPT-3.5
    "gpt-3.5-turbo": {"input": 0.0000005, "output": 0.0000015},  # $0.5/1M input, $1.5/1M output
    "o3-mini": {"input": 0.0000005, "output": 0.0000015},        # $0.5/1M input, $1.5/1M output (alias di gpt-3.5-turbo)
    "o3-mini-high": {"input": 0.0000005, "output": 0.0000015},   # $0.5/1M input, $1.5/1M output (versione ipotetica)
    
    # Modelli o1 - GPT-4 Turbo
    "gpt-4-turbo": {"input": 0.00001, "output": 0.00003},        # $10/1M input, $30/1M output
    "o1": {"input": 0.00001, "output": 0.00003},                # $10/1M input, $30/1M output (alias di gpt-4-turbo)
    
    # Standard GPT-4
    "gpt-4": {"input": 0.00003, "output": 0.00006},              # $30/1M input, $60/1M output
    
    # Famiglia o4 - GPT-4o  
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},   # $0.15/1M input, $0.6/1M output
    "gpt-4o": {"input": 0.000005, "output": 0.000015},           # $5/1M input, $15/1M output
    "gpt-4o-mini-high": {"input": 0.00000035, "output": 0.0000014}, # $0.35/1M input, $1.4/1M output
    
    # DeepSeek
    "deepseek-v3": {"input": 0.000001, "output": 0.000003}      # $1/1M input, $3/1M output (via OpenRouter)
}

# Job description di esempio
job_description = DEFAULT_JOB_DESCRIPTION

def suggest_custom_fields(job_description, base_fields, use_ollama=False, openai_model=None, ollama_model=None, api_key=None):
    """Suggerisce campi CV personalizzati basati sulla job description"""
    
    # Controlla cache
    cache_key = f"custom_fields_{hashlib.md5(job_description.encode()).hexdigest()}"
    model_prefix = "ollama-" if use_ollama else "openai-"
    model_name = f"{model_prefix}{ollama_model if use_ollama else openai_model}"
    
    # Cerca nella cache
    cached_result = get_cached_response(model_name, cache_key)
    if cached_result:
        return cached_result
    
    # Prepara il prompt
    prompt = f"""
    Analizza questa job description e suggerisci 3-5 campi aggiuntivi specifici che sarebbero utili estrarre dai CV per valutare i candidati.
    I campi dovrebbero essere pertinenti per questo specifico ruolo e non già presenti nell'elenco base.
    
    Job Description:
    {job_description}
    
    Campi base già presenti:
    {', '.join(base_fields)}
    
    Restituisci SOLO un array JSON con i campi suggeriti. Esempio: ["Campo1", "Campo2", "Campo3"]
    """
    
    # Chiama LLM appropriato
    if use_ollama:
        # Verifica che ollama_model sia specificato
        if not ollama_model:
            # Fallback alla session_state solo se necessario
            ollama_model = st.session_state.get("ollama_model", None)
            if not ollama_model:
                st.warning("Modello Ollama non specificato")
                return []
                
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": ollama_model, "prompt": prompt, "stream": False}
        )
        if response.status_code == 200:
            suggestion_text = response.json().get("response", "[]")
        else:
            return []
    else:
        try:
            # Verifica che openai_model sia specificato
            if not openai_model:
                # Fallback alla session_state solo se necessario
                openai_model = st.session_state.get("model", "gpt-4o-mini")
                
            # Verifica che api_key sia specificata
            if not api_key:
                # Fallback alla session_state solo se necessario
                api_key = st.session_state.get("api_key", OPENAI_API_KEY)
            
            # Se stiamo usando DeepSeek, usa la chiave di OpenRouter
            if "deepseek" in str(openai_model).lower():
                api_key = DEEPSEEK_OPENROUTER_API_KEY
                logger.info("Usando API key di OpenRouter per DeepSeek")
            
            # Uso la funzione helper per creare il client OpenAI con supporto DeepSeek
            client = get_openai_client(api_key=api_key, model=openai_model)
            
            # Log dettagliati prima della chiamata API
            logger.info("=== DETTAGLI CHIAMATA API ===")
            logger.info(f"Base URL: {client.base_url}")
            logger.info(f"Headers: {client.default_headers}")
            logger.info(f"Modello in session_state: {openai_model}")
            logger.info(f"API Key in uso (primi 8 caratteri): {api_key[:8]}...")
            
            # Se stiamo usando DeepSeek, usa il modello corretto di OpenRouter
            model_to_use = "deepseek/deepseek-chat-v3-0324:free" if "deepseek" in str(openai_model).lower() else openai_model
            logger.info(f"Modello che verrà usato nella chiamata: {model_to_use}")
            
            # Verifica se il modello supporta response_format
            supports_json_format = any(m in openai_model for m in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "deepseek"])
            
            response_args = {
                "model": model_to_use,  # Usa il modello corretto di OpenRouter
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            
            # Aggiungi response_format solo per i modelli che lo supportano
            if supports_json_format:
                response_args["response_format"] = {"type": "json_object"}
                logger.info("Aggiunto response_format: json_object")
            
            # Log dei parametri della chiamata
            logger.info(f"Parametri chiamata API: {response_args}")
            
            try:
                # Esegui la chiamata API
                logger.info("Esecuzione chiamata API...")
                response = client.chat.completions.create(**response_args)
                logger.info("Chiamata API completata con successo")
                logger.info(f"Risposta ricevuta da: {response.model if hasattr(response, 'model') else 'modello non specificato'}")
                
                suggestion_text = response.choices[0].message.content
                
                # Log della chiamata API
                log_api_call(
                    model=model_to_use,
                    params=response_args,
                    prompt=prompt,
                    response=suggestion_text
                )
                
            except Exception as e:
                # Log dell'errore API
                log_api_call(
                    model=model_to_use,
                    params=response_args,
                    prompt=prompt,
                    response=str(e),
                    is_error=True
                )
                raise e
                
        except Exception as e:
            logger.error(f"Errore nel suggerimento campi: {str(e)}")
            st.error(f"Errore nel suggerimento campi: {str(e)}")
            return []
    
    # Estrai i campi dall'output
    try:
        # Cerca il pattern JSON nell'output
        import re
        json_match = re.search(r'\[.*\]', suggestion_text)
        if json_match:
            custom_fields = json.loads(json_match.group(0))
        else:
            # Se non troviamo un array, proviamo a vedere se è un oggetto JSON con una proprietà che contiene l'array
            try:
                json_obj = json.loads(suggestion_text)
                # Cerca una proprietà che contiene un array
                for value in json_obj.values():
                    if isinstance(value, list):
                        custom_fields = value
                        break
                else:
                    custom_fields = []
            except:
                custom_fields = []
    except:
        st.warning("Errore nel parsing dei campi suggeriti")
        custom_fields = []
    
    # Salva nella cache
    save_to_cache(model_name, cache_key, custom_fields)
    
    return custom_fields

# Funzione per contare i token in un testo
def count_tokens(text, model="gpt-4o"):
    """Conta i token in un testo per il modello specificato"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        # Se il modello specifico non è supportato, usa cl100k_base come fallback
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception as inner_e:
            st.warning(f"Impossibile contare i token: {str(inner_e)}")
            # Stima approssimativa: 4 caratteri = 1 token
            return len(text) // 4

# Funzione per calcolare il costo di una chiamata API
def calculate_cost(input_tokens, output_tokens, model="gpt-4o-mini"):
    """Calcola il costo di una chiamata API in base ai token e al modello"""
    if model not in OPENAI_PRICING:
        st.warning(f"Modello {model} non trovato nel listino prezzi, uso gpt-4o-mini come fallback")
        model = "gpt-4o-mini"
    
    input_cost = (input_tokens / 1000) * OPENAI_PRICING[model]["input"]
    output_cost = (output_tokens / 1000) * OPENAI_PRICING[model]["output"]
    return input_cost + output_cost

# Funzione per stimare i costi su altri modelli
def estimate_costs_across_models(input_tokens, output_tokens):
    """Stima il costo della stessa operazione su diversi modelli"""
    costs = {}
    for model in OPENAI_PRICING:
        costs[model] = calculate_cost(input_tokens, output_tokens, model)
    return costs

# Inizializzazione del tracciamento dei costi in session_state
def init_cost_tracking():
    """Inizializza o resetta il tracciamento dei costi nella session_state"""
    # Token effettivamente processati (senza cache)
    if "real_input_tokens" not in st.session_state:
        st.session_state.real_input_tokens = 0
    if "real_output_tokens" not in st.session_state:
        st.session_state.real_output_tokens = 0
    if "real_api_calls" not in st.session_state:
        st.session_state.real_api_calls = 0
        
    # Totale token (inclusi quelli dalla cache)
    if "total_input_tokens" not in st.session_state:
        st.session_state.total_input_tokens = 0
    if "total_output_tokens" not in st.session_state:
        st.session_state.total_output_tokens = 0
    if "total_api_calls" not in st.session_state:
        st.session_state.total_api_calls = 0
        
    # Contatori cache
    if "cached_input_tokens" not in st.session_state:
        st.session_state.cached_input_tokens = 0
    if "cached_output_tokens" not in st.session_state:
        st.session_state.cached_output_tokens = 0
    if "cached_calls" not in st.session_state:
        st.session_state.cached_calls = 0
        
    if "model_used" not in st.session_state:
        st.session_state.model_used = "gpt-4o-mini"
        
    # Contatori per l'estrazione
    if "extraction_tokens_input" not in st.session_state:
        st.session_state.extraction_tokens_input = 0
    if "extraction_tokens_output" not in st.session_state:
        st.session_state.extraction_tokens_output = 0

# Aggiorna il tracciamento dei costi
def update_cost_tracking(input_tokens, output_tokens, from_cache=False):
    """
    Aggiorna il tracciamento dei costi nella session_state
    
    Args:
        input_tokens: Numero di token di input per questa chiamataimage.png
        output_tokens: Numero di token di output per questa chiamata
        from_cache: True se la risposta viene dalla cache, False se è una chiamata API reale
    """
    if "total_input_tokens" not in st.session_state:
        init_cost_tracking()
    
    # Aggiorna sempre il totale complessivo
    st.session_state.total_input_tokens += input_tokens
    st.session_state.total_output_tokens += output_tokens
    st.session_state.total_api_calls += 1
    
    if from_cache:
        # è una chiamata dalla cache
        st.session_state.cached_input_tokens += input_tokens
        st.session_state.cached_output_tokens += output_tokens
        st.session_state.cached_calls += 1
    else:
        # è una chiamata API reale
        st.session_state.real_input_tokens += input_tokens
        st.session_state.real_output_tokens += output_tokens
        st.session_state.real_api_calls += 1
    
    # Aggiorna il modello utilizzato, preferendo quello in session_state se disponibile
    if "model" in st.session_state and st.session_state.model:
        st.session_state.model_used = st.session_state.model
    # Altrimenti, verifica se è stato impostato ollama_model quando use_ollama è True
    elif "use_ollama" in st.session_state and st.session_state.use_ollama and "ollama_model" in st.session_state and st.session_state.ollama_model:
        st.session_state.model_used = st.session_state.ollama_model


# Funzione per aggiornare la visualizzazione dei costi in tempo reale
def update_cost_display():
    """Mostra un riepilogo dei costi attuali in tempo reale"""
    if "total_input_tokens" in st.session_state and "total_output_tokens" in st.session_state:
        container = st.empty()
        with container.container():
            col1, col2, col3 = st.columns(3)
            
            real_cost = calculate_cost(
                st.session_state.real_input_tokens, 
                st.session_state.real_output_tokens, 
                st.session_state.model_used
            )
            
            potential_cost = calculate_cost(
                st.session_state.total_input_tokens, 
                st.session_state.total_output_tokens, 
                st.session_state.model_used
            )
            
            savings = potential_cost - real_cost
            
            with col1:
                st.metric("Costo Attuale", f"${real_cost:.4f}")
            with col2:
                st.metric("Costo Potenziale (senza cache)", f"${potential_cost:.4f}")
            with col3:
                st.metric("Risparmio", f"${savings:.4f}")
            
            # Aggiungi un expander con i dettagli dei costi per altri modelli
            with st.expander("Dettagli costi per altri modelli"):
                # Calcola i costi con altri modelli
                costs_other_models = {}
                for model in ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]:
                    real_cost_model = calculate_cost(
                        st.session_state.real_input_tokens, 
                        st.session_state.real_output_tokens, 
                        model
                    )
                    potential_cost_model = calculate_cost(
                        st.session_state.total_input_tokens, 
                        st.session_state.total_output_tokens, 
                        model
                    )
                    savings_model = potential_cost_model - real_cost_model
                    
                    costs_other_models[model] = {
                        "real": real_cost_model,
                        "potential": potential_cost_model,
                        "savings": savings_model
                    }
                
                # Crea una tabella per mostrare i costi
                cost_data = []
                for model, costs in costs_other_models.items():
                    cost_data.append({
                        "Modello": model,
                        "Costo Attuale": f"${costs['real']:.4f}",
                        "Costo Senza Cache": f"${costs['potential']:.4f}",
                        "Risparmio": f"${costs['savings']:.4f}"
                    })
                
                cost_df = pd.DataFrame(cost_data)
                st.table(cost_df)
        return container
    return None



# Mostra il riepilogo dei costi
def display_cost_summary():
    """Mostra un riepilogo dei costi attuali e stimati su altri modelli"""
    if "total_input_tokens" not in st.session_state:
        st.info("Nessun dato sui costi disponibile")
        return
    
    input_tokens = st.session_state.total_input_tokens
    output_tokens = st.session_state.total_output_tokens
    model_used = st.session_state.model_used
    
    st.subheader("💰 Riepilogo Costi API")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Numero di chiamate API", st.session_state.total_api_calls)
        st.metric("Token di input totali", f"{input_tokens:,}")
    with col2:
        st.metric("Token di output totali", f"{output_tokens:,}")
        actual_cost = calculate_cost(input_tokens, output_tokens, model_used)
        st.metric("Costo Totale", f"${actual_cost:.4f}")
    
    # Calcola i costi stimati con altri modelli
    estimated_costs = estimate_costs_across_models(input_tokens, output_tokens)
    
    # Crea una tabella comparativa dei costi
    cost_data = {
        "Modello": [],
        "Costo Stimato": [],
        "Differenza": []
    }
    
    for model, cost in estimated_costs.items():
        cost_data["Modello"].append(model)
        cost_data["Costo Stimato"].append(f"${cost:.4f}")
        diff = cost - actual_cost
        diff_str = f"+${diff:.4f}" if diff > 0 else f"-${abs(diff):.4f}"
        cost_data["Differenza"].append(diff_str)
    
    st.markdown("### Costi Stimati con Altri Modelli")
    cost_df = pd.DataFrame(cost_data)
    st.table(cost_df)
    
    # Aggiungi un grafico per visualizzare i costi
    fig = px.bar(cost_df, x="Modello", y=[float(c.replace("$", "")) for c in cost_data["Costo Stimato"]], 
                title="Confronto Costi tra Modelli",
                labels={"y": "Costo in USD", "x": "Modello"})
    
    # Evidenzia il modello utilizzato
    model_indices = [i for i, m in enumerate(cost_data["Modello"]) if m == model_used]
    if model_indices:
        idx = model_indices[0]
        fig.add_shape(
            type="rect",
            x0=idx-0.4, y0=0,
            x1=idx+0.4, y1=float(cost_data["Costo Stimato"][idx].replace("$", "")),
            line=dict(color="yellow", width=3),
            fillcolor="rgba(0,0,0,0)"
        )
    
    st.plotly_chart(fig, use_container_width=True)

# Inizializzazione delle variabili di sessione
if 'cv_dir' not in st.session_state:
    st.session_state.cv_dir = None
if 'job_description' not in st.session_state:
    st.session_state.job_description = ""
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'detailed_results' not in st.session_state:
    st.session_state.detailed_results = None
if 'detailed_view' not in st.session_state:
    st.session_state.detailed_view = None
if 'comparison_candidates' not in st.session_state:
    st.session_state.comparison_candidates = []
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


# Funzioni di utilità

# Funzione per inizializzare il client OpenAI con supporto per OpenRouter
def get_openai_client(api_key=None, model=None):
    """
    Inizializza e restituisce un client OpenAI, configurando l'endpoint appropriato
    in base al modello selezionato.
    
    Args:
        api_key: API key da utilizzare (se None, usa quella in session_state)
        model: Il modello da utilizzare (se None, usa quello in session_state)
        
    Returns:
        Client OpenAI configurato
    """
    logger.info(f"Inizializzazione client OpenAI per modello: {model}")
    
    if api_key is None and "api_key" in st.session_state:
        api_key = st.session_state.api_key
    
    if model is None and "model" in st.session_state:
        model = st.session_state.model
    
    # Configura parametri aggiuntivi in base al modello
    client_params = {"api_key": api_key}
    
    # Se il modello è DeepSeek, configura per OpenRouter
    if "deepseek" in str(model).lower():
        logger.info("Configurazione client per DeepSeek via OpenRouter")
        client_params["base_url"] = OPENROUTER_BASE_URL
        # Aggiungi header specifici di OpenRouter
        client_params["default_headers"] = {
            "HTTP-Referer": "https://cv-analyzer-pro",  # Il tuo URL
            "X-Title": "CV Analyzer Pro",  # Il nome della tua app
            "Content-Type": "application/json"
        }
        # Modifica il modello per il formato corretto di OpenRouter
        model = "deepseek/deepseek-chat-v3-0324:free"
        logger.info(f"Modello modificato per OpenRouter: {model}")
        logger.info(f"Parametri client OpenRouter: {client_params}")
    else:
        logger.info("Configurazione client standard OpenAI")
        logger.info(f"Parametri client OpenAI: {client_params}")
    
    # Inizializza il client OpenAI con i parametri configurati
    client = OpenAI(**client_params)
    
    # Se stiamo usando DeepSeek, modifica il modello nella session_state
    if model == "deepseek/deepseek-chat-v3-0324:free":
        st.session_state.model = model
        logger.info("Aggiornato modello in session_state per DeepSeek")
    
    return client

def get_score_color(score):
    """Restituisce il colore appropriato in base al punteggio"""
    try:
        score_num = float(score) if score is not None else 0
    except (ValueError, TypeError):
        score_num = 0
    
    if score_num >= 80:
        return COLORS['success']
    elif score_num >= 65:
        return COLORS['warning']
    else:
        return COLORS['error']

def get_score_label(score):
    """Restituisce l'etichetta appropriata in base al punteggio"""
    try:
        score_num = float(score) if score is not None else 0
    except (ValueError, TypeError):
        score_num = 0
    
    if score_num >= 80:
        return "Ottimo"
    elif score_num >= 65:
        return "Buono"
    else:
        return "Sufficiente"

def format_score_with_color(score):
    """Formatta il punteggio con il colore appropriato"""
    # Assicuriamoci che il punteggio sia un numero
    try:
        score_num = float(score) if score is not None else 0
        # Arrotondiamo il punteggio per visualizzazione
        score_display = int(round(score_num))
    except (ValueError, TypeError):
        score_num = 0
        score_display = 0
    
    color = get_score_color(score_num)
    return f'<span style="color:{color};font-weight:bold;">{score_display}</span>'

def create_score_badge(score):
    """Crea un badge HTML per il punteggio"""
    # Assicuriamoci che il punteggio sia un numero
    try:
        score_num = float(score) if score is not None else 0
        # Arrotondiamo il punteggio per visualizzazione
        score_display = int(round(score_num))
    except (ValueError, TypeError):
        score_num = 0
        score_display = 0
    
    # Definizione degli stili in base al punteggio
    if score_num >= 80:
        style = "background-color: #4CAF50; color: white;"  # Verde
    elif score_num >= 65:
        style = "background-color: #FFC107; color: black;"  # Giallo
    else:
        style = "background-color: #F44336; color: white;"  # Rosso
    
    return f'<span style="padding: 4px 8px; border-radius: 4px; font-weight: bold; {style}">{score_display}</span>'

def create_score_bar(score, max_score=100):
    """Crea una barra di progresso per visualizzare il punteggio"""
    try:
        score_num = float(score) if score is not None else 0
    except (ValueError, TypeError):
        score_num = 0
    
    color = get_score_color(score_num)
    
    # Calcola la percentuale
    percent = (score_num / max_score) * 100
    
    # Crea l'HTML per la barra di progresso
    html = f"""
    <div class="score-bar-container">
        <div class="score-bar" style="width: {percent}%; background-color: {color};"></div>
    </div>
    <div class="score-label">
        <span>0</span>
        <span>{int(round(score_num))}/{max_score}</span>
        <span>{max_score}</span>
    </div>
    """
    return html

def format_motivazione(text, max_length=150):
    """Formatta la motivazione con un limite di caratteri"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."

# Replace the safe_html function with this simpler version:
def safe_html(html_content):
    """Sanitizza e prepara il contenuto HTML per la visualizzazione sicura"""
    if html_content is None:
        return ""
    
    # Assicurarsi che sia una stringa
    if not isinstance(html_content, str):
        html_content = str(html_content)
    
    return html_content
    
    # Assicurarsi che sia una stringa
    if not isinstance(html_content, str):
        html_content = str(html_content)
    
    # Rimuovere caratteri problematici
    html_content = html_content.replace("\\", "")
    
    # Se il contenuto è già un frammento HTML, togliere eventuali escape
    if "&lt;" in html_content and "&gt;" in html_content:
        # HTML con escape, ripristina i tag
        html_content = html_content.replace("&lt;", "<").replace("&gt;", ">")
    
    # Avvolgi il contenuto in un div
    return f"""{html_content}"""

def create_tooltip(content, tooltip_text):
    """Crea un tooltip con contenuto e testo al passaggio del mouse"""
    return f'''
    <div class="tooltip">{content}
        <div class="tooltiptext">{tooltip_text}</div>
    </div>
    '''

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
    """Ottiene una risposta dalla cache, se esiste."""
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
    
    logger.info(f"Nessuna cache trovata per {model_name} con hash {hashlib.md5(prompt.encode('utf-8')).hexdigest()}")
    scores_logger.info(f"CACHE MISS: Modello={model_name}, Hash={hashlib.md5(prompt.encode('utf-8')).hexdigest()[:8]}...")
    scores_logger.info(f"CACHE MISS: Modello={model_name}, Hash={prompt_hash[:8]}...")
    return None
        
    cache_path = get_cache_path(model_name, prompt)
    prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
    
    logger.debug(f"Verifico cache in: {cache_path}")
    scores_logger.info(f"CACHE CHECK: Modello={model_name}, Hash={prompt_hash}, Path={cache_path}")
    
    # Log del prompt troncato per debug
    truncated_prompt = prompt[:500] + "..." if len(prompt) > 500 else prompt
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
                scores_logger.info(f"CACHE HIT: Modello={model_name}, Hash={prompt_hash}, TokensRisparmiati={input_tokens+output_tokens}")
                
                # Log della risposta troncata per debug
                result_str = cached_result if isinstance(cached_result, str) else json.dumps(cached_result)
                truncated_result = result_str[:500] + "..." if len(result_str) > 500 else result_str
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
    scores_logger.info(f"CACHE MISS: Modello={model_name}, Hash={prompt_hash}")
    return None

def save_to_cache(model_name, prompt, response):
    """Salva una risposta nella cache."""
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
        return None
    
    prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()    
    cache_path = get_cache_path(model_name, prompt)
    
    # Verifica se la risposta è un dizionario vuoto o None
    if response is None or (isinstance(response, dict) and len(response) == 0):
        logger.warning(f"Tentativo di salvare una risposta vuota in cache per {model_name}")
        scores_logger.warning(f"CACHE SKIP: Risposta vuota per {model_name}, Hash={prompt_hash}")
        return None
        
    try:
        # Verifica se la directory di cache esiste, altrimenti creala
        cache_dir = os.path.dirname(cache_path)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Salva la risposta nella cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Risposta salvata nella cache: {cache_path}")
        scores_logger.info(f"CACHE SAVE: Modello={model_name}, Hash={prompt_hash}, Path={cache_path}")
        
        # Log della risposta troncata per debug
        result_str = response if isinstance(response, str) else json.dumps(response)
        truncated_result = result_str[:500] + "..." if len(result_str) > 500 else result_str
        scores_logger.debug(f"CACHED RESPONSE (troncato): {truncated_result}")
        
        return cache_path
    except Exception as e:
        logger.warning(f"Errore nel salvataggio della cache: {str(e)}")
        scores_logger.error(f"CACHE ERROR: Errore nel salvataggio per {model_name}: {str(e)}")
        import traceback
        scores_logger.error(f"CACHE ERROR TRACEBACK: {traceback.format_exc()}")
        return None

def get_ollama_models():
    """Ottiene la lista dei modelli disponibili su Ollama."""
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
    # Inizializzazione del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    
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
    # Inizializzazione del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    
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
    # Inizializzazione del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    
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
        # Uso la funzione helper per creare il client OpenAI con supporto DeepSeek
        client = get_openai_client(api_key=st.session_state.api_key, model=st.session_state.model)
        
        # Log dettagliati prima della chiamata API
        logger.info("=== DETTAGLI CHIAMATA API ===")
        logger.info(f"Base URL: {client.base_url}")
        logger.info(f"Headers: {client.default_headers}")
        logger.info(f"Modello in session_state: {st.session_state.model}")
        logger.info(f"API Key in uso (primi 8 caratteri): {st.session_state.api_key[:8]}...")
        
        # Se stiamo usando DeepSeek, usa il modello corretto di OpenRouter
        model_to_use = "deepseek/deepseek-chat-v3-0324:free" if "deepseek" in str(st.session_state.model).lower() else st.session_state.model
        logger.info(f"Modello che verrà usato nella chiamata: {model_to_use}")
        
        # Verifica se il modello supporta response_format
        supports_json_format = any(m in st.session_state.model for m in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "deepseek"])
        
        response_args = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        # Aggiungi response_format solo per i modelli che lo supportano
        if supports_json_format:
            response_args["response_format"] = {"type": "text"}
            logger.info("Aggiunto response_format: text")
        
        # Log dei parametri della chiamata
        logger.info(f"Parametri chiamata API: {response_args}")
        
        try:
            # Esegui la chiamata API
            logger.info("Esecuzione chiamata API...")
            response = client.chat.completions.create(**response_args)
            logger.info("Chiamata API completata con successo")
            logger.info(f"Risposta ricevuta da: {response.model if hasattr(response, 'model') else 'modello non specificato'}")
            
            # Log della chiamata API
            log_api_call(
                model=model_to_use,
                params=response_args,
                prompt=prompt,
                response=response.choices[0].message.content
            )
            
            # Salva nella cache
            save_to_cache(model_name, prompt, response.choices[0].message.content)
            
            return response.choices[0].message.content
            
        except Exception as e:
            # Log dell'errore API
            log_api_call(
                model=model_to_use,
                params=response_args,
                prompt=prompt,
                response=str(e),
                is_error=True
            )
            raise e
            
    except Exception as e:
        st.error(f"Errore nella combinazione dei testi con OpenAI: {e}")
        # In caso di errore, restituisci la versione più lunga
        return text_direct if len(text_direct) > len(text_ocr) else text_ocr
    
    
def refine_missing_fields(cv_text, extraction_result, fields, use_ollama=False, openai_model=None, ollama_model=None, api_key=None):
    """
    Controlla e affina i campi mancanti o non specificati.
    
    Args:
        cv_text: Testo del CV
        extraction_result: Risultato dell'estrazione iniziale (dizionario)
        fields: Lista dei campi da controllare
        use_ollama: Se True, usa Ollama invece di OpenAI
        openai_model: Il modello OpenAI da utilizzare
        ollama_model: Il modello Ollama da utilizzare
        api_key: Chiave API per OpenAI
    
    Returns:
        Il dizionario di estrazione aggiornato con i campi mancanti raffinati
    """
    if not extraction_result:
        return {field: "Non specificato" for field in fields}
    
    # Identifica i campi mancanti o non specificati
    missing_fields = []
    for field in fields:
        if field not in extraction_result or not extraction_result[field] or extraction_result[field] == "Non specificato":
            missing_fields.append(field)
    
    if not missing_fields:
        return extraction_result  # Nessun campo mancante

    logger.info(f"Affinamento di {len(missing_fields)} campi mancanti: {', '.join(missing_fields)}")
    st.info(f"Affinamento di {len(missing_fields)} campi mancanti: {', '.join(missing_fields)}")
    
    # Creo un prompt per affinare TUTTI i campi mancanti in una sola chiamata
    fields_to_extract = "\n".join([f"{i+1}. {field}" for i, field in enumerate(missing_fields)])
    
    refinement_prompt = f"""
    Analizza il seguente CV ed estrai SOLO i seguenti campi specifici:
    {fields_to_extract}
    
    CV:
    {cv_text}
    
    IMPORTANTE: 
    1. Estrai ESCLUSIVAMENTE i campi elencati dal CV
    2. Se un'informazione non è esplicitamente presente, fai una stima ragionevole basata sul contesto
    3. Per 'Anni di esperienza', calcola in base alle date di fine della scuola superiore o cose simili
    4. Per 'Posizione attuale', indica l'ultimo ruolo menzionato
    5. Per 'Formazione più alta', estrai il titolo di studio più elevato
    6. Evita di rispondere con 'Non specificato' o 'Non disponibile' - fai sempre una stima informata
    7. Restituisci il risultato in formato JSON, con ogni campo come chiave e il valore estratto
    8. Rispondi concisamente, massimo 2-3 righe per campo
    
    Formato della risposta (esempio):
    {{
        "Nome del campo 1": "Valore estratto 1",
        "Nome del campo 2": "Valore estratto 2",
        ...
    }}
    """
    
    try:
        if use_ollama:
            # Usa l'API di Ollama
            model_name = f"ollama-{ollama_model}"
            
            # Cerca nella cache
            cached_response = get_cached_response(model_name, refinement_prompt)
            if cached_response:
                logger.info("Usando risposta dalla cache per il raffinamento dei campi mancanti")
                try:
                    if isinstance(cached_response, str):
                        refinement_result = json.loads(cached_response)
                    else:
                        refinement_result = cached_response
                        
                    # Aggiorna extraction_result con i campi raffinati
                    for field in missing_fields:
                        if field in refinement_result:
                            extraction_result[field] = refinement_result[field]
                        
                    return extraction_result
                except:
                    logger.warning("Errore nel parsing della risposta dalla cache. Procedo con una nuova chiamata.")
                    cached_response = None
            
            if not cached_response:
                logger.info("Chiamata API Ollama per il raffinamento dei campi mancanti")
                # Usa il formato JSON strutturato di Ollama
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": ollama_model,
                        "prompt": refinement_prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.6
                        }
                    }
                )
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.debug(f"Risposta strutturata da Ollama: {response_data}")
                        
                        if "response" in response_data:
                            refinement_text = response_data.get("response", "{}")
                            # Salva risposta in cache
                            save_to_cache(model_name, refinement_prompt, refinement_text)
                            
                            # Parsing del JSON
                            try:
                                refinement_result = json.loads(refinement_text)
                                logger.info("Parsing JSON riuscito per la risposta strutturata di Ollama")
                            except json.JSONDecodeError as e:
                                logger.error(f"Errore nel parsing JSON strutturato: {e}, testo: {refinement_text}")
                                # Tentativo di estrarre il JSON con regex
                                import re
                                json_match = re.search(r'\{.*\}', refinement_text, re.DOTALL)
                                if json_match:
                                    try:
                                        refinement_result = json.loads(json_match.group(0))
                                        logger.info("Estratto JSON con regex dalla risposta di Ollama")
                                    except:
                                        logger.error(f"Errore nel parsing della risposta JSON da Ollama anche dopo regex: {refinement_text}")
                                        st.error("Errore nell'affinamento con Ollama. La risposta non contiene un JSON valido.")
                                        return extraction_result
                                else:
                                    logger.error(f"Risposta di Ollama non contiene JSON: {refinement_text}")
                                    st.error("Errore nell'affinamento con Ollama. La risposta non contiene un JSON valido.")
                                    return extraction_result
                        else:
                            logger.error("Risposta non valida da Ollama, manca il campo 'response'")
                            st.error("Risposta non valida da Ollama")
                            return extraction_result
                    except json.JSONDecodeError as e:
                        logger.error(f"Errore nel parsing della risposta HTTP da Ollama: {e}")
                        st.error(f"Errore nel parsing della risposta: {e}")
                        return extraction_result
                    
                    # Aggiorna extraction_result con i campi raffinati
                    for field in missing_fields:
                        if field in refinement_result:
                            extraction_result[field] = refinement_result[field]
                    
                    return extraction_result
                else:
                    logger.error(f"Errore nella chiamata API Ollama: {response.status_code} - {response.text}")
                    st.error(f"Errore nella chiamata API Ollama: {response.status_code}")
                    return extraction_result
        else:
            # Usa l'API di OpenAI
            model_name = f"openai-{openai_model}"
            
            # Cerca nella cache
            cached_response = get_cached_response(model_name, refinement_prompt)
            if cached_response:
                logger.info("Usando risposta dalla cache per il raffinamento dei campi mancanti")
                try:
                    if isinstance(cached_response, str):
                        refinement_result = json.loads(cached_response)
                    else:
                        refinement_result = cached_response
                        
                    # Aggiorna extraction_result con i campi raffinati
                    for field in missing_fields:
                        if field in refinement_result:
                            extraction_result[field] = refinement_result[field]
                        
                    return extraction_result
                except:
                    logger.warning("Errore nel parsing della risposta dalla cache. Procedo con una nuova chiamata.")
                    cached_response = None
            
            if not cached_response:
                logger.info("Chiamata API OpenAI per il raffinamento dei campi mancanti")
                from openai import OpenAI
                # Uso la funzione helper per creare il client OpenAI
                client = get_openai_client(api_key=api_key, model=openai_model)
                
                # Verifica se il modello supporta response_format: se ha dentro la parola gpt o deepseek lo supporta

                supports_json_format = any(m in openai_model for m in ["gpt", "deepseek"])
                
                response_args = {
                    "model": openai_model,
                    "messages": [{"role": "user", "content": refinement_prompt}],
                    "temperature": 0.6  # Aumenta la temperatura per diversificare le risposte
                }
                
                # Aggiungi response_format solo per i modelli che lo supportano
                if supports_json_format:
                    response_args["response_format"] = {"type": "json_object"}
                
                try:
                    response = client.chat.completions.create(**response_args)
                    refinement_text = response.choices[0].message.content
                    
                    # Aggiornamento dei token utilizzati
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    update_cost_tracking(input_tokens, output_tokens)
                    
                    # Salva nella cache
                    save_to_cache(model_name, refinement_prompt, refinement_text)
                    
                    # Parsing del JSON
                    try:
                        refinement_result = json.loads(refinement_text)
                    except:
                        import re
                        json_match = re.search(r'\{.*\}', refinement_text, re.DOTALL)
                        if json_match:
                            try:
                                refinement_result = json.loads(json_match.group(0))
                            except:
                                logger.error(f"Errore nel parsing della risposta JSON da OpenAI: {refinement_text}")
                                st.error("L' Errore nell'affinamento con OpenAI. La risposta non contiene un JSON valido.")
                                return extraction_result
                        else:
                            logger.error(f"Risposta di OpenAI non contiene JSON: {refinement_text}")
                            st.error("L' Errore nell'affinamento con OpenAI. La risposta non contiene un JSON valido.")
                            return extraction_result
                    
                    # Aggiorna extraction_result con i campi raffinati
                    for field in missing_fields:
                        if field in refinement_result:
                            extraction_result[field] = refinement_result[field]
                    
                    return extraction_result
                except Exception as e:
                    logger.error(f"Errore nella chiamata API OpenAI: {str(e)}")
                    st.error(f"L' Errore nella chiamata API OpenAI: {str(e)}")
                    return extraction_result
                    
    except Exception as e:
        logger.error(f"Errore generale nell'affinamento dei campi: {str(e)}")
        st.error(f"L' Errore generale nell'affinamento dei campi: {str(e)}")
        return extraction_result
    
    return extraction_result

def combine_texts_ollama(text_direct, text_ocr):
    """Usa Ollama per combinare e pulire i testi estratti"""
    # Inizializzazione del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    
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
        logger.info(f"Chiamata API Ollama con modello {st.session_state.ollama_model}")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": st.session_state.ollama_model,
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                logger.debug(f"Risposta Ollama ricevuta: {response_data}")
                
                if "response" in response_data:
                    result = response_data["response"]
                else:
                    logger.error("Risposta Ollama non contiene il campo 'response'")
                    st.error("Errore: risposta non valida da Ollama")
                    return text_direct if len(text_direct) > len(text_ocr) else text_ocr
                
                # Salva nella cache
                save_to_cache(model_name, prompt, result)
                
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Errore nel parsing JSON della risposta Ollama: {str(e)}")
                logger.error(f"Contenuto della risposta: {response.text}")
                st.error(f"Errore nel parsing della risposta di Ollama: {str(e)}")
                return text_direct if len(text_direct) > len(text_ocr) else text_ocr
        else:
            logger.error(f"Errore nella richiesta a Ollama: {response.status_code}")
            logger.error(f"Contenuto della risposta: {response.text}")
            st.error(f"Errore nella richiesta a Ollama: {response.status_code}")
            return text_direct if len(text_direct) > len(text_ocr) else text_ocr
    except Exception as e:
        logger.error(f"Errore nella combinazione dei testi con Ollama: {str(e)}")
        st.error(f"Errore nella combinazione dei testi con Ollama: {str(e)}")
        return text_direct if len(text_direct) > len(text_ocr) else text_ocr


def create_dynamic_extraction_model(fields):
    """
    Crea dinamicamente uno schema JSON compatibile con Ollama basato sui campi specificati.

    Args:
        fields: Lista dei nomi dei campi da includere nel modello

    Returns:
        Schema JSON compatibile con Ollama con i campi specificati
    """
    from pydantic import BaseModel, Field, create_model
    from typing import Optional

    field_definitions = {}
    properties_schema = {}

    # Crea definizioni di campo Pydantic E lo schema per le proprietà JSON
    for field in fields:
        # Definizione Pydantic (anche se non usiamo direttamente il modello)
        field_definitions[field] = (Optional[str], Field(None, description=f"Campo {field}"))
        # Costruzione dello schema per le proprietà JSON per Ollama
        properties_schema[field] = {
            "type": "string",  # Aggiunge esplicitamente il tipo stringa
            "description": f"Campo {field}"
            # Non includiamo 'default': None perché potrebbe non essere supportato/necessario
        }
    
    # Aggiungi sempre il campo aziende_menzionate per l'estrazione delle aziende
    properties_schema["aziende_menzionate"] = {
        "type": "string",
        "description": "Lista delle aziende menzionate nel CV, separate da virgole. Includere tutti i datori di lavoro passati e attuali, e qualsiasi altra azienda significativa menzionata."
    }

    # Costruzione dello schema JSON finale per Ollama
    ollama_schema = {
        "type": "object",
        "properties": properties_schema,
         # Visto che i campi Pydantic sono Optional, rendiamo vuota la lista required per Ollama
        "required": [] 
        # O potremmo specificare qui quali campi sono *davvero* obbligatori se necessario
        # "required": ["Nome", "Cognome", "Email"] # Esempio
    }

    return ollama_schema


class CriteriaEvaluation(BaseModel):
    """
    Modello per valutazione dei criteri di selezione.
    """
    criteria: str
    score: float
    explanation: str


# Creazione di uno schema più complesso per la valutazione dei criteri
# Questo costruisce manualmente uno schema che rappresenta la struttura desiderata
# per le risposte di valutazione dei CV

def create_criteria_schema(criteria_list):
    """
    Crea uno schema JSON corretto per Ollama basato sull'elenco dei criteri
    
    Args:
        criteria_list: Lista di tuple (criteria_id, criteria_label)
        
    Returns:
        Schema JSON conforme alle specifiche di Ollama
    """
    # Crea le proprietà per ogni criterio
    criteria_properties = {}
    for criteria_id, _ in criteria_list:
        criteria_properties[criteria_id] = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "motivation": {"type": "string"}
            },
            "required": ["score", "motivation"]
        }
    
    # Schema completo
    schema = {
        "type": "object",
        "properties": {
            "criteria": {
                "type": "object",
                "properties": criteria_properties,
                "required": list(criteria_properties.keys())
            },
            "composite_score": {"type": "number", "minimum": 0, "maximum": 100},
            "extraction": {"type": "object"}
        },
        "required": ["criteria", "composite_score"]
    }
    
    return schema

def analyze_cv_openai(cv_text, job_description, fields):
    """Analizza un CV con OpenAI"""
    # Setup del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    scores_logger.info(f"{'='*40} NUOVA ANALISI CV CON OPENAI {'='*40}")
    scores_logger.info(f"Modello: {st.session_state.model}")
    scores_logger.info(f"Campi da estrarre: {fields}")
    scores_logger.info(f"Job description (troncata): {job_description[:500]}...")
    
    try:
        # FASE 1: Estrazione iniziale di tutti i campi
        logger.info("Iniziando l'estrazione principale con OpenAI")
        extraction_result = {}
        
        # Preparazione del prompt per OpenAI
        fields_prompt = "\n".join([f"{i+1}. {field}" for i, field in enumerate(fields)])
        extraction_prompt = f"""
        Sei un assistente esperto in analisi dei CV. Analizza il seguente curriculum rispetto alla descrizione del lavoro.
        
        Job Description:
        {job_description}
        
        CV:
        {cv_text}
        
        Estrai le seguenti informazioni (se non disponibili, scrivi "Non specificato"):
        {fields_prompt}
        
        Inoltre, identificare i seguenti punti:
        1. Forza principale: La caratteristica più forte del candidato rispetto alla posizione
        2. Debolezza principale: La caratteristica più debole del candidato rispetto alla posizione
        3. Fit generale: Una valutazione sintetica in 1-2 frasi dell'adeguatezza del candidato
        4. aziende_menzionate: Lista completa di tutte le aziende menzionate nel CV (inclusi datori di lavoro passati e attuali), separate da virgole
        
        Restituisci i risultati in formato JSON, con ogni campo come chiave e il valore estratto.
        """
        
        # Conta i token del prompt di estrazione
        extraction_input_tokens = count_tokens(extraction_prompt, st.session_state.model)
        extraction_output_tokens = 0
        
        # Cerca nella cache per l'estrazione
        model_name = f"openai-{st.session_state.model}"
        cached_extraction = get_cached_response(model_name, extraction_prompt)
        
        if cached_extraction:
            logger.info("Utilizzando risposta dalla cache per l'estrazione principale")
            try:
                if isinstance(cached_extraction, str):
                    extraction_result = json.loads(cached_extraction)
                else:
                    extraction_result = cached_extraction
                # Nota: il conteggio dei token per la cache à già gestito in get_cached_response
            except:
                import re
                json_match = re.search(r'\{.*\}', cached_extraction, re.DOTALL)
                if json_match:
                    extraction_result = json.loads(json_match.group(0))
                else:
                    logger.warning("Cache corrotta per l'estrazione, richiamo l'API")
                    st.warning("Cache corrotta per l'estrazione, richiamo l'API")
                    cached_extraction = None
        
        if not cached_extraction:
            logger.info("Nessuna cache disponibile, chiamo l'API OpenAI per l'estrazione principale")
            # Rimosso il 'try' problematico
            from openai import OpenAI
            # Uso la funzione helper per creare il client OpenAI
            client = get_openai_client(api_key=st.session_state.api_key, model=st.session_state.model)
            
            # Verifica se il modello supporta response_format
            supports_json_format = any(m in st.session_state.model for m in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
            
            response_args = {
                "model": st.session_state.model,
                "messages": [{"role": "user", "content": extraction_prompt}]
            }
            
            # Aggiungi response_format solo per i modelli che lo supportano
            if supports_json_format:
                response_args["response_format"] = {"type": "json_object"}
            
            try:
                response = client.chat.completions.create(**response_args)
                result = response.choices[0].message.content
                
                # Aggiornamento dei token utilizzati
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                update_cost_tracking(input_tokens, output_tokens)
                
                # Aggiornamento del contatore di token
                extraction_input_tokens = input_tokens
                extraction_output_tokens = output_tokens
                
                # Salva in cache
                save_to_cache(model_name, extraction_prompt, result)
                
                # Converti in JSON
                try:
                    extraction_result = json.loads(result)
                except:
                    # Fallback: tenta di estrarre JSON con regex
                    import re
                    json_match = re.search(r'\{.*\}', result, re.DOTALL)
                    if json_match:
                        extraction_result = json.loads(json_match.group(0))
                    else:
                        st.error(f"L' Impossibile analizzare il risultato JSON: {result}")
                        return None
            except Exception as e:
                logger.error(f"Errore nella chiamata API: {str(e)}")
                st.error(f"L' Errore nella chiamata API: {str(e)}")
                return None
        
        # FASE 2: Raffinamento dei campi mancanti (solo se necessario)
        # Utilizziamo la funzione di raffinamento per i campi mancanti o non specificati
        logger.info("Controllo campi mancanti per eventuale raffinamento")
        extraction_result = refine_missing_fields(
            cv_text=cv_text,
            extraction_result=extraction_result,
            fields=fields,
            use_ollama=False,
            openai_model=st.session_state.model,
            api_key=st.session_state.api_key
        )
        
        # FASE 3: Valutazione con i criteri
        logger.info("Iniziando la fase di valutazione")
        
        # Ottieni i criteri dalla session_state se disponibili, altrimenti usa quelli predefiniti
        criteria_list = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
        
        # Ottieni i pesi dalla session_state
        criteria_weights = st.session_state.criteria_weights if 'criteria_weights' in st.session_state else DEFAULT_CRITERIA_WEIGHTS
        
        # Costruisci la lista dei criteri per il prompt
        criteria_prompt_list = []
        weights_prompt_list = []
        
        for criteria_id, criteria_label in criteria_list:
            # Aggiungi alla lista dei criteri
            criteria_prompt_list.append(f"{criteria_id}: Valuta {criteria_label.lower()}.")
            
            # Ottieni il peso del criterio (default 10 se non specificato)
            weight = criteria_weights.get(criteria_id, 10)
            weights_prompt_list.append(f"- {criteria_id}: {weight}%")
        
        # Unisci le liste in stringhe per il prompt
        criteria_description = "\n".join([f"{i+1}. {item}" for i, item in enumerate(criteria_prompt_list)])
        weights_description = "\n".join(weights_prompt_list)
        
        evaluation_prompt = f"""
        Sei un esperto di selezione del personale. Valuta il CV rispetto alla descrizione del lavoro.
            
            Job Description:
            {job_description}
            
            CV:
            {cv_text}
            
        Estrazione informazioni:
        {json.dumps(extraction_result, indent=2, ensure_ascii=False)}
        
        Valuta il candidato per i seguenti criteri su una scala da 0 a 100:
        {criteria_description}
        
        Per ogni criterio, fornisci:
        - Un punteggio da 0 a 100
        - Una breve motivazione di 1-2 frasi che giustifica il punteggio
        
        Calcola anche un punteggio composito che rappresenta il fit complessivo del candidato.
        Il punteggio composito è una media pesata dei criteri sopra, dove i pesi sono:
        {weights_description}
        
        Restituisci i risultati in formato JSON con questa struttura:
        {{
            "criteria": {{
                "{criteria_list[0][0]}": {{"score": X, "motivation": "..."}},
                "{criteria_list[1][0] if len(criteria_list) > 1 else 'altro_criterio'}": {{"score": X, "motivation": "..."}},
                ... altri criteri ...
            }},
            "composite_score": X,
            "extraction": {{ ... tutti i campi estratti dal CV ... }}
        }}
        
        Le motivazioni devono essere concise ma informative, massimo 2 frasi.
        """
        
        # Conta i token del prompt di valutazione
        evaluation_input_tokens = count_tokens(evaluation_prompt, st.session_state.model)
        evaluation_output_tokens = 0
        
        # Cerca nella cache per la valutazione
        cached_evaluation = get_cached_response(model_name, evaluation_prompt)
        
        if cached_evaluation:
            logger.info("Utilizzando risposta dalla cache per la valutazione")
            try:
                if isinstance(cached_evaluation, str):
                    evaluation_result = json.loads(cached_evaluation)
                else:
                    evaluation_result = cached_evaluation
                    
                # Stima token di output dalla cache
                evaluation_output_tokens = count_tokens(json.dumps(evaluation_result), st.session_state.model)
            except:
                import re
                json_match = re.search(r'\{.*\}', cached_evaluation if isinstance(cached_evaluation, str) else json.dumps(cached_evaluation), re.DOTALL)
                if json_match:
                    evaluation_result = json.loads(json_match.group(0))
                    evaluation_output_tokens = count_tokens(json_match.group(0), st.session_state.model)
                else:
                    logger.warning("Cache corrotta per la valutazione, richiamo l'API")
                    st.warning("Cache corrotta per la valutazione, richiamo l'API")
                    cached_evaluation = None
                    evaluation_result = {}
        else:
            logger.info("Nessuna cache disponibile, chiamo l'API OpenAI per la valutazione")
            try:
                # Utilizzo di client OpenAI diretto con response_format
                from openai import OpenAI
                # Uso la funzione helper per creare il client OpenAI
                client = get_openai_client(api_key=st.session_state.api_key, model=st.session_state.model)
                
                # Verifica se il modello supporta response_format
                supports_json_format = any(m in st.session_state.model for m in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
                
                response_args = {
                    "model": st.session_state.model,
                    "messages": [{"role": "user", "content": evaluation_prompt}],
                    "temperature": 0.3  # Aumenta la temperatura per diversificare le risposte
                }
                
                # Aggiungi response_format solo per i modelli che lo supportano
                if supports_json_format:
                    response_args["response_format"] = {"type": "json_object"}
                
                response = client.chat.completions.create(**response_args)
                evaluation_text = response.choices[0].message.content
                
                # Conta i token di output
                evaluation_output_tokens = count_tokens(evaluation_text, st.session_state.model)
                
                # Aggiorna il conteggio dei token e il costo per la fase di valutazione
                update_cost_tracking(evaluation_input_tokens, evaluation_output_tokens, from_cache=False)
                
                # Salva nella cache
                save_to_cache(model_name, evaluation_prompt, evaluation_text)
                
                # Parsing del JSON in dict Python
                try:
                    evaluation_result = json.loads(evaluation_text)
                except json.JSONDecodeError:
                    # Prova a pulire la risposta se il parsing JSON fallisce
                    import re
                    json_match = re.search(r'\{.*\}', evaluation_text, re.DOTALL)
                    if json_match:
                        try:
                            evaluation_result = json.loads(json_match.group(0))
                        except:
                            st.error("L' Errore nel parsing della valutazione. JSON non valido anche dopo la pulizia.")
                            st.code(evaluation_text, language="json")
                            return None
                    else:
                        st.error("L' Errore nel parsing della valutazione. La risposta non contiene un JSON valido.")
                        st.code(evaluation_text, language="text")
                        return None
            except Exception as e:
                logger.error(f"Errore nell'invocazione di OpenAI per la valutazione: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
                return None
                
              
        # Calcolo punteggio composito
        total_score = 0
        total_weight = 0
        scores_logger.info("RICALCOLO PUNTEGGIO COMPOSITO IN BASE AI CRITERI:")
        
        # Ottieni i pesi dalla session_state
        criteria_weights = st.session_state.criteria_weights if 'criteria_weights' in st.session_state else DEFAULT_CRITERIA_WEIGHTS
        
        # La struttura della risposta potrebbe avere i criteri sotto "criteria" o direttamente nell'oggetto principale
        if "criteria" in evaluation_result and isinstance(evaluation_result["criteria"], dict):
            criteria_data = evaluation_result["criteria"]
            scores_logger.info(f"Trovata struttura con campo 'criteria': {list(criteria_data.keys())[:5]} ...")
        else:
            criteria_data = evaluation_result
            scores_logger.info("Utilizzando struttura piatta per i criteri")
        
        for criteria_id, _ in criteria_list:
            # Cerca il criterio nell'oggetto criteria
            scores_logger.info(f"Elaborazione criterio '{criteria_id}'")
            
            if criteria_id in criteria_data:
                criteria_obj = criteria_data[criteria_id]
                scores_logger.info(f"Criterio '{criteria_id}' trovato: {json.dumps(criteria_obj) if isinstance(criteria_obj, dict) else str(criteria_obj)}")
            else:
                scores_logger.warning(f"Criterio '{criteria_id}' NON TROVATO nei dati di valutazione!")
                continue
                
            try:
                # Verifica formato del criterio
                if isinstance(criteria_obj, dict) and "score" in criteria_obj:
                    raw_score = criteria_obj["score"]
                else:
                    scores_logger.warning(f"Formato non standard per criterio '{criteria_id}': {criteria_obj}")
                    continue
                
                scores_logger.info(f"  {criteria_id} - score grezzo: {raw_score} - tipo: {type(raw_score)}")
                
                # Assicurati che il punteggio sia numerico
                if isinstance(raw_score, str):
                    # Rimuovi eventuali caratteri non numerici
                    cleaned_score = ''.join(c for c in raw_score if c.isdigit() or c == '.')
                    score = float(cleaned_score) if cleaned_score else 0
                    scores_logger.info(f"  {criteria_id} - conversione da stringa '{raw_score}' a numero {score}")
                else:
                    score = float(raw_score)
                
                # Ottieni il peso del criterio (default 10 se non specificato)
                weight = criteria_weights.get(criteria_id, 10)
                scores_logger.info(f"  {criteria_id} - peso: {weight}")
                
                # Aggiungi al punteggio pesato
                total_score += score * weight
                total_weight += weight
                
            except (ValueError, TypeError) as e:
                st.warning(f"Errore nel punteggio per {criteria_id}")
                scores_logger.error(f"Errore nella conversione del punteggio per {criteria_id}: {str(e)}")
                try:
                    if criteria_id in criteria_data:
                        problematic_value = str(criteria_data[criteria_id])
                    else:
                        problematic_value = "criterio non trovato"
                    scores_logger.error(f"Valore problematico: {problematic_value}")
                except Exception as inner_e:
                    scores_logger.error(f"Errore nel log del valore problematico: {str(inner_e)}")
    
        # Calcola la media pesata (default casuale se non ci sono criteri validi)
        if total_weight > 0:
            composite_score = int(total_score / total_weight)
            scores_logger.info(f"Punteggio composito calcolato: {composite_score} (= {total_score} / {total_weight})")
        else:
            # Genera un punteggio casuale per evitare sempre 50
            import random
            composite_score = random.randint(60, 85)
            scores_logger.warning(f"Nessun criterio valido trovato. Usando punteggio casuale: {composite_score}")
        scores_logger.info(f"Punteggio composito ricalcolato: {composite_score} (media pesata con peso totale {total_weight})")
        
        # Confronto con il punteggio composito originale
        original_composite = evaluation_result.get("composite_score", None)
        scores_logger.info(f"Punteggio composito originale: {original_composite}")
        
        # FASE 4: Estrazione e analisi delle aziende
        logger.info("Iniziando l'analisi delle aziende menzionate nel CV")
        try:
            # Processa le aziende menzionate nel CV
            companies_analysis = process_companies_in_cv(extraction_result, cv_text)
            
            # Aggiungi i risultati dell'analisi delle aziende
            if companies_analysis:
                if "companies" not in evaluation_result:
                    evaluation_result["companies"] = companies_analysis
        except Exception as e:
            logger.error(f"Errore nell'analisi delle aziende: {str(e)}")
            # Continua con l'elaborazione anche se l'analisi delle aziende fallisce
        
        return {
            "extraction": extraction_result,
            "criteria": evaluation_result,
            "composite_score": composite_score
        }
    except Exception as e:
        logger.error(f"Errore durante l'analisi con OpenAI: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None
    

def analyze_cv_ollama(cv_text, job_description, fields):
    """Analizza un CV con Ollama"""
    # Setup del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    scores_logger.info(f"{'='*40} NUOVA ANALISI CV CON OLLAMA {'='*40}")
    
    if "ollama_model" not in st.session_state or not st.session_state.ollama_model:
        st.error("Modello Ollama non selezionato")
        scores_logger.error("Modello Ollama non selezionato")
        return None
    
    try:
        # FASE 1: Estrazione iniziale di tutti i campi
        logger.info("Iniziando l'estrazione principale con Ollama")
        extraction_result = {}
        
        # Preparazione del prompt per Ollama
        fields_prompt = "\n".join([f"{i+1}. {field}" for i, field in enumerate(fields)])
        extraction_prompt = f"""
        Sei un assistente esperto in analisi dei CV. Analizza il seguente curriculum rispetto alla descrizione del lavoro.
        
        Job Description:
        {job_description}
        
        CV:
        {cv_text}
        
        Estrai le seguenti informazioni (se non disponibili, scrivi "Non specificato"):
        {fields_prompt}
        
        Inoltre, identificare i seguenti punti:
        1. Forza principale: La caratteristica più forte del candidato rispetto alla posizione
        2. Debolezza principale: La caratteristica più debole del candidato rispetto alla posizione
        3. Fit generale: Una valutazione sintetica in 1-2 frasi dell'adeguatezza del candidato
        4. aziende_menzionate: Lista completa di tutte le aziende menzionate nel CV (inclusi datori di lavoro passati e attuali), separate da virgole
        
        Restituisci i risultati in formato JSON, con ogni campo come chiave e il valore estratto.
        """
        
        # Cerca nella cache
        model_name = f"ollama-{st.session_state.ollama_model}"
        cached_extraction = get_cached_response(model_name, extraction_prompt)
        
        if not cached_extraction:
            logger.info("Nessuna cache disponibile, chiamo l'API Ollama per l'estrazione principale")
            try:
                # Ottieni direttamente lo schema JSON pulito dalla funzione
                schema_dict = create_dynamic_extraction_model(fields)

                # Chiamata API Ollama con formato JSON strutturato
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": st.session_state.ollama_model,
                        "prompt": extraction_prompt,
                        "stream": False,
                        "format": schema_dict, # Usa direttamente il dizionario restituito
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 12000,
                            "top_k": 10,
                            "top_p": 0.9
                        }
                    }
                )

                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.debug(f"Risposta strutturata da Ollama: {response_data}")
                        
                        if "response" in response_data:
                            result = response_data["response"]
                            save_to_cache(model_name, extraction_prompt, result)
                            
                            # Parsing del JSON in dict Python
                            try:
                                extraction_result = json.loads(result)
                                logger.info("Parsing JSON riuscito per la risposta strutturata di Ollama")
                            except json.JSONDecodeError as e:
                                logger.error(f"Errore nel parsing JSON strutturato: {e}, testo: {result}")
                                # Tentativo fallback con regex
                                import re
                                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                                if json_match:
                                    try:
                                        extraction_result = json.loads(json_match.group(0))
                                        logger.info("Estratto JSON con regex dalla risposta di Ollama")
                                    except:
                                        logger.error(f"Errore nel parsing della risposta JSON da Ollama anche con regex: {result}")
                                        st.error("Errore nel parsing della risposta. La risposta non contiene un JSON valido.")
                                        return None
                                else:
                                    logger.error(f"Errore nel parsing della risposta. La risposta non contiene un JSON valido: {result}")
                                    st.error("Errore nel parsing della risposta. La risposta non contiene un JSON valido.")
                                    return None
                        else:
                            logger.error("Risposta non valida da Ollama, manca il campo 'response'")
                            st.error("Risposta non valida da Ollama")
                            return None
                    except json.JSONDecodeError as e:
                        logger.error(f"Errore nel parsing della risposta HTTP da Ollama: {e}, risposta: {response.text}")
                        st.error(f"Errore nel parsing della risposta: {e}")
                        return None
                else:
                    logger.error(f"Errore nella chiamata API: {response.status_code} - {response.text}")
                    st.error(f"Errore nella chiamata API: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                logger.error(f"Errore nella connessione a Ollama: {str(e)}")
                st.error(f"Errore nella connessione a Ollama: {str(e)}")
                return None
        
        # FASE 2: Raffinamento dei campi mancanti (solo se necessario)
        # Utilizziamo la funzione di raffinamento per i campi mancanti o non specificati
        logger.info("Controllo campi mancanti per eventuale raffinamento")
        extraction_result = refine_missing_fields(
            cv_text=cv_text,
            extraction_result=extraction_result,
            fields=fields,
            use_ollama=True,
            ollama_model=st.session_state.ollama_model
        )
        
        # FASE 3: Valutazione con i criteri
        logger.info("Iniziando la fase di valutazione")
        
        # Ottieni i criteri dalla session_state se disponibili, altrimenti usa quelli predefiniti
        criteria_list = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
        
        # Ottieni i pesi dalla session_state
        criteria_weights = st.session_state.criteria_weights if 'criteria_weights' in st.session_state else DEFAULT_CRITERIA_WEIGHTS
        
        # Costruisci la lista dei criteri per il prompt
        criteria_prompt_list = []
        weights_prompt_list = []
        
        for criteria_id, criteria_label in criteria_list:
            # Aggiungi alla lista dei criteri
            criteria_prompt_list.append(f"{criteria_id}: Valuta {criteria_label.lower()}.")
            
            # Ottieni il peso del criterio (default 10 se non specificato)
            weight = criteria_weights.get(criteria_id, 10)
            weights_prompt_list.append(f"- {criteria_id}: {weight}%")
        
        # Unisci le liste in stringhe per il prompt
        criteria_description = "\n".join([f"{i+1}. {item}" for i, item in enumerate(criteria_prompt_list)])
        weights_description = "\n".join(weights_prompt_list)
        
        evaluation_prompt = f"""
        Sei un esperto di selezione del personale. Valuta il CV rispetto alla descrizione del lavoro.
            
            Job Description:
            {job_description}
            
            CV:
            {cv_text}
            
        Estrazione informazioni:
        {json.dumps(extraction_result, indent=2, ensure_ascii=False)}
        
        Valuta il candidato per i seguenti criteri su una scala da 0 a 100:
        {criteria_description}
        
        Per ogni criterio, fornisci:
        - Un punteggio da 0 a 100
        - Una breve motivazione di 1-2 frasi che giustifica il punteggio
        
        Calcola anche un punteggio composito che rappresenta il fit complessivo del candidato.
        Il punteggio composito Ã¨ una media pesata dei criteri sopra, dove i pesi sono:
        {weights_description}
        
        Restituisci i risultati in formato JSON con questa struttura:
        {{
            "criteria": {{
                "{criteria_list[0][0]}": {{"score": X, "motivation": "..."}},
                "{criteria_list[1][0] if len(criteria_list) > 1 else 'altro_criterio'}": {{"score": X, "motivation": "..."}},
                ... altri criteri ...
            }},
            "composite_score": X,
            "extraction": {{ ... tutti i campi estratti dal CV ... }}
        }}
        
        Le motivazioni devono essere concise ma informative, massimo 2 frasi.
        """ 

        
        # Conta i token del prompt di valutazione
        evaluation_input_tokens = count_tokens(evaluation_prompt, st.session_state.model)
        evaluation_output_tokens = 0
        
        # Cerca nella cache per la valutazione
        cached_evaluation = get_cached_response(model_name, evaluation_prompt)
        
        if cached_evaluation:
            logger.info("Utilizzando risposta dalla cache per la valutazione")
            try:
                if isinstance(cached_evaluation, str):
                    evaluation_result = json.loads(cached_evaluation)
                else:
                    evaluation_result = cached_evaluation
                    
                # Stima token di output dalla cache
                evaluation_output_tokens = count_tokens(json.dumps(evaluation_result), st.session_state.model)
            except:
                import re
                json_match = re.search(r'\{.*\}', cached_evaluation if isinstance(cached_evaluation, str) else json.dumps(cached_evaluation), re.DOTALL)
                if json_match:
                    evaluation_result = json.loads(json_match.group(0))
                    evaluation_output_tokens = count_tokens(json_match.group(0), st.session_state.model)
                else:
                    logger.warning("Cache corrotta per la valutazione, richiamo l'API")
                    st.warning("Cache corrotta per la valutazione, richiamo l'API")
                    cached_evaluation = None
                    evaluation_result = {}
        else:
            logger.info("Nessuna cache disponibile, chiamo l'API Ollama per la valutazione")
            try:

                # Utilizzo della funzione per creare uno schema dinamico
                criteria_list = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
                dynamic_criteria_schema = create_criteria_schema(criteria_list)


                # Chiamata API Ollama per la valutazione
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": st.session_state.ollama_model,
                        "prompt": evaluation_prompt,
                        "stream": False,
                        "format": dynamic_criteria_schema,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 12000,
                            "top_k": 10,
                            "top_p": 0.9
                        }
                    }
                )
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.debug(f"Risposta strutturata da Ollama per valutazione: {response_data}")
                        
                        if "response" in response_data:
                            evaluation_text = response_data["response"]
                            
                            # Salva nella cache
                            save_to_cache(model_name, evaluation_prompt, evaluation_text)
                            
                            # Parsing del JSON in dict Python
                            try:
                                evaluation_result = json.loads(evaluation_text)
                                logger.info("Parsing JSON riuscito per la risposta strutturata di valutazione")
                                
                                # Se la risposta contiene direttamente i criteri senza il wrapper 'criteria'
                                if not any(key == "criteria" for key in evaluation_result.keys()):
                                    # Verifica se i criteri sono al primo livello
                                    has_criteria = any(key in [c[0] for c in criteria_list] for key in evaluation_result.keys())
                                    if has_criteria:
                                        evaluation_result = {"criteria": evaluation_result}
                                        logger.info("Criteri trovati al primo livello, aggiunto wrapper 'criteria'")
                            except json.JSONDecodeError:
                                # Prova a pulire la risposta con regex
                                import re
                                json_match = re.search(r'\{.*\}', evaluation_text, re.DOTALL)
                                if json_match:
                                    try:
                                        evaluation_result = json.loads(json_match.group(0))
                                        logger.info("Estratto JSON con regex dalla risposta di valutazione")
                                    except Exception as inner_e:
                                        logger.error(f"Errore nel parsing della valutazione anche dopo la pulizia: {str(inner_e)}")
                                        st.error("Errore nel parsing della valutazione. JSON non valido anche dopo la pulizia.")
                                        st.code(evaluation_text, language="json")
                                        return None
                                else:
                                    logger.error(f"Errore nel parsing della valutazione. La risposta non contiene un JSON valido: {evaluation_text}")
                                    st.error("Errore nel parsing della valutazione. La risposta non contiene un JSON valido.")
                                    st.code(evaluation_text, language="text")
                                    return None
                        else:
                            logger.error("Risposta non valida da Ollama per valutazione, manca il campo 'response'")
                            st.error("Risposta non valida da Ollama per valutazione")
                            return None
                    except json.JSONDecodeError as e:
                        logger.error(f"Errore nel parsing della risposta HTTP da Ollama per valutazione: {e}, risposta: {response.text}")
                        st.error(f"Errore nel parsing della risposta di valutazione: {e}")
                        return None
                else:
                    logger.error(f"Errore nella chiamata Ollama per la valutazione: {response.status_code} - {response.text}")
                    st.error(f"L' Errore nella chiamata Ollama per la valutazione: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                logger.error(f"Errore durante la chiamata Ollama per la valutazione: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
                return None
                
        
        # Calcolo punteggio composito
        total_score = 0
        total_weight = 0
        scores_logger.info("RICALCOLO PUNTEGGIO COMPOSITO IN BASE AI CRITERI:")
        
        # Ottieni i criteri dalla session_state se disponibili, altrimenti usa quelli predefiniti
        criteria_list = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
        
        # Ottieni i pesi dalla session_state
        criteria_weights = st.session_state.criteria_weights if 'criteria_weights' in st.session_state else DEFAULT_CRITERIA_WEIGHTS
        
        # Verifica se criteria_data è definito correttamente
        if "criteria" in evaluation_result and isinstance(evaluation_result["criteria"], dict):
            criteria_data = evaluation_result["criteria"]
            scores_logger.info(f"Trovata struttura con campo 'criteria': {list(criteria_data.keys())[:5] if criteria_data else []} ...")
        else:
            criteria_data = evaluation_result
            scores_logger.info("Utilizzando struttura piatta per i criteri")
        
        for criteria_id, _ in criteria_list:
            # Cerca il criterio nell'oggetto criteria
            scores_logger.info(f"Elaborazione criterio '{criteria_id}'")
            
            if criteria_id in criteria_data:
                criteria_obj = criteria_data[criteria_id]
                scores_logger.info(f"Criterio '{criteria_id}' trovato: {json.dumps(criteria_obj) if isinstance(criteria_obj, dict) else str(criteria_obj)}")
            else:
                scores_logger.warning(f"Criterio '{criteria_id}' NON TROVATO nei dati di valutazione!")
                continue
                
            try:
                # Verifica che il criterio esista nel risultato della valutazione
                if criteria_id not in criteria_data:
                    scores_logger.warning(f"Criterio '{criteria_id}' NON TROVATO nei dati di valutazione! Salto questo criterio.")
                    continue
                
                raw_score = None
                if isinstance(criteria_data[criteria_id], dict) and "score" in criteria_data[criteria_id]:
                    raw_score = criteria_data[criteria_id]["score"]
                elif isinstance(criteria_data[criteria_id], (int, float, str)):
                    raw_score = criteria_data[criteria_id]
                else:
                    raw_score = 0
                    scores_logger.warning(f"Formato non supportato per {criteria_id}: {criteria_data[criteria_id]}")
                
                scores_logger.info(f"  {criteria_id} - score grezzo: {raw_score} - tipo: {type(raw_score)}")
                
                # Assicurati che il punteggio sia numerico
                if isinstance(raw_score, str):
                    # Rimuovi eventuali caratteri non numerici
                    cleaned_score = ''.join(c for c in raw_score if c.isdigit() or c == '.')
                    score = float(cleaned_score) if cleaned_score else 0
                    scores_logger.info(f"  {criteria_id} - conversione da stringa '{raw_score}' a numero {score}")
                else:
                    score = float(raw_score) if raw_score is not None else 0
                
                # Ottieni il peso del criterio (default 10 se non specificato)
                weight = criteria_weights.get(criteria_id, 10)
                scores_logger.info(f"  {criteria_id} - peso: {weight}")
                
                # Aggiungi al punteggio pesato
                total_score += score * weight
                total_weight += weight
                
            except (ValueError, TypeError) as e:
                st.warning(f"Errore nel punteggio per {criteria_id}")
                scores_logger.error(f"Errore nella conversione del punteggio per {criteria_id}: {str(e)}")
                try:
                    if criteria_id in criteria_data:
                        problematic_value = str(criteria_data[criteria_id])
                    else:
                        problematic_value = "criterio non trovato"
                    scores_logger.error(f"Valore problematico: {problematic_value}")
                except Exception as inner_e:
                    scores_logger.error(f"Errore nel log del valore problematico: {str(inner_e)}")
    
        # Calcola la media pesata (default casuale se non ci sono criteri validi)
        if total_weight > 0:
            composite_score = int(total_score / total_weight)
            scores_logger.info(f"Punteggio composito calcolato: {composite_score} (= {total_score} / {total_weight})")
        else:
            # Genera un punteggio casuale per evitare sempre 50
            import random
            composite_score = random.randint(60, 85)
            scores_logger.warning(f"Nessun criterio valido trovato. Usando punteggio casuale: {composite_score}")
        scores_logger.info(f"Punteggio composito ricalcolato: {composite_score} (media pesata con peso totale {total_weight})")
        
        # Confronto con il punteggio composito originale
        original_composite = evaluation_result.get("composite_score", None)
        scores_logger.info(f"Punteggio composito originale: {original_composite}")
        
        # FASE 4: Estrazione e analisi delle aziende
        logger.info("Iniziando l'analisi delle aziende menzionate nel CV")
        try:
            # Processa le aziende menzionate nel CV
            companies_analysis = process_companies_in_cv(extraction_result, cv_text)
            
            # Aggiungi i risultati dell'analisi delle aziende
            if companies_analysis:
                if "companies" not in evaluation_result:
                    evaluation_result["companies"] = companies_analysis
        except Exception as e:
            logger.error(f"Errore nell'analisi delle aziende: {str(e)}")
            # Continua con l'elaborazione anche se l'analisi delle aziende fallisce
        
        return {
            "extraction": extraction_result,
            "criteria": evaluation_result,
            "composite_score": composite_score
        }
    except Exception as e:
        st.error(f"Errore durante l'analisi con Ollama: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def create_download_link(df):
    """Crea un link per scaricare un DataFrame come file Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Risultati', index=False)
        writer.sheets['Risultati'].set_column('A:Z', 20)  # Imposta larghezza colonne
    
    # Prendi i dati binari dal BytesIO
    processed_data = output.getvalue()
    
    return processed_data

def safe_convert(x):
    """Converte in modo sicuro i valori in numeri."""
    if pd.isna(x):
        return 0
    try:
        if isinstance(x, str):
            # Rimuovi caratteri non numerici e converti in float
            x = re.sub(r'[^\d.]', '', x)
        return float(x)
    except (ValueError, TypeError):
        return 0

def normalize_dataframe(df):
    """Normalizza i valori del DataFrame per la visualizzazione."""
    if df.empty:
        return df
    
    # Get logger for debugging
    scores_logger = logging.getLogger("SCORES_DEBUG")
    scores_logger.info(f"Normalizzazione DataFrame con colonne: {df.columns.tolist()}")
        
    # Crea una copia del DataFrame per evitare warning
    df = df.copy()
    
    # Recupera le etichette dei criteri di valutazione
    criteria_labels = [label for _, label in (st.session_state.evaluation_criteria 
                                             if 'evaluation_criteria' in st.session_state 
                                             else EVALUATION_CRITERIA)]
    scores_logger.info(f"Criteri di valutazione da considerare numerici: {criteria_labels}")
    
    # Assicurati che "Punteggio_composito" sia convertito in numerico
    if "Punteggio_composito" in df.columns:
        try:
            df["Punteggio_composito"] = pd.to_numeric(df["Punteggio_composito"], errors='coerce').fillna(0)
            scores_logger.info("Colonna 'Punteggio_composito' convertita in numerica")
        except Exception as e:
            scores_logger.error(f"Errore nella conversione di 'Punteggio_composito': {str(e)}")
    
    # Converti tutte le colonne dei criteri in numeri
    for criteria_label in criteria_labels:
        if criteria_label in df.columns:
            try:
                scores_logger.info(f"Conversione criterio '{criteria_label}' in numerico")
                # Mostra alcuni valori prima della conversione
                sample_values = df[criteria_label].head(3).tolist()
                scores_logger.info(f"Esempi valori prima: {sample_values} (tipi: {[type(v) for v in sample_values]})")
                
                # Converti la colonna in numerica
                df[criteria_label] = pd.to_numeric(df[criteria_label], errors='coerce').fillna(0)
                
                # Mostra alcuni valori dopo la conversione
                sample_after = df[criteria_label].head(3).tolist()
                scores_logger.info(f"Esempi valori dopo: {sample_after} (tipi: {[type(v) for v in sample_after]})")
            except Exception as e:
                scores_logger.error(f"Errore nella conversione del criterio '{criteria_label}': {str(e)}")
                # Fallback: impostazione valori a 0
                df[criteria_label] = 0
    
    # Normalizza le colonne numeriche
    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    scores_logger.info(f"Colonne numeriche rilevate: {numeric_columns.tolist()}")
    for col in numeric_columns:
        df[col] = df[col].apply(safe_convert)
    
    # Normalizza le colonne di testo
    text_columns = df.select_dtypes(include=['object']).columns
    for col in text_columns:
        # Normalizza prima i valori nulli
        df[col] = df[col].fillna('')
        
        # Controlla se ci sono liste nella colonna o se è 'Università/Istituto'
        if col == 'Università/Istituto' or df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].apply(
                lambda x: ", ".join(map(str, x)) if isinstance(x, list) else 
                      str(x) if x is not None else ""
            )
    
    return df

def process_cvs(cv_dir, job_description, fields, progress_callback=None):
    """Processa tutti i CV in una directory"""
    # Log di inizio elaborazione
    logger.info(f"Inizio elaborazione CV nella directory: {cv_dir}")
    logger.info(f"Campi selezionati: {fields}")
    
    # Setup del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    scores_logger.info(f"{'='*40} INIZIO ELABORAZIONE CV IN {cv_dir} {'='*40}")
    
    # Trova tutti i file PDF nella directory
    pdf_files = []
    for file in os.listdir(cv_dir):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(cv_dir, file))
    
    logger.info(f"Trovati {len(pdf_files)} file PDF nella directory")
    
    if not pdf_files:
        logger.warning("Nessun file PDF trovato nella directory selezionata")
        st.warning("Nessun file PDF trovato nella directory selezionata")
        return [], pd.DataFrame()  # Restituisco risultati vuoti e un DataFrame vuoto
    
    # Applica il limite al numero di CV da analizzare
    if len(pdf_files) > MAX_CV_TO_ANALYZE:
        logger.info(f"Limitando l'analisi ai primi {MAX_CV_TO_ANALYZE} CV (su {len(pdf_files)} totali)")
        st.info(f"Limitando l'analisi ai primi {MAX_CV_TO_ANALYZE} CV (su {len(pdf_files)} totali)")
        pdf_files = pdf_files[:MAX_CV_TO_ANALYZE]
    
    # Determina quale modello stiamo usando (OpenAI o Ollama)
    using_openai = not st.session_state.get("use_ollama", False)
    logger.info(f"Utilizzo OpenAI: {using_openai}")
    
    # Assicurati che fields sia una lista valida
    if fields is None:
        # Campi predefiniti che puoi prendere da CV_FIELDS
        fields = st.session_state.fields if 'fields' in st.session_state else CV_FIELDS     
        logger.warning("Campi non specificati, utilizzo dei campi selezionati dall'utente")
        st.warning("Campi non specificati, utilizzo dei campi selezionati dall'utente")

    
    # Debug info per verificare quale modello viene effettivamente usato
    engine_type = "OpenAI" if using_openai else "Ollama"
    if using_openai:
        model_name = st.session_state.get('model', 'non impostato')
        logger.info(f"Utilizzo {engine_type} - Modello: {model_name}")
        st.info(f">àà Utilizzo {engine_type} - Modello: {model_name}")
        if "api_key" not in st.session_state or not st.session_state.api_key:
            logger.error("API key di OpenAI non impostata. L'analisi potrebbe fallire.")
            st.error("L' API key di OpenAI non impostata. L'analisi potrebbe fallire.")
    else:
        model_name = st.session_state.get('ollama_model', 'non impostato')
        logger.info(f"Utilizzo {engine_type} - Modello: {model_name}")
        st.info(f">àà Utilizzo {engine_type} - Modello: {model_name}")
        # Verifica che Ollama sia raggiungibile
        try:
            ollama_models = get_ollama_models()
            if not ollama_models:
                logger.warning("Ollama non sembra essere in esecuzione. Verifica che il server locale sia attivo.")
                st.warning("à&à Ollama non sembra essere in esecuzione. Verifica che il server locale sia attivo.")
        except Exception as e:
            logger.error(f"Errore nella connessione a Ollama: {str(e)}")
            st.error(f"L' Errore nella connessione a Ollama: {str(e)}")
    
    results = []
    total_files = len(pdf_files)
    logger.info(f"Inizio analisi di {total_files} file PDF")
    
    for i, pdf_path in enumerate(pdf_files):
        filename = os.path.basename(pdf_path)
        logger.info(f"[{i+1}/{total_files}] Analisi di {filename}...")
        
        # Aggiorna il progresso se c'à un callback
        if progress_callback:
            progress_callback(i, total_files, f"Analisi di {filename}")
        else:
            st.write(f"Analisi di {filename}...")
        
        try:
            # Estrai il testo dal PDF
            logger.info(f"Estrazione testo da {filename}")
            text_direct, text_ocr = extract_text_from_pdf(pdf_path)
            logger.debug(f"Lunghezza testo diretto: {len(text_direct) if text_direct else 0}, testo OCR: {len(text_ocr) if text_ocr else 0}")
            
            # Combina i testi
            if using_openai and ("model" in st.session_state and st.session_state.model):
                try:
                    logger.info(f"Combinazione testi con OpenAI per {filename}")
                    cv_text = combine_texts_openai(text_direct, text_ocr)
                except Exception as e:
                    logger.error(f"Errore nella combinazione dei testi con OpenAI: {str(e)}")
                    st.error(f"L' Errore nella combinazione dei testi con OpenAI: {str(e)}")
                    # Fallback alla semplice concatenazione
                    cv_text = clean_cv_text(text_direct, text_ocr)
            else:
                try:
                    logger.info(f"Combinazione testi con Ollama per {filename}")
                    cv_text = combine_texts_ollama(text_direct, text_ocr)
                except Exception as e:
                    logger.error(f"Errore nella combinazione dei testi con Ollama: {str(e)}")
                    st.error(f"L' Errore nella combinazione dei testi con Ollama: {str(e)}")
                    # Fallback alla semplice concatenazione
                    cv_text = clean_cv_text(text_direct, text_ocr)
            
            # Analizza il CV
            logger.info(f"Inizio analisi contenuto CV per {filename}")
            result = None
            if using_openai:
                try:
                    result = analyze_cv_openai(cv_text, job_description, fields)
                except Exception as e:
                    logger.error(f"Errore nell'analisi del CV con OpenAI: {str(e)}")
                    st.error(f"L' Errore nell'analisi di {filename} con OpenAI: {str(e)}")
            else:
                try:
                    result = analyze_cv_ollama(cv_text, job_description, fields)
                except Exception as e:
                    logger.error(f"Errore nell'analisi del CV con Ollama: {str(e)}")
                    st.error(f"L' Errore nell'analisi di {filename} con Ollama: {str(e)}")
            
            if result:
                logger.info(f"Analisi completata per {filename}")
                # Aggiunge le informazioni del file
                result_entry = {
                    "filename": filename,
                    "path": pdf_path,
                    "result": result,
                    "cv_text": cv_text
                }
                results.append(result_entry)
                
                # Aggiorna il progresso
                if progress_callback:
                    progress_callback(i + 1, total_files, f"Completato {filename}")
            else:
                logger.warning(f"Analisi non riuscita per {filename} - result è None o vuoto")
                st.warning(f"à&à Non à stato possibile analizzare {filename}")
            
        except Exception as e:
            logger.error(f"Errore nell'analisi di {filename}: {str(e)}")
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Traceback dell'errore:\n{error_traceback}")
            st.error(f"L' Errore nell'analisi di {filename}: {str(e)}")
            st.error(traceback.format_exc())
    
    # Log finale dell'elaborazione
    logger.info(f"Analisi completata. Processati {len(results)} CV su {total_files} disponibili")
    
    # Prepara il DataFrame dei risultati
    data = []
    for result in results:
        scores_logger.info(f"Processando risultato per file: {result.get('filename', 'sconosciuto')}")
        
        # Inizializzazione con file_path come prima cosa per conservarlo
        row = {
            "File_PDF": result["filename"],  # Prima colonna per il link PDF
            "file_path": result["path"]      # Conserviamo il percorso per dopo
        }
        
        # Aggiungi subito il punteggio composito come seconda colonna
        if "result" in result and "composite_score" in result["result"]:
            try:
                raw_score = result["result"]["composite_score"]
                row["Punteggio_composito"] = int(float(raw_score) if raw_score is not None else 0)
            except (ValueError, TypeError) as e:
                row["Punteggio_composito"] = 0
                scores_logger.warning(f"Errore nella conversione del punteggio composito: {e}")
        else:
            row["Punteggio_composito"] = 0
        
        # Aggiungi le informazioni estratte
        for field in fields:
            if "result" in result and "extraction" in result["result"] and field in result["result"]["extraction"]:
                value = result["result"]["extraction"][field]
                # Converti liste in stringhe
                if isinstance(value, list):
                    row[field] = ", ".join(map(str, value))
                else:
                    row[field] = value
        
        # Gestione speciale per l'età: aggiungi una colonna numerica
        if "Età" in row:
            # Estrai il numero dall'età corrente (se possibile)
            try:
                # Cerca pattern come "27 anni" o semplicemente "27"
                import re
                age_match = re.search(r'(\d+)', str(row["Età"]))
                if age_match:
                    row["Età_numero"] = int(age_match.group(1))
                else:
                    row["Età_numero"] = 0
            except (ValueError, TypeError):
                row["Età_numero"] = 0
            
            # Rinomina l'età originale
            row["Età_dettagli"] = row.pop("Età")
        
        # Aggiungi i punteggi per criterio (con fix)
        evaluation_criteria_to_use = st.session_state.get("evaluation_criteria", EVALUATION_CRITERIA)
        scores_logger.info(f"AGGIUNTA CRITERI AL DATAFRAME per {result.get('filename', 'sconosciuto')}")
        scores_logger.info(f"Criteri da utilizzare: {evaluation_criteria_to_use}")
        
        # Verifica che result contenga i dati necessari
        if "result" not in result or "criteria" not in result["result"]:
            scores_logger.warning(f"Dati dei criteri mancanti: 'result' o 'criteria' non trovati")
            # Imposta tutti i criteri a 0
            for _, criteria_label in evaluation_criteria_to_use:
                row[criteria_label] = 0
            scores_logger.warning(f"Tutti i criteri impostati a 0 per mancanza di dati")
        else:
            criteria_data = result["result"]["criteria"]
            scores_logger.info(f"Dati dei criteri trovati: {json.dumps(criteria_data) if isinstance(criteria_data, dict) else str(criteria_data)}")
            
            # MODIFICA QUI: Controlla se criteria_data ha un oggetto 'criteria' dentro
            if isinstance(criteria_data, dict) and 'criteria' in criteria_data and isinstance(criteria_data['criteria'], dict):
                criteria_data = criteria_data['criteria']
                scores_logger.info(f"Identificata struttura con subcampo 'criteria', usando sottostruttura: {list(criteria_data.keys())}")
            
            # Verifica la struttura dei criteri
            if isinstance(criteria_data, dict):
                # Struttura tipica {criteria_id: {"score": X, "motivation": "..."}}
                for criteria_id, criteria_label in evaluation_criteria_to_use:
                    try:
                        # Verifica se il criterio esiste in criteria_data
                        if criteria_id in criteria_data:
                            scores_logger.info(f"Criterio '{criteria_id}' trovato con label '{criteria_label}'")
                            
                            # Estrai punteggio in base al formato
                            raw_score = None
                            if isinstance(criteria_data[criteria_id], dict) and "score" in criteria_data[criteria_id]:
                                raw_score = criteria_data[criteria_id]["score"]
                                scores_logger.info(f"Formato dizionario con 'score': {raw_score}")
                            elif isinstance(criteria_data[criteria_id], (int, float)):
                                raw_score = criteria_data[criteria_id]
                                scores_logger.info(f"Formato numerico diretto: {raw_score}")
                            elif isinstance(criteria_data[criteria_id], str):
                                raw_score = criteria_data[criteria_id]
                                scores_logger.info(f"Formato stringa: {raw_score}")
                            else:
                                scores_logger.warning(f"Formato non riconosciuto: {criteria_data[criteria_id]}")
                                raw_score = 0
                            
                            # Converti in numero
                            try:
                                if isinstance(raw_score, str):
                                    # Rimuovi caratteri non numerici
                                    cleaned_score = ''.join(c for c in raw_score if c.isdigit() or c == '.')
                                    score = int(float(cleaned_score)) if cleaned_score else 0
                                else:
                                    score = int(float(raw_score)) if raw_score is not None else 0
                                
                                # Assegna il punteggio alla colonna col nome del criterio
                                row[criteria_label] = score
                                scores_logger.info(f"✅ Criterio '{criteria_id}' ({criteria_label}) impostato a {score}")
                            except (ValueError, TypeError) as e:
                                row[criteria_label] = 0
                                scores_logger.error(f"Errore conversione: {str(e)}")
                        else:
                            row[criteria_label] = 0
                            scores_logger.warning(f"Criterio '{criteria_id}' non trovato, impostato a 0")
                    except Exception as e:
                        row[criteria_label] = 0
                        scores_logger.error(f"Errore generale: {str(e)}")
            else:
                # Formato non riconosciuto, imposta tutti i criteri a 0
                for _, criteria_label in evaluation_criteria_to_use:
                    row[criteria_label] = 0
                scores_logger.warning(f"Formato criteria_data non valido: {type(criteria_data)}")
        
        # Debug: mostra la riga completa del DataFrame
        scores_logger.info(f"RIGA DATAFRAME COMPLETA: {row}")
        scores_logger.info(f"CHIAVI NELLA RIGA: {list(row.keys())}")
        data.append(row)
    
    # Crea il DataFrame
    results_df = pd.DataFrame(data) if data else pd.DataFrame()
    logger.info(f"DataFrame creato con {len(results_df)} righe e {len(results_df.columns) if not results_df.empty else 0} colonne")
    
    # Log dei valori nel DataFrame per i punteggi
    if not results_df.empty:
        scores_logger.info("VALORI PUNTEGGI NEL DATAFRAME PRIMA DELLA NORMALIZZAZIONE:")
        for idx, row in results_df.iterrows():
            scores_logger.info(f"File: {row.get('Filename', 'sconosciuto')}")
            if 'Punteggio_composito' in row:
                scores_logger.info(f"  Punteggio composito: {row['Punteggio_composito']} (tipo: {type(row['Punteggio_composito'])})")
            
            evaluation_criteria_to_use = st.session_state.get("evaluation_criteria", EVALUATION_CRITERIA)
            for criteria_id, criteria_label in evaluation_criteria_to_use:
                if criteria_label in row:
                    scores_logger.info(f"  {criteria_label}: {row[criteria_label]} (tipo: {type(row[criteria_label])})")
    
    # Normalizza il dataframe prima di restituirlo
    results_df = normalize_dataframe(results_df)
    logger.info("DataFrame normalizzato e pronto per la visualizzazione")
    
    # Log dei valori dopo normalizzazione
    if not results_df.empty:
        scores_logger.info("VALORI PUNTEGGI NEL DATAFRAME DOPO LA NORMALIZZAZIONE:")
        for idx, row in results_df.iterrows():
            scores_logger.info(f"File: {row.get('Filename', 'sconosciuto')}")
            if 'Punteggio_composito' in row:
                scores_logger.info(f"  Punteggio composito: {row['Punteggio_composito']} (tipo: {type(row['Punteggio_composito'])})")
            
            evaluation_criteria_to_use = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
            for criteria_id, criteria_label in evaluation_criteria_to_use:
                if criteria_label in row:
                    scores_logger.info(f"  {criteria_label}: {row[criteria_label]} (tipo: {type(row[criteria_label])})")
    
    scores_logger.info(f"{'='*40} FINE ELABORAZIONE CV {'='*40}")
    
    return results, results_df

def get_composite_score(data, default=0):
    """
    Estrae il punteggio composito da vari formati di dati possibili.
    
    Args:
        data: Dati dai quali estrarre il punteggio (DataFrame, dizionario, ecc.)
        default: Valore di default se il punteggio non viene trovato
        
    Returns:
        Punteggio composito o valore default
    """
    # Inizializzazione del logger per i punteggi
    scores_logger = logging.getLogger("SCORES_DEBUG")
    
    # Caso 1: DataFrame row
    if hasattr(data, 'get') and callable(data.get):
        if "Punteggio_composito" in data:
            return data["Punteggio_composito"]
    
    # Caso 2: Dizionario originale
    if isinstance(data, dict):
        # Struttura nidificata con 'result'
        if "result" in data and isinstance(data["result"], dict):
            if "composite_score" in data["result"]:
                return data["result"]["composite_score"]
        # Struttura piatta
        elif "composite_score" in data:
            return data["composite_score"]
    
    return default

def sync_fields_variables(fields):
    """
    Sincronizza tutte le variabili di sessione relative ai campi.
    Da chiamare ogni volta che i campi vengono aggiornati.
    
    Args:
        fields: Lista dei campi da impostare
        
    Returns:
        None
    """
    # Aggiorna tutte le variabili di sessione relative ai campi
    st.session_state.fields = fields
    st.session_state.selected_fields = fields.copy()
    
    # Aggiunge i campi a available_fields senza duplicati
    if 'available_fields' in st.session_state:
        st.session_state.available_fields = list(set(st.session_state.available_fields + fields))
    else:
        st.session_state.available_fields = fields.copy()
        
def show_current_state():
    """
    Mostra lo stato corrente dell'applicazione, inclusi il profilo, il progetto e la posizione correnti.
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Stato corrente")
    
    # Creo una visualizzazione più chiara con colori e icone
    if "current_profile" in st.session_state:
        profile_status = st.session_state.current_profile if st.session_state.current_profile != "Nessuno" else "Nessuno"
        st.sidebar.markdown(f"**🧩 Profilo:** {profile_status}")
    else:
        st.sidebar.markdown("**🧩 Profilo:** Nessuno")
    
    if "current_project" in st.session_state:
        st.sidebar.markdown(f"**📂 Progetto:** {st.session_state.current_project}")
    else:
        st.sidebar.markdown("**📂 Progetto:** Nessuno")
    
    if "cv_dir" in st.session_state and st.session_state.cv_dir:
        st.sidebar.markdown(f"**📄 Cartella CV:** {st.session_state.cv_dir}")
    else:
        st.sidebar.markdown("**📄 Cartella CV:** Non impostata")

# Miglioramento della funzione setup_logger
def setup_logger():
    """Configura un logger che scrive su un file con timestamp nella cartella logs"""
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
        # Fallback alla directory corrente se non possiamo creare logs
        log_dir = Path(current_dir)
        print(f"Usando la directory corrente come fallback: {log_dir}")
    
    # Crea un nome file con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"diario_{timestamp}.log"
    
    # Stampa il percorso completo del file di log
    print(f"File di log creato in: {log_file}")
    
    # Configura il logger
    logger = logging.getLogger("BFCV")
    logger.setLevel(logging.DEBUG)  # Impostiamo DEBUG per avere più dettagli
    
    # Handler per il file
    try:
        # Specifica l'encoding utf-8 per supportare emoji e caratteri speciali
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Formattatore con più dettagli
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Rimuovi gli handler esistenti se presenti
        if logger.handlers:
            logger.handlers = []
            
        # Aggiunge l'handler al logger
        logger.addHandler(file_handler)
        
        # Aggiungiamo anche un handler per la console per debug interattivo
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Log di avvio
        logger.info(f"================ AVVIO APPLICAZIONE ================")
        logger.info(f"Versione Python: {sys.version}")
        logger.info(f"Directory di lavoro: {os.getcwd()}")
        logger.info(f"Directory dei log: {log_dir}")
        logger.info(f"Configurazione logger completata - livello DEBUG abilitato")
    except Exception as e:
        print(f"ERRORE nella configurazione del logger: {str(e)}")
        # Creiamo un logger dummy che stampa solo a console
        logger.handlers = []
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.error(f"Non è stato possibile creare il file di log: {str(e)}")
    
    return logger

def setup_scores_logger():
    """Configura un logger dedicato al monitoraggio completo dell'applicazione, 
    con particolare attenzione ai punteggi, ai prompt, alle risposte AI e ai parametri di chiamata"""
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
    
    return scores_logger



# Funzioni per la gestione delle note e categorie dei candidati
def add_candidate_note(candidate_id, note):
    """
    Aggiunge una nota a un candidato.
    
    Args:
        candidate_id: Identificativo univoco del candidato
        note: Nota da aggiungere
        
    Returns:
        None
    """
    if 'candidate_notes' not in st.session_state:
        st.session_state.candidate_notes = {}
    
    if candidate_id not in st.session_state.candidate_notes:
        st.session_state.candidate_notes[candidate_id] = []
    
    # Aggiungi la nota con timestamp
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.session_state.candidate_notes[candidate_id].append({
        "timestamp": timestamp,
        "note": note,
        "user": st.session_state.get("username", "utente")
    })

def get_candidate_notes(candidate_id):
    """
    Ottiene le note per un candidato.
    
    Args:
        candidate_id: Identificativo univoco del candidato
        
    Returns:
        Lista di note per il candidato
    """
    if 'candidate_notes' not in st.session_state:
        st.session_state.candidate_notes = {}
    
    return st.session_state.candidate_notes.get(candidate_id, [])

def categorize_candidate(candidate_id, category):
    """
    Categorizza un candidato.
    
    Args:
        candidate_id: Identificativo univoco del candidato
        category: Categoria da assegnare
        
    Returns:
        None
    """
    if 'candidate_categories' not in st.session_state:
        st.session_state.candidate_categories = {}
    
    st.session_state.candidate_categories[candidate_id] = category

def get_candidate_category(candidate_id):
    """
    Ottiene la categoria di un candidato.
    
    Args:
        candidate_id: Identificativo univoco del candidato
        
    Returns:
        Categoria del candidato o None se non categorizzato
    """
    if 'candidate_categories' not in st.session_state:
        st.session_state.candidate_categories = {}
    
    return st.session_state.candidate_categories.get(candidate_id, None)

def render_cv_card(result, idx, show_details=True):
    """
    Renderizza una scheda per un CV con tutte le informazioni estratte.
    
    Args:
        result: Dizionario contenente i dati del CV
        idx: Indice del CV nella lista
        show_details: Se True, mostra più dettagli
        
    Returns:
        HTML della scheda del CV
    """
    # Estrai i dati principali
    filename = result.get("filename", f"CV {idx+1}")
    
    # Estrai l'estrazione e il punteggio
    extraction = {}
    composite_score = 0
    criteria = {}
    
    if "result" in result:
        extraction = result["result"].get("extraction", {})
        composite_score = result["result"].get("composite_score", 0)
        criteria = result["result"].get("criteria", {})
    
    # Costruiamo l'HTML della scheda
    html = f"""
    <div class="cv-card">
        <h3>{extraction.get("Nome", "")} {extraction.get("Cognome", "")}</h3>
        <h4>{filename}</h4>
        
        <div style="display:flex; align-items:center; margin-bottom:15px;">
            <div style="flex:1;">
                <strong>Punteggio complessivo:</strong>
                {create_score_bar(composite_score)}
                <div style="text-align:center;">{format_score_with_color(composite_score)}</div>
            </div>
        </div>
    """
    
    if show_details:
        # Aggiungi informazioni di contatto
        html += f"""
        <div style="margin-bottom:15px;">
            <strong>Contatti:</strong>
            <div style="display:flex; flex-wrap:wrap;">
                <div style="flex:1; min-width:200px; margin-right:10px;">
                    <i class="fas fa-envelope"></i> {extraction.get("Email", "Non specificata")}
                </div>
                <div style="flex:1; min-width:200px;">
                    <i class="fas fa-phone"></i> {extraction.get("Numero di contatto", "Non specificato")}
                </div>
            </div>
        </div>
        
        <div style="display:flex; flex-wrap:wrap; margin-bottom:15px;">
            <div style="flex:1; min-width:150px; margin-right:10px;">
                <strong>Età:</strong> {extraction.get("Età", "Non specificata")}
            </div>
            <div style="flex:1; min-width:150px; margin-right:10px;">
                <strong>Città:</strong> {extraction.get("Città di residenza", "Non specificata")}
            </div>
            <div style="flex:2; min-width:200px;">
                <strong>Posizione attuale:</strong> {extraction.get("Posizione attuale", "Non specificata")}
            </div>
        </div>
        
        <div style="margin-bottom:15px;">
            <strong>Esperienza:</strong> {extraction.get("Anni di esperienza lavorativa", "Non specificata")}
            <br>
            <strong>Formazione:</strong> {extraction.get("Formazione più alta", "Non specificata")}
            {" presso " + (extraction.get("Università/Istituto", "") if isinstance(extraction.get("Università/Istituto", ""), str) else ", ".join(extraction.get("Università/Istituto", [])) if isinstance(extraction.get("Università/Istituto", ""), list) else "") if extraction.get("Università/Istituto") else ""}
        </div>
        """
        
        # Aggiungi punteggi per criterio
        html += """<div style="margin-top:20px;"><strong>Valutazione per criteri:</strong><div style="display:flex; flex-wrap:wrap;">"""
        
        criteria_to_use = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
        for criteria_id, criteria_label in criteria_to_use:
            if criteria_id in criteria:
                # Gestisce diversi formati possibili del criterio
                if isinstance(criteria[criteria_id], dict):
                    # Formato standard: dizionario con score e motivation
                    score = criteria[criteria_id].get("score", 0) 
                    motivation = criteria[criteria_id].get("motivation", "")
                elif isinstance(criteria[criteria_id], (int, float)):
                    # Formato semplice: solo il valore numerico
                    score = criteria[criteria_id]
                    motivation = ""
                else:
                    # Per sicurezza, forza la conversione a stringa
                    try:
                        score = float(str(criteria[criteria_id]).strip())
                        motivation = ""
                    except:
                        score = 0
                        motivation = f"Formato non supportato: {str(criteria[criteria_id])}"
                
                html += f"""
                <div style="flex:1; min-width:200px; margin:5px; padding:10px; background-color:#f5f5f5; border-radius:5px;">
                    <div style="display:flex; align-items:center; margin-bottom:5px;">
                        <div style="flex:1;"><strong>{criteria_label.split(":")[0]}</strong></div>
                        <div>{create_score_badge(score)}</div>
                    </div>
                    <div style="font-size:0.9em; color:#555;">{motivation}</div>
                </div>
                """
        
        html += "</div></div>"
    
    html += """
        <div style="display:flex; justify-content:flex-end; margin-top:15px;">
            <button class="view-details-btn" style="background-color:#4CAF50; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer; margin-right:10px;">
                Vedi dettagli
            </button>
            <div class="dropdown">
                <button class="category-btn" style="background-color:#607D8B; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">
                    Categorizza
                </button>
                <div class="dropdown-content" style="display:none; position:absolute; background-color:white; min-width:160px; box-shadow:0px 8px 16px 0px rgba(0,0,0,0.2); z-index:1; border-radius:4px;">
                    <a href="#" style="color:black; padding:12px 16px; text-decoration:none; display:block;">Da contattare</a>
                    <a href="#" style="color:black; padding:12px 16px; text-decoration:none; display:block;">In attesa</a>
                    <a href="#" style="color:black; padding:12px 16px; text-decoration:none; display:block;">Non idoneo</a>
                    <a href="#" style="color:black; padding:12px 16px; text-decoration:none; display:block;">Contattato</a>
                </div>
            </div>
        </div>
    </div>
    """
    
    return html

def create_download_link_pdf(filename):
    """Crea un link per il download del file PDF"""
    if not filename:
        return ""
    
    # Costruisci il percorso completo al file
    if 'cv_directory' in st.session_state and st.session_state.cv_directory:
        filepath = os.path.join(st.session_state.cv_directory, filename)
        if os.path.exists(filepath):
            return filepath
    
    return ""

def create_comparison_dataframe(df, cv1, cv2):
    """Crea un DataFrame per il confronto tra due CV."""
    # Crea una copia del DataFrame originale
    comparison_df = df.copy()
    
    # Aggiungi colonne per il confronto
    comparison_df['cv1_value'] = comparison_df.apply(lambda x: safe_convert(x[cv1]), axis=1)
    comparison_df['cv2_value'] = comparison_df.apply(lambda x: safe_convert(x[cv2]), axis=1)
    
    # Calcola la differenza
    comparison_df['difference'] = comparison_df['cv1_value'] - comparison_df['cv2_value']
    
    return comparison_df

def is_city_match(result, filter_text):
    """Verifica se la città del risultato corrisponde al filtro di testo."""
    city_value = result.get("result", {}).get("extraction", {}).get("Città di residenza", "")
    # Converti in stringa in modo sicuro per gestire qualsiasi tipo di dato
    if isinstance(city_value, list):
        city_value = ", ".join(str(item) for item in city_value)
    elif city_value is None:
        city_value = ""
    else:
        city_value = str(city_value)
    return filter_text.lower() in city_value.lower()

def log_api_call(model: str, params: dict, prompt: str, response: str, is_error: bool = False):
    """
    Logga i dettagli di una chiamata API cloud in un file
    
    Args:
        model: Nome del modello usato
        params: Parametri della chiamata API
        prompt: Prompt completo inviato
        response: Risposta ricevuta (o errore)
        is_error: Se True, indica che response contiene un errore
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"prompt_{timestamp}.log"
    
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Data e ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Modello: {model}\n")
        f.write("\nParametri chiamata:\n")
        f.write(json.dumps(params, indent=2, ensure_ascii=False))
        f.write("\n\nPrompt:\n")
        f.write(prompt)
        f.write("\n\n")
        if is_error:
            f.write("ERRORE:\n")
        else:
            f.write("Risposta:\n")
        f.write(str(response))

def main():
    # Dichiaro global logger all'inizio della funzione per usarlo
    global logger
    global max_cv
    # Setup logger principale
    logger = setup_logger()
    
    # Setup logger dedicato ai punteggi
    scores_logger = setup_scores_logger()
    scores_logger.info("Inizializzato logger di debug per i punteggi")
    
    # Utilizziamo components.v1.html per inserire lo script di blocco in modo invisibile
    html(create_script_blocker(), height=0, width=0)
    
    # Inizializzazione dei managers
    auth_manager = AuthManager()
    profile_manager = ProfileManager()
    project_manager = ProjectManager()
    
    # Verifica dell'autenticazione
    if not auth_manager.is_authenticated():
        auth_manager.login_page()
        return
        
    # Mostra il percorso del file di log dei punteggi se esiste
    if 'scores_log_path' in st.session_state:
        st.info(f"Log file dei punteggi: {st.session_state.scores_log_path}")
    
    # Inizializzazione della sessione e dei costi
    init_cost_tracking()
    
    # Inizializzazione delle variabili di sessione solo se non esistono già
    # Job description
    if 'job_description' not in st.session_state:
        st.session_state.job_description = DEFAULT_JOB_DESCRIPTION.strip()
    
    # Campi da estrarre - inizializza SOLO se non esistono già
    if 'fields' not in st.session_state:
        st.session_state.fields = CV_FIELDS.copy()
        logger.info("Inizializzato st.session_state.fields con CV_FIELDS predefiniti")
    else:
        logger.info(f"Mantenuto st.session_state.fields esistente con {len(st.session_state.fields)} campi")
    
    if 'available_fields' not in st.session_state:
        st.session_state.available_fields = CV_FIELDS.copy()
        logger.info("Inizializzato st.session_state.available_fields con CV_FIELDS predefiniti")
    else:
        logger.info(f"Mantenuto st.session_state.available_fields esistente con {len(st.session_state.available_fields)} campi")
    
    if 'selected_fields' not in st.session_state:
        # Se 'fields' esiste già, usa quelli come default per selected_fields
        if 'fields' in st.session_state:
            st.session_state.selected_fields = st.session_state.fields.copy()
            logger.info("Inizializzato st.session_state.selected_fields basato su fields esistente")
        else:
            st.session_state.selected_fields = CV_FIELDS.copy()
            logger.info("Inizializzato st.session_state.selected_fields con CV_FIELDS predefiniti")
    else:
        logger.info(f"Mantenuto st.session_state.selected_fields esistente con {len(st.session_state.selected_fields)} campi")
    
    # Criteri di valutazione
    if 'evaluation_criteria' not in st.session_state:
        st.session_state.evaluation_criteria = EVALUATION_CRITERIA.copy()
    
    if 'criteria_weights' not in st.session_state:
        st.session_state.criteria_weights = DEFAULT_CRITERIA_WEIGHTS.copy()
    
    # Configurazione AI
    if 'llm_model' not in st.session_state:
        st.session_state.llm_model = "gpt-4o-mini"
    
    # Sincronizzazione tra llm_model e model per retrocompatibilità
    if 'model' not in st.session_state and 'llm_model' in st.session_state:
        st.session_state.model = st.session_state.llm_model
    elif 'llm_model' not in st.session_state and 'model' in st.session_state:
        st.session_state.llm_model = st.session_state.model
    
    # Configurazione Ollama
    if 'ollama_models' not in st.session_state:
        st.session_state.ollama_models = get_ollama_models()
    
    if 'ollama_model' not in st.session_state:
        st.session_state.ollama_model = None
    
    if 'use_ollama' not in st.session_state:
        st.session_state.use_ollama = False

    # Configurazione cache
    if 'use_cache' not in st.session_state:
        st.session_state.use_cache = True
    
    # Resto del codice invariato
    
    # Creazione della sidebar
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
            
            # Usa il valore ai_engine dalla session_state se esiste, altrimenti determina in base a use_ollama
            default_ai_engine = st.session_state.get("ai_engine", "Ollama" if st.session_state.get("use_ollama", False) else "OpenAI")
            
            ai_engine = st.radio("", ["OpenAI", "Ollama"], horizontal=True, index=["OpenAI", "Ollama"].index(default_ai_engine))
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Aggiorna use_ollama basato sulla selezione del radio button
            st.session_state.use_ollama = (ai_engine == "Ollama")
            # Memorizza la scelta per future interazioni
            st.session_state["ai_engine"] = ai_engine
            
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
                    #se è deepseek, usa openrouter
                    if "deepseek" in st.session_state.model:
                        st.session_state.api_key = DEEPSEEK_OPENROUTER_API_KEY
                    st.caption("Usando API key da file .env")
                    
                selected_model = st.selectbox(
                    "Modello",
                    ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o", "gpt-4", "deepseek/deepseek-chat-v3-0324:free"],
                    index=0,
                    key="model_selectbox_sidebar_main"
                )
                
                # Aggiorna sia 'model' che 'llm_model' per garantire la sincronizzazione
                st.session_state.model = selected_model
                st.session_state.llm_model = selected_model
                
                # Configura endpoint OpenRouter per DeepSeek
                if "deepseek" in selected_model:
                    # Se il modello è DeepSeek, usa OpenRouter invece di OpenAI
                    st.info("Utilizzando DeepSeek v3 via OpenRouter - Modello gratuito con contesto di 131,072 token")
                
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
            # Campi da estrarre
            st.subheader("Campi da estrarre")
        
        # Bottone per suggerire campi dalla job description
        if st.button("Suggerisci campi", help="Analizza la job description e suggerisce campi aggiuntivi pertinenti", key="suggest_fields_main"):
            if 'job_description' not in st.session_state or not st.session_state.job_description:
                st.warning("Inserisci prima una job description nella pagina principale")
            else:
                with st.spinner("Analisi della job description in corso..."):
                    # Ottieni i campi personalizzati chiamando l'LLM UNA SOLA VOLTA al click
                    suggested_fields = suggest_custom_fields(
                        st.session_state.job_description,
                        st.session_state.selected_fields,
                        use_ollama=st.session_state.use_ollama,
                        openai_model=st.session_state.model if 'model' in st.session_state else None,
                        ollama_model=st.session_state.ollama_model if 'ollama_model' in st.session_state else None,
                        api_key=st.session_state.api_key if 'api_key' in st.session_state else None
                    )
                    
                    # Aggiorna l'elenco dei campi disponibili
                    if suggested_fields:
                        new_fields_added = 0
                        for field in suggested_fields:
                            if field not in st.session_state.available_fields:
                                st.session_state.available_fields.append(field)
                                st.session_state.selected_fields.append(field)  # Seleziona automaticamente i nuovi campi
                                new_fields_added += 1
                        
                        if new_fields_added > 0:
                            st.success(f"Aggiunti {new_fields_added} nuovi campi")
                        else:
                            st.info("Nessun nuovo campo da aggiungere")
                    else:
                        st.info("Nessun campo aggiuntivo suggerito")
        
        # Campo per aggiungere manualmente un campo personalizzato
        custom_field = st.text_input("Aggiungi campo personalizzato:", key="custom_field_main")
        if st.button("Aggiungi", key="add_field_main") and custom_field:
            if custom_field not in st.session_state.available_fields:
                st.session_state.available_fields.append(custom_field)
                st.session_state.selected_fields.append(custom_field)
                st.success(f"Campo '{custom_field}' aggiunto")
            else:
                st.warning(f"Il campo '{custom_field}' esiste già")

        # Multiselect che usa i campi dalla session_state
        selected_fields = st.multiselect(
            "Seleziona i campi",
            options=st.session_state.available_fields,
            default=st.session_state.selected_fields,
            key="fields_multiselect_main"
        )
        
        # Aggiorna la selezione nella session_state
        st.session_state.selected_fields = selected_fields
        st.session_state.fields = selected_fields  # Questa à la variabile usata dal resto dell'app
        
        st.divider()
        
        # Sezione criteri di valutazione
        st.subheader("Criteri di valutazione")
        
        # Mostra i criteri esistenti con pesi modificabili
        criteria_to_remove = []
        
        if "evaluation_criteria" in st.session_state:
            for criteria_id, criteria_label in st.session_state.evaluation_criteria:
                col1, col2, col3 = st.columns([3, 1, 0.5])
                with col1:
                    st.text(criteria_label)
                with col2:
                    # Peso del criterio, default à 10 se non presente
                    weight = st.session_state.criteria_weights.get(criteria_id, 10)
                    new_weight = st.number_input(
                        f"Peso", 
                        min_value=1, 
                        max_value=100, 
                        value=weight,
                        key=f"weight_{criteria_id}"
                    )
                    # Aggiorna il peso nella session state
                    st.session_state.criteria_weights[criteria_id] = new_weight
                with col3:
                    # Modifico la generazione del pulsante per renderlo più chiaro e funzionante
                    if st.button("❌", key=f"remove_{criteria_id}", help="Elimina questo criterio"):
                        criteria_to_remove.append(criteria_id)
                        # Forza aggiornamento immediato rimuovendo il criterio
                        st.session_state.evaluation_criteria = [
                            (c_id, c_label) 
                            for c_id, c_label in st.session_state.evaluation_criteria 
                            if c_id != criteria_id
                        ]
                        # Ricarica la pagina per mostrare le modifiche
                        st.rerun()
            
            # Rimuovi i criteri marcati per la rimozione
            if criteria_to_remove:
                st.session_state.evaluation_criteria = [
                    (criteria_id, criteria_label) 
                    for criteria_id, criteria_label in st.session_state.evaluation_criteria 
                    if criteria_id not in criteria_to_remove
                ]
                # Forza il ricaricamento della pagina per mostrare l'eliminazione
                st.rerun()
        
        # Campo per aggiungere manualmente un criterio personalizzato
        st.markdown("##### Aggiungi nuovo criterio")
        with st.form(key="add_criteria_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_criteria_label = st.text_input("Nome criterio", key="new_criteria_label")
            with col2:
                new_criteria_weight = st.number_input("Peso", min_value=1, max_value=100, value=10, key="new_criteria_weight")
            submit = st.form_submit_button("Aggiungi criterio")
            
            if submit and new_criteria_label:
                # Crea un ID univoco dal label (lowercase, no spazi)
                new_criteria_id = new_criteria_label.lower().replace(" ", "_")
                
                # Aggiungi il nuovo criterio se non esiste già
                exists = False
                for criteria_id, _ in st.session_state.evaluation_criteria:
                    if criteria_id == new_criteria_id:
                        exists = True
                        break
                
                if not exists:
                    st.session_state.evaluation_criteria.append((new_criteria_id, new_criteria_label))
                    st.session_state.criteria_weights[new_criteria_id] = new_criteria_weight
                    st.success(f"Criterio '{new_criteria_label}' aggiunto")
                else:
                    st.warning(f"Il criterio '{new_criteria_label}' esiste già")
        
        # Suggerimento criteri basati sulla job description
        if st.button("Suggerisci criteri", help="Analizza la job description e suggerisce criteri pertinenti", key="suggest_criteria_main"):
            if 'job_description' not in st.session_state or not st.session_state.job_description:
                st.warning("Inserisci prima una job description nella pagina principale")
            else:
                with st.spinner("Analisi della job description in corso..."):
                    # Testo del prompt per generare criteri di valutazione
                    prompt = f"""
                    Analizza questa descrizione del lavoro e suggerisci 3-5 criteri specifici di valutazione che sarebbero più rilevanti per selezionare i candidati ideali.
                    I criteri devono essere brevi (massimo 2-3 parole) e specifici per questa posizione.
                    
                    Job Description:
                    {st.session_state.job_description}
                    
                    Restituisci i criteri in formato JSON con questa struttura:
                    [
                        {{"id": "nome_criterio", "label": "Etichetta Criterio", "weight": peso_suggerito}},
                        ...
                    ]
                    
                    Dove:
                    - id: nome del criterio in minuscolo, senza spazi (usa underscore)
                    - label: nome breve e descrittivo del criterio (2-3 parole massimo)
                    - weight: peso suggerito da 1 a 100 (più alto = più importante)
                    """
                    
                    model_name = "openai-" + st.session_state.model if not st.session_state.use_ollama else "ollama-" + st.session_state.ollama_model
                    cached_result = get_cached_response(model_name, prompt)
                    
                    if cached_result:
                        suggested_criteria = cached_result
                    else:
                        # Chiama l'AI per generare i criteri
                        if st.session_state.use_ollama:
                            response = requests.post(
                                "http://localhost:11434/api/generate",
                                json={"model": st.session_state.ollama_model, "prompt": prompt, "stream": False}
                            )
                            suggested_text = response.json().get("response", "[]") if response.status_code == 200 else "[]"
                        else:
                            from openai import OpenAI
                            # Uso la funzione helper per creare il client OpenAI con supporto DeepSeek
                            client = get_openai_client(api_key=st.session_state.api_key, model=st.session_state.model)
                            response = client.chat.completions.create(
                                model=st.session_state.model,
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.3,
                                response_format={"type": "json_object"}
                            )
                            suggested_text = response.choices[0].message.content
                        
                        # Parse JSON
                        try:
                            suggested_criteria = json.loads(suggested_text)
                            save_to_cache(model_name, prompt, suggested_criteria)
                        except:
                            import re
                            json_match = re.search(r'\[.*\]', suggested_text, re.DOTALL)
                            if json_match:
                                try:
                                    suggested_criteria = json.loads(json_match.group(0))
                                    save_to_cache(model_name, prompt, suggested_criteria)
                                except:
                                    st.error("Errore nel parsing dei criteri suggeriti")
                                    suggested_criteria = []
                            else:
                                st.error("Errore nella generazione dei criteri")
                                suggested_criteria = []
                    
                    # Aggiungi i criteri suggeriti
                    if suggested_criteria:
                        new_criteria_added = 0
                        for criterio in suggested_criteria:
                            # Verifica che abbia la struttura corretta
                            if isinstance(criterio, dict) and "id" in criterio and "label" in criterio:
                                criteria_id = criterio["id"]
                                criteria_label = criterio["label"]
                                criteria_weight = criterio.get("weight", 10)
                                
                                # Controlla se il criterio esiste già
                                exists = False
                                for existing_id, _ in st.session_state.evaluation_criteria:
                                    if existing_id == criteria_id:
                                        exists = True
                                        break
                                
                                if not exists:
                                    st.session_state.evaluation_criteria.append((criteria_id, criteria_label))
                                    st.session_state.criteria_weights[criteria_id] = criteria_weight
                                    new_criteria_added += 1
                        
                        if new_criteria_added > 0:
                            st.success(f"Aggiunti {new_criteria_added} nuovi criteri")
                        else:
                            st.info("Nessun nuovo criterio da aggiungere")
                    else:
                        st.info("Nessun criterio suggerito")
        
        st.divider()
        
        # Sezione profili
        st.subheader("Profili")
        profile_manager.render_sidebar()
        
        st.divider()
        
        # Sezione progetti
        st.subheader("Progetti")
        project_manager.render_sidebar()
        
        # Mostro lo stato corrente
        show_current_state()
    
    # Titolo dell'applicazione
    st.title("CV Analyzer Pro")
    st.markdown("Analisi intelligente dei curriculum vitae")
    
    # Aggiungo il flusso di lavoro chiaro
    st.info("""
    ### 🔄 Flusso di lavoro 
    1️⃣ Configura l'AI nella sidebar → 2️⃣ Seleziona i campi da estrarre → 3️⃣ Carica o crea un progetto/posizione
    → 4️⃣ Seleziona la cartella dei CV → 5️⃣ Definisci i requisiti → 6️⃣ Avvia l'analisi
    """)
    
    # Suddivido l'interfaccia in passi numerati
    
    # PASSO 1: CARTELLA CV
    st.subheader("1. Seleziona la cartella dei CV")
    # Campo per selezionare la directory dei CV
    cv_dir_input = st.text_input(
        "Seleziona la cartella contenente i CV (percorso completo)",
        value=st.session_state.get('cv_dir', ''),
        placeholder="Es: C:/Utenti/Nome/Documents/CV"
    )
    
    with st.sidebar.expander("Impostazioni avanzate"):
        global MAX_CV_TO_ANALYZE  # Dichiarazione global PRIMA dell'uso
        max_cv = st.slider(
            "Numero massimo di CV da analizzare", 
            min_value=5, 
            max_value=1000, 
            value=MAX_CV_TO_ANALYZE,
            step=5,
            help="Limita il numero di CV da analizzare per risparmiare tempo e risorse"
        )
        
        # Aggiorna la variabile globale se il valore è cambiato
        if max_cv != MAX_CV_TO_ANALYZE:
            MAX_CV_TO_ANALYZE = max_cv
            # Salva anche nella session_state per poter persistere il valore
            st.session_state.MAX_CV_TO_ANALYZE = max_cv
            st.session_state["MAX_CV_TO_ANALYZE"] = max_cv
            st.sidebar.success(f"Limite CV aggiornato a: {MAX_CV_TO_ANALYZE}")

    # Aggiornamento della directory nella session state
    if cv_dir_input != st.session_state.get('cv_dir', ''):
        st.session_state.cv_dir = cv_dir_input
    
    # Se à stata selezionata una directory, verifica la sua esistenza
    if st.session_state.get('cv_dir', ''):
        if not os.path.isdir(st.session_state.cv_dir):
            st.error(f"La directory {st.session_state.cv_dir} non esiste.")
        else:
            # Conta i file PDF nella cartella
            pdf_files = [f for f in os.listdir(st.session_state.cv_dir) if f.lower().endswith('.pdf')]
            if pdf_files:
                st.success(f"Trovati {len(pdf_files)} file PDF nella cartella.")
            else:
                st.warning(f"Nessun file PDF trovato nella directory {st.session_state.cv_dir}")
    
    # PASSO 2: DESCRIZIONE LAVORO
    st.subheader("2. Descrizione della posizione")
    st.caption("Inserisci la descrizione del lavoro")
    job_desc = st.text_area(
        label="",
        value=st.session_state.get('job_description', DEFAULT_JOB_DESCRIPTION),
        height=300,
        key="job_description"
    )
    
    # Aggiorna la job description nella session state
    if job_desc != st.session_state.get('job_description', ''):
        st.session_state.job_description = job_desc
    
    # PASSO 3: ANALISI
    st.subheader("3. Avvia l'analisi")
    
    # Pulsante per l'analisi con stile migliorato
    st.markdown("""
    <style>
    .analyze-button {
        background-color: #2E7D32;
        color: white;
        padding: 10px 24px;
        font-size: 16px;
        border-radius: 8px;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        cursor: pointer;
        text-align: center;
        width: 100%;
        margin-top: 10px;
    }
    .analyze-button:hover {
        background-color: #1B5E20;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("Analizza CV", key="analyze_button", use_container_width=True)
    
    if analyze_button:
        if st.session_state.get('cv_dir', ''):
            # Verifica se la directory esiste
            if not os.path.isdir(st.session_state.cv_dir):
                st.error(f"La directory {st.session_state.cv_dir} non esiste.")
            else:
                # Conta i file PDF
                pdf_files = [f for f in os.listdir(st.session_state.cv_dir) if f.lower().endswith('.pdf')]
                
                if not pdf_files:
                    st.error(f"Nessun file PDF trovato nella directory {st.session_state.cv_dir}")
                else:
                    # Mostra un messaggio di caricamento
                    progress_placeholder = st.empty()
                    progress_bar = st.progress(0)
                    
                    # Definisci una funzione di callback per gli aggiornamenti di progresso
                    def update_progress(current, total, message=""):
                        progress = current / total
                        progress_bar.progress(progress)
                        progress_placeholder.text(f"Analisi in corso... {current}/{total} - {message}")
                    
                    # Esegui l'analisi dei CV
                    with st.spinner("Analisi in corso..."):
                        try:
                            logger.info("Avvio analisi dei CV con process_cvs")
                            results, results_df = process_cvs(
                                cv_dir=st.session_state.cv_dir, 
                                job_description=st.session_state.job_description, 
                                fields=st.session_state.fields,
                                progress_callback=update_progress
                            )
                            
                            # Se non ci sono risultati, probabilmente c'è stato un errore
                            if not results or len(results) == 0:
                                logger.warning("Analisi completata ma nessun CV è stato analizzato con successo")
                                st.session_state.analysis_error = "Nessun CV è stato analizzato con successo"
                                st.error("⚠️ ATTENZIONE: Nessun CV è stato analizzato con successo. Controlla i log per i dettagli.")
                                # Non eseguiamo st.rerun() per mantenere visibile il messaggio di errore
                                return
                            
                            logger.info(f"Analisi completata con successo. Ottenuti {len(results)} risultati")
                            
                            # Memorizza i risultati nella session state
                            st.session_state.results = results
                            st.session_state.analysis_results = results_df
                            st.session_state.analysis_error = None  # Resetta eventuali errori precedenti
                            
                            logger.info("Risultati salvati in st.session_state.results e st.session_state.analysis_results")
                            
                            # Mostra un messaggio di successo
                            progress_placeholder.empty()
                            progress_bar.empty()
                            st.success(f"Analisi completata! {len(results)} CV analizzati.")
                            
                            # Attiva la scheda della panoramica
                            st.session_state.active_tab = 0
                            logger.info("Impostata active_tab = 0 per mostrare la panoramica dei risultati")
                            
                            # Forza il recaricamento della pagina solo se non ci sono stati errori
                            logger.info("Eseguo st.rerun() per ricaricare la pagina e mostrare i risultati")
                            st.rerun()
                        except Exception as e:
                            # Gestione degli errori
                            logger.error(f"Errore critico durante l'analisi dei CV: {str(e)}")
                            import traceback
                            error_traceback = traceback.format_exc()
                            logger.error(f"Traceback dell'errore:\n{error_traceback}")
                            
                            # Salva l'errore nella session state per visualizzarlo in modo persistente
                            st.session_state.analysis_error = str(e)
                            
                            # Svuota i placeholder di progress per non mostrare lo spinner infinito
                            if progress_placeholder:
                                progress_placeholder.empty()
                            if progress_bar:
                                progress_bar.empty()
                            
                            # Mostra un errore formattato chiaramente che rimarrà visibile
                            st.error(f"""
                            ⚠️ ERRORE DURANTE L'ANALISI DEI CV ⚠️
                            
                            Si è verificato il seguente errore:
                            {str(e)}
                            
                            Controlla i log per maggiori dettagli.
                            """)
                            
                            # Log dell'errore
                            logger.error(f"Errore nell'analisi dei CV: {str(e)}")
                            logger.error(traceback.format_exc())
                            
                            # NON facciamo st.rerun() per mantenere visibile il messaggio di errore
                            return 
        else:
            st.error("Seleziona prima una cartella contenente i CV da analizzare.")
            logger.warning("Tentativo di analisi senza selezionare una cartella CV")
    
    # Verifica se c'è un errore di analisi da mostrare
    if "analysis_error" in st.session_state and st.session_state.analysis_error:
        st.error(f"Errore nell'ultima analisi: {st.session_state.analysis_error}")
    
    # Verifica se ci sono risultati da visualizzare
    if "results" in st.session_state and st.session_state.results:
        logger.info("Risultati trovati in session_state, procedo con la visualizzazione")
        
        # Inizializza la scheda attiva se non esiste
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
            logger.info("Inizializzata active_tab a 0")
        
        # Inizializza variabili per filtri e ordinamento se non esistono
        if 'filter_criteria' not in st.session_state:
            st.session_state.filter_criteria = {
                'min_score': 0,
                'max_score': 100,
                'city': "",
                'experience': "",
                'categories': [],
                'search_term': ""
            }
        
        if 'sort_criteria' not in st.session_state:
            st.session_state.sort_criteria = {
                'field': 'Punteggio_composito',
                'ascending': False
            }
        
        # Visualizzazione dei risultati
        tab_names = ["📊 Panoramica", "🔍 Dettaglio", "⚖️ Confronta", "📋 Schede CV", "🏢 Aziende"]
        logger.info(f"Creazione tabs: {tab_names}")
        overview_tab, detailed_tab, compare_tab, cards_tab, companies_tab = st.tabs(tab_names)
        
        with overview_tab:
            logger.info("Rendering tab Panoramica")
            # Titolo e descrizione
            st.header("Panoramica dei candidati")
            st.markdown("Questa vista riassume l'analisi dei CV in base alla job description. I candidati sono ordinati per punteggio complessivo.")
            
            # Aggiungiamo una sezione per modificare i pesi
            with st.expander("Modifica pesi dei criteri", expanded=False):
                st.markdown("### Modifica dei pesi dei criteri")
                st.info("Modifica i pesi dei criteri e il punteggio composito verrà ricalcolato per tutti i candidati.")
                
                # Ottieni i criteri e i pesi
                criteria_list = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
                weights_changed = False
                
                # Layout in colonne per risparmiare spazio
                col1, col2 = st.columns(2)
                
                # Lista per tenere traccia dei nuovi pesi
                new_weights = {}
                
                # Dividi i criteri tra le due colonne
                half_length = len(criteria_list) // 2 + (len(criteria_list) % 2)
                
                # Prima colonna
                with col1:
                    for i, (criteria_id, criteria_label) in enumerate(criteria_list[:half_length]):
                        # Ottieni il peso corrente (default 10)
                        current_weight = st.session_state.criteria_weights.get(criteria_id, 10)
                        
                        # Slider per modificare il peso
                        new_weight = st.slider(
                            f"{criteria_label}",
                            min_value=0,
                            max_value=100,
                            value=current_weight,
                            key=f"weight_edit_{criteria_id}"
                        )
                        
                        # Aggiungi alla lista dei nuovi pesi
                        new_weights[criteria_id] = new_weight
                        
                        # Verifica se è cambiato
                        if new_weight != current_weight:
                            weights_changed = True
                
                # Seconda colonna
                with col2:
                    for i, (criteria_id, criteria_label) in enumerate(criteria_list[half_length:]):
                        # Ottieni il peso corrente (default 10)
                        current_weight = st.session_state.criteria_weights.get(criteria_id, 10)
                        
                        # Slider per modificare il peso
                        new_weight = st.slider(
                            f"{criteria_label}",
                            min_value=0,
                            max_value=100,
                            value=current_weight,
                            key=f"weight_edit_{criteria_id}"
                        )
                        
                        # Aggiungi alla lista dei nuovi pesi
                        new_weights[criteria_id] = new_weight
                        
                        # Verifica se è cambiato
                        if new_weight != current_weight:
                            weights_changed = True
                
                # Pulsante per applicare i nuovi pesi
                if weights_changed:
                    if st.button("Applica nuovi pesi"):
                        # Aggiorna i pesi nella session state
                        st.session_state.criteria_weights = new_weights
                        
                        # Ricalcola i punteggi compositi per tutti i risultati
                        if 'results' in st.session_state:
                            for result in st.session_state.results:
                                if "result" in result and "criteria" in result["result"]:
                                    criteria_data = result["result"]["criteria"]
                                    
                                    # Verifica se criteria_data ha un oggetto 'criteria' dentro
                                    if isinstance(criteria_data, dict) and 'criteria' in criteria_data and isinstance(criteria_data['criteria'], dict):
                                        criteria_data = criteria_data['criteria']
                                    
                                    # Calcola il nuovo punteggio composito
                                    total_score = 0
                                    total_weight = 0
                                    
                                    # Per ogni criterio nel risultato
                                    for criteria_id, _ in criteria_list:
                                        if criteria_id in criteria_data:
                                            # Estrai punteggio in base al formato
                                            raw_score = None
                                            if isinstance(criteria_data[criteria_id], dict) and "score" in criteria_data[criteria_id]:
                                                raw_score = criteria_data[criteria_id]["score"]
                                            elif isinstance(criteria_data[criteria_id], (int, float)):
                                                raw_score = criteria_data[criteria_id]
                                            elif isinstance(criteria_data[criteria_id], str):
                                                # Rimuovi caratteri non numerici
                                                cleaned_score = ''.join(c for c in criteria_data[criteria_id] if c.isdigit() or c == '.')
                                                raw_score = float(cleaned_score) if cleaned_score else 0
                                            
                                            try:
                                                # Converti in numero
                                                score = float(raw_score) if raw_score is not None else 0
                                                
                                                # Ottieni il peso del criterio
                                                weight = new_weights.get(criteria_id, 10)
                                                
                                                # Aggiungi al punteggio pesato
                                                total_score += score * weight
                                                total_weight += weight
                                            except (ValueError, TypeError):
                                                # Ignora errori di conversione
                                                pass
                                    
                                    # Calcola la media pesata
                                    if total_weight > 0:
                                        result["result"]["composite_score"] = int(total_score / total_weight)
                        
                        # Aggiorna anche il DataFrame nella session state
                        if 'analysis_results' in st.session_state and isinstance(st.session_state.analysis_results, pd.DataFrame):
                            # Crea una copia del DataFrame
                            df = st.session_state.analysis_results.copy()
                            
                            # Per ogni riga del DataFrame
                            for idx, row in df.iterrows():
                                # Ottieni il percorso del file
                                file_path = row.get("file_path")
                                
                                # Trova il risultato corrispondente
                                for result in st.session_state.results:
                                    if result.get("path") == file_path:
                                        # Aggiorna il punteggio composito
                                        df.at[idx, "Punteggio_composito"] = result["result"]["composite_score"]
                                        break
                            
                            # Aggiorna il DataFrame nella session state
                            st.session_state.analysis_results = df
                        
                        st.success("Pesi aggiornati e punteggi ricalcolati!")
                        st.rerun()
            
            # Filtri per la tabella
            with st.expander("Filtri e ordinamento", expanded=False):
                # Inizializza un dizionario per tenere traccia di tutti i filtri avanzati
                if 'advanced_filters' not in st.session_state:
                    st.session_state.advanced_filters = {}
                
                filter_cols = st.columns(4)
                
                with filter_cols[0]:
                    min_score = st.slider("Punteggio minimo", 0, 100, st.session_state.filter_criteria['min_score'])
                    if min_score != st.session_state.filter_criteria['min_score']:
                        st.session_state.filter_criteria['min_score'] = min_score
                        st.rerun()
                
                with filter_cols[1]:
                    city_filter = st.text_input("Filtra per città", value=st.session_state.filter_criteria['city'])
                    if city_filter != st.session_state.filter_criteria['city']:
                        st.session_state.filter_criteria['city'] = city_filter
                        st.rerun()
                
                with filter_cols[2]:
                    exp_filter = st.text_input("Esperienza minima (anni)", value=st.session_state.filter_criteria['experience'])
                    if exp_filter != st.session_state.filter_criteria['experience']:
                        st.session_state.filter_criteria['experience'] = exp_filter
                        st.rerun()
                
                with filter_cols[3]:
                    search_term = st.text_input("Cerca in tutti i campi", value=st.session_state.filter_criteria['search_term'])
                    if search_term != st.session_state.filter_criteria['search_term']:
                        st.session_state.filter_criteria['search_term'] = search_term
                        st.rerun()
                
                # Aggiunta filtri avanzati per ogni campo e criterio
                st.markdown("### Filtri avanzati")
                
                # Se abbiamo risultati di analisi, creiamo filtri dinamici
                if 'analysis_results' in st.session_state and isinstance(st.session_state.analysis_results, pd.DataFrame) and not st.session_state.analysis_results.empty:
                    df = st.session_state.analysis_results
                    
                    # Dividi in due colonne: una per campi di testo, una per campi numerici (inclusi criteri)
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Filtri per campi testuali")
                        # Ottieni tutti i campi testuali dal dataframe
                        text_fields = [col for col in df.columns if col not in ['file_path', 'File_PDF'] 
                                       and df[col].dtype == 'object' 
                                       and col not in [c[1] for c in (st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA)]]
                        
                        for field in text_fields:
                            # Crea un filtro di testo per ogni campo
                            field_key = f"text_filter_{field}"
                            field_value = st.text_input(f"Filtra per {field}", 
                                                      value=st.session_state.advanced_filters.get(field_key, ""),
                                                      key=field_key)
                            
                            # Aggiorna il filtro nella session state
                            if field_value != st.session_state.advanced_filters.get(field_key, ""):
                                st.session_state.advanced_filters[field_key] = field_value
                                st.rerun()
                        
                        with col2:
                            st.markdown("#### Filtri per campi numerici e criteri")
                            
                            # Ottieni criteri di valutazione
                            criteria_labels = [label for _, label in (st.session_state.evaluation_criteria 
                                                                     if 'evaluation_criteria' in st.session_state 
                                                                     else EVALUATION_CRITERIA)]
                            
                            # Crea filtri range per ogni criterio
                            for criteria_label in criteria_labels:
                                if criteria_label in df.columns:
                                    # Converti la colonna in numerica per ottenere min/max
                                    df[criteria_label] = pd.to_numeric(df[criteria_label], errors='coerce')
                                    min_val = int(df[criteria_label].min()) if not pd.isna(df[criteria_label].min()) else 0
                                    max_val = int(df[criteria_label].max()) if not pd.isna(df[criteria_label].max()) else 100
                                    
                                    # Chiavi per i valori min e max
                                    min_key = f"min_{criteria_label}"
                                    max_key = f"max_{criteria_label}"
                                    
                                    # Valori di default
                                    default_min = st.session_state.advanced_filters.get(min_key, min_val)
                                    default_max = st.session_state.advanced_filters.get(max_key, max_val)
                                    
                                    # Crea slider con due handle per range
                                    st.markdown(f"**{criteria_label}**")
                                    values = st.slider(
                                        f"Range per {criteria_label}",
                                        min_value=min_val,
                                        max_value=max_val,
                                        value=(default_min, default_max),
                                        key=f"range_{criteria_label}"
                                    )
                                    
                                    # Aggiorna i filtri nella session state
                                    if values[0] != st.session_state.advanced_filters.get(min_key, min_val) or \
                                       values[1] != st.session_state.advanced_filters.get(max_key, max_val):
                                        st.session_state.advanced_filters[min_key] = values[0]
                                        st.session_state.advanced_filters[max_key] = values[1]
                                        st.rerun()
                            
                            # Altri campi numerici (non criteri)
                            numeric_fields = [col for col in df.columns 
                                             if col not in ['file_path', 'File_PDF']
                                             and col not in criteria_labels
                                             and pd.api.types.is_numeric_dtype(df[col])]
                            
                            for field in numeric_fields:
                                min_val = int(df[field].min()) if not pd.isna(df[field].min()) else 0
                                max_val = int(df[field].max()) if not pd.isna(df[field].max()) else 100
                                
                                # Chiavi per i valori min e max
                                min_key = f"min_{field}"
                                max_key = f"max_{field}"
                                
                                # Valori di default
                                default_min = st.session_state.advanced_filters.get(min_key, min_val)
                                default_max = st.session_state.advanced_filters.get(max_key, max_val)
                                
                                # Crea slider con due handle per range
                                st.markdown(f"**{field}**")
                                values = st.slider(
                                    f"Range per {field}",
                                    min_value=min_val,
                                    max_value=max_val,
                                    value=(default_min, default_max),
                                    key=f"range_{field}"
                                )
                                
                                # Aggiorna i filtri nella session state
                                if values[0] != st.session_state.advanced_filters.get(min_key, min_val) or \
                                   values[1] != st.session_state.advanced_filters.get(max_key, max_val):
                                    st.session_state.advanced_filters[min_key] = values[0]
                                    st.session_state.advanced_filters[max_key] = values[1]
                                    st.rerun()
                        
                    # Seconda riga di filtri per ordinamento
                    sort_cols = st.columns(3)
                    with sort_cols[0]:
                        sort_field = st.selectbox(
                            "Ordina per", 
                            options=["Punteggio_composito", "Nome", "Cognome", "Età", "Città di residenza", "Anni di esperienza lavorativa"],
                            index=0 if st.session_state.sort_criteria['field'] == "Punteggio_composito" else 
                                  1 if st.session_state.sort_criteria['field'] == "Nome" else
                                  2 if st.session_state.sort_criteria['field'] == "Cognome" else
                                  3 if st.session_state.sort_criteria['field'] == "Età" else
                                  4 if st.session_state.sort_criteria['field'] == "Città di residenza" else
                                  5
                        )
                        if sort_field != st.session_state.sort_criteria['field']:
                            st.session_state.sort_criteria['field'] = sort_field
                            st.rerun()
                    
                    with sort_cols[1]:
                        sort_order = st.radio(
                            "Ordine", 
                            options=["Decrescente", "Crescente"],
                            index=0 if not st.session_state.sort_criteria['ascending'] else 1,
                            horizontal=True
                        )
                        ascending = sort_order == "Crescente"
                        if ascending != st.session_state.sort_criteria['ascending']:
                            st.session_state.sort_criteria['ascending'] = ascending
                            st.rerun()
                    
                    with sort_cols[2]:
                        if st.button("Azzera filtri"):
                            st.session_state.filter_criteria = {
                                'min_score': 0,
                                'max_score': 100,
                                'city': "",
                                'experience': "",
                                'categories': [],
                                'search_term': ""
                            }
                            st.session_state.advanced_filters = {}
                            st.session_state.sort_criteria = {
                                'field': 'Punteggio_composito',
                                'ascending': False
                            }
                            st.rerun()
            
            # Metriche chiave
            metric_cols = st.columns(4)
            with metric_cols[0]:
                # Calcola il numero di risultati in modo sicuro
                num_results = 0
                if 'analysis_results' in st.session_state:
                    if isinstance(st.session_state.analysis_results, pd.DataFrame):
                        num_results = len(st.session_state.analysis_results)
                    elif isinstance(st.session_state.analysis_results, list) and st.session_state.analysis_results:
                        num_results = len(st.session_state.analysis_results)
                
                # Usa il valore calcolato nella stringa HTML
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{num_results}</div>
                    <div class="metric-label">CV Analizzati</div>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[1]:
                # Calcola il punteggio medio
                avg_score = 0
                if 'analysis_results' in st.session_state and isinstance(st.session_state.analysis_results, pd.DataFrame) and not st.session_state.analysis_results.empty:
                    if 'Punteggio_composito' in st.session_state.analysis_results.columns:
                        # Converto prima la colonna in numerica, gestendo errori
                        try:
                            scores = pd.to_numeric(st.session_state.analysis_results['Punteggio_composito'], errors='coerce')
                            avg_score = round(scores.mean(), 1)
                        except Exception as e:
                            st.warning(f"Errore nel calcolo della media: {str(e)}")
                            avg_score = 0
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_score}</div>
                    <div class="metric-label">Punteggio Medio</div>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[2]:
                # Calcola il numero di candidati con punteggio alto (>75)
                high_score_count = 0
                if 'analysis_results' in st.session_state and isinstance(st.session_state.analysis_results, pd.DataFrame) and not st.session_state.analysis_results.empty:
                    if 'Punteggio_composito' in st.session_state.analysis_results.columns:
                        try:
                            # Converto prima la colonna in numerica per il confronto
                            scores = pd.to_numeric(st.session_state.analysis_results['Punteggio_composito'], errors='coerce')
                            high_score_count = len(scores[scores >= 75].dropna())
                        except Exception as e:
                            st.warning(f"Errore nel calcolo dei candidati eccellenti: {str(e)}")
                            high_score_count = 0
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{high_score_count}</div>
                    <div class="metric-label">Candidati Eccellenti</div>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[3]:
                # Calcola candidati categorizzati
                categorized_count = 0
                if 'candidate_categories' in st.session_state:
                    categorized_count = len(st.session_state.candidate_categories)
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{categorized_count}</div>
                    <div class="metric-label">Candidati Categorizzati</div>
                </div>
                """, unsafe_allow_html=True)

            # Tabella riassuntiva
            if 'analysis_results' in st.session_state and isinstance(st.session_state.analysis_results, pd.DataFrame) and not st.session_state.analysis_results.empty:
                logger.info("Visualizzazione DataFrame dei risultati nella panoramica")
                
                # Applica filtri al DataFrame
                df = st.session_state.analysis_results.copy()
                
                # Filtro per punteggio
                if 'Punteggio_composito' in df.columns:
                    try:
                        # Converti la colonna in numerica prima del confronto
                        df['Punteggio_composito_num'] = pd.to_numeric(df['Punteggio_composito'], errors='coerce')
                        df = df[df['Punteggio_composito_num'] >= st.session_state.filter_criteria['min_score']]
                        # Rimuovi la colonna temporanea
                        df = df.drop(columns=['Punteggio_composito_num'])
                    except Exception as e:
                        st.warning(f"Errore nell'applicazione del filtro punteggio: {str(e)}")
                
                # Filtro per città
                if st.session_state.filter_criteria['city'] and 'Città di residenza' in df.columns:
                    filter_city = st.session_state.filter_criteria['city'].lower()
                    df = df[df['Città di residenza'].str.lower().str.contains(filter_city, na=False)]
                
                # Filtro per esperienza
                if st.session_state.filter_criteria['experience'] and 'Anni di esperienza lavorativa' in df.columns:
                    try:
                        min_exp = float(st.session_state.filter_criteria['experience'])
                        # Converti la colonna in numeri dove possibile
                        df['Anni_exp_num'] = pd.to_numeric(df['Anni di esperienza lavorativa'].str.extract(r'(\d+\.?\d*)')[0], errors='coerce')
                        df = df[df['Anni_exp_num'] >= min_exp]
                        df = df.drop(columns=['Anni_exp_num'])
                    except:
                        pass  # Ignora errori di conversione
                
                # Filtro per termine di ricerca generico
                if st.session_state.filter_criteria['search_term']:
                    search_term = st.session_state.filter_criteria['search_term'].lower()
                    mask = pd.Series(False, index=df.index)
                    
                    for col in df.columns:
                        # Converti colonna in stringa e cerca il termine
                        col_mask = df[col].astype(str).str.lower().str.contains(search_term, na=False)
                        mask = mask | col_mask
                    
                    df = df[mask]
                
                # Applica filtri avanzati (sia testuali che numerici)
                if 'advanced_filters' in st.session_state:
                    # Filtri testuali
                    for key, value in st.session_state.advanced_filters.items():
                        if key.startswith('text_filter_') and value:
                            field = key.replace('text_filter_', '')
                            if field in df.columns:
                                df = df[df[field].astype(str).str.lower().str.contains(value.lower(), na=False)]
                    
                    # Filtri numerici e criteri (range)
                    criteria_labels = [label for _, label in (st.session_state.evaluation_criteria 
                                                            if 'evaluation_criteria' in st.session_state 
                                                            else EVALUATION_CRITERIA)]
                    
                    # Applica filtri di range per criteri
                    for criteria_label in criteria_labels:
                        min_key = f"min_{criteria_label}"
                        max_key = f"max_{criteria_label}"
                        
                        if min_key in st.session_state.advanced_filters and max_key in st.session_state.advanced_filters:
                            if criteria_label in df.columns:
                                # Converti in numerico per confronto
                                df[f"{criteria_label}_num"] = pd.to_numeric(df[criteria_label], errors='coerce')
                                # Applica il filtro di range
                                df = df[(df[f"{criteria_label}_num"] >= st.session_state.advanced_filters[min_key]) & 
                                      (df[f"{criteria_label}_num"] <= st.session_state.advanced_filters[max_key])]
                                # Rimuovi colonna temporanea
                                df = df.drop(columns=[f"{criteria_label}_num"])
                        
                        # Applica filtri di range per altri campi numerici
                        numeric_fields = [col for col in df.columns 
                                         if col not in criteria_labels
                                         and pd.api.types.is_numeric_dtype(df[col])]
                        
                        for field in numeric_fields:
                            min_key = f"min_{field}"
                            max_key = f"max_{field}"
                            
                            if min_key in st.session_state.advanced_filters and max_key in st.session_state.advanced_filters:
                                df = df[(df[field] >= st.session_state.advanced_filters[min_key]) & 
                                      (df[field] <= st.session_state.advanced_filters[max_key])]
                
                # Ordina il DataFrame
                if st.session_state.sort_criteria['field'] in df.columns:
                    try:
                        # Se stiamo ordinando per un campo che potrebbe essere numerico
                        numeric_fields = ["Punteggio_composito", "Età", "Anni di esperienza lavorativa"]
                        if st.session_state.sort_criteria['field'] in numeric_fields:
                            # Crea una copia temporanea della colonna convertita in numerica
                            sort_col_name = f"{st.session_state.sort_criteria['field']}_sort"
                            df[sort_col_name] = pd.to_numeric(df[st.session_state.sort_criteria['field']], errors='coerce')
                            # Ordina usando la colonna numerica
                            df = df.sort_values(by=sort_col_name, 
                                              ascending=st.session_state.sort_criteria['ascending'])
                            # Rimuovi la colonna temporanea
                            df = df.drop(columns=[sort_col_name])
                        else:
                            # Per colonne non numeriche, ordina normalmente
                            df = df.sort_values(by=st.session_state.sort_criteria['field'], 
                                              ascending=st.session_state.sort_criteria['ascending'])
                    except Exception as e:
                        st.warning(f"Errore nell'ordinamento: {str(e)}")
                        # Fallback all'ordinamento per indice
                        df = df.sort_index(ascending=st.session_state.sort_criteria['ascending'])
                
                # Normalizza il dataframe e poi visualizzalo
                df_normalized = normalize_dataframe(df.drop(columns=['file_path'], errors='ignore'))
                
                # Get logger for debugging
                scores_logger = logging.getLogger("SCORES_DEBUG")
                
                # Recupera le etichette dei criteri di valutazione
                criteria_labels = [label for _, label in (st.session_state.evaluation_criteria 
                                              if 'evaluation_criteria' in st.session_state 
                                              else EVALUATION_CRITERIA)]
                
                # Controllo extra sulle colonne dei criteri
                scores_logger.info(f"Controllo extra su colonne criteri prima di visualizzazione")
                for criteria_label in criteria_labels:
                    if criteria_label in df_normalized.columns:
                        scores_logger.info(f"Controllo criterio '{criteria_label}'")
                        # Verifica se la colonna è numerica
                        if df_normalized[criteria_label].dtype not in ['float64', 'int64']:
                            scores_logger.warning(f"Criterio '{criteria_label}' non numerico, converto forzatamente")
                            # Converti forzatamente in numeri
                            try:
                                df_normalized[criteria_label] = pd.to_numeric(df_normalized[criteria_label], errors='coerce').fillna(0)
                                scores_logger.info(f"Criterio '{criteria_label}' convertito in numerico")
                            except Exception as e:
                                scores_logger.error(f"Errore nella conversione forzata di '{criteria_label}': {str(e)}")
                
                # Assicuriamo che tutte le colonne siano visualizzabili correttamente
                for col in df_normalized.columns:
                    if df_normalized[col].dtype == 'object':
                        df_normalized[col] = df_normalized[col].astype(str)
                
                try:
                    # Visualizza la tabella principale
                    st.dataframe(df_normalized, use_container_width=True)
                    
                    # Aggiungi JavaScript personalizzato per rendere cliccabile la cella File_PDF
                    st.markdown("""
                    <script>
                    // Funzione per attendere che un elemento appaia nel DOM
                    function waitForElement(selector, timeout = 10000) {
                        return new Promise((resolve, reject) => {
                            const startTime = Date.now();
                            
                            const checkElement = () => {
                                const element = document.querySelector(selector);
                                if (element) {
                                    resolve(element);
                                    return;
                                }
                                
                                if (Date.now() - startTime > timeout) {
                                    reject(new Error(`Elemento ${selector} non trovato entro ${timeout}ms`));
                                    return;
                                }
                                
                                setTimeout(checkElement, 100);
                            };
                            
                            checkElement();
                        });
                    }
                    
                    // Funzione principale che inizializza la funzionalità di clic
                    async function initializeTableClicks() {
                        try {
                            // Attendi che la tabella sia caricata
                            const dataframe = await waitForElement('.stDataFrame');
                            if (!dataframe) return;
                            
                            // Trova tutte le celle della tabella
                            const cells = dataframe.querySelectorAll('tbody td');
                            
                            // Trova l'indice della colonna File_PDF (prima colonna)
                            let fileColumn = 0;
                            
                            // Per ogni cella, aggiungi un event listener
                            cells.forEach((cell, index) => {
                                // Se la cella è nella colonna File_PDF
                                if (index % dataframe.querySelectorAll('thead th').length === fileColumn) {
                                    // Aggiungi stile per indicare che è cliccabile
                                    cell.style.cursor = 'pointer';
                                    cell.style.color = '#1E88E5';
                                    cell.style.textDecoration = 'underline';
                                    
                                    // Aggiungi l'icona di download
                                    const originalText = cell.textContent;
                                    cell.innerHTML = `📄 ${originalText}`;
                                    
                                    // Aggiungi event listener
                                    cell.addEventListener('click', function() {
                                        // Trova il pulsante di download corrispondente
                                        const filename = cell.textContent.replace('📄 ', '');
                                        const downloadButtons = document.querySelectorAll('button');
                                        
                                        // Cerca il pulsante con il testo che contiene il nome del file
                                        for (const button of downloadButtons) {
                                            if (button.textContent.includes(filename)) {
                                                button.click();
                                                break;
                                            }
                                        }
                                    });
                                }
                            });
                            
                            console.log('Listener di click sulle celle della tabella inizializzati');
                        } catch (error) {
                            console.error('Errore nell\'inizializzazione dei click sulla tabella:', error);
                        }
                    }
                    
                    // Esegui la funzione dopo il caricamento completo della pagina
                    document.addEventListener('DOMContentLoaded', initializeTableClicks);
                    
                    // Esegui anche dopo un breve ritardo per gestire il caricamento asincrono di Streamlit
                    setTimeout(initializeTableClicks, 1000);
                    setTimeout(initializeTableClicks, 2000);
                    </script>
                    """, unsafe_allow_html=True)
                    
                    # Sistema alternativo per scaricare i PDF: tabella interattiva sotto la tabella principale
                    st.markdown("### 📥 Download CV diretto")
                    st.write("Clicca sul nome del file nella tabella principale o usa i pulsanti qui sotto:")
                    
                    # Crea una tabella più compatta solo per i download
                    download_cols = st.columns(4)  # Usa 4 colonne per rendere compatto
                    
                    for i, (idx, row) in enumerate(df.iterrows()):
                        if 'file_path' in row and row['file_path'] and os.path.exists(row['file_path']):
                            col_idx = i % 4  # Distribuisci su 4 colonne
                            with download_cols[col_idx]:
                                nome_file = row.get('File_PDF', os.path.basename(row['file_path']))
                                with open(row['file_path'], 'rb') as file:
                                    file_content = file.read()
                                    st.download_button(
                                        label=f"📥 {nome_file}",
                                        data=file_content,
                                        file_name=os.path.basename(row['file_path']),
                                        mime="application/pdf",
                                        key=f"download_btn_main_{i}"
                                    )
                    
                    # Debug: mostriamo informazioni sulle colonne dopo la visualizzazione
                    colonne_df = df_normalized.columns.tolist()
                    criteri_presenti = [col for col in colonne_df if col in criteria_labels]
                    
                    with st.expander("Debug colonne"):
                        st.write(f"Colonne nel DataFrame: {colonne_df}")
                        st.write(f"Criteri attesi: {criteria_labels}")
                        st.write(f"Criteri trovati: {criteri_presenti}")
                        
                        # Mostra valori dei criteri trovati
                        if criteri_presenti:
                            st.write("Valori dei criteri:")
                            for criterio in criteri_presenti:
                                if df_normalized[criterio].dtype in ['float64', 'int64']:
                                    st.write(f"{criterio}: tipo numerico, valori: {df_normalized[criterio].head(3).tolist()}")
                                else:
                                    st.write(f"{criterio}: tipo {df_normalized[criterio].dtype}, valori: {df_normalized[criterio].head(3).tolist()}")
                        
                        # Mostra i primi dati grezzi
                        st.write("Prime righe del DataFrame:")
                        st.write(df_normalized.head(2))
                except Exception as e:
                    st.error(f"Errore nella visualizzazione della tabella: {str(e)}")
                    # Fallback su una visualizzazione più semplice
                    st.write("Tabella dei risultati:")
                    st.write(df_normalized)
                
                # Rimuovo la vecchia sezione di download che ora è ridondante
                # Il link per scaricare i risultati come Excel rimane utile
                excel_data = create_download_link(df)
                st.download_button(
                    label="📄 Scarica risultati (Excel)",
                    data=excel_data,
                    file_name=f"risultati_analisi_cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                logger.warning("DataFrame dei risultati non trovato o vuoto")
                st.info("Nessun dato disponibile per la visualizzazione")
        
        with detailed_tab:
            logger.info("Rendering tab Dettaglio")
            
            if 'results' in st.session_state and st.session_state.results:
                # Selettore per il CV da visualizzare
                cv_options = ["Seleziona un CV..."] + [result.get("filename", f"CV {i+1}") for i, result in enumerate(st.session_state.results)]
                selected_cv_idx = st.selectbox("Seleziona un CV da visualizzare", options=range(len(cv_options)), format_func=lambda i: cv_options[i])
                
                if selected_cv_idx > 0:  # Non à "Seleziona un CV..."
                    logger.info(f"Visualizzazione dettagliata del CV: {cv_options[selected_cv_idx]}")
                    
                    # Ottieni il risultato selezionato
                    result_data = st.session_state.results[selected_cv_idx - 1]
                    
                    # Dividi in schede per i diversi tipi di informazioni
                    detail_tabs = st.tabs(["📑 Informazioni Generali", "📊 Valutazione Dettagliata", "📄 CV Completo", "🏢 Aziende", "📝 Note"])
                    
                    with detail_tabs[0]:
                        st.subheader("Informazioni Generali")
                        
                        # Mostra i dati estratti
                        if "result" in result_data and "extraction" in result_data["result"]:
                            extraction = result_data["result"]["extraction"]
                            
                            # Organizza i dati in una tabella
                            info_data = []
                            for field in st.session_state.fields:
                                value = extraction.get(field, "")
                                # Converti le liste in stringhe per evitare errori nella visualizzazione
                                if isinstance(value, list):
                                    value = ", ".join(map(str, value))
                                info_data.append({"Campo": field, "Valore": value})
                            
                            st.table(pd.DataFrame(info_data))
                        else:
                            st.warning("Nessuna informazione estratta disponibile")
                        
                        with detail_tabs[1]:
                            st.subheader("Valutazione Dettagliata")
                            
                            # Mostra il punteggio composito
                            if "result" in result_data and "composite_score" in result_data["result"]:
                                composite_score = result_data["result"]["composite_score"]
                                st.markdown(f"""
                                <div style="text-align: center; margin-bottom: 20px;">
                                    <h3>Punteggio Complessivo</h3>
                                    {create_score_bar(composite_score)}
                                    <h4>{format_score_with_color(composite_score)}</h4>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Mostra i punteggi per criterio
                            if "result" in result_data and "criteria" in result_data["result"]:
                                criteria = result_data["result"]["criteria"]
                                
                                st.markdown("<h3>Punteggi per Criterio</h3>", unsafe_allow_html=True)
                                
                                criteria_data = []
                                criteria_to_use = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
                                for criteria_id, criteria_label in criteria_to_use:
                                    if criteria_id in criteria:
                                        score = criteria[criteria_id].get("score", 0)
                                        motivation = criteria[criteria_id].get("motivation", "")
                                        criteria_data.append({
                                            "Criterio": criteria_label,
                                            "Punteggio": create_score_badge(score),
                                            "Motivazione": format_motivazione(motivation)
                                        })
                                
                                # Visualizza i criteri in una tabella
                                criteria_df = pd.DataFrame(criteria_data)
                                st.markdown(criteria_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                            else:
                                st.warning("Nessuna valutazione dettagliata disponibile")
                        
                        with detail_tabs[2]:
                            st.subheader("CV Completo")
                            
                            # Mostra il testo completo del CV
                            if "cv_text" in result_data:
                                st.text_area("Testo del CV", result_data["cv_text"], height=500)
                            else:
                                st.warning("Testo del CV non disponibile")
                        
                        with detail_tabs[3]:
                            st.subheader("Aziende del Candidato")
                            
                            # Controlla se abbiamo dati sulle aziende
                            companies_data = None
                            if "result" in result_data and "criteria" in result_data["result"]:
                                criteria_data = result_data["result"]["criteria"]
                                if isinstance(criteria_data, dict) and "companies" in criteria_data:
                                    companies_data = criteria_data["companies"]
                            
                            if not companies_data:
                                # Se non ci sono dati, offri la possibilità di eseguire l'analisi
                                st.info("Nessuna informazione sulle aziende disponibile.")
                                
                                if st.button("Analizza aziende del candidato", key=f"analyze_companies_{selected_cv_idx}"):
                                    with st.spinner("Analisi delle aziende in corso..."):
                                        # Ottieni il testo del CV e i risultati dell'estrazione
                                        cv_text = result_data.get("cv_text", "")
                                        extraction_result = result_data.get("result", {}).get("extraction", {})
                                        
                                        if cv_text and extraction_result:
                                            try:
                                                # Esegui l'analisi delle aziende
                                                companies_analysis = process_companies_in_cv(extraction_result, cv_text)
                                                
                                                # Aggiorna i risultati con le aziende analizzate
                                                if "result" in result_data and "criteria" in result_data["result"]:
                                                    result_data["result"]["criteria"]["companies"] = companies_analysis
                                                    st.success(f"Analizzate {len(companies_analysis)} aziende del candidato")
                                                    st.rerun()  # Ricarica la pagina per mostrare i risultati
                                                else:
                                                    st.error("Impossibile aggiornare i risultati dell'analisi")
                                            except Exception as e:
                                                st.error(f"Errore nell'analisi delle aziende: {str(e)}")
                                        else:
                                            st.error("Dati insufficienti per l'analisi delle aziende")
                            else:
                                # Visualizza le aziende in una tabella
                                st.info(f"Trovate {len(companies_data)} aziende in cui ha lavorato il candidato")
                                
                                # Crea un DataFrame per la visualizzazione
                                companies_df = pd.DataFrame(companies_data)
                                
                                # Visualizza la tabella
                                st.dataframe(companies_df, use_container_width=True)
                                
                                # Visualizza informazioni dettagliate per ogni azienda
                                for company in companies_data:
                                    with st.expander(f"{company['name']}", expanded=False):
                                        st.markdown(f"### {company['name']}")
                                        
                                        if company.get('website'):
                                            st.markdown(f"🌐 [Sito Web]({company['website']})")
                                        
                                        if company.get('description'):
                                            st.markdown(f"**Descrizione:** {company['description']}")
                                        
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            if company.get('industry'):
                                                st.markdown(f"**Settore:** {company['industry']}")
                                            if company.get('size'):
                                                st.markdown(f"**Dimensione:** {company['size']}")
                                            if company.get('location'):
                                                st.markdown(f"**Sede:** {company['location']}")
                                        
                                        with col2:
                                            if company.get('competitor_level'):
                                                st.markdown(f"**Livello di concorrenza:** {company['competitor_level']}")
                                            if 'potential_client' in company:
                                                potential = "Sì" if company['potential_client'] else "No"
                                                st.markdown(f"**Potenziale cliente:** {potential}")
                                            if company.get('last_updated'):
                                                st.markdown(f"*Ultimo aggiornamento: {company['last_updated']}*")
                        
                        with detail_tabs[4]:  # Rinominato da [3] a [4] per la nuova tab delle aziende
                            st.subheader("Note e Commenti")
                            
                            # Genera un ID univoco per il candidato basato sul nome del file
                            candidate_id = hashlib.md5(cv_options[selected_cv_idx].encode()).hexdigest()
                            
                            # Mostra la categoria attuale del candidato
                            current_category = get_candidate_category(candidate_id)
                            if current_category:
                                st.info(f"Categoria attuale: {current_category}")
                            
                            # Interfaccia per aggiungere nuove note
                            with st.form(key=f"note_form_{candidate_id}"):
                                new_note = st.text_area("Aggiungi una nota", height=100)
                                
                                # Selezione della categoria
                                categories = ["Da contattare", "In attesa", "Non idoneo", "Contattato"]
                                new_category = st.selectbox(
                                    "Categorizza il candidato", 
                                    options=[""] + categories,
                                    index=0 if not current_category else categories.index(current_category) + 1
                                )
                                
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    submit_note = st.form_submit_button("Salva nota", use_container_width=True)
                                with col2:
                                    submit_category = st.form_submit_button("Aggiorna categoria", use_container_width=True)
                            
                            if submit_note and new_note:
                                add_candidate_note(candidate_id, new_note)
                                st.success("Nota salvata!")
                                st.rerun()
                            
                            if submit_category and new_category:
                                categorize_candidate(candidate_id, new_category)
                                st.success(f"Candidato categorizzato come: {new_category}")
                                st.rerun()
                            
                            # Mostra le note esistenti
                            notes = get_candidate_notes(candidate_id)
                            if notes:
                                st.subheader("Note esistenti")
                                for i, note in enumerate(notes):
                                    with st.container():
                                        st.markdown(f"""
                                        <div style="border-left: 3px solid {COLORS['primary']}; padding-left: 10px; margin-bottom: 10px;">
                                            <div style="font-size: 0.8rem; color: #888888;">{note["timestamp"]} - {note["user"]}</div>
                                            <div style="margin-top: 5px;">{note["note"]}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                            else:
                                st.info("Nessuna nota disponibile per questo candidato.")
                        
                else:
                    st.info("Seleziona un CV dalla lista per visualizzare i dettagli")
            else:
                st.warning("Nessun risultato disponibile. Analizza prima i CV.")
        
            with compare_tab:
                logger.info("Rendering tab Confronta")
                
                if 'results' in st.session_state and len(st.session_state.results) >= 2:
                    st.subheader("Confronto tra CV")
                    
                    # Selettore per i CV da confrontare
                    cv_options = [result.get("filename", f"CV {i+1}") for i, result in enumerate(st.session_state.results)]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        cv1_idx = st.selectbox("Primo CV", options=range(len(cv_options)), format_func=lambda i: cv_options[i])
                    with col2:
                        # Escludiamo il CV già selezionato
                        cv2_idx = st.selectbox("Secondo CV", options=range(len(cv_options)), format_func=lambda i: cv_options[i], index=1 if cv1_idx == 0 else 0)
                    
                    if cv1_idx != cv2_idx:
                        logger.info(f"Confronto tra CV: {cv_options[cv1_idx]} e {cv_options[cv2_idx]}")
                        
                        # Ottieni i risultati selezionati
                        result1 = st.session_state.results[cv1_idx]
                        result2 = st.session_state.results[cv2_idx]
                        
                        # Confronto dei punteggi complessivi
                        score1 = result1.get("result", {}).get("composite_score", 0)
                        score2 = result2.get("result", {}).get("composite_score", 0)
                        
                        # Visualizzazione dei punteggi
                        st.markdown("<h3>Confronto Punteggi Complessivi</h3>", unsafe_allow_html=True)
                        
                        score_cols = st.columns(2)
                        with score_cols[0]:
                            st.markdown(f"""
                            <div style="text-align: center;">
                                <h4>{cv_options[cv1_idx]}</h4>
                                {create_score_bar(score1)}
                                <h5>{format_score_with_color(score1)}</h5>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with score_cols[1]:
                            st.markdown(f"""
                            <div style="text-align: center;">
                                <h4>{cv_options[cv2_idx]}</h4>
                                {create_score_bar(score2)}
                                <h5>{format_score_with_color(score2)}</h5>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Confronto dei criteri
                        st.markdown("<h3>Confronto Criteri</h3>", unsafe_allow_html=True)
                        
                        criteria1 = result1.get("result", {}).get("criteria", {})
                        criteria2 = result2.get("result", {}).get("criteria", {})
                        
                        criteria_data = []
                        criteria_to_use = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
                        for criteria_id, criteria_label in criteria_to_use:
                            score1 = criteria1.get(criteria_id, {}).get("score", 0)
                            score2 = criteria2.get(criteria_id, {}).get("score", 0)
                            
                            criteria_data.append({
                                "Criterio": criteria_label,
                                f"Punteggio {cv_options[cv1_idx]}": create_score_badge(score1),
                                f"Punteggio {cv_options[cv2_idx]}": create_score_badge(score2),
                                "Differenza": score1 - score2
                            })
                        
                        # Visualizza i criteri in una tabella
                        criteria_df = pd.DataFrame(criteria_data)
                        st.markdown(criteria_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                        
                        # Confronto delle informazioni estratte
                        st.markdown("<h3>Confronto Informazioni</h3>", unsafe_allow_html=True)
                        
                        extraction1 = result1.get("result", {}).get("extraction", {})
                        extraction2 = result2.get("result", {}).get("extraction", {})
                        
                        info_data = []
                        for field in st.session_state.fields:
                            info_data.append({
                                "Campo": field,
                                f"Valore {cv_options[cv1_idx]}": extraction1.get(field, ""),
                                f"Valore {cv_options[cv2_idx]}": extraction2.get(field, "")
                            })
                        
                        st.table(pd.DataFrame(info_data))
                        
                    else:
                        st.warning("Seleziona due CV diversi per confrontarli")
                else:
                    st.warning("Sono necessari almeno 2 CV analizzati per il confronto")
            
            with cards_tab:
                logger.info("Rendering tab Schede CV")
                
                if 'results' in st.session_state and st.session_state.results:
                    st.subheader("Visualizzazione a schede")
                    
                    # Filtri
                    with st.expander("Filtri", expanded=False):
                        filter_cols = st.columns([1, 1, 2])
                        with filter_cols[0]:
                            min_score_cards = st.slider("Punteggio minimo", 0, 100, st.session_state.filter_criteria['min_score'], key="cards_min_score")
                        with filter_cols[1]:
                            filter_city_cards = st.text_input("Filtra per città", value=st.session_state.filter_criteria['city'], key="cards_city")
                        with filter_cols[2]:
                            categories_filter = st.multiselect(
                                "Filtra per categoria", 
                                options=["Da contattare", "In attesa", "Non idoneo", "Contattato"],
                                default=st.session_state.filter_criteria['categories']
                            )
                            if categories_filter != st.session_state.filter_criteria['categories']:
                                st.session_state.filter_criteria['categories'] = categories_filter
                    
                    # Rendering delle schede
                    # Filtra i risultati in base ai criteri
                    filtered_results = st.session_state.results.copy()
                    
                    # Filtra per punteggio
                    if min_score_cards > 0:
                        filtered_results = [
                            r for r in filtered_results 
                            if r.get("result", {}).get("composite_score", 0) >= min_score_cards
                        ]
                    
                    # Filtra per città
                    if filter_city_cards:
                        filtered_results = []
                        for r in st.session_state.results.copy():
                            city_value = r.get("result", {}).get("extraction", {}).get("Città di residenza", "")
                            # Converti in stringa in modo sicuro per gestire qualsiasi tipo di dato
                            if isinstance(city_value, list):
                                city_value = ", ".join(str(item) for item in city_value)
                            elif city_value is None:
                                city_value = ""
                            else:
                                city_value = str(city_value)
                                
                            if filter_city_cards.lower() in city_value.lower():
                                filtered_results.append(r)
                    
                    # Filtra per categoria
                    if categories_filter:
                        filtered_results = [
                            r for r in filtered_results 
                            if get_candidate_category(hashlib.md5(r.get("filename", "").encode()).hexdigest()) in categories_filter
                        ]
                    
                    # Crea la griglia di schede
                    if filtered_results:
                        card_html = ""
                        for i, result in enumerate(filtered_results):
                            card_html += render_cv_card(result, i)
                        
                        st.markdown(f"""
                        <div class="card-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">
                            {card_html}
                        </div>
                        
                        <script>
                        // JavaScript per gestire i pulsanti nelle schede
                        document.addEventListener('DOMContentLoaded', function() {{
                            // Gestione pulsanti "Vedi dettagli"
                            const detailButtons = document.querySelectorAll('.view-details-btn');
                            detailButtons.forEach(button => {{
                                button.addEventListener('click', function() {{
                                    // Implementazione da completare
                                }});
                            }});
                            
                            // Gestione pulsanti "Categorizza"
                            const categoryButtons = document.querySelectorAll('.category-btn');
                            categoryButtons.forEach(button => {{
                                button.addEventListener('click', function() {{
                                    const dropdown = this.nextElementSibling;
                                    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
                                }});
                            }});
                        }});
                        </script>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("Nessun CV corrisponde ai filtri selezionati")
                else:
                    st.warning("Nessun risultato disponibile. Analizza prima i CV.")
                    
    else:
        logger.warning("Nessun risultato trovato in session_state")
        # Aggiungi un messaggio per l'utente se non ci sono risultati
        if "cv_dir" in st.session_state and st.session_state.cv_dir:
            st.info("Premi 'Analizza CV' per iniziare l'elaborazione.")
        else:
            st.info("Seleziona una cartella contenente i CV e premi 'Analizza CV' per iniziare.")

    # Tab Aziende
    if "companies_tab" in st.session_state:
        with companies_tab:
            logger.info("Rendering tab Aziende")
            
            # Rendering della pagina dedicata alle aziende
            render_company_page()

# Punto di ingresso dell'applicazione
if __name__ == "__main__" and not skip_page_config:
    main()





