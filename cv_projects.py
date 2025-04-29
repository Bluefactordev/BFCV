import os
import json
import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime
import shutil

class ProjectManager:
    """
    Classe per gestire i progetti di analisi CV.
    Un progetto contiene un elenco di CV, un profilo di campi e una descrizione del lavoro.
    """
    
    def __init__(self, storage_dir: str = "projects"):
        """
        Inizializza il ProjectManager.
        
        Args:
            storage_dir: Directory dove salvare i progetti (relativa alla directory di lavoro)
        """
        self.storage_dir = storage_dir
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self) -> None:
        """Crea la directory di storage se non esiste."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _get_user_projects_dir(self, username: str) -> str:
        """Ottiene il percorso della directory dei progetti dell'utente."""
        user_dir = os.path.join(self.storage_dir, username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        return user_dir
    
    def _get_user_projects_index_path(self, username: str) -> str:
        """Ottiene il percorso del file indice dei progetti dell'utente."""
        return os.path.join(self._get_user_projects_dir(username), "projects_index.json")
    
    def _get_project_dir(self, username: str, project_name: str) -> str:
        """Ottiene il percorso della directory di un progetto specifico."""
        project_dir = os.path.join(self._get_user_projects_dir(username), project_name)
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
        return project_dir
    
    def get_projects(self, username: str) -> Dict[str, Dict[str, Any]]:
        """
        Ottiene tutti i progetti dell'utente.
        
        Args:
            username: Nome utente
            
        Returns:
            Dizionario con nomi dei progetti come chiavi e metadati come valori
        """
        index_path = self._get_user_projects_index_path(username)
        if not os.path.exists(index_path):
            return {}
        
        try:
            with open(index_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore durante il caricamento dell'indice dei progetti: {e}")
            return {}
    
    def create_project(self, project_name: str, description: str, username: str, fields: List[str], 
                      job_description: str, criteria_weights: Optional[Dict[str, int]] = None,
                      evaluation_criteria: Optional[List[tuple]] = None, cv_dir: Optional[str] = None,
                      llm_model: Optional[str] = None, use_ollama: Optional[bool] = None,
                      ollama_model: Optional[str] = None, api_key: Optional[str] = None,
                      use_cache: Optional[bool] = None) -> bool:
        """
        Crea un nuovo progetto.
        
        Args:
            project_name: Nome del progetto
            description: Descrizione del progetto
            username: Nome utente
            fields: Lista dei campi da analizzare
            job_description: Descrizione del lavoro
            criteria_weights: Pesi dei criteri di valutazione (opzionale)
            evaluation_criteria: Criteri di valutazione (opzionale)
            cv_dir: Directory dei CV (opzionale)
            llm_model: Modello LLM da utilizzare (opzionale)
            use_ollama: Flag per indicare se usare Ollama (opzionale)
            ollama_model: Modello Ollama da utilizzare (opzionale)
            api_key: API key per OpenAI (opzionale)
            use_cache: Flag per indicare se usare la cache (opzionale)
            
        Returns:
            True se la creazione è avvenuta con successo, False altrimenti
        """
        # Ottieni i progetti esistenti
        projects = self.get_projects(username)
        
        # Controlla se il progetto esiste già
        if project_name in projects:
            return False
        
        # Crea la directory del progetto
        project_dir = self._get_project_dir(username, project_name)
        
        # Crea la directory per i CV se non è specificata
        if cv_dir is None:
            cv_dir = os.path.join(project_dir, "cvs")
            if not os.path.exists(cv_dir):
                os.makedirs(cv_dir)
        
        # Crea la directory per i risultati
        results_dir = os.path.join(project_dir, "results")
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        
        # Salva la configurazione del progetto
        config = {
            "name": project_name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "fields": fields,
            "job_description": job_description,
            "cv_dir": cv_dir  # Salva sempre il percorso della directory CV
        }
        
        # Aggiungi i nuovi parametri solo se forniti
        if criteria_weights is not None:
            config["criteria_weights"] = criteria_weights
        
        if evaluation_criteria is not None:
            # Converti lista di tuple in lista di liste per JSON
            config["evaluation_criteria"] = [list(item) for item in evaluation_criteria]
        
        if llm_model is not None:
            config["llm_model"] = llm_model
            
        if use_ollama is not None:
            config["use_ollama"] = use_ollama
            
        if ollama_model is not None:
            config["ollama_model"] = ollama_model
            
        if api_key is not None:
            config["api_key"] = api_key
            
        if use_cache is not None:
            config["use_cache"] = use_cache
        
        with open(os.path.join(project_dir, "config.json"), 'w') as f:
            json.dump(config, f, indent=2)
        
        # Aggiorna l'indice dei progetti
        projects[project_name] = {
            "description": description,
            "created_at": config["created_at"],
            "updated_at": config["updated_at"],
            "cv_count": 0
        }
        
        with open(self._get_user_projects_index_path(username), 'w') as f:
            json.dump(projects, f, indent=2)
        
        return True
    
    def delete_project(self, project_name: str, username: str) -> bool:
        """
        Elimina un progetto.
        
        Args:
            project_name: Nome del progetto da eliminare
            username: Nome utente
            
        Returns:
            True se l'eliminazione è avvenuta con successo, False altrimenti
        """
        projects = self.get_projects(username)
        if project_name not in projects:
            return False
        
        # Rimuovi la directory del progetto
        project_dir = self._get_project_dir(username, project_name)
        try:
            shutil.rmtree(project_dir)
        except Exception as e:
            print(f"Errore durante l'eliminazione della directory del progetto: {e}")
            return False
        
        # Aggiorna l'indice dei progetti
        del projects[project_name]
        with open(self._get_user_projects_index_path(username), 'w') as f:
            json.dump(projects, f, indent=2)
        
        return True
    
    def get_project_config(self, project_name: str, username: str) -> Dict[str, Any]:
        """
        Ottiene la configurazione di un progetto.
        
        Args:
            project_name: Nome del progetto
            username: Nome utente
            
        Returns:
            Dizionario con la configurazione del progetto
        """
        config_path = os.path.join(self._get_project_dir(username, project_name), "config.json")
        if not os.path.exists(config_path):
            return {}
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore durante il caricamento della configurazione del progetto: {e}")
            return {}
    
    def get_project_cv_dir(self, project_name: str, username: str) -> str:
        """
        Ottiene il percorso della directory dei CV di un progetto.
        
        Args:
            project_name: Nome del progetto
            username: Nome utente
            
        Returns:
            Percorso della directory dei CV
        """
        # Prima verifica se è salvato nella configurazione
        config = self.get_project_config(project_name, username)
        if config and "cv_dir" in config:
            # Verifica che la directory esista
            if os.path.exists(config["cv_dir"]):
                return config["cv_dir"]
        
        # Fallback alla directory predefinita
        return os.path.join(self._get_project_dir(username, project_name), "cvs")
    
    def get_project_results_dir(self, project_name: str, username: str) -> str:
        """
        Ottiene il percorso della directory dei risultati di un progetto.
        
        Args:
            project_name: Nome del progetto
            username: Nome utente
            
        Returns:
            Percorso della directory dei risultati
        """
        return os.path.join(self._get_project_dir(username, project_name), "results")
    
    def update_project(self, project_name: str, username: str, fields: Optional[List[str]] = None, 
                       job_description: Optional[str] = None, criteria_weights: Optional[Dict[str, int]] = None, 
                       evaluation_criteria: Optional[List[tuple]] = None, cv_dir: Optional[str] = None,
                       llm_model: Optional[str] = None, use_ollama: Optional[bool] = None,
                       ollama_model: Optional[str] = None, api_key: Optional[str] = None,
                       use_cache: Optional[bool] = None) -> bool:
        """
        Aggiorna la configurazione di un progetto.
        
        Args:
            project_name: Nome del progetto
            username: Nome utente
            fields: Nuova lista di campi (opzionale)
            job_description: Nuova descrizione del lavoro (opzionale)
            criteria_weights: Pesi dei criteri di valutazione (opzionale)
            evaluation_criteria: Criteri di valutazione (opzionale)
            cv_dir: Directory dei CV (opzionale)
            llm_model: Modello LLM da utilizzare (opzionale)
            use_ollama: Flag per indicare se usare Ollama (opzionale)
            ollama_model: Modello Ollama da utilizzare (opzionale)
            api_key: API key per OpenAI (opzionale)
            use_cache: Flag per indicare se usare la cache (opzionale)
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti
        """
        config = self.get_project_config(project_name, username)
        if not config:
            return False
        
        # Aggiorna i campi se forniti
        if fields is not None:
            config["fields"] = fields
        
        if job_description is not None:
            config["job_description"] = job_description
        
        if criteria_weights is not None:
            config["criteria_weights"] = criteria_weights
        
        if evaluation_criteria is not None:
            # Converti lista di tuple in lista di liste per JSON
            config["evaluation_criteria"] = [list(item) for item in evaluation_criteria]
        
        if cv_dir is not None:
            config["cv_dir"] = cv_dir
        
        if llm_model is not None:
            config["llm_model"] = llm_model
            
        if use_ollama is not None:
            config["use_ollama"] = use_ollama
            
        if ollama_model is not None:
            config["ollama_model"] = ollama_model
            
        if api_key is not None:
            config["api_key"] = api_key
            
        if use_cache is not None:
            config["use_cache"] = use_cache
        
        # Aggiorna il timestamp
        config["updated_at"] = datetime.now().isoformat()
        
        # Salva la configurazione aggiornata
        with open(os.path.join(self._get_project_dir(username, project_name), "config.json"), 'w') as f:
            json.dump(config, f, indent=2)
        
        # Aggiorna l'indice dei progetti
        projects = self.get_projects(username)
        if project_name in projects:
            projects[project_name]["updated_at"] = config["updated_at"]
            with open(self._get_user_projects_index_path(username), 'w') as f:
                json.dump(projects, f, indent=2)
        
        return True
    
    def _load_project_to_session(self, project_name: str, username: str) -> bool:
        """
        Carica un progetto nella session_state corrente.
        
        Args:
            project_name: Nome del progetto
            username: Nome utente
            
        Returns:
            True se il caricamento è avvenuto con successo, False altrimenti
        """
        config = self.get_project_config(project_name, username)
        if not config:
            return False
        
        # Pulisci lo stato corrente
        for key in ["fields", "selected_fields", "job_description", "criteria_weights", 
                   "evaluation_criteria", "cv_dir", "llm_model", "model", "use_ollama", 
                   "ollama_model", "api_key", "results"]:
            if key in st.session_state:
                del st.session_state[key]
        
        # Imposta il progetto corrente
        st.session_state.current_project = project_name
        st.session_state["current_project"] = project_name
        
        # Carica i campi
        if "fields" in config:
            fields = config["fields"]
            st.session_state.fields = fields
            st.session_state.selected_fields = fields
            st.session_state["fields"] = fields
            st.session_state["selected_fields"] = fields
            # Aggiorna anche available_fields aggiungendo i campi del progetto
            if "available_fields" not in st.session_state:
                st.session_state.available_fields = []
            for field in fields:
                if field not in st.session_state.available_fields:
                    st.session_state.available_fields.append(field)
        
        # Carica la job description - Assicuriamoci che venga impostata correttamente
        if "job_description" in config:
            jd = config["job_description"]
            # Imposta la job description sia come attributo che come elemento del dizionario
            st.session_state.job_description = jd
            st.session_state["job_description"] = jd
            # Imposta anche eventuali altri campi correlati che potrebbero usare la job description
            if "DEFAULT_JOB_DESCRIPTION" in st.session_state:
                st.session_state["DEFAULT_JOB_DESCRIPTION"] = jd
            # Forza l'aggiornamento del widget della job_description
            if "job_description" in st.session_state:
                st.session_state["job_description"] = jd
        
        # Carica i pesi dei criteri
        if "criteria_weights" in config:
            weights = config["criteria_weights"]
            st.session_state.criteria_weights = weights
            st.session_state["criteria_weights"] = weights
        
        # Carica i criteri di valutazione
        if "evaluation_criteria" in config:
            criteria = [tuple(item) for item in config["evaluation_criteria"]]
            st.session_state.evaluation_criteria = criteria
            st.session_state["evaluation_criteria"] = criteria
        
        # Carica la directory dei CV
        if "cv_dir" in config:
            cv_dir = config["cv_dir"]
            st.session_state.cv_dir = cv_dir
            st.session_state["cv_dir"] = cv_dir
        
        # Carica il modello di ML
        if "llm_model" in config:
            model = config["llm_model"]
            st.session_state.llm_model = model
            st.session_state["llm_model"] = model
            # Aggiorna anche il campo model per retrocompatibilità
            st.session_state.model = model
            st.session_state["model"] = model
        
        # Carica l'impostazione per Ollama
        if "use_ollama" in config:
            use_ollama = config["use_ollama"]
            st.session_state.use_ollama = use_ollama
            st.session_state["use_ollama"] = use_ollama
        
        # Carica il modello Ollama
        if "ollama_model" in config:
            ollama_model = config["ollama_model"]
            st.session_state.ollama_model = ollama_model
            st.session_state["ollama_model"] = ollama_model
        
        # Carica l'API key
        if "api_key" in config:
            api_key = config["api_key"]
            st.session_state.api_key = api_key
            st.session_state["api_key"] = api_key
        
        # Carica l'impostazione per la cache
        if "use_cache" in config:
            use_cache = config["use_cache"]
            st.session_state.use_cache = use_cache
            st.session_state["use_cache"] = use_cache
            
        # Carica il limite dei CV da analizzare
        if "max_cv_to_analyze" in config:
            max_cv = config["max_cv_to_analyze"]
            # Aggiorna sia la variabile globale che la session state
            st.session_state.MAX_CV_TO_ANALYZE = max_cv
            st.session_state["MAX_CV_TO_ANALYZE"] = max_cv
            # Aggiorna anche la variabile globale
            import sys
            if 'MAX_CV_TO_ANALYZE' in dir(sys.modules['__main__']):
                sys.modules['__main__'].MAX_CV_TO_ANALYZE = max_cv
        
        # Forza l'aggiornamento dello stato
        st.session_state["project_reloaded"] = True
        st.session_state["force_reload"] = True
        
        return True
    
    def _save_current_session_to_project(self, project_name: str, username: str) -> bool:
        """
        Salva lo stato corrente della sessione in un progetto esistente.
        
        Args:
            project_name: Nome del progetto
            username: Nome utente
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        # Verifica che il progetto esista
        projects = self.get_projects(username)
        if project_name not in projects:
            return False
        
        # Raccogli i dati dalla sessione corrente
        fields = st.session_state.get("fields", [])
        job_description = st.session_state.get("job_description", "")
        criteria_weights = st.session_state.get("criteria_weights", {})
        evaluation_criteria = st.session_state.get("evaluation_criteria", [])
        cv_dir = st.session_state.get("cv_dir", "")
        llm_model = st.session_state.get("llm_model", None)
        use_ollama = st.session_state.get("use_ollama", False)
        ollama_model = st.session_state.get("ollama_model", None)
        api_key = st.session_state.get("api_key", None)
        use_cache = st.session_state.get("use_cache", True)
        max_cv_to_analyze = st.session_state.get("MAX_CV_TO_ANALYZE", 999)  # Salva il limite dei CV
        
        # Aggiungi MAX_CV_TO_ANALYZE come campo aggiuntivo nella configurazione
        config = self.get_project_config(project_name, username)
        config["max_cv_to_analyze"] = max_cv_to_analyze
        
        # Salva la configurazione aggiornata
        config_path = os.path.join(self._get_project_dir(username, project_name), "config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Aggiorna il progetto
        return self.update_project(
            project_name=project_name,
            username=username,
            fields=fields,
            job_description=job_description,
            criteria_weights=criteria_weights,
            evaluation_criteria=evaluation_criteria,
            cv_dir=cv_dir,
            llm_model=llm_model,
            use_ollama=use_ollama,
            ollama_model=ollama_model,
            api_key=api_key,
            use_cache=use_cache
        )
    
    def render_project_ui(self, username: str, cv_fields: List[str]):
        """Renderizza l'interfaccia utente per i progetti con il contesto dell'utente."""
        self._render_project_ui_with_context(username, username)
    
    def render_sidebar(self):
        """Renderizza l'interfaccia utente per i progetti nella sidebar."""
        username = st.session_state.get("username", None)
        if not username:
            st.sidebar.warning("Devi accedere per gestire i progetti")
            return
        
        # Utilizza un identificatore per il contesto della sidebar
        self._render_project_ui_with_context(username, "sidebar")
    
    def _render_project_ui_with_context(self, username: str, username_with_ctx: str):
        """Renderizza l'interfaccia utente per i progetti con un contesto specifico."""
        # Ottieni i progetti dell'utente
        projects = self.get_projects(username)
        
        # Mostra i progetti esistenti
        if projects:
            # Seleziona un progetto
            project_options = ["Seleziona un progetto..."] + list(projects.keys())
            default_project_name = st.session_state.get("current_project", None)
            default_index = 0
            if default_project_name and default_project_name in project_options:
                default_index = project_options.index(default_project_name)
            
            selected_project = st.sidebar.selectbox(
                "Progetti salvati",
                options=project_options,
                index=default_index,
                key=f"project_select_{username_with_ctx}"
            )
            
            # Se è stato selezionato un progetto (non "Seleziona un progetto...")
            if selected_project != "Seleziona un progetto...":
                # Mostra i dettagli del progetto
                project_meta = projects[selected_project]
                st.sidebar.markdown(f"**Descrizione:** {project_meta.get('description', 'Nessuna descrizione')}")
                st.sidebar.markdown(f"**Creato il:** {project_meta.get('created_at', 'Data sconosciuta')[:10]}")
                
                # Bottoni per aprire, eliminare e salvare il progetto
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    if st.button("Apri progetto", key=f"open_project_{username_with_ctx}"):
                        if st.session_state.get("current_project") == selected_project:
                            # Usa una chiave diversa per il flag di conferma
                            confirm_state_key = f"needs_confirmation_{username_with_ctx}"
                            if confirm_state_key not in st.session_state:
                                st.session_state[confirm_state_key] = True
                                st.warning("Questo progetto è già aperto. Vuoi ricaricarlo?")
                                st.button("Conferma ricarica", key=f"confirm_reload_{username_with_ctx}")
                            else:
                                # Se l'utente ha cliccato su Conferma ricarica
                                if st.session_state[confirm_state_key]:
                                    # Pulisci lo stato corrente prima di ricaricare
                                    keys_to_clear = ["fields", "selected_fields", "job_description", "criteria_weights", 
                                                   "evaluation_criteria", "cv_dir", "llm_model", "model", "use_ollama", 
                                                   "ollama_model", "api_key", "results", "current_project"]
                                    for key in keys_to_clear:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                    
                                    # Ricarica il progetto
                                    if self._load_project_to_session(selected_project, username):
                                        st.success(f"Progetto '{selected_project}' ricaricato")
                                        # Pulisci il flag di conferma
                                        del st.session_state[confirm_state_key]
                                        st.rerun()
                                    else:
                                        st.error(f"Errore durante il ricaricamento del progetto '{selected_project}'")
                                        del st.session_state[confirm_state_key]
                        else:
                            # Controlla se ci sono modifiche non salvate nel progetto corrente
                            current_project = st.session_state.get("current_project")
                            if current_project:
                                # Usa una chiave diversa per il flag di modifiche non salvate
                                unsaved_state_key = f"has_unsaved_{username_with_ctx}"
                                if unsaved_state_key not in st.session_state:
                                    st.session_state[unsaved_state_key] = True
                                    st.warning("Hai modifiche non salvate nel progetto corrente. Vuoi salvarle prima di aprire il nuovo progetto?")
                                    col_save, col_discard = st.columns(2)
                                    with col_save:
                                        if st.button("Salva modifiche", key=f"save_changes_{username_with_ctx}"):
                                            if self._save_current_session_to_project(current_project, username):
                                                st.success(f"Modifiche salvate nel progetto '{current_project}'")
                                                self._load_project_to_session(selected_project, username)
                                                st.success(f"Progetto '{selected_project}' caricato")
                                                del st.session_state[unsaved_state_key]
                                                st.rerun()
                                            else:
                                                st.error(f"Impossibile salvare le modifiche nel progetto '{current_project}'")
                                                del st.session_state[unsaved_state_key]
                                    with col_discard:
                                        if st.button("Scarta modifiche", key=f"discard_changes_{username_with_ctx}"):
                                            self._load_project_to_session(selected_project, username)
                                            st.success(f"Progetto '{selected_project}' caricato")
                                            del st.session_state[unsaved_state_key]
                                            st.rerun()
                            else:
                                self._load_project_to_session(selected_project, username)
                                st.success(f"Progetto '{selected_project}' caricato")
                                st.rerun()
                
                with col2:
                    if st.button("Elimina", key=f"delete_project_{username_with_ctx}"):
                        if self.delete_project(selected_project, username):
                            st.success(f"Progetto '{selected_project}' eliminato")
                            # Se il progetto corrente era quello eliminato, rimuovilo
                            if st.session_state.get("current_project") == selected_project:
                                del st.session_state.current_project
                            st.rerun()
                        else:
                            st.error(f"Impossibile eliminare il progetto '{selected_project}'")
                
                # Bottone per salvare lo stato corrente nel progetto
                if st.sidebar.button("Salva stato corrente", key=f"save_current_state_{username_with_ctx}"):
                    if self._save_current_session_to_project(selected_project, username):
                        st.success(f"Stato corrente salvato nel progetto '{selected_project}'")
                    else:
                        st.error(f"Impossibile salvare lo stato corrente nel progetto '{selected_project}'")
        
        # Form per creare un nuovo progetto
        with st.sidebar.expander("Crea nuovo progetto"):
            with st.form(key=f"new_project_form_{username_with_ctx}"):
                new_project_name = st.text_input("Nome progetto", key=f"new_project_name_{username_with_ctx}")
                new_project_description = st.text_area("Descrizione", key=f"new_project_description_{username_with_ctx}")
                
                # Campi e job description da salvare nel progetto
                save_current_fields = st.checkbox("Salva campi correnti", value=True, key=f"save_fields_{username_with_ctx}")
                save_current_jd = st.checkbox("Salva job description corrente", value=True, key=f"save_jd_{username_with_ctx}")
                save_current_criteria = st.checkbox("Salva criteri correnti", value=True, key=f"save_criteria_{username_with_ctx}")
                save_current_cv_dir = st.checkbox("Salva directory CV corrente", value=True, key=f"save_cv_dir_{username_with_ctx}")
                save_current_model = st.checkbox("Salva configurazione AI corrente", value=True, key=f"save_model_{username_with_ctx}")
                
                submit_button = st.form_submit_button("Crea progetto")
                
                if submit_button and new_project_name:
                    # Raccogli i dati da salvare
                    fields_to_save = st.session_state.get("fields", []) if save_current_fields else []
                    jd_to_save = st.session_state.get("job_description", "") if save_current_jd else ""
                    criteria_weights_to_save = st.session_state.get("criteria_weights", {}) if save_current_criteria else None
                    evaluation_criteria_to_save = st.session_state.get("evaluation_criteria", []) if save_current_criteria else None
                    cv_dir_to_save = st.session_state.get("cv_dir", None) if save_current_cv_dir else None
                    llm_model_to_save = st.session_state.get("llm_model", None) if save_current_model else None
                    use_ollama_to_save = st.session_state.get("use_ollama", False) if save_current_model else None
                    ollama_model_to_save = st.session_state.get("ollama_model", None) if save_current_model else None
                    api_key_to_save = st.session_state.get("api_key", None) if save_current_model else None
                    use_cache_to_save = st.session_state.get("use_cache", True) if save_current_model else None
                    
                    # Crea il progetto
                    if self.create_project(
                        project_name=new_project_name,
                        description=new_project_description,
                        username=username,
                        fields=fields_to_save,
                        job_description=jd_to_save,
                        criteria_weights=criteria_weights_to_save,
                        evaluation_criteria=evaluation_criteria_to_save,
                        cv_dir=cv_dir_to_save,
                        llm_model=llm_model_to_save,
                        use_ollama=use_ollama_to_save,
                        ollama_model=ollama_model_to_save,
                        api_key=api_key_to_save,
                        use_cache=use_cache_to_save
                    ):
                        st.success(f"Progetto '{new_project_name}' creato con successo!")
                        st.session_state.current_project = new_project_name
                        st.rerun()
                    else:
                        st.error(f"Impossibile creare il progetto '{new_project_name}'. Potrebbe già esistere.") 