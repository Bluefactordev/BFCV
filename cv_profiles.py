import os
import json
import streamlit as st
from typing import List, Dict, Any, Optional

# Aggiungo la funzione direttamente in questo file
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

class ProfileManager:
    """
    Classe per gestire i profili dei campi dei CV.
    Permette di salvare, caricare ed eliminare profili personalizzati per la selezione dei campi.
    """
    
    def __init__(self, storage_dir: str = "profiles"):
        """
        Inizializza il ProfileManager.
        
        Args:
            storage_dir: Directory dove salvare i profili (relativa alla directory di lavoro)
        """
        self.storage_dir = storage_dir
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self) -> None:
        """Crea la directory di storage se non esiste."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _get_user_profiles_path(self, username: str) -> str:
        """Ottiene il percorso del file dei profili dell'utente."""
        return os.path.join(self.storage_dir, f"{username}_profiles.json")
    
    def save_profile(self, profile_name: str, fields: List[str], username: str) -> bool:
        """
        Salva un profilo di campi.
        
        Args:
            profile_name: Nome del profilo
            fields: Lista dei campi selezionati
            username: Nome utente
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        profiles = self.get_profiles(username)
        profiles[profile_name] = fields
        
        try:
            with open(self._get_user_profiles_path(username), 'w') as f:
                json.dump(profiles, f, indent=2)
            return True
        except Exception as e:
            print(f"Errore durante il salvataggio del profilo: {e}")
            return False
    
    def get_profiles(self, username: str) -> Dict[str, List[str]]:
        """
        Ottiene tutti i profili dell'utente.
        
        Args:
            username: Nome utente
            
        Returns:
            Dizionario con nomi dei profili come chiavi e liste di campi come valori
        """
        profiles_path = self._get_user_profiles_path(username)
        if not os.path.exists(profiles_path):
            return {}
        
        try:
            with open(profiles_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore durante il caricamento dei profili: {e}")
            return {}
    
    def delete_profile(self, profile_name: str, username: str) -> bool:
        """
        Elimina un profilo.
        
        Args:
            profile_name: Nome del profilo da eliminare
            username: Nome utente
            
        Returns:
            True se l'eliminazione è avvenuta con successo, False altrimenti
        """
        profiles = self.get_profiles(username)
        if profile_name in profiles:
            del profiles[profile_name]
            
            try:
                with open(self._get_user_profiles_path(username), 'w') as f:
                    json.dump(profiles, f, indent=2)
                return True
            except Exception as e:
                print(f"Errore durante l'eliminazione del profilo: {e}")
                return False
        return False
    
    def render_profile_ui(self, cv_fields: List[str], username: str):
        """
        Renderizza l'interfaccia utente per la gestione dei profili.
        
        Args:
            cv_fields: Lista completa di tutti i campi possibili
            username: Nome utente
            
        Returns:
            Lista dei campi selezionati (dal profilo o manualmente)
        """
        # Per evitare conflitti nelle chiamate multiple, aggiungiamo un contesto 'ui'
        username_with_ctx = f"{username}_ui"
        return self._render_profile_ui_with_context(cv_fields, username_with_ctx)
        
    def render_sidebar(self):
        """
        Alias per render_profile_ui per compatibilità.
        Utilizza i campi e l'username dalla sessione.
        
        Returns:
            Risultato di render_profile_ui()
        """
        if 'fields' not in st.session_state or 'username' not in st.session_state:
            st.warning("Sessione non inizializzata correttamente.")
            return []
        
        # Creiamo un contesto unico per questa chiamata alla sidebar
        if 'sidebar_ctx' not in st.session_state:
            st.session_state.sidebar_ctx = "sb"
            
        # Appendiamo il contesto all'username per rendere le chiavi uniche
        username_with_ctx = f"{st.session_state.username}_{st.session_state.sidebar_ctx}"
            
        return self._render_profile_ui_with_context(st.session_state.fields, username_with_ctx)
        
    def _render_profile_ui_with_context(self, cv_fields: List[str], username_with_ctx: str):
        """
        Versione interna di render_profile_ui che accetta un username con contesto.
        Questo metodo è usato per evitare conflitti di chiavi.
        
        Args:
            cv_fields: Lista completa di tutti i campi possibili
            username_with_ctx: Nome utente con contesto aggiuntivo per chiavi uniche
            
        Returns:
            Lista dei campi selezionati (dal profilo o manualmente)
        """
        # Estraiamo il vero username dalla stringa username_with_ctx
        username = username_with_ctx.split("_")[0]
        
        st.sidebar.subheader("Profili di campi")
        
        # Carica profili esistenti
        profiles = self.get_profiles(username)
        
        # UI per il caricamento di un profilo
        profile_names = list(profiles.keys())
        if profile_names:
            selected_profile = st.sidebar.selectbox(
                "Seleziona un profilo salvato",
                options=["Nessun profilo"] + profile_names,
                key=f"profile_select_{username_with_ctx}"
            )
            
            if selected_profile != "Nessun profilo":
                if st.sidebar.button("Carica profilo", key=f"load_profile_{username_with_ctx}"):
                    selected_fields = profiles[selected_profile]
                    # Uso la funzione di utility per sincronizzare tutte le variabili
                    sync_fields_variables(selected_fields)
                    
                    # Memorizzo il profilo corrente nella session_state
                    st.session_state.current_profile = selected_profile
                    
                    st.sidebar.success(f"Profilo '{selected_profile}' caricato con successo!")
                    # Forzo un rerun per aggiornare la UI
                    st.rerun()
                
                # Pulsante di salvataggio per sovrascrivere il profilo corrente
                if st.sidebar.button("Aggiorna profilo", key=f"update_profile_{username_with_ctx}"):
                    # Salva i campi selezionati correnti nel profilo selezionato
                    if self.save_profile(selected_profile, st.session_state.fields, username):
                        st.sidebar.success(f"Profilo '{selected_profile}' aggiornato con successo!")
                        st.rerun()
                    else:
                        st.sidebar.error(f"Errore durante l'aggiornamento del profilo '{selected_profile}'.")
                
                if st.sidebar.button("Elimina profilo", key=f"delete_profile_{username_with_ctx}"):
                    if self.delete_profile(selected_profile, username):
                        st.sidebar.success(f"Profilo '{selected_profile}' eliminato!")
                    else:
                        st.sidebar.error("Errore durante l'eliminazione del profilo.")
            else:
                # Reset del profilo corrente quando si seleziona "Nessun profilo"
                if "current_profile" in st.session_state:
                    # Mostro un pulsante per confermare la rimozione
                    if st.sidebar.button("Rimuovi selezione profilo", key=f"reset_profile_{username_with_ctx}"):
                        st.session_state.current_profile = "Nessuno"
                        st.sidebar.info("Nessun profilo selezionato")
        
        # UI per il salvataggio di un nuovo profilo
        with st.sidebar.expander("Salva profilo attuale"):
            # Nome del nuovo profilo da creare - precompilato con il profilo corrente se disponibile
            default_profile_name = ""
            if "current_profile" in st.session_state and st.session_state.current_profile != "Nessuno":
                default_profile_name = st.session_state.current_profile
                
            new_profile_name = st.sidebar.text_input(
                "Nome nuovo profilo", 
                value=default_profile_name,
                key=f"new_profile_name_{username_with_ctx}"
            )
            
            # Pulsante per salvare il nuovo profilo
            if st.sidebar.button("Salva profilo corrente", key=f"save_new_profile_{username_with_ctx}"):
                if not new_profile_name:
                    st.sidebar.error("Inserisci un nome per il profilo.")
                else:
                    # Controlla se il profilo esiste già
                    if new_profile_name in profiles:
                        st.sidebar.warning(f"Il profilo '{new_profile_name}' esiste già. Scegli un altro nome o aggiorna il profilo esistente.")
                    else:
                        # Salva il nuovo profilo
                        if self.save_profile(new_profile_name, st.session_state.fields, username):
                            st.sidebar.success(f"Profilo '{new_profile_name}' salvato con successo!")
                            # Memorizzo il profilo corrente nella session_state
                            st.session_state.current_profile = new_profile_name
                            st.rerun()
                        else:
                            st.sidebar.error(f"Errore durante il salvataggio del profilo '{new_profile_name}'.")
        
        return st.session_state.fields 