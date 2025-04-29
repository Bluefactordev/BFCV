import streamlit as st
from auth_system import AuthManager

# Configurazione della pagina - DEVE essere il primo comando Streamlit
st.set_page_config(
    page_title="CV Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato
st.markdown("""
<style>
    body {
        color: #37474F;
        background-color: #F5F7FA;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #2E7D32;
    }
    .metric-card {
        padding: 1rem;
        border-radius: 8px;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E7D32;
    }
    .metric-label {
        font-size: 1rem;
        color: #607D8B;
    }
    .cv-card {
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .cv-card:hover {
        transform: translateY(-5px);
    }
    .sidebar .block-container {
        padding-top: 1rem;
    }
    /* Form styling */
    [data-testid="stForm"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F9FAFB;
    }
    /* Tables */
    [data-testid="stTable"] {
        width: 100%;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    table td, table th {
        border: 1px solid #ddd;
        padding: 8px;
    }
    table tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    table tr:hover {
        background-color: #f5f5f5;
    }
    table th {
        padding-top: 12px;
        padding-bottom: 12px;
        text-align: left;
        background-color: #4CAF50;
        color: white;
    }
    /* Login form */
    .login-form {
        max-width: 500px;
        margin: 0 auto;
        padding: 2rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Funzione principale del launcher"""
    # Inizializza il manager di autenticazione
    auth_manager = AuthManager()
    
    # Logo e titolo
    st.markdown("<div class='login-header'><h1>📄 CV Analyzer Pro</h1></div>", unsafe_allow_html=True)
    
    # Verifica se l'utente è già autenticato
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        # Importa il modulo bfcv_008 solo quando necessario
        import bfcv_008
        
        # Imposta le variabili per evitare configurazione pagina e autenticazione duplicata
        bfcv_008.skip_page_config = True
        bfcv_008.skip_authentication = True
        
        # Inizializzo le variabili di sessione necessarie
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
            
        if 'available_fields' not in st.session_state:
            st.session_state.available_fields = bfcv_008.CV_FIELDS.copy()
            
        if 'selected_fields' not in st.session_state:
            st.session_state.selected_fields = bfcv_008.CV_FIELDS.copy()
            
        if 'fields' not in st.session_state:
            st.session_state.fields = bfcv_008.CV_FIELDS.copy()
        
        # Mostra l'app principale
        bfcv_008.main()
        
        # Pulsante di logout nell'angolo in alto a destra
        with st.sidebar:
            st.markdown(f"**Utente:** {st.session_state.username}")
            if st.button("Logout", key="launcher_logout_button"):
                auth_manager.logout()
                st.rerun()
    else:
        # Mostra l'interfaccia di login
        st.markdown("<div class='login-form'>", unsafe_allow_html=True)
        
        # Form di login
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if auth_manager.login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"Benvenuto, {username}!")
                    st.rerun()
                else:
                    st.error("Username o password non validi.")
        
        # Link per la registrazione
        st.markdown("Non hai un account? [Registrati](#registrazione)")
        
        # Form di registrazione
        st.subheader("Registrazione")
        with st.form("register_form"):
            new_username = st.text_input("Nuovo Username")
            new_password = st.text_input("Nuova Password", type="password")
            confirm_password = st.text_input("Conferma Password", type="password")
            register_submit = st.form_submit_button("Registrati", use_container_width=True)
            
            if register_submit:
                if new_password != confirm_password:
                    st.error("Le password non coincidono.")
                elif not new_username or not new_password:
                    st.error("Username e password sono obbligatori.")
                else:
                    if auth_manager.register_user(new_username, new_password):
                        st.success(f"Utente {new_username} registrato con successo! Ora puoi effettuare il login.")
                    else:
                        st.error(f"L'utente {new_username} esiste già.")
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main() 