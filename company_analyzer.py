import requests
import json
import os
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, create_model
import re
import time

# Configurazione del logger per questo modulo
logger = logging.getLogger("COMPANY_ANALYZER")

def create_dynamic_extraction_model(fields):
    """
    Crea dinamicamente un modello Pydantic basato sui campi specificati.
    
    Args:
        fields: Lista dei nomi dei campi da includere nel modello
        
    Returns:
        Modello Pydantic dinamico con i campi specificati
    """
    field_definitions = {}
    
    # Crea definizioni di campo per ogni campo richiesto
    for field in fields:
        field_definitions[field] = (Optional[str], Field(None, description=f"Campo {field}"))
    
    # Aggiungi campi obbligatori per la valutazione
    field_definitions["forza_principale"] = (Optional[str], Field(None, description="La caratteristica più forte del candidato"))
    field_definitions["debolezza_principale"] = (Optional[str], Field(None, description="La caratteristica più debole del candidato"))
    field_definitions["fit_generale"] = (Optional[str], Field(None, description="Valutazione sintetica dell'adeguatezza del candidato"))
    
    # Crea e restituisci il modello dinamico
    return create_model("DynamicExtractionModel", **field_definitions)

class CriteriaEvaluation(BaseModel):
    """Modello per la valutazione dei criteri."""
    criteria: Dict[str, Dict[str, Any]] = Field(..., description="Valutazioni dei criteri")
    composite_score: int = Field(..., description="Punteggio composito")
    extraction: Dict[str, Any] = Field(..., description="Dati estratti dal CV")

class Company(BaseModel):
    """Modello per i dati delle aziende."""
    name: str = Field(..., description="Nome dell'azienda")
    website: Optional[str] = Field(None, description="Sito web dell'azienda")
    description: Optional[str] = Field(None, description="Descrizione dell'azienda")
    industry: Optional[str] = Field(None, description="Settore dell'azienda")
    size: Optional[str] = Field(None, description="Dimensione dell'azienda (piccola, media, grande)")
    location: Optional[str] = Field(None, description="Sede principale dell'azienda")
    founded_year: Optional[int] = Field(None, description="Anno di fondazione")
    competitor_level: Optional[str] = Field(None, description="Livello di competizione (superiore, pari, inferiore)")
    potential_client: Optional[bool] = Field(None, description="Se potrebbe essere un cliente potenziale")
    last_updated: Optional[str] = Field(None, description="Data ultimo aggiornamento dei dati")
    notes: Optional[str] = Field(None, description="Note aggiuntive")
    search_source: Optional[str] = Field(None, description="Fonte dei dati (ricerca web, manuale, ecc.)")
    relevance_score: Optional[int] = Field(None, description="Punteggio di rilevanza da 0 a 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte il modello in un dizionario."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Company':
        """Crea un'istanza del modello da un dizionario."""
        return cls(**data)

class CompanyManager:
    """Gestore delle aziende, con funzionalità di ricerca e archiviazione."""
    
    def __init__(self, data_dir: str = None):
        """
        Inizializza il gestore delle aziende.
        
        Args:
            data_dir: Directory per il salvataggio dei dati (default: ./company_data)
        """
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.companies: Dict[str, Company] = {}
        self.load_companies()
        
        # Parametri per le API DuckDuckGo
        self.api_url = "https://api.duckduckgo.com/"
        
        logger.info(f"CompanyManager inizializzato con directory dati: {self.data_dir}")
    
    def load_companies(self) -> None:
        """Carica le aziende dal disco."""
        try:
            companies_file = os.path.join(self.data_dir, "companies.json")
            if os.path.exists(companies_file):
                with open(companies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for company_data in data:
                        company = Company.from_dict(company_data)
                        self.companies[company.name.lower()] = company
                logger.info(f"Caricate {len(self.companies)} aziende dal disco")
            else:
                logger.info("Nessun file di aziende trovato, inizializzazione con database vuoto")
        except Exception as e:
            logger.error(f"Errore nel caricamento delle aziende: {str(e)}")
    
    def save_companies(self) -> None:
        """Salva le aziende su disco."""
        try:
            companies_file = os.path.join(self.data_dir, "companies.json")
            with open(companies_file, 'w', encoding='utf-8') as f:
                json.dump([company.to_dict() for company in self.companies.values()], f, ensure_ascii=False, indent=2)
            logger.info(f"Salvate {len(self.companies)} aziende su disco")
        except Exception as e:
            logger.error(f"Errore nel salvataggio delle aziende: {str(e)}")
    
    def add_or_update_company(self, company: Company) -> None:
        """
        Aggiunge o aggiorna un'azienda nel database.
        
        Args:
            company: Istanza dell'azienda da aggiungere o aggiornare
        """
        company.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.companies[company.name.lower()] = company
        self.save_companies()
        logger.info(f"Azienda {company.name} aggiunta/aggiornata")
    
    def get_company(self, company_name: str) -> Optional[Company]:
        """
        Recupera un'azienda dal database per nome.
        
        Args:
            company_name: Nome dell'azienda da cercare
            
        Returns:
            Istanza dell'azienda o None se non trovata
        """
        return self.companies.get(company_name.lower())
    
    def delete_company(self, company_name: str) -> bool:
        """
        Elimina un'azienda dal database.
        
        Args:
            company_name: Nome dell'azienda da eliminare
            
        Returns:
            True se l'azienda è stata eliminata, False altrimenti
        """
        if company_name.lower() in self.companies:
            del self.companies[company_name.lower()]
            self.save_companies()
            logger.info(f"Azienda {company_name} eliminata")
            return True
        logger.warning(f"Tentativo di eliminare l'azienda {company_name} non trovata")
        return False
    
    def get_all_companies(self) -> List[Company]:
        """
        Recupera tutte le aziende dal database.
        
        Returns:
            Lista di tutte le aziende
        """
        return list(self.companies.values())
    
    def search_duckduckgo(self, company_name: str) -> Dict[str, Any]:
        """
        Esegue una ricerca su DuckDuckGo per ottenere informazioni sull'azienda.
        
        Args:
            company_name: Nome dell'azienda da cercare
            
        Returns:
            Dizionario con i risultati della ricerca
        """
        try:
            # Controlla se abbiamo già l'azienda nel database
            existing_company = self.get_company(company_name)
            if existing_company:
                logger.info(f"Azienda {company_name} già presente nel database")
                return {"status": "cached", "company": existing_company}
            
            # Altrimenti, eseguiamo la ricerca online
            params = {
                'q': f"{company_name} company information",
                'format': 'json',
                't': 'BFCV'
            }
            
            logger.info(f"Esecuzione ricerca DuckDuckGo per '{company_name}'")
            response = requests.get(self.api_url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Errore nella richiesta a DuckDuckGo: {response.status_code}")
                return {"status": "error", "message": f"Errore API: {response.status_code}"}
            
            # Processa i risultati
            results = response.json()
            
            # Ritardo per rispettare i limiti di rate dell'API
            time.sleep(1)
            
            return {"status": "success", "results": results}
        except Exception as e:
            logger.error(f"Errore nella ricerca DuckDuckGo: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def analyze_company(self, company_name: str, client_company_data: Dict[str, Any]) -> Company:
        """
        Analizza un'azienda in base alle informazioni del nostro cliente.
        
        Args:
            company_name: Nome dell'azienda da analizzare
            client_company_data: Dati dell'azienda cliente
            
        Returns:
            Istanza dell'azienda analizzata
        """
        # Verifica se abbiamo già questa azienda nel database
        existing_company = self.get_company(company_name)
        if existing_company:
            logger.info(f"Azienda {company_name} già analizzata in precedenza")
            return existing_company
        
        # Esegui la ricerca DuckDuckGo
        search_result = self.search_duckduckgo(company_name)
        
        if search_result["status"] == "cached":
            return search_result["company"]
        
        if search_result["status"] != "success":
            # Crea un'azienda con dati minimi
            logger.warning(f"Impossibile ottenere dati per {company_name}, creazione record minimale")
            company = Company(
                name=company_name,
                search_source="ricerca fallita",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self.add_or_update_company(company)
            return company
        
        # Estrai informazioni rilevanti dalla ricerca
        results = search_result["results"]
        
        # Estrai l'abstract se disponibile
        description = results.get("AbstractText", "")
        if not description and results.get("RelatedTopics"):
            # Prova a ottenere informazioni dai topic correlati
            for topic in results["RelatedTopics"]:
                if isinstance(topic, dict) and "Text" in topic:
                    description = topic["Text"]
                    break
        
        # Crea l'oggetto Company con le informazioni disponibili
        company = Company(
            name=company_name,
            description=description,
            search_source="DuckDuckGo",
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # Estrai il sito web se disponibile
        if results.get("Results") and len(results["Results"]) > 0:
            first_result = results["Results"][0]
            company.website = first_result.get("FirstURL", None)
        
        # Deduce il settore e altre informazioni dal testo
        if description:
            # Analisi semplice per il settore basata su parole chiave
            sectors = [
                "tech", "technolog", "software", "hardware", "IT", "informatica",
                "finanz", "finance", "banking", "investment", "assicura", "insurance",
                "salute", "health", "healthcare", "medical", "pharma", "farmac",
                "commercio", "retail", "e-commerce", "ecommerce", "shop",
                "manufactur", "manufat", "produzion", "industrial",
                "consulenz", "consult", "advisory", "profession",
                "educat", "formazione", "school", "university",
                "media", "entertainment", "giochi", "games",
                "food", "cibo", "restaurant", "ristor",
                "travel", "viaggio", "tourism", "turismo",
                "fashion", "moda", "clothing", "abbigliamento",
                "real estate", "immobil", "construction", "costruzion"
            ]
            
            description_lower = description.lower()
            detected_sectors = []
            
            for sector in sectors:
                if sector.lower() in description_lower:
                    detected_sectors.append(sector)
            
            if detected_sectors:
                company.industry = ", ".join(detected_sectors)
        
        # Confronta con l'azienda cliente
        client_industry = client_company_data.get("industry", "").lower()
        if company.industry and client_industry:
            # Determina se è un concorrente
            company_industry_lower = company.industry.lower()
            if any(sector in company_industry_lower for sector in client_industry.split(",")):
                # Stessa industria, potrebbe essere un concorrente
                company.competitor_level = "pari"  # Default, può essere modificato manualmente
                
                # Determina se è un cliente potenziale
                company.potential_client = False  # Se è un concorrente, non è un cliente
            else:
                # Industria diversa, potrebbe essere un cliente
                company.competitor_level = "non concorrente"
                company.potential_client = True
        
        # Salva l'azienda nel database
        self.add_or_update_company(company)
        
        return company
    
    def extract_companies_from_cv(self, cv_text: str, extraction_result: Dict[str, Any]) -> List[str]:
        """
        Estrae i nomi delle aziende da un CV e dai risultati dell'estrazione.
        
        Args:
            cv_text: Testo completo del CV
            extraction_result: Risultati dell'estrazione precedente
            
        Returns:
            Lista dei nomi delle aziende trovate
        """
        companies = []
        
        # Controlla se esiste già un campo dedicato alle aziende nell'estrazione
        if "aziende_menzionate" in extraction_result:
            companies_field = extraction_result["aziende_menzionate"]
            if isinstance(companies_field, list):
                companies.extend(companies_field)
            elif isinstance(companies_field, str) and companies_field.strip():
                # Split basato su vari separatori
                for sep in [",", ";", "e ", " and "]:
                    if sep in companies_field:
                        companies.extend([e.strip() for e in companies_field.split(sep) if e.strip()])
                        break
                else:
                    # Se non ci sono separatori, considera l'intera stringa
                    companies.append(companies_field.strip())
        
        # Estrai dalle informazioni strutturate dei datori di lavoro precedenti
        if "Datori di lavoro precedenti" in extraction_result:
            employers = extraction_result["Datori di lavoro precedenti"]
            if isinstance(employers, list):
                companies.extend(employers)
            elif isinstance(employers, str) and employers.strip():
                # Split basato su vari separatori
                for sep in [",", ";", "e ", " and "]:
                    if sep in employers:
                        companies.extend([e.strip() for e in employers.split(sep) if e.strip()])
                        break
                else:
                    # Se non ci sono separatori, considera l'intera stringa
                    companies.append(employers.strip())
        
        # Estrai anche la posizione attuale
        if "Posizione attuale" in extraction_result:
            current_position = extraction_result["Posizione attuale"]
            if current_position and isinstance(current_position, str):
                # Cerca di estrarre l'azienda dalla posizione attuale
                position_parts = re.split(r'\bat\b|\bpresso\b|\bper\b|\bin\b', current_position, flags=re.IGNORECASE)
                if len(position_parts) > 1:
                    current_company = position_parts[1].strip()
                    if current_company:
                        companies.append(current_company)
        
        # Cerca eventuali aziende menzionate nella formazione
        if "Formazione" in extraction_result:
            education = extraction_result["Formazione"]
            if isinstance(education, str) and education.strip():
                # Cerca le istituzioni educative che potrebbero essere aziende
                edu_parts = re.split(r'\bat\b|\bpresso\b|\ba\b|\bin\b', education, flags=re.IGNORECASE)
                if len(edu_parts) > 1:
                    for part in edu_parts[1:]:  # Considera tutti tranne il primo
                        edu_company = part.strip().split(".")[0].split(",")[0]  # Prendi fino al primo punto o virgola
                        if edu_company and len(edu_company) > 3:  # Ignora stringhe troppo corte
                            companies.append(edu_company)
        
        # Rimuovi eventuali duplicati e elementi vuoti
        unique_companies = []
        for company in companies:
            if company and company not in unique_companies:
                # Rimuovi eventuali caratteri non necessari
                clean_company = re.sub(r'^\W+|\W+$', '', company)
                if clean_company and len(clean_company) > 1 and clean_company not in unique_companies:
                    unique_companies.append(clean_company)
        
        return unique_companies
    
    def process_companies_from_cv(self, companies: List[str], client_company_data: Dict[str, Any]) -> List[Company]:
        """
        Processa un elenco di aziende estratte da un CV.
        
        Args:
            companies: Lista dei nomi delle aziende da processare
            client_company_data: Dati dell'azienda cliente
            
        Returns:
            Lista delle aziende processate
        """
        processed_companies = []
        
        for company_name in companies:
            # Pulisci il nome dell'azienda
            company_name = company_name.strip()
            if not company_name:
                continue
                
            # Analizza l'azienda
            company = self.analyze_company(company_name, client_company_data)
            processed_companies.append(company)
        
        return processed_companies
