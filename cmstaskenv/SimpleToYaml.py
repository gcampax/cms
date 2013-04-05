#!/usr/bin/python2
# -*- coding: utf-8 -*-

# Modulo "cms_simple_to_yaml"

"""
 Converte il formato di storage di problemi "simple" nel formato classico "yaml" italiano.
 Lo script ha un approccio euristico (tenta di indovinare le informazioni non specificate)
 e tollerante (accetta anche cartelle in un formato non aderente al "simple", agendo solamente
 per la parte che comprende).

 SPECIFICA DEL FORMATO "SIMPLE":

 FILE/CARTELLA                                    CONTENUTO

 cartella_con_nome_lungo_della_gara
 \_ contest.yaml                    (opzionale)   impostazioni globali sulla gara
 |
 |_ cartella_con_nome_lungo_del_problema
 |  \_ problema.yaml                (opzionale)   impostazioni sul problema (token...)
 |  |_ soluzione.{c,cpp,pas}                      soluzione ufficiale
 |  |_ testo.{xml,pdf}                            testo ufficiale
 |  |
 |  |_ input                        <o questa>    file di input pregenerati
 |  |  \_ file di input...
 |  |
 |  |_ generatore.{c,cpp,pas,sh,py} <o questo>    generatore di file di input
 |  |_ generatore.txt               (opzionale)   parametri per il generatore di file di input
 |  |_ valida.{py,sh}               (opzionale)   validatore di file di input
 |  |_ valida.txt                   (opzionale)   informazioni sulla struttura del file di input (per generare un validatore)
 |  |
 |  |_ altre soluzioni, grader, stub, correttore, manager...
 |  |_ immagini e altri contenuti aggiuntivi del testo...
 |
 |_ altri problemi...
"""

from sys import argv
from shutil import move
from datetime import datetime
from os import listdir, path, unlink
import pytz, re, yaml, io, os

#############################################

def usage(err="",noExit=False):
    """Stampa informazioni sull'utilizzo del programma ed eventuali messaggi di errore, eventualmente terminando il programma."""
    if err != "":
        print "errore: ", err
        print
    if not noExit:
        print "usage:"
        print "  ", argv[0], "cartella_problema"
        print "  ", argv[0], "cartella_gara", "inizio", "durata"
        exit(0)

#############################################

def task_names(my_path):
    """Capitalizza il nome lungo e indovina il nome breve scegliendo la parola più lunga."""
    full = re.sub("[ \t_\n.]+", ' ', path.basename(my_path)).strip()
    long_name = full[0:1].upper() + full[1:]

    full = sorted(re.sub("[^a-z0-9A-Z]+", ' ', full).split(' '), key=lambda x: len(x), reverse=True)
    short_name = full[0].lower()

    return short_name, long_name

#############################################

def parse_times(startdate, duration):
    """Converte i parametri "inizio" e "durata" in timestamps interpretandoli come "YYYY-mm-dd HH:MM:SS" e "HH:MM"."""
    _EPOCH=datetime(1970, 1, 1, tzinfo=pytz.utc)
    starttime = datetime.strptime(startdate, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone('Europe/Rome'))
    starttime = (starttime - _EPOCH).total_seconds()
    duration = duration.split(":")
    return starttime, starttime + (int(duration[0]) * 60 + int(duration[1])) * 60

#############################################

def try_mkdir(task_folder,sub_folder=""):
    """Crea la cartella "sub_folder" se ancora non esiste."""
    if task_folder == "":
        task_folder = "."
    if not path.isdir(path.join(task_folder,sub_folder)):
        os.mkdir(path.join(task_folder,sub_folder))

#############################################

def try_rename(source,dest="",exe=False):
    """Sposta "source" in "dest" se esiste, e ritorna "False" altrimenti."""
    if dest == "":
        dest = source
    if path.exists(source):
        try_mkdir(path.dirname(dest))
        os.rename(source,dest)
        if exe:
            os.chmod(dest, 0o700)
        return True
    return False

#############################################

def move_sources(task_folder,sub_folder,file_name,types=('.c','.cpp','.pas'),one=True,exe=False):
    """Sposta i file nominati "file_name" con estensione in "types" nella cartella "sub_folder", rendendoli eseguibili se "exe==True", e ritorna "True" se l'operazione ha avuto successo. Se "one=True" ne sposta uno solo, altrimenti li sposta tutti."""
    done = False
    for extension in types:
        done = done or try_rename(path.join(task_folder, file_name + extension), path.join(task_folder, sub_folder, file_name + extension))
        if done and one:
            return True
    return done

#############################################

def make_validator(task_folder):
    """Crea un file "valida.py" a partire dal formato semplificato del file "valida.txt", così specificato:

    [riga 1]  asserzioni sulle variabili presenti nella prima riga del file di input,
              separate da ";" e nell'ordine corrispondente (in ogni asserzione viene
              considerata in lettura la prima variabile indicata).

    [riga 2+] blocco di righe indicato come "RIGHE x COLONNE : ASSERTION", da cui il
              validatore controlla l'esistenza di un gruppo di "RIGHE" righe ciascuna
              con "COLONNE" elementi che rispettino "ASSERTION".
              Dentro "ASSERTION" è possibile utilizzare le variabili "v" (singolo
              elemento in lettura), ed "r" (vettore con gli elementi della riga), mentre
              "RIGHE" e "COLONNE" possono essere espressioni python arbitrarie.
              I valori in "v" ed "r" vengono convertiti in formato numerico se possibile.
    """
    val = io.open(path.join(task_folder, 'valida.txt'), 'r').readlines()
    ass_list = val[0].split(';')
    var_list = [ re.sub("[^a-zA-Z]+"," ",ass).strip().split()[0] for ass in ass_list ]
    with io.open(path.join(task_folder,'gen','valida.py'), 'wb') as f:
        print >> f, "#!/usr/bin/env python"
        print >> f, "import sys, io"
        print >> f, ""
        print >> f, "def safe_read(f):"
        print >> f, "    s = f.readline()"
        print >> f, "    assert len(s) > 0"
        print >> f, "    return s"
        print >> f, ""
        print >> f, "def try_str_to_num(string):"
        print >> f, "    if string[0] != 0 or len(string) == 1:"
        print >> f, "        try:"
        print >> f, "            return int(string)"
        print >> f, "        except ValueError:"
        print >> f, "            pass"
        print >> f, "        try:"
        print >> f, "            return float(string)"
        print >> f, "        except ValueError:"
        print >> f, "            pass"
        print >> f, "    return string"
        print >> f, ""
        print >> f, "f = io.open(sys.argv[1],'r')"
        print >> f, "riga = map(try_str_to_num,safe_read(f).strip().split())"
        print >> f, "assert len(riga) == %d" % len(var_list)
        print >> f, "%s, = riga" % ",".join(var_list)
        print >> f, ""
        for ass in ass_list:
            print >> f, "assert %s" % (ass.strip(),)
        print >> f, ""
        for riga in val[1:]:
            ass = re.sub(';',':',riga).split(':')
            if len(ass) != 2:
                usage('file "valida.txt" malformato', noExit=True)
                return
            nr, ass = ass
            nr = nr.split('x')
            if len(nr) != 2:
                usage('file "valida.txt" malformato', noExit=True)
                return
            nr, nc  = nr
            print >> f, "for i in xrange(%s):" % (nr.strip(),)
            print >> f, "    r = map(try_str_to_num,safe_read(f).strip().split())"
            print >> f, "    assert len(r) == %s" % (nc.strip(),)
            print >> f, "    for v in r:"
            print >> f, "        assert %s" % (ass.strip(),)
        print >> f, ""
        print >> f, "assert f.readline() == \"\""
        print >> f, "sys.exit(0)"
    unlink(path.join(task_folder,'valida.txt'))
    try_rename(path.join(task_folder,'gen','valida.py'),exe=True)

#############################################

def check_task(task_folder):
    """Controlla che la cartella del task contenga tutti i contenuti obbligatori."""
    task = path.basename(task_folder)
    check = False
    for extension in ('.c','.cpp','.pas'):
        if path.exists(path.join(task_folder,'sol','soluzione' + extension)):
            check = True
    if not check:
        usage('nessuna soluzione trovata per il task "%s" (creare file soluzione.[c,cpp,pas])' % (task,), noExit=True)
    check = False
    for extension in ('.xml','.pdf'):
        if path.exists(path.join(task_folder,'testo','testo' + extension)):
            check = True
    if not check:
        usage('nessun testo trovato per il task "%s" (creare file testo.[xml,pdf])' % (task,), noExit=True)
    check = False
    for extension in ('.c','.cpp','.pas','.sh','.py'):
        if path.exists(path.join(task_folder,'gen','generatore' + extension)):
            check = True
    if not check:
        usage('nessun generatore trovato per il task "%s" (creare file generatore.[py,sh,c,cpp,pas])' % (task,), noExit=True)
    if not path.exists(path.join(task_folder,'gen','GEN')):
        usage('errore interno (file "GEN" non creato)', noExit=True)
    if not path.exists(path.join(task_folder,'gen','valida.py')):
        usage('errore interno (file "valida.py" non creato)', noExit=True)

#############################################

def conv_task(task_folder):
    """Converte un problema dal formato "simple" al formato "yaml", e ritorna il "nome_breve" scelto per il problema."""
    short_name, long_name = task_names(path.basename(task_folder))

    # Leggo un eventuale file "yaml", o lo creo con i valori di default.
    defaults = {
        "nome_breve": short_name,
        "nome": long_name,
        "timeout": 2,
        "memlimit": 512,
        "risultati": "0",
        "n_input": 20,
        "auxiliary": "{}",
        "infile": "input.txt",
        "outfile": "output.txt",
        "token_initial": 2,
        "token_gen_time": 30*60,
        "token_gen_number": 2,
        "min_submission_interval": 60,
        "min_user_test_interval": 60
        }
    task_obj = {}
    try:
        with io.open(path.join(task_folder, 'problema.yaml'), 'rb') as f:
            task_obj = yaml.safe_load(f)
        unlink(path.join(task_folder, 'problema.yaml'))
    except Exception:
        try:
            with io.open(path.join(path.dirname(task_folder), path.basename(task_folder) + '.yaml'), 'rb') as f:
                task_obj = yaml.safe_load(f)
        except Exception:
            pass
    for k in defaults.keys():
        if not k in task_obj:
            task_obj[k] = defaults[k]

    # Sposto i file nelle sottocartelle a seconda del nome e/o dell'estensione
    try_mkdir(task_folder,"sol")
    try_mkdir(task_folder, "gen")
    move_sources(task_folder,'testo','testo',('.pdf','.xml'))
    move_sources(task_folder,'cor','correttore')
    move_sources(task_folder,'cor','manager')
    move_sources(task_folder,'gen','generatore',('.py', '.sh', '.c', '.cpp', '.pas'),exe=True)
    move_sources(task_folder,'gen','valida',('.py','.sh'),exe=True)

    # Se non c'è un validatore (o ci sono istruzioni di creazione validatore), lo creo
    if path.exists(path.join(task_folder,'valida.txt')):
        make_validator(task_folder)
    if not path.exists(path.join(task_folder,'gen','valida.py')):
        with io.open(path.join(task_folder,'gen','valida.py'), 'wb') as f:
            print >> f, "#!/usr/bin/env python\n\nimport sys\nsys.exit(0)"
        try_rename(path.join(task_folder, 'gen/valida.py'), exe=True)

    # Se c'è "generatore.txt" lo metto in "gen/GEN", se non c'è un 'gen/GEN' lo creo di default con 1..n_test_cases
    try_rename(path.join(task_folder, 'generatore.txt'),path.join(task_folder, 'gen', 'GEN'))
    if not path.exists(path.join(task_folder,'gen','GEN')):
        with io.open(path.join(task_folder, 'gen', 'GEN'), 'wb') as f:
            for i in xrange(task_obj['n_input']):
                print >> f, i+1

    # Se c'è una cartella con file di input, creo un generatore di copia
    try_rename(path.join(task_folder, "input"),path.join(task_folder, "io"))
    if path.exists(path.join(task_folder, "io")):
        input_names = sorted(listdir(path.join(task_folder,"io")))
        with io.open(path.join(task_folder, 'gen', 'GEN'), 'wb') as f:
            for n in input_names:
                print >> f, n
        with io.open(path.join(task_folder, 'gen', 'generatore.sh'), 'wb') as f:
            print >> f, "#!/bin/bash"
            print >> f, "cat io/$1"
        try_rename(path.join(task_folder, 'gen', 'generatore.sh'), exe=True)

    # Calcolo il corretto numero di test case
    with io.open(path.join(task_folder, 'gen', 'GEN'), 'r') as f:
        v = [re.sub("#.*$","",line).strip() for line in f.readlines()]
        v.sort(reverse=True)
        while v[-1] == "":
            v.pop()
        task_obj['n_input'] = len(v)

    # Smisto soluzioni ed eventuali altri file rimasti nella cartella del problema
    for f in listdir(task_folder):
        if len(f) > 3 and f[-3] in ('.py','.sh'):
            try_rename(path.join(task_folder,f),path.join(task_folder,"gen",f))
        elif f.endswith('.h') or f.endswith('.hpp'):
            try_rename(path.join(task_folder,f),path.join(task_folder,"cor",f))
        elif f.endswith('.c') or f.endswith('.cpp') or f.endswith('.pas'):
            try_rename(path.join(task_folder,f),path.join(task_folder,"sol",f))
        elif f not in ('sol','cor','gen','testo','io'):
            move(path.join(task_folder,f),path.join(task_folder,"testo",f))

    # Rinomino la cartella del problema e creo il file "yaml"
    check_task(task_folder)
    try_rename(task_folder, path.join(path.dirname(task_folder),task_obj['nome_breve']))
    with io.open(path.join(path.dirname(task_folder),task_obj['nome_breve']+".yaml"), 'wb') as f:
        yaml.safe_dump(task_obj, stream=f, encoding="utf-8", default_flow_style=False)
    return task_obj['nome_breve']

#############################################

def conv_contest(contest_folder,start,duration):
    """Converte una gara dal formato "simple" al formato "yaml"."""
    contest_folder = re.sub("[/ ]+$","",contest_folder)
    contest_short_name, contest_long_name = task_names(path.basename(contest_folder))
    begin, end = parse_times(start,duration)
    defaults = { "nome_breve": contest_short_name,
                 "nome": contest_long_name,
                 "problemi": [],
                 "utenti": [],
                 "token_initial": 0,
                 "token_gen_time": 0,
                 "token_gen_number": 1,
                 "inizio": begin,
                 "fine": end
                 }
    contest = {}
    try:
        with io.open(path.join(contest_folder, 'contest.yaml'), 'rb') as f:
            contest = yaml.safe_load(f)
    except Exception:
        pass
    for k in defaults.keys():
        if not k in contest:
            contest[k] = defaults[k]
    contest['problemi'] = []

    for task in listdir(contest_folder):
        if path.isdir(path.join(contest_folder,task)):
            contest['problemi'].append(conv_task(path.join(contest_folder,task)))

    with io.open(path.join(contest_folder,'contest.yaml'), 'wb') as f:
        yaml.safe_dump(contest, stream=f, encoding="utf-8")
    try_rename(contest_folder,path.join(path.dirname(contest_folder),contest['nome_breve']))

#############################################

if __name__ == "__main__":
    if   len(argv) == 2:
        conv_task(argv[1])
    elif len(argv) == 4:
        conv_contest(argv[1],argv[2],argv[3])
    else:
        usage()
