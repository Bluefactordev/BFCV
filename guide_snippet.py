# Codice per la funzione show_current_state migliorata
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
    
    if "current_position" in st.session_state:
        st.sidebar.markdown(f"**💼 Posizione:** {st.session_state.current_position}")
    else:
        st.sidebar.markdown("**💼 Posizione:** Nessuna")
    
    if "cv_dir" in st.session_state and st.session_state.cv_dir:
        st.sidebar.markdown(f"**📄 Cartella CV:** {st.session_state.cv_dir}")
    else:
        st.sidebar.markdown("**📄 Cartella CV:** Non impostata")

# Codice per la guida utente da inserire nella sidebar
def add_user_guide():
    with st.sidebar.expander("📚 Guida all'uso"):
        st.markdown("""
        ### Come usare CV Analyzer
        
        **Ordine consigliato:**
        
        1. **Configura AI**: Scegli il motore di AI da utilizzare
        2. **Seleziona Campi**: Imposta i campi da estrarre dai CV
        3. **Imposta Progetto/Posizione**: Carica o crea un progetto o una posizione
        4. **Carica CV**: Seleziona la cartella contenente i CV da analizzare
        5. **Inserisci Job Description**: Definisci i requisiti della posizione
        6. **Analizza**: Clicca su "Analizza CV" per avviare l'elaborazione
        
        **Gestione dati:**
        - I **Progetti** contengono campi e job description
        - Le **Posizioni** aggiungono anche gestione di più job description e set di campi
        - I **Profili** salvano solo le configurazioni dei campi
        
        **Suggerimento:** Inizia caricando un progetto o una posizione esistente, o creane uno nuovo.
        """) 