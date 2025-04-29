        # FASE 3: Valutazione con i criteri
        logger.info("Iniziando la fase di valutazione")
        
        # Ottieni i criteri dalla session_state se disponibili, altrimenti usa quelli predefiniti
        criteria_list = st.session_state.evaluation_criteria if 'evaluation_criteria' in st.session_state else EVALUATION_CRITERIA
        
        # Ottieni i pesi dalla session_state
        criteria_weights = st.session_state.criteria_weights if 'criteria_weights' in st.session_state else DEFAULT_CRITERIA_WEIGHTS
        
        # Costruisci la lista dei criteri per il prompt
        criteria_prompt_list = []
        weights_prompt_list = []
        
        for criteria_id, criteria_label in criteria_list:
            # Aggiungi alla lista dei criteri
            criteria_prompt_list.append(f"{criteria_id}: Valuta {criteria_label.lower()}.")
            
            # Ottieni il peso del criterio (default 10 se non specificato)
            weight = criteria_weights.get(criteria_id, 10)
            weights_prompt_list.append(f"- {criteria_id}: {weight}%")
        
        # Unisci le liste in stringhe per il prompt
        criteria_description = "\n".join([f"{i+1}. {item}" for i, item in enumerate(criteria_prompt_list)])
        weights_description = "\n".join(weights_prompt_list)
        
        evaluation_prompt = f"""
        Sei un esperto di selezione del personale. Valuta il CV rispetto alla descrizione del lavoro.
            
            Job Description:
            {job_description}
            
            CV:
            {cv_text}
            
        Estrazione informazioni:
        {json.dumps(extraction_result, indent=2, ensure_ascii=False)}
        
        Valuta il candidato per i seguenti criteri su una scala da 0 a 100:
        {criteria_description}
        
        Per ogni criterio, fornisci:
        - Un punteggio da 0 a 100
        - Una breve motivazione di 1-2 frasi che giustifica il punteggio
        
        Calcola anche un punteggio composito che rappresenta il fit complessivo del candidato.
        Il punteggio composito è una media pesata dei criteri sopra, dove i pesi sono:
        {weights_description}
        
        Restituisci i risultati in formato JSON con questa struttura:
        {{
            "criteria": {{
                "{criteria_list[0][0]}": {{"score": X, "motivation": "..."}},
                "{criteria_list[1][0] if len(criteria_list) > 1 else 'altro_criterio'}": {{"score": X, "motivation": "..."}},
                ... altri criteri ...
            }},
            "composite_score": X,
            "extraction": {{ ... tutti i campi estratti dal CV ... }}
        }}
        
        Le motivazioni devono essere concise ma informative, massimo 2 frasi.
        """ 