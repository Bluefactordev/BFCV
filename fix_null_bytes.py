# Script per rimuovere i byte nulli da un file
import sys

def fix_file(input_file, output_file):
    print(f"Inizio la riparazione del file {input_file}")
    try:
        with open(input_file, 'rb') as f_in:
            content = f_in.read()
            
        # Rimuovo i byte nulli
        fixed_content = content.replace(b'\x00', b'')
        
        # Calcolo quanti byte sono stati rimossi
        removed_bytes = len(content) - len(fixed_content)
        print(f"Trovati {removed_bytes} byte nulli da rimuovere")
        
        # Scrivo nel file di output
        with open(output_file, 'wb') as f_out:
            f_out.write(fixed_content)
            
        print(f"File riparato salvato come {output_file}")
        return True
    except Exception as e:
        print(f"Errore durante la riparazione del file: {e}")
        return False

if __name__ == "__main__":
    input_file = "bfcv_007.py"
    output_file = "bfcv_007.py.fixed"
    
    if fix_file(input_file, output_file):
        print("Riparazione completata con successo")
    else:
        print("Si è verificato un errore durante la riparazione") 