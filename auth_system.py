import os
import json
import streamlit as st
import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple

class AuthManager:
    """
    Classe per gestire l'autenticazione e la registrazione degli utenti.
    Implementa un sistema di login basico con username e password.
    """
    
    def __init__(self, storage_dir: str = "auth"):
        """
        Inizializza l'AuthManager.
        
        Args:
            storage_dir: Directory dove salvare i dati degli utenti (relativa alla directory di lavoro)
        """
        self.storage_dir = storage_dir
        self._ensure_storage_dir()
        self._ensure_default_admin()
    
    def _ensure_storage_dir(self) -> None:
        """Crea la directory di storage se non esiste."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _get_users_file_path(self) -> str:
        """Ottiene il percorso del file degli utenti."""
        return os.path.join(self.storage_dir, "users.json")
    
    def _ensure_default_admin(self) -> None:
        """Crea un utente admin di default se non esiste alcun utente."""
        users_file = self._get_users_file_path()
        if not os.path.exists(users_file):
            # Crea l'utente admin di default
            self.register_user("admin", "admin", is_admin=True)
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Crea un hash della password con un salt.
        
        Args:
            password: Password da hashare
            salt: Salt da utilizzare (se None, ne viene generato uno nuovo)
            
        Returns:
            Tupla con (hash_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Combina password e salt
        salted = (password + salt).encode('utf-8')
        
        # Crea l'hash
        hashed = hashlib.sha256(salted).hexdigest()
        
        return hashed, salt
    
    def _get_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Ottiene tutti gli utenti registrati.
        
        Returns:
            Dizionario con username come chiavi e dati utente come valori
        """
        users_file = self._get_users_file_path()
        if not os.path.exists(users_file):
            return {}
        
        try:
            with open(users_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore durante il caricamento degli utenti: {e}")
            return {}
    
    def _save_users(self, users: Dict[str, Dict[str, Any]]) -> bool:
        """
        Salva gli utenti nel file.
        
        Args:
            users: Dizionario con username come chiavi e dati utente come valori
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        try:
            with open(self._get_users_file_path(), 'w') as f:
                json.dump(users, f, indent=2)
            return True
        except Exception as e:
            print(f"Errore durante il salvataggio degli utenti: {e}")
            return False
    
    def register_user(self, username: str, password: str, is_admin: bool = False) -> bool:
        """
        Registra un nuovo utente.
        
        Args:
            username: Nome utente
            password: Password
            is_admin: Se l'utente è un amministratore
            
        Returns:
            True se la registrazione è avvenuta con successo, False altrimenti
        """
        users = self._get_users()
        
        # Controlla se l'utente esiste già
        if username in users:
            return False
        
        # Crea l'hash della password
        hashed_password, salt = self._hash_password(password)
        
        # Crea l'utente
        users[username] = {
            "password_hash": hashed_password,
            "salt": salt,
            "is_admin": is_admin,
            "created_at": "", # Potremmo usare datetime.now().isoformat() se importassimo datetime
            "last_login": ""
        }
        
        return self._save_users(users)
    
    def login(self, username: str, password: str) -> bool:
        """
        Verifica le credenziali di login.
        
        Args:
            username: Nome utente
            password: Password
            
        Returns:
            True se le credenziali sono valide, False altrimenti
        """
        users = self._get_users()
        
        # Controlla se l'utente esiste
        if username not in users:
            return False
        
        # Ottieni i dati dell'utente
        user_data = users[username]
        
        # Verifica la password
        hashed_password, _ = self._hash_password(password, user_data["salt"])
        return hashed_password == user_data["password_hash"]
    
    def is_admin(self, username: str) -> bool:
        """
        Verifica se un utente è un amministratore.
        
        Args:
            username: Nome utente
            
        Returns:
            True se l'utente è un amministratore, False altrimenti
        """
        users = self._get_users()
        
        # Controlla se l'utente esiste
        if username not in users:
            return False
        
        return users[username].get("is_admin", False)
    
    def render_login_ui(self):
        """
        Renderizza l'interfaccia utente per il login.
        
        Returns:
            Tuple(bool, str): (login_successful, username)
        """
        st.title("CV Analyzer - Login")
        
        # Verifica se l'utente è già loggato
        if "authenticated" in st.session_state and st.session_state.authenticated:
            return True, st.session_state.username
        
        # Form di login
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if self.login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"Benvenuto, {username}!")
                    st.rerun()
                else:
                    st.error("Username o password non validi.")
        
        # Link per la registrazione
        st.markdown("Non hai un account? [Registrati](#registrazione)")
        
        # Form di registrazione (nascosto di default)
        with st.expander("Registrazione", expanded=False):
            with st.form("register_form"):
                new_username = st.text_input("Nuovo Username")
                new_password = st.text_input("Nuova Password", type="password")
                confirm_password = st.text_input("Conferma Password", type="password")
                register_submit = st.form_submit_button("Registrati")
                
                if register_submit:
                    if new_password != confirm_password:
                        st.error("Le password non coincidono.")
                    elif not new_username or not new_password:
                        st.error("Username e password sono obbligatori.")
                    else:
                        if self.register_user(new_username, new_password):
                            st.success(f"Utente {new_username} registrato con successo! Ora puoi effettuare il login.")
                        else:
                            st.error(f"L'utente {new_username} esiste già.")
        
        return False, ""
    
    def logout(self):
        """Effettua il logout dell'utente."""
        if "authenticated" in st.session_state:
            del st.session_state.authenticated
        
        if "username" in st.session_state:
            del st.session_state.username 
            
    def is_authenticated(self) -> bool:
        """
        Verifica se l'utente è autenticato.
        
        Returns:
            True se l'utente è autenticato, False altrimenti
        """
        return "authenticated" in st.session_state and st.session_state.authenticated
        
    def login_page(self):
        """
        Alias per render_login_ui per compatibilità.
        
        Returns:
            Risultato di render_login_ui()
        """
        return self.render_login_ui() 