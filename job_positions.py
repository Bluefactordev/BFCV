import os
import json
import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime
import shutil

class PositionManager:
    """
    Classe per gestire le posizioni lavorative.
    Ogni posizione può avere una cartella CV, più job descriptions e più set di campi.
    """
    
    def __init__(self, storage_dir: str = "positions"):
        """
        Inizializza il PositionManager.
        
        Args:
            storage_dir: Directory dove salvare le posizioni (relativa alla directory di lavoro)
        """
        self.storage_dir = storage_dir
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self) -> None:
        """Crea la directory di storage se non esiste."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _get_user_positions_dir(self, username: str) -> str:
        """Ottiene il percorso della directory delle posizioni dell'utente."""
        user_dir = os.path.join(self.storage_dir, username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        return user_dir
    
    def _get_user_positions_index_path(self, username: str) -> str:
        """Ottiene il percorso del file indice delle posizioni dell'utente."""
        return os.path.join(self._get_user_positions_dir(username), "positions_index.json")
    
    def _get_position_dir(self, username: str, position_name: str) -> str:
        """Ottiene il percorso della directory di una posizione specifica."""
        position_dir = os.path.join(self._get_user_positions_dir(username), position_name)
        if not os.path.exists(position_dir):
            os.makedirs(position_dir)
        return position_dir
    
    def get_positions(self, username: str) -> Dict[str, Dict[str, Any]]:
        """
        Ottiene tutte le posizioni dell'utente.
        
        Args:
            username: Nome utente
            
        Returns:
            Dizionario con nomi delle posizioni come chiavi e metadati come valori
        """
        index_path = self._get_user_positions_index_path(username)
        if not os.path.exists(index_path):
            return {}
        
        try:
            with open(index_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore durante il caricamento dell'indice delle posizioni: {e}")
            return {}
    
    def create_position(self, position_name: str, description: str, username: str) -> bool:
        """
        Crea una nuova posizione.
        
        Args:
            position_name: Nome della posizione
            description: Descrizione della posizione
            username: Nome utente
            
        Returns:
            True se la creazione è avvenuta con successo, False altrimenti
        """
        # Ottieni le posizioni esistenti
        positions = self.get_positions(username)
        
        # Controlla se la posizione esiste già
        if position_name in positions:
            return False
        
        # Crea la directory della posizione
        position_dir = self._get_position_dir(username, position_name)
        
        # Crea la directory per i CV
        cv_dir = os.path.join(position_dir, "cvs")
        if not os.path.exists(cv_dir):
            os.makedirs(cv_dir)
        
        # Crea la directory per i risultati
        results_dir = os.path.join(position_dir, "results")
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        
        # Crea la directory per le job descriptions
        jd_dir = os.path.join(position_dir, "job_descriptions")
        if not os.path.exists(jd_dir):
            os.makedirs(jd_dir)
        
        # Crea la directory per i field sets
        fields_dir = os.path.join(position_dir, "field_sets")
        if not os.path.exists(fields_dir):
            os.makedirs(fields_dir)
        
        # Salva la configurazione della posizione
        config = {
            "name": position_name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "job_descriptions": [],
            "field_sets": [],
            "current_job_description": "",
            "current_field_set": []
        }
        
        with open(os.path.join(position_dir, "config.json"), 'w') as f:
            json.dump(config, f, indent=2)
        
        # Aggiorna l'indice delle posizioni
        positions[position_name] = {
            "description": description,
            "created_at": config["created_at"],
            "updated_at": config["updated_at"],
            "cv_count": 0,
            "job_description_count": 0,
            "field_set_count": 0
        }
        
        with open(self._get_user_positions_index_path(username), 'w') as f:
            json.dump(positions, f, indent=2)
        
        return True
    
    def delete_position(self, position_name: str, username: str) -> bool:
        """
        Elimina una posizione.
        
        Args:
            position_name: Nome della posizione da eliminare
            username: Nome utente
            
        Returns:
            True se l'eliminazione è avvenuta con successo, False altrimenti
        """
        positions = self.get_positions(username)
        if position_name not in positions:
            return False
        
        # Rimuovi la directory della posizione
        position_dir = self._get_position_dir(username, position_name)
        try:
            shutil.rmtree(position_dir)
        except Exception as e:
            print(f"Errore durante l'eliminazione della directory della posizione: {e}")
            return False
        
        # Aggiorna l'indice delle posizioni
        del positions[position_name]
        with open(self._get_user_positions_index_path(username), 'w') as f:
            json.dump(positions, f, indent=2)
        
        return True
    
    def get_position_config(self, position_name: str, username: str) -> Dict[str, Any]:
        """
        Ottiene la configurazione di una posizione.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            
        Returns:
            Dizionario con la configurazione della posizione
        """
        config_path = os.path.join(self._get_position_dir(username, position_name), "config.json")
        if not os.path.exists(config_path):
            return {}
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore durante il caricamento della configurazione della posizione: {e}")
            return {}
    
    def get_position_cv_dir(self, position_name: str, username: str) -> str:
        """
        Ottiene il percorso della directory dei CV di una posizione.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            
        Returns:
            Percorso della directory dei CV
        """
        return os.path.join(self._get_position_dir(username, position_name), "cvs")
    
    def get_position_results_dir(self, position_name: str, username: str) -> str:
        """
        Ottiene il percorso della directory dei risultati di una posizione.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            
        Returns:
            Percorso della directory dei risultati
        """
        return os.path.join(self._get_position_dir(username, position_name), "results")
    
    def save_job_description(self, position_name: str, username: str, jd_name: str, 
                             jd_content: str) -> bool:
        """
        Salva una job description per una posizione.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            jd_name: Nome della job description
            jd_content: Contenuto della job description
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        config = self.get_position_config(position_name, username)
        if not config:
            return False
        
        # Verifica se la job description esiste già
        jd_exists = False
        for jd in config.get("job_descriptions", []):
            if jd["name"] == jd_name:
                jd["content"] = jd_content
                jd["updated_at"] = datetime.now().isoformat()
                jd_exists = True
                break
        
        # Se non esiste, aggiungila
        if not jd_exists:
            config.setdefault("job_descriptions", []).append({
                "name": jd_name,
                "content": jd_content,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
        
        # Imposta questa job description come corrente
        config["current_job_description"] = jd_name
        
        # Aggiorna il timestamp dell'ultima modifica
        config["updated_at"] = datetime.now().isoformat()
        
        # Salva la configurazione aggiornata
        try:
            with open(os.path.join(self._get_position_dir(username, position_name), "config.json"), 'w') as f:
                json.dump(config, f, indent=2)
            
            # Aggiorna anche il contatore nell'indice
            positions = self.get_positions(username)
            if position_name in positions:
                positions[position_name]["job_description_count"] = len(config.get("job_descriptions", []))
                positions[position_name]["updated_at"] = config["updated_at"]
                with open(self._get_user_positions_index_path(username), 'w') as f:
                    json.dump(positions, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Errore durante il salvataggio della job description: {e}")
            return False
    
    def delete_job_description(self, position_name: str, username: str, jd_name: str) -> bool:
        """
        Elimina una job description da una posizione.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            jd_name: Nome della job description da eliminare
            
        Returns:
            True se l'eliminazione è avvenuta con successo, False altrimenti
        """
        config = self.get_position_config(position_name, username)
        if not config:
            return False
        
        # Cerca la job description da eliminare
        jd_list = config.get("job_descriptions", [])
        for i, jd in enumerate(jd_list):
            if jd["name"] == jd_name:
                # Rimuovi la job description dalla lista
                del jd_list[i]
                
                # Se era quella corrente, imposta a vuoto o alla prima disponibile
                if config.get("current_job_description") == jd_name:
                    config["current_job_description"] = jd_list[0]["name"] if jd_list else ""
                
                # Aggiorna il timestamp dell'ultima modifica
                config["updated_at"] = datetime.now().isoformat()
                
                # Salva la configurazione aggiornata
                try:
                    with open(os.path.join(self._get_position_dir(username, position_name), "config.json"), 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    # Aggiorna anche il contatore nell'indice
                    positions = self.get_positions(username)
                    if position_name in positions:
                        positions[position_name]["job_description_count"] = len(jd_list)
                        positions[position_name]["updated_at"] = config["updated_at"]
                        with open(self._get_user_positions_index_path(username), 'w') as f:
                            json.dump(positions, f, indent=2)
                    
                    return True
                except Exception as e:
                    print(f"Errore durante l'eliminazione della job description: {e}")
                    return False
        
        return False  # Job description non trovata
    
    def save_field_set(self, position_name: str, username: str, field_set_name: str, 
                       fields: List[str]) -> bool:
        """
        Salva un set di campi per una posizione.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            field_set_name: Nome del set di campi
            fields: Lista dei campi nel set
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        config = self.get_position_config(position_name, username)
        if not config:
            return False
        
        # Verifica se il set di campi esiste già
        field_set_exists = False
        for fs in config.get("field_sets", []):
            if fs["name"] == field_set_name:
                fs["fields"] = fields
                fs["updated_at"] = datetime.now().isoformat()
                field_set_exists = True
                break
        
        # Se non esiste, aggiungilo
        if not field_set_exists:
            config.setdefault("field_sets", []).append({
                "name": field_set_name,
                "fields": fields,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
        
        # Imposta questo set di campi come corrente
        config["current_field_set"] = field_set_name
        
        # Aggiorna il timestamp dell'ultima modifica
        config["updated_at"] = datetime.now().isoformat()
        
        # Salva la configurazione aggiornata
        try:
            with open(os.path.join(self._get_position_dir(username, position_name), "config.json"), 'w') as f:
                json.dump(config, f, indent=2)
            
            # Aggiorna anche il contatore nell'indice
            positions = self.get_positions(username)
            if position_name in positions:
                positions[position_name]["field_set_count"] = len(config.get("field_sets", []))
                positions[position_name]["updated_at"] = config["updated_at"]
                with open(self._get_user_positions_index_path(username), 'w') as f:
                    json.dump(positions, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Errore durante il salvataggio del set di campi: {e}")
            return False
    
    def delete_field_set(self, position_name: str, username: str, field_set_name: str) -> bool:
        """
        Elimina un set di campi da una posizione.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            field_set_name: Nome del set di campi da eliminare
            
        Returns:
            True se l'eliminazione è avvenuta con successo, False altrimenti
        """
        config = self.get_position_config(position_name, username)
        if not config:
            return False
        
        # Cerca il set di campi da eliminare
        field_sets = config.get("field_sets", [])
        for i, fs in enumerate(field_sets):
            if fs["name"] == field_set_name:
                # Rimuovi il set di campi dalla lista
                del field_sets[i]
                
                # Se era quello corrente, imposta a vuoto o al primo disponibile
                if config.get("current_field_set") == field_set_name:
                    config["current_field_set"] = field_sets[0]["name"] if field_sets else ""
                
                # Aggiorna il timestamp dell'ultima modifica
                config["updated_at"] = datetime.now().isoformat()
                
                # Salva la configurazione aggiornata
                try:
                    with open(os.path.join(self._get_position_dir(username, position_name), "config.json"), 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    # Aggiorna anche il contatore nell'indice
                    positions = self.get_positions(username)
                    if position_name in positions:
                        positions[position_name]["field_set_count"] = len(field_sets)
                        positions[position_name]["updated_at"] = config["updated_at"]
                        with open(self._get_user_positions_index_path(username), 'w') as f:
                            json.dump(positions, f, indent=2)
                    
                    return True
                except Exception as e:
                    print(f"Errore durante l'eliminazione del set di campi: {e}")
                    return False
        
        return False  # Set di campi non trovato
    
    def get_job_description(self, position_name: str, username: str, jd_name: str = None) -> Optional[str]:
        """
        Ottiene il contenuto di una job description.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            jd_name: Nome della job description (se None, usa quella corrente)
            
        Returns:
            Contenuto della job description o None se non trovata
        """
        config = self.get_position_config(position_name, username)
        if not config:
            return None
        
        # Se non è specificato un nome, usa quello corrente
        if jd_name is None:
            jd_name = config.get("current_job_description", "")
            if not jd_name:
                return None
        
        # Cerca la job description
        for jd in config.get("job_descriptions", []):
            if jd["name"] == jd_name:
                return jd["content"]
        
        return None
    
    def get_field_set(self, position_name: str, username: str, field_set_name: str = None) -> Optional[List[str]]:
        """
        Ottiene i campi di un set.
        
        Args:
            position_name: Nome della posizione
            username: Nome utente
            field_set_name: Nome del set di campi (se None, usa quello corrente)
            
        Returns:
            Lista dei campi o None se non trovata
        """
        config = self.get_position_config(position_name, username)
        if not config:
            return None
        
        # Se non è specificato un nome, usa quello corrente
        if field_set_name is None:
            field_set_name = config.get("current_field_set", "")
            if not field_set_name:
                return None
        
        # Cerca il set di campi
        for fs in config.get("field_sets", []):
            if fs["name"] == field_set_name:
                return fs["fields"]
        
        return None
    
    def render_positions_ui(self, username: str, cv_fields: List[str]):
        """
        Renderizza l'interfaccia utente per la gestione delle posizioni.
        
        Args:
            username: Nome utente
            cv_fields: Lista completa di tutti i campi possibili
            
        Returns:
            Dict con la posizione corrente e le relative configurazioni
        """
        # Per evitare conflitti nelle chiamate multiple, aggiungiamo un contesto 'ui'
        username_with_ctx = f"{username}_ui"
        return self._render_positions_ui_with_context(username, cv_fields, username_with_ctx)
    
    def render_sidebar(self):
        """
        Alias per render_positions_ui per compatibilità.
        Utilizza l'username e i campi dalla sessione.
        
        Returns:
            Risultato di render_positions_ui()
        """
        if 'fields' not in st.session_state or 'username' not in st.session_state:
            st.warning("Sessione non inizializzata correttamente.")
            return {}
        
        # Creiamo un contesto unico per questa chiamata alla sidebar
        if 'position_sidebar_ctx' not in st.session_state:
            st.session_state.position_sidebar_ctx = "sb"
            
        # Appendiamo il contesto all'username per rendere le chiavi uniche
        username_with_ctx = f"{st.session_state.username}_{st.session_state.position_sidebar_ctx}"
            
        return self._render_positions_ui_with_context(st.session_state.username, st.session_state.fields, username_with_ctx)
    
    def _render_positions_ui_with_context(self, username: str, cv_fields: List[str], username_with_ctx: str):
        """
        Versione interna di render_positions_ui che accetta un username con contesto.
        Questo metodo è usato per evitare conflitti di chiavi.
        
        Args:
            username: Nome utente
            cv_fields: Lista completa di tutti i campi possibili
            username_with_ctx: Nome utente con contesto aggiuntivo per chiavi uniche
            
        Returns:
            Dict con la posizione corrente e le relative configurazioni
        """
        st.sidebar.subheader("Posizioni lavorative")
        
        # Ottieni le posizioni esistenti
        positions = self.get_positions(username)
        position_names = list(positions.keys())
        
        # Variabili per memorizzare i risultati
        result = {
            "position_name": None,
            "cv_dir": None,
            "job_description": None,
            "fields": None,
            "position_loaded": False
        }
        
        # Selezione della posizione
        if position_names:
            selected_position = st.sidebar.selectbox(
                "Seleziona una posizione",
                options=["Nessuna posizione"] + position_names,
                key=f"position_select_{username_with_ctx}"
            )
            
            if selected_position != "Nessuna posizione":
                # Mostra i dettagli della posizione
                config = self.get_position_config(selected_position, username)
                if config:
                    st.sidebar.markdown(f"**Descrizione**: {config.get('description', 'Nessuna descrizione')}")
                    st.sidebar.markdown(f"**CV**: {positions[selected_position].get('cv_count', 0)}")
                    st.sidebar.markdown(f"**Job Descriptions**: {positions[selected_position].get('job_description_count', 0)}")
                    st.sidebar.markdown(f"**Field Sets**: {positions[selected_position].get('field_set_count', 0)}")
                
                # Carica la posizione selezionata
                if st.sidebar.button("Carica posizione", key=f"load_position_{username_with_ctx}"):
                    # Imposta la directory dei CV
                    cv_dir = self.get_position_cv_dir(selected_position, username)
                    
                    # Carica la job description corrente
                    jd_name = config.get("current_job_description", "")
                    job_description = self.get_job_description(selected_position, username, jd_name)
                    
                    # Carica il set di campi corrente
                    field_set_name = config.get("current_field_set", "")
                    fields = self.get_field_set(selected_position, username, field_set_name)
                    
                    # Se non ci sono campi selezionati, usa quelli di default
                    if not fields:
                        fields = cv_fields
                    
                    # Aggiorna la session_state
                    st.session_state.cv_dir = cv_dir
                    
                    if job_description:
                        st.session_state.job_description = job_description
                    
                    if fields:
                        st.session_state.fields = fields
                    
                    # Memorizza la posizione corrente
                    st.session_state.current_position = selected_position
                    
                    # Prepara il risultato
                    result = {
                        "position_name": selected_position,
                        "cv_dir": cv_dir,
                        "job_description": job_description,
                        "fields": fields,
                        "position_loaded": True
                    }
                    
                    st.sidebar.success(f"Posizione '{selected_position}' caricata con successo!")
                    st.rerun()
                
                # Aggiungo pulsante per salvare lo stato corrente come aggiornamento della posizione
                if st.sidebar.button("Aggiorna posizione", key=f"update_position_{username_with_ctx}"):
                    # Ottieni i dati correnti
                    job_description = st.session_state.get("job_description", "")
                    fields = st.session_state.get("fields", [])
                    
                    # Salva la job description come corrente
                    jd_name = f"job_desc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    if job_description and self.save_job_description(selected_position, username, jd_name, job_description):
                        # Salva il field set come corrente
                        fs_name = f"fields_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        if fields and self.save_field_set(selected_position, username, fs_name, fields):
                            # Aggiorna la configurazione della posizione
                            config = self.get_position_config(selected_position, username)
                            config["current_job_description"] = jd_name
                            config["current_field_set"] = fs_name
                            config["updated_at"] = datetime.now().isoformat()
                            
                            # Salva la configurazione aggiornata
                            try:
                                with open(os.path.join(self._get_position_dir(username, selected_position), "config.json"), 'w') as f:
                                    json.dump(config, f, indent=2)
                                st.sidebar.success(f"Posizione '{selected_position}' aggiornata con successo!")
                            except Exception as e:
                                st.sidebar.error(f"Errore durante l'aggiornamento della posizione: {e}")
                        else:
                            st.sidebar.error("Errore durante il salvataggio del Field Set.")
                    else:
                        st.sidebar.error("Errore durante il salvataggio della Job Description.")
                
                # Gestione delle job descriptions
                with st.sidebar.expander("Gestisci Job Descriptions"):
                    # Lista delle job descriptions disponibili
                    jd_names = [jd["name"] for jd in config.get("job_descriptions", [])]
                    if jd_names:
                        selected_jd = st.selectbox("Seleziona Job Description", options=jd_names, key=f"jd_select_{username_with_ctx}")
                        if st.button("Carica Job Description", key=f"load_jd_button_{username_with_ctx}"):
                            job_description = self.get_job_description(selected_position, username, selected_jd)
                            if job_description:
                                st.session_state.job_description = job_description
                                st.success(f"Job Description '{selected_jd}' caricata!")
                        
                        if st.button("Elimina Job Description", key=f"delete_jd_button_{username_with_ctx}"):
                            if self.delete_job_description(selected_position, username, selected_jd):
                                st.success(f"Job Description '{selected_jd}' eliminata!")
                            else:
                                st.error("Errore durante l'eliminazione della Job Description.")
                    
                    # Salvataggio di una nuova job description
                    new_jd_name = st.text_input("Nome della Job Description", key=f"new_jd_name_{username_with_ctx}")
                    if st.button("Salva Job Description corrente", key=f"save_jd_button_{username_with_ctx}") and new_jd_name:
                        job_description = st.session_state.get("job_description", "")
                        if job_description:
                            if self.save_job_description(selected_position, username, new_jd_name, job_description):
                                st.success(f"Job Description '{new_jd_name}' salvata!")
                            else:
                                st.error("Errore durante il salvataggio della Job Description.")
                        else:
                            st.warning("Nessuna Job Description da salvare.")
                
                # Gestione dei field sets
                with st.sidebar.expander("Gestisci Field Sets"):
                    # Lista dei field sets disponibili
                    fs_names = [fs["name"] for fs in config.get("field_sets", [])]
                    if fs_names:
                        selected_fs = st.selectbox("Seleziona Field Set", options=fs_names, key=f"fs_select_{username_with_ctx}")
                        if st.button("Carica Field Set", key=f"load_fs_button_{username_with_ctx}"):
                            fields = self.get_field_set(selected_position, username, selected_fs)
                            if fields:
                                st.session_state.fields = fields
                                st.success(f"Field Set '{selected_fs}' caricato!")
                        
                        if st.button("Elimina Field Set", key=f"delete_fs_button_{username_with_ctx}"):
                            if self.delete_field_set(selected_position, username, selected_fs):
                                st.success(f"Field Set '{selected_fs}' eliminato!")
                            else:
                                st.error("Errore durante l'eliminazione del Field Set.")
                    
                    # Salvataggio di un nuovo field set
                    new_fs_name = st.text_input("Nome del Field Set", key=f"new_fs_name_{username_with_ctx}")
                    if st.button("Salva Field Set corrente", key=f"save_fs_button_{username_with_ctx}") and new_fs_name:
                        fields = st.session_state.get("fields", [])
                        if fields:
                            if self.save_field_set(selected_position, username, new_fs_name, fields):
                                st.success(f"Field Set '{new_fs_name}' salvato!")
                            else:
                                st.error("Errore durante il salvataggio del Field Set.")
                        else:
                            st.warning("Nessun Field Set da salvare.")
                
                # Aggiornamento CV
                if st.sidebar.button("Aggiorna conteggio CV", key=f"update_cv_count_button_{username_with_ctx}"):
                    try:
                        cv_dir = self.get_position_cv_dir(selected_position, username)
                        cv_count = len([f for f in os.listdir(cv_dir) if f.lower().endswith('.pdf')])
                        
                        # Aggiorna il contatore nell'indice
                        positions = self.get_positions(username)
                        if selected_position in positions:
                            positions[selected_position]["cv_count"] = cv_count
                            with open(self._get_user_positions_index_path(username), 'w') as f:
                                json.dump(positions, f, indent=2)
                            
                            st.sidebar.success(f"Conteggio CV aggiornato: {cv_count}")
                    except Exception as e:
                        st.sidebar.error(f"Errore durante l'aggiornamento del conteggio CV: {e}")
                
                # Elimina la posizione
                if st.sidebar.button("Elimina posizione", key=f"delete_position_button_{username_with_ctx}"):
                    if self.delete_position(selected_position, username):
                        # Resetta le variabili di sessione
                        if "current_position" in st.session_state:
                            del st.session_state.current_position
                        
                        st.sidebar.success(f"Posizione '{selected_position}' eliminata!")
                        st.rerun()
                    else:
                        st.sidebar.error("Errore durante l'eliminazione della posizione.")
        
        # Creazione di una nuova posizione
        st.sidebar.subheader("Crea/Salva posizione")
        
        # Precompila con la posizione corrente se disponibile
        default_position_name = ""
        if "current_position" in st.session_state:
            default_position_name = st.session_state.current_position
            
        new_position_name = st.sidebar.text_input(
            "Nome della posizione", 
            value=default_position_name,
            key=f"new_position_name_{username_with_ctx}"
        )
        new_position_description = st.sidebar.text_area("Descrizione (opzionale)", key=f"new_position_description_{username_with_ctx}", height=100)
        
        if st.sidebar.button("Salva posizione corrente", key=f"save_current_position_{username_with_ctx}"):
            if not new_position_name:
                st.sidebar.error("Inserisci un nome per la posizione.")
            else:
                # Verifica se la posizione esiste già
                if new_position_name in position_names:
                    if st.sidebar.button(f"Conferma sovrascrittura di '{new_position_name}'", key=f"confirm_overwrite_position_{username_with_ctx}"):
                        # Aggiorna la posizione esistente
                        job_description = st.session_state.get("job_description", "")
                        fields = st.session_state.get("fields", [])
                        
                        # Salva la job description come corrente
                        jd_name = f"job_desc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        if job_description and self.save_job_description(new_position_name, username, jd_name, job_description):
                            # Salva il field set come corrente
                            fs_name = f"fields_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            if fields and self.save_field_set(new_position_name, username, fs_name, fields):
                                # Aggiorna la configurazione della posizione
                                config = self.get_position_config(new_position_name, username)
                                config["current_job_description"] = jd_name
                                config["current_field_set"] = fs_name
                                config["description"] = new_position_description
                                config["updated_at"] = datetime.now().isoformat()
                                
                                # Salva la configurazione aggiornata
                                try:
                                    with open(os.path.join(self._get_position_dir(username, new_position_name), "config.json"), 'w') as f:
                                        json.dump(config, f, indent=2)
                                    st.sidebar.success(f"Posizione '{new_position_name}' aggiornata con successo!")
                                    st.session_state.current_position = new_position_name
                                    st.rerun()
                                except Exception as e:
                                    st.sidebar.error(f"Errore durante l'aggiornamento della posizione: {e}")
                            else:
                                st.sidebar.error("Errore durante il salvataggio del Field Set.")
                        else:
                            st.sidebar.error("Errore durante il salvataggio della Job Description.")
                else:
                    # Crea una nuova posizione
                    if self.create_position(new_position_name, new_position_description, username):
                        # Salva la job description
                        job_description = st.session_state.get("job_description", "")
                        if job_description:
                            jd_name = f"job_desc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            self.save_job_description(new_position_name, username, jd_name, job_description)
                            
                            # Aggiorna la configurazione per usare questa job description
                            config = self.get_position_config(new_position_name, username)
                            config["current_job_description"] = jd_name
                        
                        # Salva il field set
                        fields = st.session_state.get("fields", [])
                        if fields:
                            fs_name = f"fields_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            self.save_field_set(new_position_name, username, fs_name, fields)
                            
                            # Aggiorna la configurazione per usare questo field set
                            if "config" not in locals():
                                config = self.get_position_config(new_position_name, username)
                            config["current_field_set"] = fs_name
                        
                        # Salva la configurazione aggiornata se necessario
                        if "config" in locals():
                            try:
                                with open(os.path.join(self._get_position_dir(username, new_position_name), "config.json"), 'w') as f:
                                    json.dump(config, f, indent=2)
                            except Exception as e:
                                st.sidebar.error(f"Errore durante l'aggiornamento della configurazione: {e}")
                        
                        st.sidebar.success(f"Posizione '{new_position_name}' creata con successo!")
                        st.session_state.current_position = new_position_name
                        st.rerun()
                    else:
                        st.sidebar.error(f"Errore durante la creazione della posizione '{new_position_name}'")
        
        return result 