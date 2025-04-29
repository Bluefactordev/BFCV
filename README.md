# CV Analyzer Pro

Un'applicazione avanzata per l'analisi dei curriculum vitae con AI.

## Nuove funzionalità

Ora l'applicazione include:

1. **Sistema di autenticazione**: Protezione con username e password
2. **Gestione profili**: Salva e carica configurazioni personalizzate di campi
3. **Gestione progetti**: Organizza i CV in progetti con impostazioni dedicate
4. **Gestione posizioni lavorative**: Associa cartelle CV, job descriptions e set di campi a posizioni specifiche

## Come avviare l'applicazione

Per avviare l'applicazione con autenticazione:

```bash
streamlit run launcher.py
```

Per utilizzare la versione originale senza autenticazione:

```bash
streamlit run bfcv_007.py
```

## Credenziali predefinite

Username: `admin`  
Password: `admin`

È possibile registrare nuovi utenti direttamente dall'interfaccia di login.

## Struttura dei file

- `launcher.py`: Punto di ingresso con autenticazione
- `bfcv_007.py`: Applicazione principale per l'analisi dei CV
- `auth_system.py`: Sistema di autenticazione e gestione utenti
- `cv_profiles.py`: Gestione dei profili di campi
- `cv_projects.py`: Gestione dei progetti di analisi
- `job_positions.py`: Gestione delle posizioni lavorative

## Note importanti

- Tutti i dati vengono salvati in file JSON nelle rispettive directory (`auth`, `profiles`, `projects`, `positions`)
- Ogni utente ha i propri profili, progetti e posizioni
- La registrazione è aperta a tutti gli utenti
- L'utente `admin` ha accesso a tutte le funzionalità 