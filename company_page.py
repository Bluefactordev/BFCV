import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, List, Any, Optional
from company_analyzer import CompanyManager, Company

def render_company_page():
    """Renderizza la pagina per la gestione delle aziende."""
    
    st.title("Gestione Aziende")
    st.subheader("Analisi e monitoraggio aziende")
    
    # Inizializza o ottieni il CompanyManager dalla session state
    if "company_manager" not in st.session_state:
        st.session_state.company_manager = CompanyManager()
    
    # Ottieni i dati dell'azienda cliente
    if "client_company_data" not in st.session_state:
        st.session_state.client_company_data = {
            "name": "Azienda Cliente",
            "industry": "digital marketing, software, consulenza",
            "target_clients": "retail, finance, technology"
        }
    
    company_manager = st.session_state.company_manager
    
    # Crea tab per organizzare l'interfaccia
    tabs = st.tabs(["📊 Panoramica", "➕ Aggiungi Azienda", "🔍 Cerca Azienda", "⚙️ Impostazioni"])
    
    # Tab 1: Panoramica
    with tabs[0]:
        st.subheader("Panoramica delle Aziende")
        
        # Carica tutte le aziende
        companies = company_manager.get_all_companies()
        
        if not companies:
            st.info("Nessuna azienda nel database. Usa la scheda 'Aggiungi Azienda' per iniziare.")
        else:
            # Mostra statistiche
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Totale Aziende", len(companies))
            
            with col2:
                competitors = [c for c in companies if c.competitor_level in ["superiore", "pari", "inferiore"]]
                st.metric("Concorrenti", len(competitors))
            
            with col3:
                potential_clients = [c for c in companies if c.potential_client]
                st.metric("Potenziali Clienti", len(potential_clients))
            
            # Crea DataFrame per visualizzazione
            companies_data = []
            for company in companies:
                company_dict = company.to_dict()
                # Converti potenziale cliente in testo
                if company.potential_client is not None:
                    company_dict["potential_client"] = "Sì" if company.potential_client else "No"
                else:
                    company_dict["potential_client"] = "Non valutato"
                companies_data.append(company_dict)
            
            df = pd.DataFrame(companies_data)
            
            # Aggiungi filtri
            with st.expander("Filtri", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    industry_filter = st.multiselect(
                        "Filtra per Settore",
                        options=sorted(list(set([c.industry for c in companies if c.industry])))
                    )
                
                with col2:
                    competitor_filter = st.multiselect(
                        "Filtra per Livello Competitore",
                        options=["superiore", "pari", "inferiore", "non concorrente"]
                    )
                
                client_filter = st.checkbox("Mostra solo potenziali clienti")
                
                # Applica filtri
                filtered_df = df.copy()
                if industry_filter:
                    filtered_df = filtered_df[filtered_df["industry"].isin(industry_filter)]
                if competitor_filter:
                    filtered_df = filtered_df[filtered_df["competitor_level"].isin(competitor_filter)]
                if client_filter:
                    filtered_df = filtered_df[filtered_df["potential_client"] == "Sì"]
            
            # Visualizza i dati
            if "filtered_df" in locals() and not filtered_df.empty:
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
            
            # Visualizzazioni
            st.subheader("Analisi delle Aziende")
            
            # Analisi per settore
            if "industry" in df.columns:
                # Espandi l'industria (potrebbe essere una stringa con più settori separati da virgole)
                all_industries = []
                for ind in df["industry"].dropna():
                    if ind:
                        all_industries.extend([i.strip() for i in str(ind).split(",")])
                
                # Conta le occorrenze
                industry_counts = pd.Series(all_industries).value_counts().reset_index()
                industry_counts.columns = ["Settore", "Conteggio"]
                
                if not industry_counts.empty:
                    # Crea il grafico
                    fig = px.bar(
                        industry_counts, 
                        x="Settore", 
                        y="Conteggio",
                        title="Aziende per Settore",
                        color="Conteggio",
                        color_continuous_scale=px.colors.sequential.Blues
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            # Analisi per livello di concorrenza
            if "competitor_level" in df.columns:
                comp_counts = df["competitor_level"].value_counts().reset_index()
                comp_counts.columns = ["Livello", "Conteggio"]
                
                if not comp_counts.empty:
                    fig = px.pie(
                        comp_counts,
                        values="Conteggio",
                        names="Livello",
                        title="Distribuzione per Livello di Concorrenza",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: Aggiungi Azienda
    with tabs[1]:
        st.subheader("Aggiungi Nuova Azienda")
        
        with st.form("add_company_form"):
            name = st.text_input("Nome Azienda *", help="Nome completo dell'azienda")
            
            col1, col2 = st.columns(2)
            with col1:
                website = st.text_input("Sito Web", help="URL completo del sito web aziendale")
                industry = st.text_input("Settore", help="Settore principale dell'azienda (es. tecnologia, finanza)")
                location = st.text_input("Sede", help="Sede principale dell'azienda")
            
            with col2:
                size = st.selectbox(
                    "Dimensione", 
                    options=["", "Piccola", "Media", "Grande"],
                    help="Dimensione approssimativa dell'azienda"
                )
                founded_year = st.number_input(
                    "Anno di Fondazione", 
                    min_value=1800, 
                    max_value=2100, 
                    value=2000,
                    help="Anno in cui l'azienda è stata fondata"
                )
                
                competitor_level = st.selectbox(
                    "Livello di Concorrenza",
                    options=["", "superiore", "pari", "inferiore", "non concorrente"],
                    help="Livello di concorrenza rispetto alla tua azienda"
                )
            
            potential_client = st.checkbox(
                "Potenziale Cliente", 
                help="Seleziona se questa azienda potrebbe essere un potenziale cliente"
            )
            
            description = st.text_area(
                "Descrizione", 
                height=100, 
                help="Breve descrizione dell'azienda e della sua attività"
            )
            
            notes = st.text_area(
                "Note", 
                height=100, 
                help="Note interne o commenti sull'azienda"
            )
            
            submit = st.form_submit_button("Salva Azienda")
            
            if submit:
                if not name:
                    st.error("Il nome dell'azienda è obbligatorio")
                else:
                    # Crea l'oggetto Company
                    company = Company(
                        name=name,
                        website=website if website else None,
                        description=description if description else None,
                        industry=industry if industry else None,
                        size=size if size else None,
                        location=location if location else None,
                        founded_year=founded_year,
                        competitor_level=competitor_level if competitor_level else None,
                        potential_client=potential_client,
                        notes=notes if notes else None,
                        search_source="manuale",
                        last_updated=None  # Verrà impostato da add_or_update_company
                    )
                    
                    # Aggiungi l'azienda
                    company_manager.add_or_update_company(company)
                    st.success(f"Azienda '{name}' aggiunta con successo!")
    
    # Tab 3: Cerca Azienda
    with tabs[2]:
        st.subheader("Cerca e Modifica Azienda")
        
        # Carica tutte le aziende
        companies = company_manager.get_all_companies()
        
        if not companies:
            st.info("Nessuna azienda nel database. Usa la scheda 'Aggiungi Azienda' per iniziare.")
        else:
            # Campo di ricerca
            search_term = st.text_input("Cerca Azienda", help="Filtra per nome o settore")
            
            if search_term:
                # Filtra le aziende in base al termine di ricerca
                filtered_companies = [
                    c for c in companies
                    if search_term.lower() in c.name.lower() or
                       (c.industry and search_term.lower() in c.industry.lower()) or
                       (c.description and search_term.lower() in c.description.lower())
                ]
                
                if not filtered_companies:
                    st.info(f"Nessuna azienda trovata per '{search_term}'")
                else:
                    st.write(f"Trovate {len(filtered_companies)} aziende")
                    
                    # Menu a tendina per selezionare l'azienda
                    selected_company_name = st.selectbox(
                        "Seleziona Azienda",
                        options=[c.name for c in filtered_companies]
                    )
                    
                    # Ottieni l'azienda selezionata
                    selected_company = next((c for c in filtered_companies if c.name == selected_company_name), None)
                    
                    if selected_company:
                        # Mostra i dettagli dell'azienda
                        with st.expander("Dettagli Azienda", expanded=True):
                            st.markdown(f"### {selected_company.name}")
                            
                            if selected_company.website:
                                st.markdown(f"🌐 [Sito Web]({selected_company.website})")
                            
                            if selected_company.description:
                                st.markdown(f"**Descrizione:** {selected_company.description}")
                            
                            # Organizza le informazioni in colonne
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if selected_company.industry:
                                    st.markdown(f"**Settore:** {selected_company.industry}")
                                if selected_company.size:
                                    st.markdown(f"**Dimensione:** {selected_company.size}")
                                if selected_company.location:
                                    st.markdown(f"**Sede:** {selected_company.location}")
                            
                            with col2:
                                if selected_company.founded_year:
                                    st.markdown(f"**Anno di fondazione:** {selected_company.founded_year}")
                                if selected_company.competitor_level:
                                    st.markdown(f"**Livello di concorrenza:** {selected_company.competitor_level}")
                                if selected_company.potential_client is not None:
                                    client_status = "Sì" if selected_company.potential_client else "No"
                                    st.markdown(f"**Potenziale cliente:** {client_status}")
                            
                            if selected_company.notes:
                                st.markdown("**Note:**")
                                st.text_area("", value=selected_company.notes, height=100, disabled=True)
                            
                            if selected_company.last_updated:
                                st.markdown(f"*Ultimo aggiornamento: {selected_company.last_updated}*")
                        
                        # Form per modificare l'azienda
                        with st.expander("Modifica Azienda", expanded=False):
                            with st.form("edit_company_form"):
                                # Ripeti i campi di input come nella scheda "Aggiungi Azienda"
                                # ma con i valori precompilati
                                name = st.text_input("Nome Azienda *", value=selected_company.name)
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    website = st.text_input("Sito Web", value=selected_company.website or "")
                                    industry = st.text_input("Settore", value=selected_company.industry or "")
                                    location = st.text_input("Sede", value=selected_company.location or "")
                                
                                with col2:
                                    size_options = ["", "Piccola", "Media", "Grande"]
                                    size_index = size_options.index(selected_company.size) if selected_company.size in size_options else 0
                                    size = st.selectbox("Dimensione", options=size_options, index=size_index)
                                    
                                    founded_year = st.number_input(
                                        "Anno di Fondazione", 
                                        min_value=1800, 
                                        max_value=2100, 
                                        value=selected_company.founded_year or 2000
                                    )
                                    
                                    comp_options = ["", "superiore", "pari", "inferiore", "non concorrente"]
                                    comp_index = comp_options.index(selected_company.competitor_level) if selected_company.competitor_level in comp_options else 0
                                    competitor_level = st.selectbox("Livello di Concorrenza", options=comp_options, index=comp_index)
                                
                                potential_client = st.checkbox(
                                    "Potenziale Cliente", 
                                    value=selected_company.potential_client or False
                                )
                                
                                description = st.text_area(
                                    "Descrizione", 
                                    value=selected_company.description or "",
                                    height=100
                                )
                                
                                notes = st.text_area(
                                    "Note", 
                                    value=selected_company.notes or "",
                                    height=100
                                )
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    submit = st.form_submit_button("Aggiorna Azienda")
                                with col2:
                                    delete = st.form_submit_button("Elimina Azienda", type="primary")
                                
                                if submit:
                                    if not name:
                                        st.error("Il nome dell'azienda è obbligatorio")
                                    else:
                                        # Aggiorna l'oggetto Company
                                        updated_company = Company(
                                            name=name,
                                            website=website if website else None,
                                            description=description if description else None,
                                            industry=industry if industry else None,
                                            size=size if size else None,
                                            location=location if location else None,
                                            founded_year=founded_year,
                                            competitor_level=competitor_level if competitor_level else None,
                                            potential_client=potential_client,
                                            notes=notes if notes else None,
                                            search_source=selected_company.search_source,
                                            last_updated=None  # Verrà impostato da add_or_update_company
                                        )
                                        
                                        # Aggiungi l'azienda
                                        company_manager.add_or_update_company(updated_company)
                                        st.success(f"Azienda '{name}' aggiornata con successo!")
                                        st.rerun()
                                
                                if delete:
                                    # Elimina l'azienda
                                    if company_manager.delete_company(selected_company.name):
                                        st.success(f"Azienda '{selected_company.name}' eliminata con successo!")
                                        st.rerun()
                                    else:
                                        st.error(f"Errore nell'eliminazione dell'azienda '{selected_company.name}'")
            else:
                # Senza un termine di ricerca, mostra tutte le aziende in una tabella
                companies_data = []
                for company in companies:
                    company_dict = company.to_dict()
                    # Converti potenziale cliente in testo per visualizzazione
                    if company.potential_client is not None:
                        company_dict["potential_client"] = "Sì" if company.potential_client else "No"
                    else:
                        company_dict["potential_client"] = "Non valutato"
                    companies_data.append(company_dict)
                
                df = pd.DataFrame(companies_data)
                st.dataframe(df, use_container_width=True)
    
    # Tab 4: Impostazioni
    with tabs[3]:
        st.subheader("Impostazioni Azienda Cliente")
        
        with st.form("client_company_settings"):
            # Campi per le impostazioni dell'azienda cliente
            client_name = st.text_input(
                "Nome dell'Azienda Cliente", 
                value=st.session_state.client_company_data.get("name", ""),
                help="Il nome della tua azienda"
            )
            
            client_industry = st.text_input(
                "Settori dell'Azienda Cliente", 
                value=st.session_state.client_company_data.get("industry", ""),
                help="I settori in cui opera la tua azienda, separati da virgole"
            )
            
            client_target = st.text_input(
                "Settori Target", 
                value=st.session_state.client_company_data.get("target_clients", ""),
                help="I settori dei clienti target della tua azienda, separati da virgole"
            )
            
            submit = st.form_submit_button("Salva Impostazioni")
            
            if submit:
                st.session_state.client_company_data = {
                    "name": client_name,
                    "industry": client_industry,
                    "target_clients": client_target
                }
                st.success("Impostazioni salvate con successo!")

def process_companies_in_cv(extraction_result: Dict[str, Any], cv_text: str) -> List[Dict[str, Any]]:
    """
    Processa le aziende menzionate in un CV.
    
    Args:
        extraction_result: Risultato dell'estrazione del CV
        cv_text: Testo completo del CV
        
    Returns:
        Lista delle informazioni sulle aziende processate
    """
    # Inizializza o ottieni il CompanyManager
    if "company_manager" not in st.session_state:
        st.session_state.company_manager = CompanyManager()
    
    company_manager = st.session_state.company_manager
    
    # Estrai le aziende dal CV
    companies = company_manager.extract_companies_from_cv(cv_text, extraction_result)
    
    if not companies:
        return []
    
    # Ottieni i dati dell'azienda cliente
    client_company_data = st.session_state.get("client_company_data", {})
    
    # Processa le aziende
    processed_companies = company_manager.process_companies_from_cv(companies, client_company_data)
    
    # Converti in dizionari per il risultato
    return [company.to_dict() for company in processed_companies]
