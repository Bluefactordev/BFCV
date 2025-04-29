# Script per applicare le correzioni al file bfcv_007.py

# Assicurati che esista un backup
if (-not (Test-Path -Path "bfcv_007.py.backup_before_fix")) {
    Copy-Item -Path "bfcv_007.py" -Destination "bfcv_007.py.backup_before_fix"
    Write-Host "Backup creato: bfcv_007.py.backup_before_fix"
}

# Leggi il contenuto del file originale
$content = Get-Content -Path "bfcv_007.py" -Raw

# 1. Correggi il problema con evaluation_result vs criteria_data
$pattern1 = "                # Verifica che il criterio esista nel risultato della valutazione`r?`n                if criteria_id not in evaluation_result:`r?`n                    scores_logger.warning\(f`"Criterio '\{criteria_id\}' NON TROVATO nei dati di valutazione! Salto questo criterio.`"\)`r?`n                    continue`r?`n`r?`n                raw_score = evaluation_result\[criteria_id\].get\(`"score`", 0\)"
$replacement1 = (Get-Content -Path "fix.tmp" -Raw)
$content = $content -replace $pattern1, $replacement1

# 2. Correggi il problema con la gestione degli errori
$pattern2 = "            except \(ValueError, TypeError\) as e:`r?`n                st.warning\(f`"à&à Errore nel punteggio per \{criteria_id\}`"\)`r?`n                scores_logger.error\(f`"Errore nella conversione del punteggio per \{criteria_id\}: \{str\(e\)\}`"\)`r?`n                scores_logger.error\(f`"Valore problematico: \{evaluation_result\[criteria_id\].get\('score'\)\}`"\)"
$replacement2 = (Get-Content -Path "fix2.tmp" -Raw)
$content = $content -replace $pattern2, $replacement2

# 3. Correggi la gestione principale dell'analisi dei CV
$pattern3 = "                    # Esegui l'analisi dei CV`r?`n                    with st.spinner\(`"Analisi in corso...`"\):`r?`n                        try:`r?`n                            logger.info\(`"Avvio analisi dei CV con process_cvs`"\)`r?`n                            results, results_df = process_cvs\(`r?`n                                cv_dir=st.session_state.cv_dir, `r?`n                                job_description=st.session_state.job_description, `r?`n                                fields=st.session_state.fields,`r?`n                                progress_callback=update_progress`r?`n                            \)`r?`n                            `r?`n                            logger.info\(f`"Analisi completata con successo. Ottenuti \{len\(results\)\} risultati`"\)`r?`n                            `r?`n                            # Memorizza i risultati nella session state`r?`n                            st.session_state.results = results`r?`n                            st.session_state.analysis_results = results_df`r?`n                            st.session_state.analysis_error = None  # Resetta eventuali errori precedenti`r?`n                            `r?`n                            logger.info\(`"Risultati salvati in st.session_state.results e st.session_state.analysis_results`"\)`r?`n                            `r?`n                            # Mostra un messaggio di successo`r?`n                            progress_placeholder.empty\(\)`r?`n                            progress_bar.empty\(\)`r?`n                            st.success\(f`"Analisi completata! \{len\(results\)\} CV analizzati.`"\)`r?`n                            `r?`n                            # Attiva la scheda della panoramica`r?`n                            st.session_state.active_tab = 0`r?`n                            logger.info\(`"Impostata active_tab = 0 per mostrare la panoramica dei risultati`"\)`r?`n                            `r?`n                            # Forza il recaricamento della pagina solo se non ci sono stati errori`r?`n                            logger.info\(`"Eseguo st.rerun\(\) per ricaricare la pagina e mostrare i risultati`"\)`r?`n                            st.rerun\(\)`r?`n                        except Exception as e:`r?`n                            # Gestione degli errori`r?`n                            logger.error\(f`"Errore critico durante l'analisi dei CV: \{str\(e\)\}`"\)`r?`n                            import traceback`r?`n                            error_traceback = traceback.format_exc\(\)`r?`n                            logger.error\(f`"Traceback dell'errore:\\n\{error_traceback\}`"\)`r?`n                            `r?`n                            # Salva l'errore nella session state per visualizzarlo in modo persistente`r?`n                            st.session_state.analysis_error = str\(e\)`r?`n                            `r?`n                            # Svuota i placeholder di progress`r?`n                            progress_placeholder.empty\(\)`r?`n                            progress_bar.empty\(\)`r?`n                            `r?`n                            # Mostra l'errore in modo persistente`r?`n                            st.error\(f`"Errore durante l'analisi dei CV: \{str\(e\)\}`"\)`r?`n                            `r?`n                            # Log dell'errore`r?`n                            logger.error\(f`"Errore nell'analisi dei CV: \{str\(e\)\}`"\)`r?`n                            logger.error\(traceback.format_exc\(\)\)"
$replacement3 = (Get-Content -Path "analyze_fix.tmp" -Raw)
$content = $content -replace $pattern3, $replacement3

# Salva il contenuto modificato
$content | Set-Content -Path "bfcv_007.py"

Write-Host "Correzioni applicate con successo a bfcv_007.py" 