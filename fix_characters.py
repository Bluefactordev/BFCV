#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import re

def fix_characters(filename):
    """Corregge i caratteri strani nel file specificato"""
    print(f"Inizio la riparazione del file {filename}")
    
    # Crea un backup del file originale
    backup_filename = f"{filename}.backup_chars"
    if not os.path.exists(backup_filename):
        shutil.copy2(filename, backup_filename)
        print(f"Creato backup in {backup_filename}")
    else:
        print(f"Backup {backup_filename} già esistente, viene utilizzato quello")
    
    # Leggi il contenuto del file
    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Definisci le sostituzioni da effettuare
    replacements = [
        ('pi�', 'più'),
        ('gi�', 'già'),
        ('�', 'à'),
        ('�', 'è'),
        ('citt�', 'città'),
        ('Et�', 'Età'),
        ('Universit�', 'Università'),
        ('capacit�', 'capacità'),
        ('�&�', ''),
        ('>��', '>'),
    ]
    
    # Esegui le sostituzioni
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Scrivi il contenuto corretto nel file originale
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Riparazione completata con successo per {filename}")

if __name__ == "__main__":
    fix_characters("bfcv_007.py") 