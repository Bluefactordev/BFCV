# Script per correggere problemi di codifica e byte nulli
import sys
import codecs
import os

def fix_file(input_file, output_file):
    print(f"Inizio la riparazione del file {input_file}")
    try:
        # Leggi il file in modalità binaria
        with open(input_file, 'rb') as f_in:
            content = f_in.read()
        
        print(f"Letto il file {input_file} - dimensione: {len(content)} byte")
        print(f"Primi byte del file: {content[:20]}")
        
        # Controlla se inizia con byte non validi (BOM errati o altri caratteri problematici)
        # 0xFF 0xFE = UTF-16 LE BOM, 0xFE 0xFF = UTF-16 BE BOM, 0xEF 0xBB 0xBF = UTF-8 BOM
        if content.startswith(b'\xff') and not content.startswith(b'\xff\xfe'):
            print("Rilevato byte 0xFF invalido all'inizio del file, verrà rimosso")
            # Rimuovi i byte non validi all'inizio
            # Cerca la posizione dove inizia il contenuto Python effettivo
            python_start = content.find(b'#')
            if python_start == -1:
                python_start = content.find(b'import')
            
            if python_start > 0:
                print(f"Rimozione di {python_start} byte all'inizio del file")
                content = content[python_start:]
            else:
                # Se non troviamo un punto di riferimento chiaro, rimuoviamo solo i primi byte problematici
                content = content[1:]
                print("Rimosso il primo byte 0xFF")
        
        # Rimuovi i byte nulli
        fixed_content = content.replace(b'\x00', b'')
        removed_bytes = len(content) - len(fixed_content)
        print(f"Rimossi {removed_bytes} byte nulli")
        
        # Assicurati che il file inizi con l'encoding corretto
        if not fixed_content.startswith(b'# -*- coding'):
            fixed_content = b'# -*- coding: utf-8 -*-\n' + fixed_content
            print("Aggiunta dichiarazione di codifica UTF-8")
        
        # Scrivi nel file di output
        with open(output_file, 'wb') as f_out:
            f_out.write(fixed_content)
        
        print(f"File riparato salvato come {output_file} - dimensione: {len(fixed_content)} byte")
        return True
    except Exception as e:
        print(f"Errore durante la riparazione del file: {e}")
        return False

if __name__ == "__main__":
    input_file = "bfcv_007.py"
    output_file = "bfcv_007.py.fixed"
    
    # Crea un backup se non esiste già
    backup_file = input_file + ".backup2"
    if not os.path.exists(backup_file):
        print(f"Creazione di un backup in {backup_file}")
        try:
            with open(input_file, 'rb') as src, open(backup_file, 'wb') as dst:
                dst.write(src.read())
            print(f"Backup creato con successo in {backup_file}")
        except Exception as e:
            print(f"Errore nella creazione del backup: {e}")
    else:
        print(f"Backup {backup_file} già esistente, viene utilizzato quello")
    
    if fix_file(input_file, output_file):
        print("Riparazione completata con successo")
        
        # Sostituisci il file originale
        print("Sostituzione del file originale con la versione riparata...")
        try:
            os.replace(output_file, input_file)
            print(f"File {input_file} sostituito con successo")
        except Exception as e:
            print(f"Errore durante la sostituzione del file: {e}")
    else:
        print("Si è verificato un errore durante la riparazione") 