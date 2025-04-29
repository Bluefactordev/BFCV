# Modulo di Analisi Aziende per BFCV

## Descrizione
Questo modulo aggiunge funzionalità di analisi automatica delle aziende citate nei CV dei candidati. Il sistema identifica le aziende in cui ha lavorato ciascun candidato, raccoglie informazioni su queste aziende utilizzando le API DuckDuckGo, e classifica le aziende in base alla loro relazione con l'azienda che sta conducendo la ricerca.

## Funzionalità

### 1. Identificazione automatica delle aziende
- Estrae i nomi delle aziende da campi strutturati come "Datori di lavoro precedenti" e "Posizione attuale"
- Supporta vari formati e separatori per elenchi di aziende

### 2. Raccolta di informazioni sulle aziende
- Utilizza le API gratuite di DuckDuckGo per raccogliere informazioni sulle aziende
- Salva e riutilizza le informazioni già raccolte per evitare ricerche duplicate
- Estrae automaticamente informazioni come descrizione, sito web e settore

### 3. Classificazione delle aziende
- Determina se un'azienda è un concorrente in base al settore
- Classifica i concorrenti per livello (superiore, pari, inferiore)
- Identifica potenziali clienti

### 4. Interfaccia integrata
- Tab dedicata nell'applicazione principale per gestire tutte le aziende
- Integrazione nella visualizzazione dettagliata dei CV
- Statistiche e grafici per analizzare i dati delle aziende

## Utilizzo

### Analisi automatica durante l'elaborazione dei CV
Durante l'analisi dei CV, le aziende vengono automaticamente identificate ed analizzate. I risultati sono disponibili:

1. Nella tab "Dettaglio" di ciascun CV, sotto la sezione "Aziende"
2. Nella tab generale "Aziende" che mostra tutte le aziende censite

### Analisi manuale on-demand
Se l'analisi automatica non è stata eseguita, è possibile avviarla manualmente:

1. Seleziona un CV nella tab "Dettaglio"
2. Vai alla sezione "Aziende"
3. Clicca su "Analizza aziende del candidato"

### Gestione completa delle aziende
Nella tab "Aziende" puoi:

1. Visualizzare tutte le aziende censite
2. Filtrare le aziende per settore, livello di concorrenza o potenziali clienti
3. Aggiungere manualmente nuove aziende
4. Modificare le informazioni delle aziende esistenti
5. Visualizzare statistiche e grafici

## Note tecniche

### Archiviazione dei dati
Le informazioni sulle aziende vengono archiviate in:
- `company_data/companies.json`

### Moduli
- `company_analyzer.py`: Implementa la logica di analisi e gestione delle aziende
- `company_page.py`: Implementa l'interfaccia utente per la gestione delle aziende

### Modelli di dati
La classe `Company` include i seguenti campi:
- `name`: Nome dell'azienda
- `website`: Sito web
- `description`: Descrizione
- `industry`: Settore (tecnologia, finanza, ecc.)
- `size`: Dimensione (piccola, media, grande)
- `location`: Sede principale
- `founded_year`: Anno di fondazione
- `competitor_level`: Livello di concorrenza (superiore, pari, inferiore, non concorrente)
- `potential_client`: Se è un potenziale cliente
- `notes`: Note aggiuntive
- `search_source`: Fonte delle informazioni (DuckDuckGo, manuale, ecc.)
- `last_updated`: Data ultimo aggiornamento

## Configurazione
In "Impostazioni" della tab "Aziende" puoi configurare:
- Nome dell'azienda cliente
- Settori in cui opera l'azienda cliente
- Settori target per i clienti dell'azienda cliente

Queste informazioni vengono utilizzate per classificare automaticamente le aziende trovate nei CV. 