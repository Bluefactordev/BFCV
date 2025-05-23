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
        
