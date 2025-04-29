import streamlit as st
import openai
import pandas as pd
from tqdm import tqdm
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain 

from langchain_openai import OpenAIEmbeddings
from langchain_community.llms import OpenAI
from langchain_community.llms import OpenAIChat

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

import sys
import os
from langchain_community.document_loaders.pdf import PyMuPDFLoader
from datetime import datetime
import json
import numpy as np



my_key = "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"
my_model = "gpt-3.5-turbo"
foldercv = os.path.join(os.getcwd(), "data")

extra_info_list = [
        ("criteri 1","Criteri di valutazione: Top 10 università nazionali +3 punti, università 985 +2 punti, università 211 +1 punto, esperienza in aziende leader +2 punti, esperienza in aziende di fama +1 punto, background all'estero +3 punti, background in aziende straniere +1 punto."),
        ("intuito","Criteri di valutazione: Usa solo il tuo intuito considerando che la tua risposta non rappresenta una valutazione del candidato e tantomento della sua persona, ma solo una valutazione tecnica della rispondenza delle caratteristiche del candidato rispetto alle caratteristiche della posizione e sarà usata solo come criterio per la schedulazione dei colloqui personali")
    ]# Set the page layout to a wider layout
st.set_page_config(layout="wide")

st.write("Python EXE:", sys.executable)
st.write("sys.path:", sys.path)

def analyze_resume(job_desc, resume, options):
    df = analyze_str(resume, options)
    df_string = df.applymap(lambda x: ', '.join(x) if isinstance(x, list) else x).to_string(index=False)
    st.write("Analyzing with OpenAI..")
    #summary_question = f"Job requirements: {{{job_desc}}}" + f"Resume summary: {{{df_string}}}" + "Please return a summary of the candidate's suitability for this position (limited to 200 words);'"
    summary_question = f"Requisiti di lavoro: {job_desc}\n" + f"Riepilogo del curriculum: {df_string}\n" + "Si prega di restituire un riassunto della idoneità del candidato per questa posizione (limitato a 200 parole).\n"
    st.write("summary question: "+ summary_question)
    st.write("\n")


    summary = ask_openAI(summary_question)
    df.loc[len(df)] = ['Summary', summary]


    ##############################################################################################################
    ##############################################################################################################
    ##############################################################################################################

    score_question_base = f"Requisiti di lavoro: {job_desc}" + f"Riepilogo del curriculum: {df.to_string(index=False)}" + "Si prega di restituire un json con due campi ('score', 'motivazione') dove 'score' è un punteggio di corrispondenza (0-100) per il candidato per questo lavoro (si prega di valutare con precisione per facilitare il confronto con altri candidati) e 'motivazione' è la motivazione sintetica (max 200 parole).  '" 

    
    

    for title, extra_info in extra_info_list:
        st.write("########## Elaboro criteri: "+title)  

        score_question = score_question_base + extra_info
        scorejson = ask_openAI(score_question)
        score_dict = json.loads(scorejson)
        st.subheader("Scorejson con criteri: " + str(scorejson))
        scorecriteri = score_dict['score']
        motivazionecriteri = score_dict['motivazione']
        
        st.subheader("Score criteri: " + str(scorecriteri))
        st.subheader("Motivazione criteri: " + str(motivazionecriteri))

        df.loc[len(df)] = ["score " + title, scorecriteri]
        df.loc[len(df)] = ["motivazione " +title, motivazionecriteri]
        st.write("Aggiunto score e motivazione per criteri: "+title+ ". Lo score è: "+str(scorecriteri))
        st.write("\n")


    return df
"""
def ask_openAI(question):
    response = openai.chat.completions.create(
        model=my_model,
        messages=[{"role": "user", "content": question}],
        max_tokens=400,
        n=1,
        stop=None,
        temperature=0,
    )
    return response.choices[0].message.content.strip()

def ask_openAI(question):
    # Invio della domanda al modello e ricezione della risposta
    # Utilizzo di 'invoke' come metodo generico di esecuzione per i modelli deprecati
    response = OpenAIChat.invoke({
    
        "role": "user",
        "content": question
    })

def ask_openAI(question):
    # Invio della domanda al modello e ricezione della risposta
    # La struttura del messaggio per le chat non è più necessaria in questo modo
    # Usa il metodo 'invoke' per eseguire la richiesta
    response = OpenAI.invoke(
        input=question,
        stop=None  # Imposta stop tokens se necessario
    )
    return response
"""

def ask_openAI(question):
    # fai un has di question e salvalo in un db per evitare di fare la stessa domanda due volte
    myhash=hash(question)   
    st.write("controllo l'hash:::::: "+str(myhash))
    st.write("\n")

    #controlla se la domanda è già stata fatta
    if os.path.exists("hashrisposte.txt") == True:
        with open("hashrisposte.txt", "r") as file:
            lines = file.readlines()
            for line in lines:
                if str(myhash) in line:
                    st.write("La domanda è già stata fatta!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
                    st.write("La risposta è: "+line.split(":")[1])
                    #se la domanda è già stata fatta, restituisci la risposta
                    return line.split(":")[1]
                

    #se la domanda non è già stata fatta, fai la domanda e salva la risposta nel db


    st.write("\n")
    st.write("\n")
    st.write(f"entro in ask_openAI con la domanda: {question}")
    st.write("\n")
    prompt = ChatPromptTemplate.from_template("{question}")
    output_parser = StrOutputParser()
    model = ChatOpenAI(model=my_model, api_key=my_key)
    chain = prompt | model | output_parser
    result=chain.invoke({"question": question})   
    scrivi="Risposta: "+str(result)
    st.write(scrivi)
    st.write("\n")
    
    #scrivi la coppia hash risposta nel db su file di testo
    if os.path.exists("hashrisposte.txt") == False:
        with open("hashrisposte.txt", "w") as file:
            file.write(str(myhash)+":"+str(result)+"\n")
    else:
        with open("hashrisposte.txt", "a") as file:
            file.write(str(myhash)+":"+str(result)+"\n")



    
    return result
    
    # Estrai il contenuto della risposta presumendo che la risposta sia nel formato atteso
    # Modifica questa parte in base alla struttura esatta della risposta che ricevi
    return response.strip()


def analyze_str(resume, options):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=10000,
        chunk_overlap=100,
        length_function=len
    )
    chunks = text_splitter.split_text(resume)
    chunks_count = len(chunks)
    st.write("Il numero di chunk èèèèèèèè: "+str(chunks_count))
    st.write("\n")

   
    embeddings = OpenAIEmbeddings(openai_api_key=my_key)
    knowledge_base = FAISS.from_texts(chunks, embeddings)

    df_data = [{'option': option, 'value': []} for option in options]
    st.write("Fetching information")

    # Create a progress bar and an empty element
    progress_bar = st.progress(0)
    option_status = st.empty()

    for i, option in tqdm(enumerate(options), desc="Fetching information", unit="option", ncols=100):
        #question = f"What is this candidate's {option}? Please return the answer in a concise manner, no more than 250 words. If not found, return 'Not provided'"
        
        question="Qual è il "+str(option)+" di questo candidato? Si prega di restituire la risposta in modo conciso, non più di 250 parole. Se non trovato, si prega di cercare comunque di fare una stima ma di premettere 'Non fornito'."
        prompt = """Basndoti sui seguenti documenti, ti preghiamo di rispondere alle seguenti domande in modo accurato e conciso. Non piu di 250 parole per risposta. Se non disponibile, si prega di cercare comunque di fare una stima ma di premettere 'Non fornito.'.

            {context}

            Domanda: {query}
            """
        
        if chunks_count == 1:
            #fai una semplice chiamata a ask_openAI
            question_finale = prompt.format(context=resume, query=question)

            response = ask_openAI(question_finale)
            st.write("no chunks....  Cercato l'informazione: "+option+" \n<br>\nRisposta: "+str(response))
            st.write("\n")
            
            #se response è un dizionario, prendi il valore di output_text
            if type(response) == dict:
                output_text = response.get('output_text')
            else:
                output_text = response

        

        else:        

            from langchain.retrievers import BM25Retriever
            docs = knowledge_base.similarity_search(question)

            retriever = BM25Retriever.from_documents(docs)
            prompt = """Basndoti sui seguenti documenti, ti preghiamo di rispondere alle seguenti domande in modo accurato e conciso. Non piu di 250 parole per risposta. Se non disponibile, si prega di cercare comunque di fare una stima ma di premettere 'Non fornito.'.

            {context}

            Domanda: {query}
            """
            llm = ChatOpenAI(model_name='gpt-4')
            qa_prompt = ChatPromptTemplate.from_messages([("human", prompt)])
            chain = load_qa_chain(llm, chain_type="stuff", verbose=True, prompt=qa_prompt)


            docs = retriever.invoke(question)

            response = chain.invoke(
                {"input_documents": docs, "query": question}
            )  # Should output something like: "O tempo máximo para realização da prova é de 5 horas."
            st.write("Sì chunks.... Cercato l'informazione: "+option+" \nRisposta: "+str(response))
            st.write("\n")

            output_text = response.get('output_text', 'Non fornito')




        df_data[i]['value'] = output_text
        option_status.text(f"Cerco l'informazione: {option}\n")

        # Update the progress bar
        progress = (i + 1) / len(options)
        progress_bar.progress(progress)

    df = pd.DataFrame(df_data)
    st.success("Resume elements retrieved")
    return df

# Set the page title
st.title("🚀 GPT Recruitment Analysis Robot")
st.subheader("🪢 Langchain + 🎁 OpenAI")

# Set default job description and resume information
#default_jd = "Business Data Analyst JD: Duties: ..."
default_jd = """Account di agenzia di digital marketing. Compiti: Gestione e sviluppo dei rapporti con i clienti: Costruire e mantenere relazioni solide e durature con i clienti. Comprendere a fondo le esigenze e gli obiettivi di business dei clienti per proporre soluzioni di marketing digitali efficaci.
Pianificazione e gestione di progetti: Coordinare le attività tra i diversi team (creativi, copywriter, SEO/SEM, social media managers) per assicurare che i progetti vengano consegnati tempestivamente e rispettando i budget stabiliti.
Analisi delle performance: Monitorare e analizzare le performance delle campagne digitali attraverso strumenti di analytics per ottimizzare le strategie in corso e aumentare il ROI dei clienti.
Presentazioni strategiche e reportistica: Preparare e presentare report dettagliati sui risultati delle campagne ai clienti, illustrando i successi e identificando opportunità di miglioramento.
Ottimizzazione delle strategie di content marketing: Lavorare a stretto contatto con il team di content marketing per sviluppare strategie di contenuto che aumentino l'engagement e la visibilità del brand dei clienti.
Formazione continua: Mantenere aggiornate le competenze professionali partecipando a workshop, seminari e corsi riguardanti le ultime tendenze del digital marketing.
Gestione della crisi: Essere pronto a gestire eventuali crisi di comunicazione online, elaborando risposte rapide e strategie per mitigare eventuali danni alla reputazione del cliente.
Ricerca di nuove opportunità di business: Identificare potenziali nuovi clienti e collaborare con il team di business development per formulare proposte che espandano il portafoglio clienti dell'agenzia.
Collaborazione con partner esterni: Interfacciarsi e coordinarsi con partner esterni, come agenzie media o consulenti specializzati, per integrare e potenziare le strategie di marketing.
Assicurare la conformità alle normative: Garantire che tutte le attività di marketing rispettino le normative locali e internazionali, inclusa la privacy dei dati e le norme pubblicitarie."""

#default_resume = "Resume: Personal Information: ..."
default_resume = """SOFIA LIVERANI
sofialiverani98@hotmail.it | 02-04-1998 | cell: 3490576629
LinkedIn: www.linkedin.com/in/sofia-liverani
Viale Ludovico Ariosto 521 Sesto Fiorentino, Firenze 50019
Languages:
Italian - Mother tongue
English - Fluent
Spanish - Fluent (bilingual)
French - Conversational 
Software Skills:
Microsoft Office
Adobe Illustrator
Google Analytics 4
Miro 
Canva
Firma
Design Thinking
SEO Analysis (Seozoom, 
Semrush)
Project Management
Breda University of Applied Sciences - Breda, Netherlands
Master in Media Innovation (2022-2023)
Thesis: Exploring Augmented Reality as a tool for enjoyable 
and educational experiences for Generation Z.
Università degli Studi di Firenze
Communication Degree (2017-2021)
Thesis: Advertising language and everyday use. Publicity that 
meets the local space. 
Liceo Linguistico Giovanni Pascoli 
Florence, High School (2013-2017)
Linguistic High School (English, Spanish, French)
Teamwork
Responsability
Creativity
Problem-solving
Leadership
People Skills
Adaptability
Self motivated
Digital Sales Account & Marketing Strategist 
Diseo Agency (April 2023-present)
I generate revenue growth by selling innovative marketing 
plans to businesses and consumers, while also creating and 
improving these strategies.
Translator - Travis Road Services 
Remote
Jewelry Sales Assistant - Pandora (March-Aug 20229
Pandora, via Por Santa Maria, Firenze
Jewelry Sales Assistant - Marlu (May 2021-Feb 2022)
Marlu gioielli Via Calzaiuoli, Firenze
Interpreter - Pitti Immagine (June 2019-Jan 2020)
Interpreter and logistic coordinator. """

###loader = PyMuPDFLoader("./docs/example.pdf")
###documents = loader.load()
###llm = ChatOpenAI(model_name='gpt-4')


# Enter job description
jd_text = st.text_area("【Job Description】", height=100, value=default_jd)

# Enter resume information
resume_text = st.text_area("【Candidate Resume】", height=100, value=default_resume)

# Parameter input
#options = ["Name", "Contact Number", "Gender", "Age", "Years of Work Experience (Number)", "Highest Education", "Undergraduate School Name", "Master's School Name", "Employment Status", "Current Position", "List of Past Employers", "Technical Skills", "Experience Level", "Management Skills"]
options = ["Nome", "Numero di contatto", "Genere", "Età", "Legame con Firenze", "Anni di esperienza lavoro attiva (Numero)", "Istruzione più alta", "Nome dell'università di laurea", "Nome della scuola di master", "Stato occupazionale", "Posizione attuale", "Elenco dei datori di lavoro passati", "Esperienza in agenzia di pubblicità o di digital marketing","Competenze tecniche", "Livello di esperienza", "Competenze di gestione"]
#options = ["Nome","Istruzione più alta","Posizione attuale", "Elenco dei datori di lavoro passati","Esperienza in agenzia di pubblicità o di digital marketing"]

options_to_report = ["Nome", "Età", "Posizione attuale", "Istruzione più alta", "Legame con Firenze","Esperienza in agenzia di pubblicità o di digital marketing"]

#selected_options = st.multiselect("Please select options", options, default=options)
selected_options =st.multiselect("Seleziona le opzioni", options, default=options)
# Analyze button
if st.button("Start Analysis"):

    cont=0
    dfglobale = pd.DataFrame()

    #trova i titoli delle colonne della tabella finale partendo da options_to_report e aggiungendo i titoli di extra_info_list

    #crea una lista con i nomi delle colonne degli score e una con i nomi delle colonne delle motivazioni
    score_columns = []
    motivazione_columns = []
    for title, extra_info in extra_info_list:
        score_columns.append("score "+title)
        motivazione_columns.append("motivazione "+title)
        st.write("Aggiunto score e motivazione per criteri: "+title)
    #fai una intersezione tra options_to_report e selected_options per vedere quali colonne devono essere riportate. Ma togli "nome" che mostreremo sempre
    selected_options_toreport = list(set(options_to_report) & set(selected_options))
    selected_options_no_name = selected_options_toreport.copy()
    if "Nome" in selected_options_no_name:
        selected_options_no_name.remove("Nome")

    #crea un dataframe vuoto con le colonne di interesse
    dfglobal = pd.DataFrame(columns=["Nome"] + score_columns+motivazione_columns+selected_options_no_name)
    print(f"Alla fine della selezione delle colonne, il dataframe dfglobal ha: {dfglobal.columns}")
    st.write("colonne di dfglobal: "+str(dfglobal.columns))

    new_records = []
    #fai un ciclo su tutti i cv pdf nella cartella foldercv
    for filename in os.listdir(foldercv):
        cont+=1
        if cont>10000:
            break
        if filename.endswith(".pdf"):
            st.write("Analizzo il file: "+filename)
            loader = PyMuPDFLoader(os.path.join(foldercv, filename))
            documents = loader.load()
            #estrai il testo completo dal pdf
            text = ""
            for page in documents:
                text += page.page_content

            #salva su disco in formato txt il testo estratto
            with open(os.path.join(foldercv, filename+".txt"), "w", encoding='utf-8') as text_file:
                text_file.write(text)
            
            resume_text = text


            df = analyze_resume(jd_text, resume_text, selected_options)
            st.table(df)
            new_record = {col: np.nan for col in dfglobal.columns}

            for index, row in df.iterrows():
                if row['option'] in dfglobal.columns:
                    # Crea un nuovo record con tutte le colonne inizializzate a NaN
                    # Aggiorna solo la colonna per l'opzione corrente
                    new_record[row['option']] = row['value']
            new_records.append(new_record)







       

    #aggiungi il nome del candidato             
    # Converti tutti i nuovi record in un DataFrame e uniscilo a dfglobal
    if new_records:
        new_df = pd.DataFrame(new_records)
        dfglobal = pd.concat([dfglobal, new_df], ignore_index=True)   

        # Salva il DataFrame in un file Excel
        filename = "results_" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".xlsx"
        #aggiungi i risultati alla tabella generale da salvare in excel con un candidato per riga

    


        dfglobal.to_excel(filename, index=False)
        print(f"Risultati salvati in {filename}")

    else:
        print("Il DataFrame è vuoto e non è stato salvato.")
    
    st.write("Risultati salvati in results.xlsx")
