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
import xlsxwriter
import logging
import sys
from pathlib import Path
from streamlit.components.v1 import html


# Configurazione della pagina DEVE essere il primo comando Streamlit
st.set_page_config(
    page_title="CV Analyzer Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Costante per limitare il numero di CV da analizzare
MAX_CV_TO_ANALYZE = 99999

# RIMUOVO TUTTI I COMANDI UI DI STREAMLIT A LIVELLO GLOBALE
# Ma mantengo tutte le variabili, costanti, classi e import originali

# Variabili, costanti, ecc. rimangono invariate
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

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
    ("criteri_base", "Valuta principalmente la corrispondenza tra requisiti del lavoro e competenze/esperienze del candidato, considerando il livello di esperienza, la formazione e le competenze tecniche."),
    ("criteri_estesi", "Criteri di valutazione: Top 10 università nazionali +3 punti, università prestigiose +2 punti, esperienza in aziende leader +2 punti, esperienza in aziende di fama +1 punto, background all'estero +3 punti, background in aziende straniere +1 punto."),
    ("intuito", "Criteri di valutazione: Usa solo il tuo intuito considerando che la tua risposta non rappresenta una valutazione del candidato come persona, ma solo una valutazione tecnica della rispondenza delle caratteristiche del candidato rispetto alle caratteristiche della posizione e sarà usata solo come criterio per la schedulazione dei colloqui personali."),
]

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
    "gpt-4o-mini-high": {"input": 0.00000035, "output": 0.0000014} # $0.35/1M input, $1.4/1M output
}

# Job description di esempio
job_description = DEFAULT_JOB_DESCRIPTION

# Definizione dei criteri di valutazione
EVALUATION_CRITERIA = [
    ("competenze_tecniche", "Competenze Tecniche"),
    ("esperienza_rilevante", "Esperienza Rilevante"),
    ("formazione", "Formazione"),
    ("soft_skills", "Soft Skills"),
    ("fit_culturale", "Fit Culturale"),
    ("potenziale_crescita", "Potenziale di Crescita"),
    ("criteri_base", "Criteri Base"),
    ("criteri_estesi", "Criteri Estesi"),
    ("intuito", "Intuito")
]

# Prompt per i criteri di valutazione
EVALUATION_CRITERIA_PROMPT = """
1. Competenze Tecniche: Valuta quanto le competenze tecniche del candidato corrispondono a quelle richieste nella job description.
2. Esperienza Rilevante: Valuta quanto l'esperienza lavorativa precedente è rilevante per la posizione.
3. Formazione: Valuta l'adeguatezza della formazione accademica e professionale.
4. Soft Skills: Valuta le capacità comunicative, di lavoro in team e di problem solving.
5. Fit Culturale: Valuta quanto il candidato potrebbe integrarsi nell'ambiente di lavoro.
6. Potenziale di Crescita: Valuta il potenziale di crescita e sviluppo professionale del candidato.
"""


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
            llm = ChatOpenAI(model=openai_model, api_key=api_key)
            chat_prompt = ChatPromptTemplate.from_template("{text}")
            chain = chat_prompt | llm | StrOutputParser()
            suggestion_text = chain.invoke({"text": prompt})
        except Exception as e:
            st.warning(f"Errore nel suggerimento campi: {str(e)}")
            return []
    
    # Estrai i campi dall'output
    try:
        # Cerca il pattern JSON nell'output
        import re
        json_match = re.search(r'\[.*\]', suggestion_text)
        if json_match:
            custom_fields = json.loads(json_match.group(0))
        else:
            custom_fields = json.loads(suggestion_text)
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
        # È una chiamata dalla cache
        st.session_state.cached_input_tokens += input_tokens
        st.session_state.cached_output_tokens += output_tokens
        st.session_state.cached_calls += 1
    else:
        # È una chiamata API reale
        st.session_state.real_input_tokens += input_tokens
        st.session_state.real_output_tokens += output_tokens
        st.session_state.real_api_calls += 1
    
    if "model" in st.session_state:
        st.session_state.model_used = st.session_state.model


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

def get_score_color(score):
    """Restituisce il colore appropriato in base al punteggio"""
    if score >= 80:
        return COLORS['success']
    elif score >= 65:
        return COLORS['warning']
    else:
        return COLORS['error']

def get_score_label(score):
    """Restituisce l'etichetta appropriata in base al punteggio"""
    if score >= 80:
        return "Ottimo"
    elif score >= 65:
        return "Buono"
    else:
        return "Sufficiente"

def format_score_with_color(score):
    """Formatta il punteggio con il colore appropriato"""
    color = get_score_color(score)
    return f'<span style="color:{color};font-weight:bold;">{score}</span>'

def create_score_badge(score):
    """Crea un badge HTML per il punteggio"""
    color_class = ""
    if score >= 80:
        color_class = "score-high"
    elif score >= 65:
        color_class = "score-medium"
    else:
        color_class = "score-low"
    
    return f'<span class="score-badge {color_class}">{score}</span>'

def create_score_bar(score, max_score=100):
    """Crea una barra di progresso per visualizzare il punteggio"""
    color = get_score_color(score)
    percent = (score / max_score) * 100
    
    html = f'''
    <div class="score-bar-container">
        <div class="score-bar" style="width:{percent}%;background-color:{color};"></div>
    </div>
    <div class="score-label">
        <span>{get_score_label(score)}</span>
        <span>{score}/100</span>
    </div>
    '''
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
    # Se la cache è disabilitata, restituisci sempre None
    if "use_cache" in st.session_state and not st.session_state.use_cache:
        return None
        
    cache_path = get_cache_path(model_name, prompt)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cached_result = json.load(f)
                
                # Conta i token per la metrica di risparmio, segnalando che viene dalla cache
                input_tokens = count_tokens(prompt)
                output_tokens = count_tokens(cached_result if isinstance(cached_result, str) else json.dumps(cached_result))
                update_cost_tracking(input_tokens, output_tokens, from_cache=True)
                
                return cached_result
        except Exception as e:
            st.warning(f"Errore nella lettura della cache: {str(e)}")
            return None
    return None

def save_to_cache(model_name, prompt, response):
    """Salva una risposta nella cache."""
    # Se la cache è disabilitata, non salvare
    if "use_cache" in st.session_state and not st.session_state.use_cache:
        return None
        
    try:
        cache_path = get_cache_path(model_name, prompt)
        with open(cache_path, 'w') as f:
            json.dump(response, f)
        return cache_path
    except Exception as e:
        st.warning(f"Errore nel salvataggio della cache: {str(e)}")
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

    st.info(f"Affinamento di {len(missing_fields)} campi mancanti: {', '.join(missing_fields)}")
    
    # Per ogni campo mancante, fai una nuova richiesta specifica
    for field in missing_fields:
        # Creo un prompt specifico per questo campo
        field_prompt = f"""
        Analizza il seguente CV per estrarre SOLO il campo: {field}
        
        CV:
        {cv_text}
        
        IMPORTANTE: 
        1. Estrai ESCLUSIVAMENTE il campo {field} dal CV
        2. Se l'informazione non è esplicitamente presente, fai una stima ragionevole basata sul contesto
        3. Per 'Anni di esperienza', calcola in base alle date di lavoro o al percorso professionale
        4. Per 'Posizione attuale', indica l'ultimo ruolo menzionato
        5. Per 'Formazione più alta', estrai il titolo di studio più elevato
        6. Evita di rispondere con 'Non specificato' o 'Non disponibile' - fai sempre una stima informata
        7. Rispondi direttamente con l'informazione, senza frasi introduttive
        8. Rispondi concisamente, massimo 2-3 righe
        """
        
        try:
            if use_ollama:
                # Usa l'API di Ollama
                model_name = f"ollama-{ollama_model}"
                
                # Cerca nella cache
                cached_response = get_cached_response(model_name, field_prompt)
                if cached_response:
                    extraction_result[field] = cached_response
                    continue
                
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": ollama_model,
                        "prompt": field_prompt,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    save_to_cache(model_name, field_prompt, result)
                    extraction_result[field] = result.strip()
                else:
                    st.warning(f"Errore nell'affinamento del campo {field}")
                    continue
            else:
                # Usa OpenAI
                model_name = openai_model
                
                # Cerca nella cache
                cached_response = get_cached_response(model_name, field_prompt)
                if cached_response:
                    extraction_result[field] = cached_response
                    continue
                
                try:
                    # Utilizzo di LangChain per OpenAI
                    llm = ChatOpenAI(model=model_name, api_key=api_key)
                    chat_prompt = ChatPromptTemplate.from_template("{text}")
                    chain = chat_prompt | llm | StrOutputParser()
                    result = chain.invoke({"text": field_prompt})
                    
                    # Salva nella cache
                    save_to_cache(model_name, field_prompt, result)
                    extraction_result[field] = result.strip()
                except Exception as chain_error:
                    # Fallback a chiamata diretta OpenAI in caso di errore LangChain
                    st.warning(f"Errore con LangChain: {str(chain_error)}. Tentativo con client diretto...")
                    
                    # Importa e usa il client OpenAI direttamente
                    try:
                        from openai import OpenAI
                        client = OpenAI(api_key=api_key)
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": field_prompt}]
                        )
                        result = response.choices[0].message.content
                        save_to_cache(model_name, field_prompt, result)
                        extraction_result[field] = result.strip()
                    except Exception as api_error:
                        st.error(f"Errore anche con client diretto: {str(api_error)}")
                        if field not in extraction_result or not extraction_result[field]:
                            extraction_result[field] = "Non specificato"
                        continue
            
            # Pulisci la risposta e rimuovi frasi introduttive comuni
            result = extraction_result[field]
            common_intros = [
                "Basandomi sul CV,", "Dal CV fornito,", "Dal curriculum,", 
                "Secondo il CV,", "Il candidato ha", "L'informazione richiesta è"
            ]
            for intro in common_intros:
                if isinstance(result, str) and result.startswith(intro):
                    result = result[len(intro):].strip()
                    if result.startswith(",") or result.startswith(":"):
                        result = result[1:].strip()
                    extraction_result[field] = result
            
        except Exception as e:
            st.error(f"Errore nell'estrazione del campo {field}: {str(e)}")
            if field not in extraction_result or not extraction_result[field]:
                extraction_result[field] = "Non specificato"
            
    return extraction_result

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
    if "model" not in st.session_state or not st.session_state.model:
        st.error("❌ Modello OpenAI non selezionato")
        return None
    
    if "api_key" not in st.session_state or not st.session_state.api_key:
        st.error("❌ API key di OpenAI non impostata")
        return None
        
    try:
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
        
        Restituisci i risultati in formato JSON, con ogni campo come chiave e il valore estratto.
        """
        
        # Conta i token del prompt di estrazione
        extraction_input_tokens = count_tokens(extraction_prompt, st.session_state.model)
        extraction_output_tokens = 0
        
        # Cerca nella cache per l'estrazione
        model_name = f"openai-{st.session_state.model}"
        cached_extraction = get_cached_response(model_name, extraction_prompt)
        
        if cached_extraction:
            try:
                if isinstance(cached_extraction, str):
                    extraction_result = json.loads(cached_extraction)
                else:
                    extraction_result = cached_extraction
                # Nota: il conteggio dei token per la cache è già gestito in get_cached_response
            except:
                import re
                json_match = re.search(r'\{.*\}', cached_extraction, re.DOTALL)
                if json_match:
                    extraction_result = json.loads(json_match.group(0))
                else:
                    st.warning("⚠️ Cache corrotta per l'estrazione, richiamo l'API")
                    cached_extraction = None
        
        if not cached_extraction:
            # Rimosso il 'try' problematico
            from openai import OpenAI
            client = OpenAI(api_key=st.session_state.api_key)
            
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
                st.session_state.extraction_tokens_input += input_tokens
                st.session_state.extraction_tokens_output += output_tokens
            except Exception as e:
                st.error(f"❌ Errore nella chiamata API: {str(e)}")
                return None
        
        # Utilizziamo il secondo passaggio per estrarre campi mancanti
        if extraction_result:
            missing_fields = []
            for field in fields:
                if field not in extraction_result or not extraction_result[field] or extraction_result[field] == "Non specificato":
                    missing_fields.append(field)
            
            if missing_fields:
                st.info(f"🔍 Affinamento di {len(missing_fields)} campi mancanti: {', '.join(missing_fields)}")
                refine_input_tokens = 0
                refine_output_tokens = 0
                
                for field in missing_fields:
                    field_prompt = f"""
                    Analizza il seguente CV per estrarre SOLO il campo: {field}
                    
                    CV:
                    {cv_text}
                    
                    IMPORTANTE: 
                    1. Estrai ESCLUSIVAMENTE il campo {field} dal CV
                    2. Se l'informazione non è esplicitamente presente, fai una stima ragionevole basata sul contesto
                    3. Per 'Anni di esperienza', calcola in base alle date di lavoro o al percorso professionale
                    4. Per 'Posizione attuale', indica l'ultimo ruolo menzionato
                    5. Per 'Formazione più alta', estrai il titolo di studio più elevato
                    6. Evita di rispondere con 'Non specificato' o 'Non disponibile' - fai sempre una stima informata
                    7. Rispondi direttamente con l'informazione, senza frasi introduttive
                    8. Rispondi concisamente, massimo 2-3 righe
                    """
                    
                    # Conta i token del prompt di affinamento
                    field_input_tokens = count_tokens(field_prompt, st.session_state.model)
                    refine_input_tokens += field_input_tokens
                    
                    # Cerca nella cache
                    cached_response = get_cached_response(model_name, field_prompt)
                    if cached_response:
                        extraction_result[field] = cached_response if isinstance(cached_response, str) else json.dumps(cached_response)
                        continue
                    
                    try:
                        # Usa OpenAI direttamente
                        from openai import OpenAI
                        client = OpenAI(api_key=st.session_state.api_key)
                        response = client.chat.completions.create(
                            model=st.session_state.model,
                            messages=[{"role": "user", "content": field_prompt}]
                        )
                        result = response.choices[0].message.content
                        
                        # Conta i token di output
                        field_output_tokens = count_tokens(result, st.session_state.model)
                        refine_output_tokens += field_output_tokens
                        
                        # Salva nella cache
                        save_to_cache(model_name, field_prompt, result)
                        
                        # Pulisci la risposta
                        result = result.strip()
                        common_intros = [
                            "Basandomi sul CV,", "Dal CV fornito,", "Dal curriculum,", 
                            "Secondo il CV,", "Il candidato ha", "L'informazione richiesta è"
                        ]
                        for intro in common_intros:
                            if isinstance(result, str) and result.startswith(intro):
                                result = result[len(intro):].strip()
                                if result.startswith(",") or result.startswith(":"):
                                    result = result[1:].strip()
                        
                        extraction_result[field] = result
                    except Exception as e:
                        st.warning(f"⚠️ Errore nell'affinamento del campo {field}: {str(e)}")
                        continue
                
                # Aggiorna il conteggio dei token e il costo per la fase di affinamento
                update_cost_tracking(refine_input_tokens, refine_output_tokens, from_cache=False)
        
        # Valutazione con i criteri
        evaluation_prompt = f"""
        Sei un esperto di selezione del personale. Valuta il CV rispetto alla descrizione del lavoro.
            
            Job Description:
            {job_description}
            
            CV:
            {cv_text}
            
        Estrazione informazioni:
        {json.dumps(extraction_result, indent=2, ensure_ascii=False)}
        
        Valuta il candidato per i seguenti criteri su una scala da 0 a 100:
        1. competenze_tecniche: Valuta quanto le competenze tecniche del candidato corrispondono a quelle richieste.
        2. esperienza_rilevante: Valuta quanto l'esperienza lavorativa precedente è rilevante per la posizione.
        3. formazione: Valuta l'adeguatezza della formazione accademica e professionale.
        4. soft_skills: Valuta le capacità comunicative, di lavoro in team e di problem solving.
        5. fit_culturale: Valuta quanto il candidato potrebbe integrarsi nell'ambiente di lavoro.
        6. potenziale_crescita: Valuta il potenziale di crescita e sviluppo professionale del candidato.
        7. criteri_base: Valuta quanto il candidato soddisfa i requisiti minimi del ruolo.
        8. criteri_estesi: Valuta quanto il candidato soddisfa requisiti aggiuntivi desiderabili.
        9. intuito: Valuta, in base al tuo intuito professionale, quanto il candidato sia adatto alla posizione.
        
        IMPORTANTE: Assegna un punteggio onesto che rifletta accuratamente quanto il candidato soddisfa i requisiti.
        Utilizza l'intera gamma di valori (0-100) e NON assegnare automaticamente punteggi alti.
        La tua valutazione dovrebbe essere:
        - 90-100: Candidato eccezionale, corrisponde perfettamente ai requisiti
        - 75-89: Candidato molto buono, soddisfa la maggior parte dei requisiti
        - 60-74: Candidato discreto, alcune lacune ma generalmente adatto
        - 40-59: Candidato mediocre, lacune significative
        - 0-39: Candidato non adatto
        
        Per ogni criterio, restituisci un oggetto JSON con i campi:
        - "score": punteggio numerico da 0 a 100
        - "motivation": breve spiegazione del punteggio (max 150 caratteri)
        - "key_points": 2-3 punti chiave che motivano il punteggio
        
        Il risultato complessivo deve essere un oggetto JSON con ogni criterio come chiave.
        """
        
        # Conta i token del prompt di valutazione
        evaluation_input_tokens = count_tokens(evaluation_prompt, st.session_state.model)
        evaluation_output_tokens = 0
        
        # Cerca nella cache per la valutazione
        cached_evaluation = get_cached_response(model_name, evaluation_prompt)
        
        if cached_evaluation:
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
                    st.warning("⚠️ Cache corrotta per la valutazione, richiamo l'API")
                    cached_evaluation = None
                    evaluation_result = {}
        else:
            evaluation_result = {}
            
        if not cached_evaluation:
            try:
                # Utilizzo di client OpenAI diretto con response_format
                from openai import OpenAI
                client = OpenAI(api_key=st.session_state.api_key)
                
                # Verifica se il modello supporta response_format
                supports_json_format = any(m in st.session_state.model for m in ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
                
                response_args = {
                    "model": st.session_state.model,
                    "messages": [{"role": "user", "content": evaluation_prompt}]
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
                            st.error("❌ Errore nel parsing della valutazione. JSON non valido anche dopo la pulizia.")
                            st.code(evaluation_text, language="json")
                            return None
                    else:
                        st.error("❌ Errore nel parsing della valutazione. La risposta non contiene un JSON valido.")
                        st.code(evaluation_text, language="text")
                        return None
            except Exception as e:
                st.error(f"❌ Errore nell'invocazione di OpenAI per la valutazione: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
                return None
                
        # Controlla i campi obbligatori
        missing_criteria = []
        for criteria_id, _ in EVALUATION_CRITERIA:
            if criteria_id not in evaluation_result:
                missing_criteria.append(criteria_id)
        
        if missing_criteria:
            st.warning(f"⚠️ Mancano i seguenti criteri: {', '.join(missing_criteria)}")
            for criteria_id in missing_criteria:
                evaluation_result[criteria_id] = {
                    "score": 50,
                    "motivation": "Valutazione automatica (criterio mancante)",
                    "key_points": ["Criterio non valutato dal modello"]
                }
        
        # Calcolo punteggio composito
        total_score = 0
        count = 0
        for criteria_id, _ in EVALUATION_CRITERIA:
            if criteria_id in evaluation_result:
                try:
                    score = float(evaluation_result[criteria_id].get("score", 0))
                    total_score += score
                    count += 1
                except (ValueError, TypeError):
                    st.warning(f"⚠️ Errore nel punteggio per {criteria_id}")
        
        composite_score = int(total_score / max(1, count))
        
        return {
            "extraction": extraction_result,
            "criteria": evaluation_result,
            "composite_score": composite_score
        }
    except Exception as e:
        st.error(f"❌ Errore durante l'analisi con OpenAI: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def analyze_cv_ollama(cv_text, job_description, fields):
    """Analizza un CV con Ollama"""
    if "ollama_model" not in st.session_state or not st.session_state.ollama_model:
        st.error("Modello Ollama non selezionato")
        return None
        
    try:
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
        
        Restituisci i risultati in formato JSON, con ogni campo come chiave e il valore estratto.
        """
        
        # Cerca nella cache
        model_name = f"ollama-{st.session_state.ollama_model}"
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
            try:
                # Chiamata API Ollama
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": st.session_state.ollama_model,
                        "prompt": extraction_prompt,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    save_to_cache(model_name, extraction_prompt, result)
                    
                    # Parsing del JSON in dict Python
                    try:
                        extraction_result = json.loads(result)
                    except:
                        import re
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            extraction_result = json.loads(json_match.group(0))
                        else:
                            st.error("Errore nel parsing della risposta. La risposta non contiene un JSON valido.")
                            return None
                else:
                    st.error(f"Errore nella chiamata Ollama: {response.status_code}")
                    return None
            except Exception as e:
                st.error(f"Errore durante la chiamata Ollama: {str(e)}")
                return None
        
        # Utilizziamo il secondo passaggio per estrarre campi mancanti
        if extraction_result:
            extraction_result = refine_missing_fields(
                cv_text=cv_text,
                extraction_result=extraction_result,
                fields=fields,
                use_ollama=True,
                ollama_model=st.session_state.ollama_model
            )
        
        # Valutazione con Ollama
        evaluation_prompt = f"""
        Sei un esperto di selezione del personale. Valuta il CV rispetto alla descrizione del lavoro.
        
        Job Description:
        {job_description}
        
        CV:
        {cv_text}
        
        Estrazione informazioni:
        {json.dumps(extraction_result, indent=2, ensure_ascii=False)}
        
        Valuta il candidato per i seguenti criteri su una scala da 0 a 100:
        {EVALUATION_CRITERIA_PROMPT}
        
        IMPORTANTE: Assegna un punteggio onesto che rifletta accuratamente quanto il candidato soddisfa i requisiti.
        Utilizza l'intera gamma di valori (0-100) e NON assegnare automaticamente punteggi alti.
        La tua valutazione dovrebbe essere:
        - 90-100: Candidato eccezionale, corrisponde perfettamente ai requisiti
        - 75-89: Candidato molto buono, soddisfa la maggior parte dei requisiti
        - 60-74: Candidato discreto, alcune lacune ma generalmente adatto
        - 40-59: Candidato mediocre, lacune significative
        - 0-39: Candidato non adatto
        
        Per ogni criterio, restituisci un oggetto JSON con i campi:
        - "score": punteggio numerico da 0 a 100
        - "motivation": breve spiegazione del punteggio (max 150 caratteri)
        - "key_points": 2-3 punti chiave che motivano il punteggio
        
        Il risultato complessivo deve essere un oggetto JSON con ogni criterio come chiave.
        """
        
        # Cerca nella cache
        cached_evaluation = get_cached_response(model_name, evaluation_prompt)
        
        if cached_evaluation:
            try:
                evaluation_result = json.loads(cached_evaluation)
            except:
                import re
                json_match = re.search(r'\{.*\}', cached_evaluation, re.DOTALL)
                if json_match:
                    evaluation_result = json.loads(json_match.group(0))
                else:
                    st.warning("Cache corrotta per la valutazione, richiamo l'API")
                    cached_evaluation = None
                    evaluation_result = {}
        else:
            evaluation_result = {}
            
        if not cached_evaluation:
            try:
                # Chiamata API Ollama per la valutazione
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": st.session_state.ollama_model,
                        "prompt": evaluation_prompt,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    evaluation_text = response.json().get("response", "")
                    save_to_cache(model_name, evaluation_prompt, evaluation_text)
                    
                    # Parsing del JSON in dict Python
                    try:
                        evaluation_result = json.loads(evaluation_text)
                    except:
                        import re
                        json_match = re.search(r'\{.*\}', evaluation_text, re.DOTALL)
                        if json_match:
                            evaluation_result = json.loads(json_match.group(0))
                        else:
                            st.error("Errore nel parsing della valutazione. La risposta non contiene un JSON valido.")
                            return None
                else:
                    st.error(f"Errore nella chiamata Ollama per la valutazione: {response.status_code}")
                    return None
            except Exception as e:
                st.error(f"Errore durante la chiamata Ollama per la valutazione: {str(e)}")
                return None
        
        # Mancano i controlli sui campi obbligatori
        missing_criteria = []
        for criteria_id, _ in EVALUATION_CRITERIA:
            if criteria_id not in evaluation_result:
                missing_criteria.append(criteria_id)
        
        if missing_criteria:
            st.warning(f"Mancano i seguenti criteri: {', '.join(missing_criteria)}")
            for criteria_id in missing_criteria:
                evaluation_result[criteria_id] = {
                    "score": 50,
                    "motivation": "Valutazione automatica (criterio mancante)",
                    "key_points": ["Criterio non valutato dal modello"]
                }
        
        # Calcolo punteggio composito
        total_score = 0
        count = 0
        for criteria_id, _ in EVALUATION_CRITERIA:
            if criteria_id in evaluation_result:
                try:
                    score = float(evaluation_result[criteria_id].get("score", 0))
                    total_score += score
                    count += 1
                except (ValueError, TypeError):
                    st.warning(f"Errore nel punteggio per {criteria_id}")
        
        composite_score = int(total_score / max(1, count))
        
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

def create_download_link(df, sheet_name='Analisi CV', filename='analisi_cv.xlsx'):
    """Crea un link per scaricare il DataFrame come file Excel"""
    
    # Verifica che df non sia None
    if df is None:
        return "Nessun dato disponibile per il download"
    
    output = BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        b64 = base64.b64encode(output.getvalue()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" class="download-button">Scarica Excel</a>'
        return href
    except Exception as e:
        return f"Errore nella creazione del file Excel: {str(e)}"

def normalize_dataframe(df):
    """Normalizza i tipi di dati nel DataFrame per evitare errori di visualizzazione"""
    df_normalized = df.copy()
    
    # Conversione di liste in stringhe per tutte le colonne
    for col in df_normalized.columns:
        df_normalized[col] = df_normalized[col].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x) if x is not None else ""
        )
    
    # Gestione specifica per "Anni di esperienza lavorativa"
    if "Anni di esperienza lavorativa" in df_normalized.columns:
        df_normalized["Anni di esperienza lavorativa"] = df_normalized["Anni di esperienza lavorativa"].apply(
            lambda x: str(x).replace("None", "")
        )
    
    # Gestione specifica per "Competenze tecniche"
    if "Competenze tecniche" in df_normalized.columns:
        df_normalized["Competenze tecniche"] = df_normalized["Competenze tecniche"].apply(
            lambda x: str(x).replace("None", "").replace("[", "").replace("]", "").replace("'", "")
        )
    
    # Rimuovi caratteri problematici da tutte le stringhe
    for col in df_normalized.columns:
        if df_normalized[col].dtype == 'object':
            df_normalized[col] = df_normalized[col].apply(
                lambda x: str(x).replace("\n", " ").replace("\r", " ") if isinstance(x, str) else x
            )
    
    return df_normalized

def process_cvs(cv_dir, job_description, fields, progress_callback=None):
    """Processa tutti i CV in una directory"""
    # Trova tutti i file PDF nella directory
    pdf_files = []
    for file in os.listdir(cv_dir):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(cv_dir, file))
    
    if not pdf_files:
        st.warning("Nessun file PDF trovato nella directory selezionata")
        return [], pd.DataFrame()  # Restituisco risultati vuoti e un DataFrame vuoto
    
    # Applica il limite al numero di CV da analizzare
    if len(pdf_files) > MAX_CV_TO_ANALYZE:
        st.info(f"Limitando l'analisi ai primi {MAX_CV_TO_ANALYZE} CV (su {len(pdf_files)} totali)")
        pdf_files = pdf_files[:MAX_CV_TO_ANALYZE]
    
    # Determina quale modello stiamo usando (OpenAI o Ollama)
    using_openai = st.session_state.get("model_type", "OpenAI") == "OpenAI"
    
    # Assicurati che fields sia una lista valida
    if fields is None:
        # Campi predefiniti che puoi prendere da CV_FIELDS
        fields = st.session_state.fields if 'fields' in st.session_state else CV_FIELDS     
        st.warning("Campi non specificati, utilizzo dei campi selezionati dall'utente")

    
    # Debug info per verificare quale modello viene effettivamente usato
    engine_type = "OpenAI" if using_openai else "Ollama"
    if using_openai:
        model_name = st.session_state.get('model', 'non impostato')
        st.info(f"🤖 Utilizzo {engine_type} - Modello: {model_name}")
        if "api_key" not in st.session_state or not st.session_state.api_key:
            st.error("❌ API key di OpenAI non impostata. L'analisi potrebbe fallire.")
    else:
        model_name = st.session_state.get('ollama_model', 'non impostato')
        st.info(f"🤖 Utilizzo {engine_type} - Modello: {model_name}")
        # Verifica che Ollama sia raggiungibile
        try:
            ollama_models = get_ollama_models()
            if not ollama_models:
                st.warning("⚠️ Ollama non sembra essere in esecuzione. Verifica che il server locale sia attivo.")
        except Exception as e:
            st.error(f"❌ Errore nella connessione a Ollama: {str(e)}")
    
    results = []
    total_files = len(pdf_files)
    
    for i, pdf_path in enumerate(pdf_files):
        filename = os.path.basename(pdf_path)
        
        # Aggiorna il progresso se c'è un callback
        if progress_callback:
            progress_callback(i, total_files, f"Analisi di {filename}")
        else:
            st.write(f"Analisi di {filename}...")
        
        try:
            # Estrai il testo dal PDF
            text_direct, text_ocr = extract_text_from_pdf(pdf_path)
            
            # Combina i testi
            if using_openai and ("model" in st.session_state and st.session_state.model):
                try:
                    cv_text = combine_texts_openai(text_direct, text_ocr)
                except Exception as e:
                    st.error(f"❌ Errore nella combinazione dei testi con OpenAI: {str(e)}")
                    cv_text = text_direct if len(text_direct) > len(text_ocr) else text_ocr
            else:
                try:
                    cv_text = combine_texts_ollama(text_direct, text_ocr)
                except Exception as e:
                    st.error(f"❌ Errore nella combinazione dei testi con Ollama: {str(e)}")
                    cv_text = text_direct if len(text_direct) > len(text_ocr) else text_ocr
            
            # Analizza il CV
            if using_openai:
                # Verifica requisiti per OpenAI
                if "model" not in st.session_state or not st.session_state.model:
                    st.error(f"❌ Modello OpenAI non selezionato per {filename}")
                    continue
                if "api_key" not in st.session_state or not st.session_state.api_key:
                    st.error(f"❌ API key di OpenAI non impostata per {filename}")
                    continue
                    
                try:
                    result = analyze_cv_openai(cv_text, job_description, fields)
                except Exception as e:
                    st.error(f"❌ Errore nell'analisi con OpenAI: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
                    continue
            else:
                # Verifica requisiti per Ollama
                if "ollama_model" not in st.session_state or not st.session_state.ollama_model:
                    st.error(f"❌ Modello Ollama non selezionato per {filename}")
                    continue
                    
                try:
                    result = analyze_cv_ollama(cv_text, job_description, fields)
                except Exception as e:
                    st.error(f"❌ Errore nell'analisi con Ollama: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
                    continue
            
            if result:
                # Aggiungiamo il filename nel risultato
                result["filename"] = filename
                results.append(result)
                st.success(f"✅ Analisi completata per {filename}")
            else:
                st.error(f"❌ Analisi fallita per {filename}")
            
            # Aggiorna il progresso dopo ogni file con i costi aggiornati
            if progress_callback:
                progress_callback(i + 1, total_files, f"Completato {filename}")
            
        except Exception as e:
            st.error(f"❌ Errore nell'analisi di {filename}: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
    
    # Prepara il DataFrame dei risultati
    data = []
    for result in results:
        row = {
            "Filename": result["filename"]
        }
        
        # Aggiungi le informazioni estratte
        for field in fields:
            if "result" in result and "extraction" in result["result"] and field in result["result"]["extraction"]:
                row[field] = result["result"]["extraction"][field]
        
        # Aggiungi il punteggio composito
        if "result" in result and "composite_score" in result["result"]:
            row["Punteggio_composito"] = result["result"]["composite_score"]
        
        # Aggiungi i punteggi per criterio
        for criteria_id, criteria_label in EVALUATION_CRITERIA:
            if "result" in result and "criteria" in result["result"] and criteria_id in result["result"]["criteria"]:
                row[criteria_label] = result["result"]["criteria"][criteria_id].get("score", 0)
        
        data.append(row)
    
    # Crea il DataFrame
    results_df = pd.DataFrame(data) if data else pd.DataFrame()
    
    # Normalizza il dataframe prima di restituirlo
    results_df = normalize_dataframe(results_df)
    
    return results, results_df

def get_composite_score(data, default=0):
    """
    Funzione di utilità per accedere al punteggio composito in modo sicuro,
    indipendentemente dalla struttura dei dati (DataFrame o dizionario originale).
    
    Args:
        data: Può essere un dizionario (dati originali) o una riga di DataFrame
        default: Valore predefinito da restituire se il punteggio non è trovato
        
    Returns:
        Il punteggio composito o il valore predefinito
    """
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
            value="" if "api_key" not in st.session_state or st.session_state.api_key == OPENAI_API_KEY else st.session_state.api_key, 
            type="password",
            placeholder="Inserisci la tua chiave API o lascia vuoto per usare quella in .env",
            key="api_key_input_sidebar"
        )
        
        # Se l'utente ha inserito una chiave, usala, altrimenti usa quella di default
        if api_key_input:
            st.session_state.api_key = api_key_input
        else:
            st.session_state.api_key = OPENAI_API_KEY
            
        st.session_state.model = st.selectbox(
            "Modello OpenAI",
            ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o", "gpt-4"],
            index=0,
            key="model_selectbox_sidebar"
        )
        
        # Mostra un messaggio che indica se si sta usando la chiave dal file .env
        if "api_key" in st.session_state and st.session_state.api_key == OPENAI_API_KEY:
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
    # Campi da estrarre
    st.subheader("Campi da estrarre")

    # Inizializza i campi disponibili nella session_state se non esistono
    if 'available_fields' not in st.session_state:
        st.session_state.available_fields = CV_FIELDS.copy()

    # Inizializza i campi selezionati nella session_state se non esistono
    if 'selected_fields' not in st.session_state:
        st.session_state.selected_fields = CV_FIELDS.copy()  # Inizialmente seleziona tutti

    # Bottone per suggerire campi dalla job description
    if st.button("🔍 Suggerisci campi dalla job description", help="Analizza la job description e suggerisce campi aggiuntivi pertinenti"):
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
                        st.write("Campi suggeriti:")
                        for field in suggested_fields:
                            if field in st.session_state.available_fields[-new_fields_added:]:
                                st.write(f"- {field}")
                    else:
                        st.info("Nessun nuovo campo da aggiungere")
                else:
                    st.info("Nessun campo aggiuntivo suggerito")

    # Campo per aggiungere manualmente un campo personalizzato
    custom_field = st.text_input("Aggiungi un campo personalizzato:")
    if st.button("Aggiungi campo") and custom_field:
        if custom_field not in st.session_state.available_fields:
            st.session_state.available_fields.append(custom_field)
            st.session_state.selected_fields.append(custom_field)
            st.success(f"Campo '{custom_field}' aggiunto")
        else:
            st.warning(f"Il campo '{custom_field}' esiste già")

    # Multiselect che usa i campi dalla session_state (inclusi quelli suggeriti)
    selected_fields = st.multiselect(
        "Seleziona i campi da estrarre",
        options=st.session_state.available_fields,
        default=st.session_state.selected_fields,
        key="fields_multiselect_sidebar"
    )

    # Aggiorna la selezione nella session_state
    st.session_state.selected_fields = selected_fields
    st.session_state.fields = selected_fields  # Questa è la variabile usata dal resto dell'app
    # Info box
    st.subheader("Informazioni")
    st.markdown("CV Analyzer Pro v1.0")
    st.markdown("Sviluppato con ❤️ by Claude AI")

# Miglioramento della funzione setup_logger
def setup_logger():
    """Configura un logger che scrive su un file con timestamp nella cartella logs"""
    import os
    from pathlib import Path
    
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
    logger.setLevel(logging.DEBUG)
    
    # Handler per il file
    try:
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(logging.DEBUG)
        
        # Formattatore
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Rimuovi gli handler esistenti se presenti
        if logger.handlers:
            logger.handlers = []
            
        # Aggiunge l'handler al logger
        logger.addHandler(file_handler)
        
        # Log di avvio
        logger.info(f"================ AVVIO APPLICAZIONE ================")
        logger.info(f"Versione Python: {sys.version}")
        logger.info(f"Directory di lavoro: {os.getcwd()}")
        logger.info(f"Directory dei log: {log_dir}")
    except Exception as e:
        print(f"ERRORE nella configurazione del logger: {str(e)}")
        # Creiamo un logger dummy che stampa solo a console
        logger.handlers = []
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.error(f"Non è stato possibile creare il file di log: {str(e)}")
    
    return logger

def main():
    # Dichiaro global logger all'inizio della funzione per usarlo
    global logger
    
    # Inizializzazione del logger
    logger = setup_logger()
    
    # Verifica se ci sono parametri di query per il cambio di scheda
    query_params = st.experimental_get_query_params()
    if "tab" in query_params:
        if query_params["tab"][0] == "detailed":
            # Imposta la scheda di dettaglio come attiva
            st.session_state.active_tab = 1  # 0=overview, 1=detailed, 2=compare
    
    # Inizializzazione delle variabili di sessione
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    
    # Le prime righe della funzione main()
    st.markdown(f"""
    <style>
    // ... existing code ...
    </style>
    """, unsafe_allow_html=True)
    
    # Mostriamo il percorso dei log all'avvio dell'applicazione
    try:
        log_dir = os.path.join(os.path.abspath(os.getcwd()), "logs")
        st.sidebar.info(f"File di log salvati in: {log_dir}")
    except:
        pass
    

    # Inizializza i campi predefiniti se non esistono
    if "fields" not in st.session_state:
        st.session_state.fields = CV_FIELDS
    
    # Resto dell'inizializzazione
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
    
    # TUTTO IL CODICE UI VA QUI DENTRO
    
    # Titolo dell'applicazione
    st.title("CV Analyzer Pro")
    st.markdown("### Analisi intelligente dei curriculum vitae")
    
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
                    # Processa i CV
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Funzione di callback per aggiornare la progress bar e i costi
                    def update_progress(current, total, message=""):
                        """Aggiorna la progress bar e i costi in tempo reale"""
                        progress = int(current / total * 100)
                        progress_bar.progress(progress)
                        status_text.text(f"Analisi in corso... {progress}% - {message}")
                        # Aggiorna anche i costi in tempo reale
                        update_cost_display()
                    
                    # Chiama process_cvs che ora restituisce results, results_df
                    results, results_df = process_cvs(
                        cv_dir=cv_dir_input,
                        job_description=job_desc,
                        fields=st.session_state.fields,
                        progress_callback=update_progress
                    )
                    
                    if results:
                        st.session_state.results = results
                        st.session_state.results_df = results_df
                        st.session_state.job_description = job_description
                        progress_bar.progress(100)
                        status_text.text("✅ Analisi completata!")
                        st.success(f"Analisi completata con successo per {len(results)} CV.")
                    else:
                        st.error("❌ Si è verificato un errore durante l'analisi. Controlla i messaggi di errore sopra.")

    # Verifica se ci sono risultati da visualizzare
    if "results" in st.session_state and st.session_state.results:
        # Inizializza la scheda attiva se non esiste
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
        
        # Visualizzazione dei risultati
        tab_names = ["📊 Panoramica", "🔍 Dettaglio", "⚖️ Confronta"]
        overview_tab, detailed_tab, compare_tab = st.tabs(tab_names)
        
        with overview_tab:
            # Titolo e descrizione
            st.header("Panoramica dei candidati")
            st.markdown("Questa vista riassume l'analisi dei CV in base alla job description. I candidati sono ordinati per punteggio complessivo.")
            
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
                <div class="metric-container">
                    <div class="metric-label">CV Analizzati</div>
                    <div class="metric-value">{num_results}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with metric_cols[1]:
                top_score = 0
                if ('analysis_results' in st.session_state and 
                    st.session_state.analysis_results is not None):
                    if isinstance(st.session_state.analysis_results, pd.DataFrame) and "Punteggio_composito" in st.session_state.analysis_results:
                        scores = st.session_state.analysis_results["Punteggio_composito"]
                        if len(scores) > 0:
                            top_score = max(scores)
                    elif isinstance(st.session_state.analysis_results, list) and st.session_state.analysis_results:
                        # Calcola il punteggio massimo dalla lista di risultati
                        top_score = max(get_composite_score(result) for result in st.session_state.analysis_results)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{top_score}</div>
                    <div class="metric-label">Punteggio Massimo</div>
                </div>
                """, unsafe_allow_html=True)
                
            with metric_cols[2]:
                # Gestione sicura per il calcolo del punteggio medio
                avg_score = 0
                if ('analysis_results' in st.session_state and 
                    st.session_state.analysis_results is not None):
                    if isinstance(st.session_state.analysis_results, pd.DataFrame) and "Punteggio_composito" in st.session_state.analysis_results:
                        scores = st.session_state.analysis_results["Punteggio_composito"]
                        if len(scores) > 0:
                            avg_score = int(sum(scores) / len(scores))
                    elif isinstance(st.session_state.analysis_results, list) and st.session_state.analysis_results:
                        # Calcola il punteggio medio dalla lista di risultati
                        scores = [get_composite_score(result) for result in st.session_state.analysis_results]
                        if scores:
                            avg_score = int(sum(scores) / len(scores))
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_score}</div>
                    <div class="metric-label">Punteggio Medio</div>
                </div>
                """, unsafe_allow_html=True)
                
            with metric_cols[3]:
                # Gestione sicura per il calcolo del punteggio minimo
                min_score_val = 0
                if ('analysis_results' in st.session_state and 
                    st.session_state.analysis_results is not None):
                    if isinstance(st.session_state.analysis_results, pd.DataFrame) and "Punteggio_composito" in st.session_state.analysis_results:
                        scores = st.session_state.analysis_results["Punteggio_composito"]
                        if len(scores) > 0:
                            min_score_val = min(scores)
                    elif isinstance(st.session_state.analysis_results, list) and st.session_state.analysis_results:
                        # Calcola il punteggio minimo dalla lista di risultati
                        scores = [get_composite_score(result) for result in st.session_state.analysis_results]
                        if scores:
                            min_score_val = min(scores)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{min_score_val}</div>
                    <div class="metric-label">Punteggio Minimo</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Filtri
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            with filter_col1:
                min_score = st.slider("Punteggio minimo", 0, 100, 0)
            with filter_col2:
                search_term = st.text_input("Cerca nei CV", "")
            with filter_col3:
                # Aggiunta del link per il download
                if 'analysis_results' in st.session_state and st.session_state.analysis_results is not None:
                    excel_data = st.session_state.analysis_results
                elif 'results' in st.session_state and st.session_state.results is not None:
                    excel_data = st.session_state.results
                else:
                    excel_data = pd.DataFrame()
                    
                excel_link = create_download_link(excel_data, sheet_name='Analisi CV')
                st.markdown(excel_link, unsafe_allow_html=True)
            
            # Applicazione dei filtri
            if 'analysis_results' in st.session_state and st.session_state.analysis_results is not None:
                print("Usando st.session_state.analysis_results per filtrare")
                # Assicuriamo che sia un DataFrame
                if isinstance(st.session_state.analysis_results, pd.DataFrame):
                    filtered_results = st.session_state.analysis_results.copy()
                else:
                    print("analysis_results non è un DataFrame, converto...")
                    # Se è una lista, convertiamo in DataFrame con i campi corretti
                    if isinstance(st.session_state.analysis_results, list) and st.session_state.analysis_results:
                        # Creiamo una lista di dizionari con i campi necessari
                        data = []
                        for result in st.session_state.analysis_results:
                            row_data = {
                                "Nome_file": result.get("filename", ""),
                                "Punteggio_composito": get_composite_score(result),
                            }
                            # Aggiungi i dati di estrazione se disponibili
                            if "result" in result and "extraction" in result["result"]:
                                extraction = result["result"]["extraction"]
                                row_data.update({
                                    "Nome": extraction.get("Nome", ""),
                                    "Posizione attuale": extraction.get("Posizione attuale", ""),
                                    "Anni di esperienza lavorativa": extraction.get("Anni di esperienza lavorativa", ""),
                                    "Formazione più alta": extraction.get("Formazione più alta", "")
                                })
                            data.append(row_data)
                        filtered_results = pd.DataFrame(data)
                    else:
                        filtered_results = pd.DataFrame(columns=["Nome_file", "Punteggio_composito"])
                
                # Aggiorniamo anche analysis_results per coerenza
                st.session_state.analysis_results = filtered_results.copy()
            elif 'results' in st.session_state and st.session_state.results is not None:
                print("Usando st.session_state.results per filtrare (analysis_results è None)")
                # Assicuriamo che sia un DataFrame
                if isinstance(st.session_state.results, pd.DataFrame):
                    filtered_results = st.session_state.results.copy()
                else:
                    print("results non è un DataFrame, converto...")
                    # Se è una lista, convertiamo in DataFrame con i campi corretti
                    if isinstance(st.session_state.results, list) and st.session_state.results:
                        # Creiamo una lista di dizionari con i campi necessari
                        data = []
                        for result in st.session_state.results:
                            row_data = {
                                "Nome_file": result.get("filename", ""),
                                "Punteggio_composito": get_composite_score(result),
                            }
                            # Aggiungi i dati di estrazione se disponibili
                            if "result" in result and "extraction" in result["result"]:
                                extraction = result["result"]["extraction"]
                                row_data.update({
                                    "Nome": extraction.get("Nome", ""),
                                    "Posizione attuale": extraction.get("Posizione attuale", ""),
                                    "Anni di esperienza lavorativa": extraction.get("Anni di esperienza lavorativa", ""),
                                    "Formazione più alta": extraction.get("Formazione più alta", "")
                                })
                            data.append(row_data)
                        filtered_results = pd.DataFrame(data)
                    else:
                        filtered_results = pd.DataFrame(columns=["Nome_file", "Punteggio_composito"])
                
                # Aggiorniamo anche analysis_results per coerenza
                st.session_state.analysis_results = filtered_results.copy()
            else:
                print("Né analysis_results né results contengono dati validi")
                filtered_results = pd.DataFrame(columns=["Nome_file", "Punteggio_composito"])
            
            # Applica i filtri solo se ci sono dati
            if len(filtered_results) > 0:
                if min_score > 0 and "Punteggio_composito" in filtered_results.columns:
                    # Filtra per punteggio minimo
                    filtered_results = filtered_results[filtered_results["Punteggio_composito"].fillna(0) >= min_score]
                if search_term:
                    # Filtra per termine di ricerca
                    mask = filtered_results.apply(lambda row: any(search_term.lower() in str(val).lower() for val in row), axis=1)
                    filtered_results = filtered_results[mask]
            
            # Visualizzazione dei candidati in una tabella compatta
            if len(filtered_results) > 0:
                # Inizializza lo stato per il candidato selezionato se non esiste
                if 'selected_candidate_index' not in st.session_state:
                    st.session_state.selected_candidate_index = None
                
                # Crea una tabella compatta con i dati essenziali
                table_data = []
                for index, row in filtered_results.iterrows():
                    # Ottieni l'indice originale del risultato
                    original_index = row.get("ID", index) if "ID" in row else index
                    
                    # Accedi al risultato originale usando l'indice
                    if original_index < len(st.session_state.results):
                        result = st.session_state.results[original_index]
                        
                        # Verifica se il risultato contiene 'result' (struttura nidificata)
                        if 'result' in result:
                            candidate_data = result['result']
                        else:
                            candidate_data = result
                        
                        # Accesso sicuro ai dati di estrazione
                        extraction = candidate_data.get('extraction', {})
                        
                        # Accesso sicuro alle colonne con gestione delle chiavi mancanti
                        score = get_composite_score(candidate_data)  # Utilizzo della funzione di utilità
                        nome = extraction.get('Nome', os.path.basename(candidate_data.get('filename', f'Candidato {original_index+1}')))
                        posizione = extraction.get('Posizione attuale', 'Non spec.')
                        esperienze = extraction.get('Anni di esperienza lavorativa', 'Non spec.')
                        formazione = extraction.get('Formazione più alta', 'Non spec.')
                    else:
                        # Fallback ai dati del DataFrame se non riusciamo ad accedere ai dati originali
                        score = get_composite_score(row)  # Utilizzo della funzione di utilità
                        nome = row.get("Nome", row.get("Filename", f"Candidato {index+1}"))
                        posizione = row.get("Posizione attuale", "Non spec.") if pd.notna(row.get("Posizione attuale")) else "Non spec."
                        esperienze = row.get("Anni di esperienza lavorativa", "Non spec.") if pd.notna(row.get("Anni di esperienza lavorativa")) else "Non spec."
                        formazione = row.get("Formazione più alta", "Non spec.") if pd.notna(row.get("Formazione più alta")) else "Non spec."
                    
                    # Aggiungi i dati alla tabella
                    table_data.append({
                        "ID": original_index,
                        "Nome": nome,
                        "Posizione": posizione,
                        "Esperienza": esperienze,
                        "Formazione": formazione,
                        "Punteggio": score
                    })
                
                # Crea un DataFrame per la tabella
                table_df = pd.DataFrame(table_data)
                
                # Usiamo una chiave temporanea univoca per identificare le righe
                table_df['_temp_row_key'] = [f"row_{i}" for i in range(len(table_df))]
                
                # Manteniamo una mappatura tra la chiave temporanea e l'ID originale
              
                # Con questa versione corretta
                row_key_to_id = {}
                for i, row in enumerate(table_data):
                    row_key_to_id[f"row_{i}"] = row["ID"]
                    print(f"Mappatura creata: row_{i} -> {row['ID']}")  # Debug log  

                # Nascondiamo la colonna ID e la chiave temporanea nell'interfaccia utente
                column_hide_list = ['ID', '_temp_row_key']
                
                # Visualizza la tabella con possibilità di selezione
                st.markdown("### Elenco Candidati")
                st.markdown("Clicca su una riga per visualizzare i dettagli del candidato.")
                
                # Usa AgGrid per una tabella interattiva
                from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
                
                gb = GridOptionsBuilder.from_dataframe(table_df)
                gb.configure_selection(selection_mode='single', use_checkbox=False)
                # Nascondi le colonne che non vogliamo mostrare
                for col in column_hide_list:
                    gb.configure_column(col, hide=True)
                
                gb.configure_column("Punteggio", cellStyle=JsCode("""
                function(params) {
                    const score = params.value;
                    let color = '#777777';
                    if (score >= 80) color = '#28a745';
                    else if (score >= 60) color = '#17a2b8';
                    else if (score >= 40) color = '#ffc107';
                    else color = '#dc3545';
                    
                    return {
                        'backgroundColor': color,
                        'color': 'white',
                        'fontWeight': 'bold',
                        'borderRadius': '4px',
                        'padding': '2px 6px',
                        'textAlign': 'center'
                    };
                }
                """))
                
                # Configura l'altezza delle righe per renderle compatte
                gb.configure_grid_options(rowHeight=35)
                
                gridOptions = gb.build()
                
                # Visualizza la tabella
                grid_response = AgGrid(
                    table_df,
                    gridOptions=gridOptions,
                    height=400,
                    fit_columns_on_grid_load=True,
                    allow_unsafe_jscode=True,
                    key="candidate_table"  # Assegna una chiave univoca alla tabella
                )
                
                # Gestisci la selezione
                selected_rows = grid_response['selected_rows']
                # Replace the current selection handling code
                if hasattr(selected_rows, 'empty') and not selected_rows.empty:  # Check if it's a DataFrame with data
                    # Get the first row as a Series
                    selected_row = selected_rows.iloc[0]
                    
                    # Extract the ID value
                    if 'ID' in selected_rows.columns:
                        selected_id = int(selected_row['ID'])
                        print(f"Selected candidate ID: {selected_id}")
                        
                        # Update the session state with the correct index
                        st.session_state.selected_candidate_index = selected_id
                        print(f"Updated selected_candidate_index to: {selected_id}")
                    else:
                        # Fallback to row index if ID column not available
                        print("ID column not found, using index")
                        selected_id = int(selected_rows.index[0]) if selected_rows.index[0].isdigit() else 0
                        st.session_state.selected_candidate_index = selected_id
                
                # Visualizza i dettagli del candidato selezionato
                if st.session_state.selected_candidate_index is not None:
                    st.markdown("---")
                    st.markdown("### Dettagli Candidato Selezionato")
                    
                    # Ottieni i dati del candidato selezionato
                    selected_index = st.session_state.selected_candidate_index
                    candidate_data = st.session_state.results[selected_index]
                    
                    # Appiattisci la struttura dei dati
                    if 'result' in candidate_data:
                        candidate_data = candidate_data['result']
                    
                    # Visualizza i dettagli del candidato selezionato
                    html_content =f"""
                    <div id="candidate-{selected_index}" class="cv-card" style="padding: 2rem; background-color: {COLORS['lightgray']}; border-radius: 8px;">
                        <h2 style="margin-top: 0; color: {COLORS['primary']};">{candidate_data['extraction'].get('Nome', 'Candidato Senza Nome')}</h2>
                        <p style="color: {COLORS['neutral']}; font-size: 1.1rem; margin-bottom: 2rem;">{candidate_data['extraction'].get('Posizione attuale', 'Posizione non specificata')}</p>
                        
                        <div style="display: flex; margin-bottom: 2rem;">
                            <div style="flex: 1; margin-right: 1rem;">
                                <div style="padding: 1rem; border-radius: 8px; background-color: white;">
                                    <h3 style="margin-top: 0; color: {COLORS['primary']};">Riepilogo</h3>
                                    <p>
                                        <strong>Posizione attuale:</strong> {candidate_data['extraction'].get('Posizione attuale', 'Non specificata')}<br>
                                        <strong>Esperienza:</strong> {candidate_data['extraction'].get('Anni di esperienza lavorativa', 'Non specificata')}<br>
                                        <strong>Formazione:</strong> {candidate_data['extraction'].get('Formazione più alta', 'Non specificata')}<br>
                                        <strong>Competenze:</strong> {candidate_data['extraction'].get('Competenze tecniche', 'Non specificate')}
                                    </p>
                                    
                                    <h4 style="color: {COLORS['primary']};">Punti di Forza e Debolezza</h4>
                                    <p><strong>✅ Forza principale:</strong> {candidate_data['extraction'].get('Forza principale', 'Non specificata')}</p>
                                    <p><strong>❌ Debolezza principale:</strong> {candidate_data['extraction'].get('Debolezza principale', 'Non specificata')}</p>
                                    <p><strong>⚖️ Fit generale:</strong> {candidate_data['extraction'].get('Fit generale', 'Non specificato')}</p>
                                </div>
                            </div>
                            <div style="flex: 1;">
                                <div style="padding: 1rem; border-radius: 8px; background-color: white;">
                                    <h3 style="margin-top: 0; color: {COLORS['primary']};">Punteggio Complessivo</h3>
                                    {create_score_bar(get_composite_score(candidate_data))}
                                    
                                    <h4 style="color: {COLORS['primary']}; margin-top: 1.5rem;">Punteggi per Criterio</h4>
            """
                    html(html_content, height=600)

                    for criteria_id, criteria_desc in EVALUATION_CRITERIA:
                        if criteria_id in candidate_data['criteria']:
                            score = candidate_data['criteria'][criteria_id].get('score', 0)
                            st.markdown(f"""
                            <div style="margin-bottom: 1rem;">
                                <p style="margin-bottom: 0.25rem; font-weight: bold;">{criteria_id.replace('_', ' ').title()}</p>
                                {create_score_bar(score)}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("""
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Aggiungi un pulsante per visualizzare più dettagli
                    if st.button("Visualizza Dettagli Completi", key="view_full_details"):
                        # Imposta l'indice del candidato selezionato per la visualizzazione dettagliata
                        st.session_state.detailed_view_index = selected_index
                        # Cambia alla scheda di dettaglio
                        st.experimental_set_query_params(tab="detailed")
            else:
                st.warning("Nessun candidato corrisponde ai criteri di filtro.")
            
            st.markdown("---")
            
           
        
        with detailed_tab:
            st.header("Visualizzazione Dettagliata")
            
            # Selettore per il candidato
            if 'results' in st.session_state and st.session_state.results:
                filenames = [detail["filename"] for detail in st.session_state.results]
                names = []
                for i, detail in enumerate(st.session_state.results):
                    try:
                        name = detail["extraction"].get("Nome", f"Candidato {i+1}")
                        if not isinstance(name, str) or not name.strip():
                            name = f"Candidato {i+1}"
                        names.append(name)
                    except:
                        names.append(f"Candidato {i+1}")
                
                candidate_options = [f"{name} ({filename})" for name, filename in zip(names, filenames)]
                
                # Usa l'indice selezionato nella panoramica, se disponibile
                default_index = 0
                if 'selected_candidate_index' in st.session_state and st.session_state.selected_candidate_index is not None:
                    # Trova l'indice corrispondente nelle opzioni
                    selected_index = st.session_state.selected_candidate_index
                    if 0 <= selected_index < len(candidate_options):
                        default_index = selected_index
                
                selected_candidate = st.selectbox(
                    "Seleziona un candidato da visualizzare in dettaglio", 
                    options=candidate_options,
                    index=default_index
                )
                
                # Ottieni l'indice del candidato selezionato
                selected_index = candidate_options.index(selected_candidate)
                
                # Aggiorna l'indice selezionato nella session_state
                st.session_state.selected_candidate_index = selected_index
                
                candidate_data = st.session_state.results[selected_index]
                
                # Appiattisci la struttura dei dati
                if 'result' in candidate_data:
                    candidate_data = candidate_data['result']
                else:
                    st.error("La struttura dei dati del candidato non è corretta. Manca la chiave 'result'.")
                
                # Debug della struttura dei dati
                st.write("Struttura dei dati del candidato:")
                st.write(candidate_data)
            else:
                st.warning("Nessun risultato disponibile. Esegui prima l'analisi dei CV.")
            
            # Visualizza i dettagli del candidato selezionato
            html_content=f"""
            <div id="candidate-{selected_index}" class="cv-card" style="padding: 2rem;">
                <h2 style="margin-top: 0; color: {COLORS['primary']};">{candidate_data['extraction'].get('Nome', 'Candidato Senza Nome')}</h2>
                <p style="color: {COLORS['neutral']}; font-size: 1.1rem; margin-bottom: 2rem;">{candidate_data['extraction'].get('Posizione attuale', 'Posizione non specificata')}</p>
                
                <div style="display: flex; margin-bottom: 2rem;">
                    <div style="flex: 1; margin-right: 1rem;">
                        <div style="background-color: {COLORS['lightgray']}; padding: 1.5rem; border-radius: 8px;">
                            <h3 style="margin-top: 0; color: {COLORS['primary']};">Riepilogo</h3>
                            <p>
                                <strong>Posizione attuale:</strong> {candidate_data['extraction'].get('Posizione attuale', 'Non specificata')}<br>
                                <strong>Esperienza:</strong> {candidate_data['extraction'].get('Anni di esperienza lavorativa', 'Non specificata')}<br>
                                <strong>Formazione:</strong> {candidate_data['extraction'].get('Formazione più alta', 'Non specificata')}<br>
                                <strong>Competenze:</strong> {candidate_data['extraction'].get('Competenze tecniche', 'Non specificate')}
                            </p>
                            
                            <h4 style="color: {COLORS['primary']};">Punti di Forza e Debolezza</h4>
                            <p><strong>✅ Forza principale:</strong> {candidate_data['extraction'].get('Forza principale', 'Non specificata')}</p>
                            <p><strong>❌ Debolezza principale:</strong> {candidate_data['extraction'].get('Debolezza principale', 'Non specificata')}</p>
                            <p><strong>⚖️ Fit generale:</strong> {candidate_data['extraction'].get('Fit generale', 'Non specificato')}</p>
                        </div>
                    </div>
                    <div style="flex: 1;">
                        <div style="background-color: {COLORS['lightgray']}; padding: 1.5rem; border-radius: 8px;">
                            <h3 style="margin-top: 0; color: {COLORS['primary']};">Punteggio Complessivo</h3>
                            {create_score_bar(get_composite_score(candidate_data))}
                            
                            <h4 style="color: {COLORS['primary']}; margin-top: 1.5rem;">Punteggi per Criterio</h4>
            """
            html(html_content, height=600)

            for criteria_id, criteria_desc in EVALUATION_CRITERIA:
                if criteria_id in candidate_data['criteria']:
                    score = candidate_data['criteria'][criteria_id].get('score', 0)
                    st.markdown(f"""
                    <div style="margin-bottom: 1rem;">
                        <p style="margin-bottom: 0.25rem; font-weight: bold;">{criteria_id.replace('_', ' ').title()}</p>
                        {create_score_bar(score)}
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("""
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Dettagli del candidato
        detail_tabs = st.tabs(["📑 Informazioni Generali", "📊 Valutazione Dettagliata", "📋 CV Completo"])
        
        with detail_tabs[0]:
            col1, col2 = st.columns(2)
            
            # Informazioni personali
            with col1:
                st.markdown("#### Informazioni Personali")
                info_html = ""
                for field in ["Nome", "Email", "Numero di contatto", "Età", "Città di residenza"]:
                    if field in candidate_data['extraction']:
                        value = candidate_data['extraction'][field]
                        if value != "Non specificato" and pd.notna(value):
                            info_html += f"<p><strong>{field}:</strong> {value}</p>"
                
                st.markdown(info_html, unsafe_allow_html=True)
                
                # Formazione
                st.markdown("#### Formazione")
                edu_html = ""
                for field in ["Formazione più alta", "Università/Istituto"]:
                    if field in candidate_data['extraction']:
                        value = candidate_data['extraction'][field]
                        if value != "Non specificato" and pd.notna(value):
                            edu_html += f"<p><strong>{field}:</strong> {value}</p>"
                
                st.markdown(edu_html, unsafe_allow_html=True)
            
            # Esperienza lavorativa
            with col2:
                st.markdown("#### Esperienza Lavorativa")
                exp_html = ""
                for field in ["Posizione attuale", "Anni di esperienza lavorativa", "Datori di lavoro precedenti"]:
                    if field in candidate_data['extraction']:
                        value = candidate_data['extraction'][field]
                        if value != "Non specificato" and pd.notna(value):
                            exp_html += f"<p><strong>{field}:</strong> {value}</p>"
                
                st.markdown(exp_html, unsafe_allow_html=True)
                
                # Competenze
                st.markdown("#### Competenze")
                skills_html = ""
                for field in ["Competenze tecniche", "Lingue conosciute", "Competenze specializzate"]:
                    if field in candidate_data['extraction']:
                        value = candidate_data['extraction'][field]
                        if value != "Non specificato" and pd.notna(value):
                            skills_html += f"<p><strong>{field}:</strong> {value}</p>"
                
                st.markdown(skills_html, unsafe_allow_html=True)
        
        with detail_tabs[1]:
            # Visualizzazione dettagliata dei criteri di valutazione
            for criteria_id, criteria_desc in EVALUATION_CRITERIA:
                if criteria_id in candidate_data['criteria']:
                    score = candidate_data['criteria'][criteria_id].get('score', 0)
                    motivazione = candidate_data['criteria'][criteria_id].get('motivazione', '')
                    punti_chiave = candidate_data['criteria'][criteria_id].get('punti_chiave', [])
                    
                    st.markdown(f"""
                    <div style="background-color: {COLORS['lightgray']}; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                            <h3 style="margin: 0; color: {COLORS['primary']};">{criteria_id.replace('_', ' ').title()}</h3>
                            <div style="background-color: {get_score_color(score)}; color: white; font-weight: bold; padding: 0.5rem 1rem; border-radius: 20px;">
                                {score}/100
                            </div>
                        </div>
                        
                        <h4 style="color: {COLORS['primary']};">Motivazione</h4>
                        <p>{motivazione}</p>
                        
                        <h4 style="color: {COLORS['primary']};">Punti Chiave</h4>
                        <ul>
                    """, unsafe_allow_html=True)
                    
                    for punto in punti_chiave:
                        st.markdown(f"<li>{punto}</li>", unsafe_allow_html=True)
                    
                    st.markdown("""
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
        
        with detail_tabs[2]:
            # Visualizzazione del CV completo
            st.markdown("### Testo Completo del CV")
            
            # Verifichiamo se abbiamo il nome del file originale e la directory dei CV
            extraction = candidate_data['extraction']
            filename = extraction.get('filename', None)
            
            if filename and 'cv_dir' in st.session_state and st.session_state.cv_dir:
                # Verifichiamo se il filename contiene già il percorso completo
                if os.path.isabs(filename) and os.path.exists(filename):
                    pdf_path = filename
                else:
                    # Altrimenti, costruiamo il percorso completo usando il filename (potrebbe essere solo il nome file)
                    pdf_base_name = os.path.basename(filename)
                    pdf_path = os.path.join(st.session_state.cv_dir, pdf_base_name)
                
                # Verifichiamo se il file esiste
                if os.path.exists(pdf_path):
                    try:
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            st.download_button(
                                label="📥 Scarica il PDF originale",
                                data=pdf_bytes,
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf"
                            )
                            st.success(f"Puoi scaricare il PDF originale del CV usando il pulsante qui sopra.")
                    except Exception as e:
                        st.error(f"Impossibile leggere il file PDF: {str(e)}")
                else:
                    st.warning(f"File PDF non trovato: {pdf_path}")
            else:
                st.warning("Il percorso al file PDF originale non è disponibile.")
            
            # Messaggio informativo
            st.info("Di seguito un riassunto dei dati estratti dal CV:")
            
            # Creiamo un testo di riepilogo dai campi di estrazione disponibili
            extraction = candidate_data['extraction']
            riepilogo = ""
            
            # Aggiungi i campi più importanti in formato leggibile
            for campo, valore in extraction.items():
                if isinstance(valore, str) and campo not in ['filename']:
                    riepilogo += f"**{campo}:** {valore}\n\n"
            
            # Mostra il riepilogo formattato
            st.markdown(riepilogo)
            
            # Rimuoviamo il text_area che causava l'errore
            # st.text_area("", value=candidate_data['raw_text'], height=400, disabled=True)
    
        with compare_tab:
            st.header("Confronto tra Candidati")
            
            try:
                # Selettore per i candidati da confrontare
                comparison_candidates = st.multiselect(
                    "Seleziona 2-4 candidati da confrontare",
                    options=candidate_options,
                    default=candidate_options[:min(3, len(candidate_options))]
                )
                
                if len(comparison_candidates) >= 2:
                    # Ottieni gli indici dei candidati selezionati
                    selected_indices = [candidate_options.index(candidate) for candidate in comparison_candidates]
                    selected_data = [st.session_state.results[idx] for idx in selected_indices]
                    
                    
                    # Crea un grafico radar per confrontare i punteggi
                    criteria_names = [criteria_id.replace('_', ' ').title() for criteria_id, _ in EVALUATION_CRITERIA]
                    
                    fig = go.Figure()
                    
                    for candidate_data in selected_data:
                        name = candidate_data['extraction'].get('Nome', 'Candidato Senza Nome')
                        if not isinstance(name, str) or not name.strip():
                            name = 'Candidato Senza Nome'
                        scores = []
                        
                        for criteria_id, _ in EVALUATION_CRITERIA:
                            if criteria_id in candidate_data['criteria']:
                                scores.append(candidate_data['criteria'][criteria_id].get('score', 0))
                            else:
                                scores.append(0)
                        
                        fig.add_trace(go.Scatterpolar(
                            r=scores,
                            theta=criteria_names,
                            fill='toself',
                            name=name,
                            line=dict(width=2)
                        ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100],
                                tickvals=[0, 20, 40, 60, 80, 100]
                            ),
                            angularaxis=dict(
                                tickfont=dict(size=12, family="Arial, sans-serif")
                            )
                        ),
                        title=dict(
                            text="Confronto Punteggi per Criterio",
                            font=dict(size=18, family="Arial, sans-serif")
                        ),
                        showlegend=True,
                        legend=dict(
                            font=dict(size=12, family="Arial, sans-serif"),
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5
                        ),
                        height=600,
                        margin=dict(l=80, r=80, t=100, b=100)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Crea una tabella di confronto
                    st.subheader("Tabella di Confronto")
                    
                    # Crea una tabella HTML per il confronto
                    html_table = """
                    <table class="comparison-table">
                        <tr>
                            <th>Criteri</th>
                    """
                    
                    # Aggiungi intestazioni colonna per ogni candidato
                    for candidate_data in selected_data:
                        name = candidate_data['extraction'].get('Nome', 'Candidato Senza Nome')
                        if not isinstance(name, str) or not name.strip():
                            name = 'Candidato Senza Nome'
                        html_table += f"<th>{name}</th>"
                    
                    html_table += "</tr>"
                    
                    # Aggiungi riga per il punteggio composito
                    html_table += "<tr><td><strong>Punteggio Complessivo</strong></td>"
                    for candidate_data in selected_data:
                        score = get_composite_score(candidate_data)
                        color = get_score_color(score)
                        html_table += f'<td style="color:{color};font-weight:bold;">{score}</td>'
                    html_table += "</tr>"
                    
                    # Aggiungi righe per ogni criterio
                    for criteria_id, _ in EVALUATION_CRITERIA:
                        criteria_name = criteria_id.replace('_', ' ').title()
                        html_table += f"<tr><td><strong>{criteria_name}</strong></td>"
                        
                        for candidate_data in selected_data:
                            if criteria_id in candidate_data['criteria']:
                                score = candidate_data['criteria'][criteria_id].get('score', 0)
                                color = get_score_color(score)
                                html_table += f'<td style="color:{color};font-weight:bold;">{score}</td>'
                            else:
                                html_table += "<td>-</td>"
                        
                        html_table += "</tr>"
                    
                    # Aggiungi righe per altre informazioni rilevanti
                    for field in ["Formazione più alta", "Anni di esperienza lavorativa", "Posizione attuale", "Legame con Firenze"]:
                        html_table += f"<tr><td><strong>{field}</strong></td>"
                        
                        for candidate_data in selected_data:
                            value = candidate_data['extraction'].get(field, "Non specificato")
                            html_table += f"<td>{value}</td>"
                        
                        html_table += "</tr>"
                    
                    html_table += "</table>"
                    
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                    # Punti di forza e debolezza
                    st.subheader("Punti di Forza e Debolezza")
                    
                    for candidate_data in selected_data:
                        name = candidate_data['extraction'].get('Nome', 'Candidato Senza Nome')
                        if not isinstance(name, str) or not name.strip():
                            name = 'Candidato Senza Nome'
                        forza = candidate_data['extraction'].get('Forza principale', 'Non specificata')
                        debolezza = candidate_data['extraction'].get('Debolezza principale', 'Non specificata')
                        
                        st.markdown(f"""
                        <div style="background-color: {COLORS['lightgray']}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                            <h4 style="margin-top: 0; color: {COLORS['primary']};">{name}</h4>
                            <p><strong>✅ Forza principale:</strong> {forza}</p>
                            <p><strong>❌ Debolezza principale:</strong> {debolezza}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Seleziona almeno 2 candidati per visualizzare il confronto.")
            except Exception as e:
                st.error(f"Errore nella visualizzazione del confronto: {e}")
                st.info("Prova a selezionare candidati diversi o riavvia l'analisi.")
    else:
        # Messaggio informativo iniziale
        st.info("Seleziona una cartella, definisci la descrizione del lavoro e clicca su 'Analizza CV' per iniziare.")
        
        # Esempio di risultati attesi (solo per la UI)
        st.markdown("""
        <div style="background-color: #f1f8ff; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
            <h3 style="margin-top: 0;">Come funziona CV Analyzer Pro</h3>
            <ol>
                <li>Inserisci il <strong>percorso della cartella</strong> contenente i CV in formato PDF</li>
                <li>Definisci o modifica la <strong>descrizione del lavoro</strong> in base alle tue esigenze</li>
                <li>Clicca sul pulsante <strong>"Analizza CV"</strong> per avviare l'analisi</li>
                <li>Esplora i risultati nelle diverse visualizzazioni:
                    <ul>
                        <li><strong>Panoramica</strong>: classifica dei candidati in base al punteggio</li>
                        <li><strong>Dettaglio</strong>: approfondimento su ciascun candidato</li>
                        <li><strong>Confronto</strong>: comparazione diretta tra più candidati</li>
                    </ul>
                </li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            # Mostra un esempio
            st.subheader("Esempio di Risultati")
            
            st.markdown("""
            <div class="cv-card">
                <div class="candidate-header">
                    <div class="candidate-avatar" style="background-color: #4CAF50;">MR</div>
                    <div>
                        <div class="candidate-name">Mario Rossi</div>
                        <div class="candidate-position">Digital Marketing Specialist</div>
                    </div>
                </div>
                <div style="margin-top: 1rem;">
                    <div class="score-bar-container">
                        <div class="score-bar" style="width:85%;background-color:#4CAF50;"></div>
                    </div>
                    <div class="score-label">
                        <span>Ottimo</span>
                        <span>85/100</span>
                    </div>
                </div>
                <div class="candidate-details">
                    <div class="candidate-detail">📚 Master in Digital Marketing</div>
                    <div class="candidate-detail">⏱️ 5 anni</div>
                    <div class="candidate-detail">🏙️ Firenze</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Errore nella visualizzazione dell'esempio: {e}")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #607D8B; padding: 1rem;">
        <p>CV Analyzer Pro • Sviluppato con Streamlit • Powered by AI • 2024</p>
    </div>
    """, unsafe_allow_html=True)

    # Link per scaricare i risultati come Excel
    st.markdown("### Download Risultati")
    
    # Verifica che analysis_results non sia None prima di creare il link
    if ('analysis_results' in st.session_state and 
        st.session_state.analysis_results is not None):
        excel_link = create_download_link(st.session_state.analysis_results, sheet_name='Analisi CV')
        st.markdown(excel_link, unsafe_allow_html=True)
    else:
        st.info("Nessun dato disponibile per il download")

# RIMUOVO QUALSIASI st.xxx QUI, TRA LA DEFINIZIONE DI main() E if __name__...

if __name__ == "__main__":
    main()
    
    # RIMUOVO IL FOOTER DA QUI E LO SPOSTO DENTRO main()
    # LASCIANDO QUESTO BLOCCO VUOTO
