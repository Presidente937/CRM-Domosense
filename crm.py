import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# CONFIGURAZIONE SUPABASE
DATABASE_URL="postgresql://postgres.ruwbodnfktfcppxfjkxq:MC.D0m0s3ns3@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

# Connessione robusta al database PostgreSQL
engine = create_engine(DATABASE_URL)

st.set_page_config(page_title="Domosense CRM", layout="wide")

# Inizializzazione delle variabili di stato (Session State)
if "contact_form_version" not in st.session_state:
    st.session_state.contact_form_version = 0
if "activity_form_version" not in st.session_state:
    st.session_state.activity_form_version = 0
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""

# Funzione per eseguire query di scrittura in sicurezza
def esegui_query(query, params=None):
    with engine.begin() as conn:
        conn.execute(text(query), params or {})

# Funzione per leggere i dati
def leggi_query(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})

# ==================== SCHERMATA DI LOGIN ====================
if not st.session_state.logged_in:
    st.title("🔒 Domosense CRM - Accesso")
    
    with st.form("login_form"):
        st.subheader("Inserisci le tue credenziali")
        username_input = st.text_input("Nome utente")
        password_input = st.text_input("Password", type="password")
        submit_login = st.form_submit_button("Accedi")
        
        if submit_login:
            user_df = leggi_query(
                "SELECT id, username FROM utenti WHERE username = :user AND password = :pass",
                {"user": username_input.strip(), "pass": password_input.strip()}
            )
            
            if not user_df.empty:
                st.session_state.logged_in = True
                st.session_state.user_id = int(user_df.iloc[0]['id'])
                st.session_state.username = user_df.iloc[0]['username']
                st.success(f"Accesso effettuato! Benvenuto {st.session_state.username}.")
                st.rerun()
            else:
                st.error("Nome utente o Password errati. Riprova.")
    st.stop()

# ==================== APPLICATIVO LOGGATO ====================
st.title("Domosense CRM")
st.sidebar.write(f"👤 Utente connesso: **{st.session_state.username}**")

# --- NUOVA FUNZIONALITÀ: FLAG PER VISUALIZZAZIONE GLOBALE O PERSONALE ---
mostra_tutti = st.sidebar.checkbox("👀 Mostra i contatti di tutti gli utenti", value=False)

if st.sidebar.button("Logout", type="secondary"):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.rerun()

st.sidebar.write("---")

# Finestre modali di conferma eliminazione
@st.dialog("Conferma Eliminazione Contatto")
def conferma_eliminazione_dialog(contatto_id, nome_completo):
    st.warning(f"Sei sicuro di voler eliminare definitivamente **{nome_completo}**?")
    col_conferma, col_annulla = st.columns(2)
    with col_conferma:
        if st.button("Sì, elimina", type="primary", use_container_width=True):
            esegui_query("DELETE FROM contatti WHERE id = :id", {"id": int(contatto_id)})
            st.success("Contatto eliminato!")
            st.rerun()
    with col_annulla:
        if st.button("Annulla", use_container_width=True): st.rerun()

@st.dialog("Conferma Eliminazione Attività")
def conferma_eliminazione_attivita_dialog(attivita_id, descrizione_breve):
    st.warning(f"Sei sicuro di voler eliminare l'attività: **\"{descrizione_breve}\"**?")
    col_conferma, col_annulla = st.columns(2)
    with col_conferma:
        if st.button("Sì, elimina", type="primary", use_container_width=True):
            esegui_query("DELETE FROM attivita WHERE id = :id", {"id": int(attivita_id)})
            st.success("Attività eliminata!")
            st.rerun()
    with col_annulla:
        if st.button("Annulla", use_container_width=True): st.rerun()

# Navigazione
st.sidebar.title("📁 Menu Principale")
macro_sezione = st.sidebar.radio("Seleziona Area:", ["👥 Contatti", "📅 Attività"])
st.sidebar.write("---")

OPZIONI_PROVENIENZA = ["Social", "BNI", "Fiere/Eventi in presenza"]

if macro_sezione == "👥 Contatti":
    sotto_sezione = st.sidebar.radio("Scegli Azione:", ["ℹ️ Info e Gestione Contatto", "➕ Aggiungi Contatto"])
else:
    sotto_sezione = st.sidebar.radio("Scegli Azione:", ["🔍 Riepilogo Scadenze", "➕ Aggiungi Attività", "⚙️ Gestione Attività"])


# ==# ==================== LOGICA SOTTOSEZIONI (CON TABELLA ED EDITOR) ====================

# 1. INFO E GESTIONE CONTATTO
if macro_sezione == "👥 Contatti" and sotto_sezione == "ℹ️ Info e Gestione Contatto":
    st.header("👤 Elenco e Gestione Contatti")
    
    # Caricamento dei dati in base al flag globale - Ordinati di default per Cognome (ORDER BY cognome ASC)
    if mostra_tutti:
        contatti_df = leggi_query("SELECT id, nome, cognome, ruolo, azienda, provenienza_lead, email, telefono, utente_id FROM contatti ORDER BY cognome ASC")
    else:
        contatti_df = leggi_query("SELECT id, nome, cognome, ruolo, azienda, provenienza_lead, email, telefono, utente_id FROM contatti WHERE utente_id = :uid ORDER BY cognome ASC", {"uid": st.session_state.user_id})
    
    if not contatti_df.empty:
        st.write("💡 *Clicca sulla casella a sinistra di una riga per selezionare il contatto da modificare o eliminare.*")
        
        # Prepariamo il DataFrame per la visualizzazione rinominando le colonne
        contatti_visualizzazione = contatti_df.copy()
        contatti_visualizzazione.columns = ["ID", "Nome", "Cognome", "Ruolo", "Azienda", "Provenienza", "Email", "Telefono", "Utente ID"]
        
        scelta_griglia = st.dataframe(
            contatti_visualizzazione,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",  # Ricarica la pagina appena l'utente seleziona una riga
            selection_mode="single-row",  # Permette di selezionare un solo contatto alla volta
            column_config={
                "ID": None  # Nasconde completamente la colonna ID del contatto dalla vista degli utenti
            }
        )
        
        # Controlliamo se l'utente ha selezionato una riga
        righe_selezionate = scelta_griglia.get("selection", {}).get("rows", [])
        
        if righe_selezionate:
            # Recuperiamo l'indice della riga selezionata nel DataFrame originale
            indice_selezionato = righe_selezionate[0]
            info_contatto = contatti_df.iloc[indice_selezionato]
            contatto_id = info_contatto["id"]
            nome_completo = f"{info_contatto['nome']} {info_contatto['cognome']}"
            
            st.write("---")
            st.subheader(f"⚙️ Azioni per: {nome_completo}")
            
            # Layout con i pulsanti di gestione sotto la tabella
            col_btn1, col_btn2, _ = st.columns([1, 1, 4])
            
            with col_btn1:
                mostra_form_modifica = st.checkbox("📝 Modifica Anagrafica", value=False, key=f"check_mod_{contatto_id}")
            with col_btn2:
                if st.button("🗑️ Elimina Contatto", type="primary", key=f"btn_del_{contatto_id}"):
                    conferma_eliminazione_dialog(contatto_id, nome_completo)
            
            # Se la spunta di modifica è attiva, mostriamo il form precompilato
            if mostra_form_modifica:
                tutti_utenti = leggi_query("SELECT id, username FROM utenti")
                dict_utenti = dict(zip(tutti_utenti['username'], tutti_utenti['id']))
                
                with st.form(f"modifica_contatto_tabella_{contatto_id}"):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        nuovo_nome = st.text_input("Nome *", value=info_contatto['nome'])
                        nuovo_cognome = st.text_input("Cognome *", value=info_contatto['cognome'])
                        nuovo_ruolo = st.text_input("Ruolo / Lavoro", value=info_contatto['ruolo'] if pd.notna(info_contatto['ruolo']) else "")
                        nuova_azienda = st.text_input("Azienda", value=info_contatto['azienda'] if pd.notna(info_contatto['azienda']) else "")
                    with col_m2:
                        nuova_email = st.text_input("Email", value=info_contatto['email'] if pd.notna(info_contatto['email']) else "")
                        nuovo_telefono = st.text_input("Telefono", value=info_contatto['telefono'] if pd.notna(info_contatto['telefono']) else "")
                        
                        idx_prov = OPZIONI_PROVENIENZA.index(info_contatto['provenienza_lead']) if info_contatto['provenienza_lead'] in OPZIONI_PROVENIENZA else 0
                        nuova_provenienza = st.selectbox("Provenienza Lead", OPZIONI_PROVENIENZA, index=idx_prov)
                        
                        if pd.notna(info_contatto['utente_id']) and info_contatto['utente_id'] in tutti_utenti['id'].values:
                            utente_corrente_nome = tutti_utenti[tutti_utenti['id'] == info_contatto['utente_id']]['username'].values[0]
                            idx_utente_sel = list(dict_utenti.keys()).index(utente_corrente_nome)
                        else:
                            idx_utente_sel = 0
                            
                        nuovo_assegnato = st.selectbox("Assegnato a Utente", list(dict_utenti.keys()), index=idx_utente_sel)
                    
                    if st.form_submit_button("Salva Modifiche"):
                        if nuovo_nome.strip() and nuovo_cognome.strip():
                            esegui_query(
                                "UPDATE contatti SET nome=:n, cognome=:c, azienda=:a, email=:e, telefono=:t, ruolo=:r, provenienza_lead=:p, utente_id=:uid WHERE id=:id",
                                {"n": nuovo_nome, "c": nuovo_cognome, "a": nuova_azienda, "e": nuova_email, "t": nuovo_telefono, "r": nuovo_ruolo, "p": nuova_provenienza, "uid": dict_utenti[nuovo_assegnato], "id": int(contatto_id)}
                            )
                            st.success("Contatto aggiornato con successo!")
                            st.rerun()
                        else:
                            st.error("I campi Nome e Cognome sono obbligatori.")
            
            # Mostra lo storico delle attività del contatto selezionato in fondo
            st.write("---")
            st.write(f"### 📋 Storico Attività per {nome_completo}")
            attivita_df = leggi_query("SELECT descrizione as \"Attività\", data_scadenza as \"Scadenza\", stato as \"Stato\" FROM attivita WHERE contatto_id = :cid ORDER BY data_scadenza DESC", {"cid": int(contatto_id)})
            if not attivita_df.empty:
                attivita_df["Scadenza"] = pd.to_datetime(attivita_df["Scadenza"]).dt.strftime('%d/%m/%Y')
                st.dataframe(attivita_df, use_container_width=True)
            else: 
                st.info("Nessuna attività registrata per questo contatto.")
        else:
            st.info("Seleziona un contatto dalla tabella sopra per vederne i dettagli, modificarlo o eliminarlo.")
    else: 
        st.info("Nessun contatto trovato con i criteri di filtro attuali.")

# 2. AGGIUNGI CONTATTO
elif macro_sezione == "👥 Contatti" and sotto_sezione == "➕ Aggiungi Contatto":
    st.header("Inserimento Nuovo Contatto")
    tutti_utenti = leggi_query("SELECT id, username FROM utenti")
    dict_utenti = dict(zip(tutti_utenti['username'], tutti_utenti['id']))
    
    with st.form(f"nuovo_contatto_{st.session_state.contact_form_version}"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            cognome = st.text_input("Cognome *")
            ruolo = st.text_input("Ruolo / Lavoro")
            azienda = st.text_input("Azienda")
        with col2:
            email = st.text_input("Email")
            telefono = st.text_input("Telefono")
            provenienza = st.selectbox("Provenienza Lead", OPZIONI_PROVENIENZA)
            assegna_a = st.selectbox("Assegna a Utente", list(dict_utenti.keys()), index=list(dict_utenti.keys()).index(st.session_state.username))
        
        if st.form_submit_button("Salva in Anagrafica"):
            if nome.strip() and cognome.strip():
                esegui_query(
                    "INSERT INTO contatti (nome, cognome, azienda, email, telefono, ruolo, provenienza_lead, utente_id) VALUES (:nome, :cognome, :azienda, :email, :telefono, :ruolo, :prov, :uid)",
                    {"nome": nome, "cognome": cognome, "azienda": azienda, "email": email, "telefono": telefono, "ruolo": ruolo, "prov": provenienza, "uid": dict_utenti[assegna_a]}
                )
                st.session_state.contact_form_version += 1
                st.success("Contatto salvato con successo!")
                st.rerun()
            else:
                st.error("I campi Nome e Cognome sono obbligatori.")

# 3. RIEPILOGO SCADENZE ATTIVITÀ
elif macro_sezione == "📅 Attività" and sotto_sezione == "🔍 Riepilogo Scadenze":
    st.header("Riepilogo Scadenze Attività")
    oggi = datetime.today()
    tra_sette_giorni = oggi + timedelta(days=7)
    
    col1, col2 = st.columns(2)
    with col1: data_inizio = st.date_input("Da data", oggi, format="DD/MM/YYYY")
    with col2: data_fine = st.date_input("A data", tra_sette_giorni, format="DD/MM/YYYY")
        
    if mostra_tutti:
        query = """
        SELECT a.id as "ID Attività", c.nome || ' ' || c.cognome as "Contatto", c.azienda as "Azienda", a.descrizione as "Attività", a.data_scadenza as "Data Scadenza", a.stato as "Stato"
        FROM attivita a JOIN contatti c ON a.contatto_id = c.id
        WHERE a.data_scadenza BETWEEN :inizio AND :fine ORDER BY a.data_scadenza ASC
        """
        df_riepilogo = leggi_query(query, {"inizio": data_inizio, "fine": data_fine})
    else:
        query = """
        SELECT a.id as "ID Attività", c.nome || ' ' || c.cognome as "Contatto", c.azienda as "Azienda", a.descrizione as "Attività", a.data_scadenza as "Data Scadenza", a.stato as "Stato"
        FROM attivita a JOIN contatti c ON a.contatto_id = c.id
        WHERE c.utente_id = :uid AND a.data_scadenza BETWEEN :inizio AND :fine ORDER BY a.data_scadenza ASC
        """
        df_riepilogo = leggi_query(query, {"uid": st.session_state.user_id, "inizio": data_inizio, "fine": data_fine})
    
    if not df_riepilogo.empty:
        df_riepilogo["Data Scadenza"] = pd.to_datetime(df_riepilogo["Data Scadenza"]).dt.strftime('%d/%m/%Y')
        st.dataframe(df_riepilogo, use_container_width=True)
    else: 
        st.info("Nessuna attività programmata in questo intervallo di date.")

# 4. AGGIUNGI ATTIVITÀ
elif macro_sezione == "📅 Attività" and sotto_sezione == "➕ Aggiungi Attività":
    st.header("Pianifica Nuova Attività")
    
    if mostra_tutti:
        contatti_df = leggi_query("SELECT id, nome, cognome, azienda FROM contatti")
    else:
        contatti_df = leggi_query("SELECT id, nome, cognome, azienda FROM contatti WHERE utente_id = :uid", {"uid": st.session_state.user_id})
    
    if not contatti_df.empty:
        contatti_df["nominativo"] = contatti_df["nome"] + " " + contatti_df["cognome"] + " (" + contatti_df["azienda"].fillna("") + ")"
        with st.form(f"nuova_attivita_{st.session_state.activity_form_version}"):
            contatto_scelto = st.selectbox("Associa a Contatto", contatti_df["nominativo"])
            descrizione = st.text_area("Descrizione dell'attività *")
            data_scadenza = st.date_input("Data Scadenza", datetime.today(), format="DD/MM/YYYY")
            stato = st.selectbox("Stato", ["Da fare", "In corso", "Completata"])
            
            if st.form_submit_button("Pianifica Attività"):
                if descrizione.strip():
                    contatto_id = contatti_df[contatti_df["nominativo"] == contatto_scelto]["id"].values[0]
                    esegui_query("INSERT INTO attivita (contatto_id, descrizione, data_scadenza, stato) VALUES (:cid, :desc, :scad, :stato)",
                                 {"cid": int(contatto_id), "desc": descrizione, "scad": data_scadenza, "stato": stato})
                    st.session_state.activity_form_version += 1
                    st.success("Attività pianificata!")
                    st.rerun()
                else:
                    st.error("La descrizione è obbligatoria.")
    else: 
        st.warning("Nessun contatto disponibile per la pianificazione delle attività.")

# 5. GESTIONE E MODIFICA ATTIVITÀ
elif macro_sezione == "📅 Attività" and sotto_sezione == "⚙️ Gestione Attività":
    st.header("Gestione e Modifica Attività")
    
    if mostra_tutti:
        query_all_attivita = """
        SELECT a.id as attivita_id, c.nome || ' ' || c.cognome || ' (' || COALESCE(c.azienda, '') || ')' as contatto_info, a.descrizione, a.data_scadenza, a.stato
        FROM attivita a JOIN contatti c ON a.contatto_id = c.id ORDER BY a.data_scadenza ASC
        """
        attivita_totali_df = leggi_query(query_all_attivita)
    else:
        query_all_attivita = """
        SELECT a.id as attivita_id, c.nome || ' ' || c.cognome || ' (' || COALESCE(c.azienda, '') || ')' as contatto_info, a.descrizione, a.data_scadenza, a.stato
        FROM attivita a JOIN contatti c ON a.contatto_id = c.id WHERE c.utente_id = :uid ORDER BY a.data_scadenza ASC
        """
        attivita_totali_df = leggi_query(query_all_attivita, {"uid": st.session_state.user_id})
    
    if not attivita_totali_df.empty:
        attivita_totali_df["label_scelta"] = "[" + attivita_totali_df["stato"] + "] " + attivita_totali_df["contatto_info"] + " - " + attivita_totali_df["descrizione"].str.slice(0, 40) + "..."
        scelta_att = st.selectbox("Seleziona l'attività:", attivita_totali_df["label_scelta"])
        
        if scelta_att:
            dati_att = attivita_totali_df[attivita_totali_df["label_scelta"] == scelta_att].iloc[0]
            id_att_selezionata = dati_att["attivita_id"]
            
            with st.form("modifica_attivita_form"):
                nuova_descrizione = st.text_area("Descrizione *", value=dati_att["descrizione"])
                data_attuale_att = pd.to_datetime(dati_att["data_scadenza"]).date()
                nuova_data = st.date_input("Data Scadenza", data_attuale_att, format="DD/MM/YYYY")
                stati_possibili = ["Da fare", "In corso", "Completata"]
                nuovo_stato = st.selectbox("Stato", stati_possibili, index=stati_possibili.index(dati_att["stato"]))
                
                if st.form_submit_button("Salva Modifiche"):
                    if nuova_descrizione.strip():
                        esegui_query("UPDATE attivita SET descrizione=:desc, data_scadenza=:scad, stato=:stato WHERE id=:id",
                                     {"desc": nuova_descrizione, "scad": nuova_data, "stato": nuovo_stato, "id": int(id_att_selezionata)})
                        st.success("Attività aggiornata!")
                        st.rerun()
            
            st.write("---")
            if st.button("Elimina definitivamente questa attività", type="primary"):
                conferma_eliminazione_attivita_dialog(id_att_selezionata, dati_att["descrizione"][:30])
    else: 
        st.info("Nessuna attività in scadenziario corrispondente ai criteri selezionati.")