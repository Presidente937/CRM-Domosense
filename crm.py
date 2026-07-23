import streamlit as st
import pandas as pd
import bcrypt
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from st_keyup import st_keyup
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# Inizializzazione del gestore Cookie
cookie_manager = stx.CookieManager()

# CONFIGURAZIONE SUPABASE
DATABASE_URL = st.secrets["DATABASE_URL"]

@st.cache_resource
def ottieni_engine():
    return create_engine(DATABASE_URL)

engine = ottieni_engine()

st.set_page_config(page_title="Domosense CRM", layout="wide")

# SOSTITUISCI IL BLOCCO DI INIZIALIZZAZIONE CON QUESTO:
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
if "messaggio_successo_contatto" not in st.session_state:
    st.session_state.messaggio_successo_contatto = None
if "messaggio_successo_attivita" not in st.session_state:
    st.session_state.messaggio_successo_attivita = None
if "chiave_griglia_contatti" not in st.session_state:
    st.session_state.chiave_griglia_contatti = 0
if "chiave_griglia_scadenze" not in st.session_state:  # <-- Aggiunto
    st.session_state.chiave_griglia_scadenze = 0

# Funzione per eseguire query di scrittura in sicurezza
def esegui_query(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        return True
    except Exception as e:
        st.error(f"⚠️ Si è verificato un errore durante il salvataggio: {e}")
        return False

# Lettura dati ottimizzata con Cache
@st.cache_data(ttl=300)
def leggi_query(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})

# Finestre modali di conferma eliminazione
@st.dialog("Conferma Eliminazione Contatto")
def conferma_eliminazione_dialog(contatto_id, nome_completo):
    st.warning(f"Sei sicuro di voler eliminare definitivamente **{nome_completo}**?")
    col_conferma, col_annulla = st.columns(2)
    with col_conferma:
        if st.button("Sì, elimina", type="primary", use_container_width=True):
            esegui_query("DELETE FROM contatti WHERE id = :id", {"id": int(contatto_id)})
            st.cache_data.clear()
            st.success("Contatto eliminato!")
            st.rerun()
    with col_annulla:
        if st.button("Annulla", use_container_width=True): 
            st.rerun()

@st.dialog("Conferma Eliminazione Attività")
def conferma_eliminazione_attivita_dialog(attivita_id, descrizione_breve):
    st.warning(f"Sei sicuro di voler eliminare l'attività: **\"{descrizione_breve}\"**?")
    col_conferma, col_annulla = st.columns(2)
    with col_conferma:
        if st.button("Sì, elimina", type="primary", use_container_width=True):
            esegui_query("DELETE FROM attivita WHERE id = :id", {"id": int(attivita_id)})
            st.cache_data.clear()
            st.success("Attività eliminata!")
            st.rerun()
    with col_annulla:
        if st.button("Annulla", use_container_width=True): 
            st.rerun()

OPZIONI_PROVENIENZA = ["Social", "BNI", "Fiere/Eventi in presenza"]

# ==================== SCHERMATA DI LOGIN & PERSISTENZA ====================

# 1. Verifichiamo se esiste già un cookie salvato nel browser
saved_user_id = cookie_manager.get(cookie="domosense_crm_uid")

if saved_user_id and not st.session_state.logged_in:
    with engine.connect() as conn:
        user_df = pd.read_sql_query(
            text("SELECT id, username FROM utenti WHERE id = :uid"),
            conn, params={"uid": int(saved_user_id)}
        )
        if not user_df.empty:
            st.session_state.logged_in = True
            st.session_state.user_id = int(user_df.iloc[0]['id'])
            st.session_state.username = user_df.iloc[0]['username']

# 2. Se l'utente non è loggato (e non ha cookie), mostra la form di Login
if not st.session_state.logged_in:
    st.title("🔒 Domosense CRM - Accesso")
    
    with st.form("login_form"):
        st.subheader("Inserisci le tue credenziali")
        username_input = st.text_input("Nome utente")
        password_input = st.text_input("Password", type="password")
        submit_login = st.form_submit_button("Accedi")
        
        if submit_login:
            with engine.connect() as conn:
                user_df = pd.read_sql_query(
                    text("SELECT id, username, password FROM utenti WHERE username = :user"),
                    conn, params={"user": username_input.strip()}
                )
            
            if not user_df.empty:
                stored_hash = user_df.iloc[0]['password']
                password_corretta = bcrypt.checkpw(
                    password_input.strip().encode('utf-8'), 
                    stored_hash.encode('utf-8')
                )
                
                if password_corretta:
                    uid = int(user_df.iloc[0]['id'])
                    st.session_state.logged_in = True
                    st.session_state.user_id = uid
                    st.session_state.username = user_df.iloc[0]['username']
                    
                    # Salva il Cookie nel browser per 7 giorni
                    scadenza_cookie = datetime.now() + timedelta(days=7)
                    cookie_manager.set('domosense_crm_uid', str(uid), expires_at=scadenza_cookie)
                    
                    st.success("Accesso effettuato!")
                    st.rerun()
                else:
                    st.error("Nome utente o Password errati.")
            else:
                st.error("Nome utente o Password errati.")
    st.stop()

# ==================== APPLICATIVO LOGGATO ====================

# ==================== APPLICATIVO LOGGATO ====================

# --- BARRA LATERALE: SOLO AZIONI GLOBALI E UTENTE ---
st.sidebar.title("📁 Menu Principale")
st.sidebar.write(f"👤 Utente: **{st.session_state.username}**")
mostra_tutti = st.sidebar.checkbox("👀 Mostra dati di tutti gli utenti", value=False)

# --- NUOVE METRICHE KPI NELLA BARRA LATERALE ---
st.sidebar.write("---")
st.sidebar.subheader("📊 Metriche Rapide")

# Calcolo contatori dinamico in base alla spunta "mostra_tutti"
if mostra_tutti:
    tot_contatti = leggi_query("SELECT COUNT(*) as tot FROM contatti").iloc[0]['tot']
    tot_da_fare = leggi_query("SELECT COUNT(*) as tot FROM attivita WHERE stato = 'Da fare'").iloc[0]['tot']
else:
    tot_contatti = leggi_query("SELECT COUNT(*) as tot FROM contatti WHERE utente_id = :uid", {"uid": st.session_state.user_id}).iloc[0]['tot']
    tot_da_fare = leggi_query("""
        SELECT COUNT(*) as tot 
        FROM attivita a 
        JOIN contatti c ON a.contatto_id = c.id 
        WHERE c.utente_id = :uid AND a.stato = 'Da fare'
    """, {"uid": st.session_state.user_id}).iloc[0]['tot']

col_kpi1, col_kpi2 = st.columns(2)
with st.sidebar:
    col_k1, col_k2 = st.columns(2)
    col_k1.metric("👥 Contatti", tot_contatti)
    col_k2.metric("📋 Da Fare", tot_da_fare)

st.sidebar.write("---")
if st.sidebar.button("Logout", type="secondary", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    
    # Cancella il Cookie di sessione dal browser
    cookie_manager.delete('domosense_crm_uid')
    
    st.cache_data.clear() 
    st.rerun()

# ==================== AREA CENTRALE ULTRA-RAPIDA (TABS AD ALBERO) ====================
st.title("Domosense CRM")

# Primo livello di Tab: Macro-Aree (Il passaggio qui diventa istantaneo)
tab_macro_contatti, tab_macro_attivita = st.tabs(["👥 Sezione Contatti", "📅 Sezione Attività"])

# ==================== 1. MACRO TAB: CONTATTI ====================
with tab_macro_contatti:
    # Secondo livello di Tab: Sottomenu interni
    sotto_tab_info, sotto_tab_add_c = st.tabs(["ℹ️ Info e Gestione Contatto", "➕ Aggiungi Contatto"])
    
    # --- SOTTOMENU: INFO E GESTIONE CONTATTO ---
        # --- SOTTOMENU: INFO E GESTIONE CONTATTO ---
    with sotto_tab_info:
        if mostra_tutti:
            query_contatti = """
                SELECT c.id, c.nome, c.cognome, c.ruolo, c.azienda, c.provenienza_lead, c.email, c.telefono, u.username as assegnato_a
                FROM contatti c
                LEFT JOIN utenti u ON c.utente_id = u.id
                ORDER BY c.cognome ASC
            """
            contatti_df = leggi_query(query_contatti)
        else:
            query_contatti = """
                SELECT c.id, c.nome, c.cognome, c.ruolo, c.azienda, c.provenienza_lead, c.email, c.telefono, u.username as assegnato_a
                FROM contatti c
                LEFT JOIN utenti u ON c.utente_id = u.id
                WHERE c.utente_id = :uid
                ORDER BY c.cognome ASC
            """
            contatti_df = leggi_query(query_contatti, {"uid": st.session_state.user_id})

        if not contatti_df.empty:
            # --- BARRA DI RICERCA ED ESPORTAZIONE AFFIANCATE ---
            col_ricerca, col_reset, col_export = st.columns([3, 1, 1])
            
            with col_ricerca:
                cerca_termine = st_keyup(
                    "🔍 Cerca contatto (Nome, Cognome o Azienda)", 
                    value="", 
                    key=f"cerca_contatto_input_{st.session_state.chiave_griglia_contatti}",
                    debounce=200
                ).strip()
            
            with col_reset:
                st.write("") # Spaziatori per allineare il pulsante in basso
                st.write("")
                if st.button("🔄 Reset", use_container_width=True, key="btn_reset_contatti"):
                    st.session_state.chiave_griglia_contatti += 1
                    st.rerun()
            
            with col_export:
                st.write("") 
                st.write("") 
                csv_data = contatti_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Esporta CSV",
                    data=csv_data,
                    file_name=f"contatti_domosense_{datetime.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            contatti_visualizzazione = contatti_df.copy()
            contatti_visualizzazione.columns = ["ID", "Nome", "Cognome", "Ruolo", "Azienda", "Provenienza", "Email", "Telefono", "Assegnato a"]
            
            # Applica il filtro se l'utente scrive qualcosa
            if cerca_termine:
                maschera_ricerca = (
                    contatti_visualizzazione["Nome"].str.contains(cerca_termine, case=False, na=False) |
                    contatti_visualizzazione["Cognome"].str.contains(cerca_termine, case=False, na=False) |
                    contatti_visualizzazione["Azienda"].str.contains(cerca_termine, case=False, na=False)
                )
                contatti_visualizzazione = contatti_visualizzazione[maschera_ricerca]
            
            # Ordinamento alfabetico di default per Cognome, poi Nome
            contatti_visualizzazione = contatti_visualizzazione.sort_values(by=["Cognome", "Nome"], ascending=True)
            
            # Griglia con chiave dinamica
            scelta_griglia = st.dataframe(
                contatti_visualizzazione,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={"ID": None}, 
                key=f"griglia_contatti_main_{st.session_state.chiave_griglia_contatti}"
            )
            
            
            righe_selezionate = scelta_griglia.get("selection", {}).get("rows", [])
            
            if righe_selezionate:
                indice_selezionato = righe_selezionate[0]
                
                # Controllo di sicurezza: verifichiamo che l'indice esista nel DataFrame filtrato
                if indice_selezionato < len(contatti_visualizzazione):
                    info_contatto = contatti_visualizzazione.iloc[indice_selezionato]
                else:
                    # Se l'indice è fuori dai limiti (es. causa ricerca), resettiamo la griglia in sicurezza
                    st.session_state.chiave_griglia_contatti += 1
                    st.rerun()
                contatto_id = info_contatto["ID"]
                nome_completo = f"{info_contatto['Nome']} {info_contatto['Cognome']}"
                
                st.write("---")
                st.subheader(f"⚙️ Gestione di: {nome_completo}")
                
                col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 4])
                with col_btn1:
                    mostra_form_modifica = st.checkbox("📝 Modifica Anagrafica", value=False, key=f"check_mod_{contatto_id}")
                with col_btn2:
                    if st.button("🗑️ Elimina Contatto", type="primary", key=f"btn_del_{contatto_id}"):
                        conferma_eliminazione_dialog(int(contatto_id), nome_completo)
                
                if mostra_form_modifica:
                    tutti_utenti = leggi_query("SELECT id, username FROM utenti")
                    dict_utenti = dict(zip(tutti_utenti['username'], tutti_utenti['id']))
                    
                    with st.form(f"modifica_contatto_{contatto_id}"):
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            nuovo_nome = st.text_input("Nome *", value=info_contatto['Nome'])
                            nuovo_cognome = st.text_input("Cognome *", value=info_contatto['Cognome'])
                            nuovo_ruolo = st.text_input("Ruolo / Lavoro", value=info_contatto['Ruolo'] if pd.notna(info_contatto['Ruolo']) else "")
                            nuova_azienda = st.text_input("Azienda", value=info_contatto['Azienda'] if pd.notna(info_contatto['Azienda']) else "")
                        with col_m2:
                            nuova_email = st.text_input("Email", value=info_contatto['Email'] if pd.notna(info_contatto['Email']) else "")
                            nuovo_telefono = st.text_input("Telefono", value=info_contatto['Telefono'] if pd.notna(info_contatto['Telefono']) else "")
                            nuova_provenienza = st.selectbox("Provenienza Lead", OPZIONI_PROVENIENZA, index=OPZIONI_PROVENIENZA.index(info_contatto['Provenienza']) if info_contatto['Provenienza'] in OPZIONI_PROVENIENZA else 0)
                            
                            utente_corrente_nome = info_contatto['Assegnato a']
                            idx_ut = list(dict_utenti.keys()).index(utente_corrente_nome) if (pd.notna(utente_corrente_nome) and utente_corrente_nome in dict_utenti) else 0
                            nuovo_assegnato = st.selectbox("Assegnato a Utente", list(dict_utenti.keys()), index=idx_ut)
                        
                        if st.form_submit_button("Salva Modifiche"):
                            # 1. Verifica campi obbligatori Nome e Cognome
                            if not (nuovo_nome.strip() and nuovo_cognome.strip()):
                                st.error("⚠️ Nome e Cognome non possono essere vuoti!")
                            # 2. Validazione formato Email (se compilata)
                            elif nuova_email.strip() and ("@" not in nuova_email or "." not in nuova_email):
                                st.error("⚠️ Inserisci un indirizzo Email valido (es. nome@dominio.it).")
                            # 3. Validazione Telefono (se compilato)
                            elif nuovo_telefono.strip() and not any(char.isdigit() for char in nuovo_telefono):
                                st.error("⚠️ Il numero di Telefono inserito non sembra valido.")
                            else:
                                # Se tutti i controlli passano, esegui l'aggiornamento
                                esegui_query(
                                    "UPDATE contatti SET nome=:n, cognome=:c, azienda=:a, email=:e, telefono=:t, ruolo=:r, provenienza_lead=:p, utente_id=:uid WHERE id=:id",
                                    {"n": nuovo_nome.strip(), "c": nuovo_cognome.strip(), "a": nuova_azienda.strip(), "e": nuova_email.strip(), "t": nuovo_telefono.strip(), "r": nuovo_ruolo.strip(), "p": nuova_provenienza, "uid": dict_utenti[nuovo_assegnato], "id": int(contatto_id)}
                                )
                                st.cache_data.clear()
                                st.session_state.chiave_griglia_contatti += 1
                                st.success("Contatto aggiornato!")
                                st.rerun()
                
                st.write("---")
                st.write("### 📋 Storico Rapido Attività")
                attivita_df = leggi_query("SELECT descrizione as \"Attività\", data_scadenza as \"Scadenza\", stato as \"Stato\" FROM attivita WHERE contatto_id = :cid ORDER BY data_scadenza DESC", {"cid": int(contatto_id)})
                if not attivita_df.empty:
                    attivita_df["Scadenza"] = pd.to_datetime(attivita_df["Scadenza"]).dt.strftime('%d/%m/%Y')
                    st.dataframe(attivita_df, use_container_width=True)
                else: 
                    st.info("Nessuna attività registrata per questo contatto.")
        else: 
            st.info("Nessun contatto trovato.")

    # --- SOTTOMENU: AGGIUNGI CONTATTO ---
    with sotto_tab_add_c:
        if st.session_state.messaggio_successo_contatto:
            st.success(st.session_state.messaggio_successo_contatto)
            
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
                # 1. Verifica campi obbligatori Nome e Cognome
                if not (nome.strip() and cognome.strip()):
                    st.error("⚠️ Nome e Cognome sono campi obbligatori!")
                # 2. Validazione formato Email (se compilata)
                elif email.strip() and ("@" not in email or "." not in email):
                    st.error("⚠️ Inserisci un indirizzo Email valido (es. nome@dominio.it).")
                # 3. Validazione Telefono (se compilato, controlla che contenga solo cifre, spazi o +)
                elif telefono.strip() and not any(char.isdigit() for char in telefono):
                    st.error("⚠️ Il numero di Telefono inserito non sembra valido.")
                else:
                    # Se tutti i controlli passano, esegui il salvataggio
                    esegui_query(
                        "INSERT INTO contatti (nome, cognome, azienda, email, telefono, ruolo, provenienza_lead, utente_id) VALUES (:nome, :cognome, :azienda, :email, :telefono, :ruolo, :prov, :uid)",
                        {"nome": nome.strip(), "cognome": cognome.strip(), "azienda": azienda.strip(), "email": email.strip(), "telefono": telefono.strip(), "ruolo": ruolo.strip(), "prov": provenienza, "uid": dict_utenti[assegna_a]}
                    )
                    st.cache_data.clear()
                    st.session_state.messaggio_successo_contatto = f"✅ Contatto \"{nome} {cognome}\" aggiunto con successo!"
                    st.session_state.contact_form_version += 1
                    st.rerun()

# ==================== 2. MACRO TAB: ATTIVITÀ ====================
with tab_macro_attivita:
    # Secondo livello di Tab per le attività (Rinominata la prima scheda)
    sotto_tab_scad, sotto_tab_add_a, sotto_tab_gest_a = st.tabs(["🔍 Riepilogo Scadenze Attività", "➕ Aggiungi Attività", "⚙️ Gestione Attività"])
    
    # --- SOTTOMENU: RIEPILOGO SCADENZE ATTIVITÀ ---
    with sotto_tab_scad:
        oggi = datetime.today()
        tra_sette_giorni = oggi + timedelta(days=7)
    
        col1, col2 = st.columns(2)
        with col1: data_inizio = st.date_input("Da data", oggi, format="DD/MM/YYYY")
        with col2: data_fine = st.date_input("A data", tra_sette_giorni, format="DD/MM/YYYY")
        
        # Aggiungiamo 1 giorno a data_fine per catturare tutte le scadenze dell'ultimo giorno
        data_fine_esclusiva = data_fine + timedelta(days=1)
    
        if mostra_tutti:
            query = """
                SELECT u.username as "Assegnato a", c.nome || ' ' || c.cognome as "Contatto", c.azienda as "Azienda", 
                   a.descrizione as "Attività", a.data_scadenza as "Data Scadenza", a.stato as "Stato", a.contatto_id
                FROM attivita a 
                JOIN contatti c ON a.contatto_id = c.id
                LEFT JOIN utenti u ON c.utente_id = u.id
                WHERE a.data_scadenza >= :inizio AND a.data_scadenza < :fine 
                ORDER BY a.data_scadenza ASC
            """
            df_riepilogo = leggi_query(query, {"inizio": data_inizio.isoformat(), "fine": data_fine_esclusiva.isoformat()})
        else:
            query = """
                SELECT u.username as "Assegnato a", c.nome || ' ' || c.cognome as "Contatto", c.azienda as "Azienda", 
                   a.descrizione as "Attività", a.data_scadenza as "Data Scadenza", a.stato as "Stato", a.contatto_id
                FROM attivita a 
                JOIN contatti c ON a.contatto_id = c.id
                LEFT JOIN utenti u ON c.utente_id = u.id
                WHERE c.utente_id = :uid AND a.data_scadenza >= :inizio AND a.data_scadenza < :fine 
                ORDER BY a.data_scadenza ASC
            """
            df_riepilogo = leggi_query(query, {"uid": st.session_state.user_id, "inizio": data_inizio.isoformat(), "fine": data_fine_esclusiva.isoformat()})
        
        if not df_riepilogo.empty:
            st.write("🔍 **Ricerca rapida scadenze** (digita per filtrare all'istante):")
            
            # st.chat_input cattura la digitazione in tempo reale senza vincoli di 'Invio'
                    # --- RICERCA E RESET SCADENZE AFFIANCATI ---
            col_cerca_att, col_reset_att = st.columns([4, 1])
        
            with col_cerca_att:
                cerca_attivita = st_keyup(
                    "🔍 Cerca attività (Contatto, Azienda o Descrizione):", 
                    value="", 
                    key=f"cerca_attivita_input_{st.session_state.chiave_griglia_scadenze}",
                    debounce=200
                ).strip()
            
            with col_reset_att:
                st.write("") # Spaziatori per allineare il pulsante
                st.write("")
                if st.button("🔄 Reset Filtri", use_container_width=True, key="btn_reset_scadenze"):
                    st.session_state.chiave_griglia_scadenze += 1
                    st.rerun()
                df_visualizzazione = df_riepilogo.copy()
            
            # Applica il filtro drastico: restano SOLO le righe che corrispondono alla ricerca
            if cerca_attivita:
                cerca_attivita = cerca_attivita.strip()
                maschera_ricerca = (
                    df_visualizzazione["Contatto"].str.contains(cerca_attivita, case=False, na=False) |
                    df_visualizzazione["Azienda"].str.contains(cerca_attivita, case=False, na=False) |
                    df_visualizzazione["Attività"].str.contains(cerca_attivita, case=False, na=False)
                )
                df_visualizzazione = df_visualizzazione[maschera_ricerca]
            
            # Formattiamo la data dopo il filtraggio
            df_visualizzazione["Data Scadenza"] = pd.to_datetime(df_visualizzazione["Data Scadenza"]).dt.strftime('%d/%m/%Y')
            
            # Mostra solo i risultati filtrati
            scelta_scadenze = st.dataframe(
                df_visualizzazione,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={"contatto_id": None}, 
                key=f"griglia_scadenze_attivita_{st.session_state.get('chiave_griglia_scadenze', 0)}"
            )
            
            righe_selezionate = scelta_scadenze.get("selection", {}).get("rows", [])
            
            if righe_selezionate and righe_selezionate[0] < len(df_visualizzazione):
                riga_info = df_visualizzazione.iloc[righe_selezionate[0]]
                id_contatto_selezionato = riga_info["contatto_id"]
                nome_contatto_selezionato = riga_info["Contatto"]
                
                st.write("")
                if st.button(f"📊 Mostra Storico Attività di {nome_contatto_selezionato}", type="secondary"):
                    st.write(f"### 📋 Storico Attività Completo: {nome_contatto_selezionato}")
                    
                    query_storico = """
                        SELECT descrizione as "Attività", data_scadenza as "Scadenza", stato as "Stato" 
                        FROM attivita 
                        WHERE contatto_id = :cid 
                        ORDER BY data_scadenza DESC
                    """
                    storico_df = leggi_query(query_storico, {"cid": int(id_contatto_selezionato)})
                    
                    if not storico_df.empty:
                        storico_df["Scadenza"] = pd.to_datetime(storico_df["Scadenza"]).dt.strftime('%d/%m/%Y')
                        st.dataframe(storico_df, use_container_width=True)
                    else:
                        st.info("Nessuna attività in storico per questo contatto.")
                        
            elif righe_selezionate:
                st.session_state.chiave_griglia_scadenze = st.session_state.get('chiave_griglia_scadenze', 0) + 1
                st.rerun()
            # ----------------------------------
        
        else: 
            st.info("Nessuna attività in questo intervallo di date.")

    # --- SOTTOMENU: AGGIUNGI ATTIVITÀ ---
    with sotto_tab_add_a:
        if st.session_state.messaggio_successo_attivita:
            st.success(st.session_state.messaggio_successo_attivita)
        
        if mostra_tutti:
            contatti_df = leggi_query("SELECT id, nome, cognome, azienda FROM contatti ORDER BY cognome ASC, nome ASC")
        else:
            contatti_df = leggi_query("SELECT id, nome, cognome, azienda FROM contatti WHERE utente_id = :uid ORDER BY cognome ASC, nome ASC", {"uid": st.session_state.user_id})
    
        if not contatti_df.empty:
            # Creiamo un dizionario ID -> Nominativo per evitare collisioni su nomi uguali
            mappa_contatti = {
                row['id']: f"{row['cognome']} {row['nome']} ({row['azienda'] if pd.notna(row['azienda']) else ''})"
                for _, row in contatti_df.iterrows()
            }
        
            with st.form(f"nuova_attivita_{st.session_state.activity_form_version}"):
                contatto_id_scelto = st.selectbox(
                    "Associa a Contatto", 
                    options=list(mappa_contatti.keys()), 
                    format_func=lambda cid: mappa_contatti[cid]
                )
                descrizione = st.text_area("Descrizione dell'attività *")
                data_scadenza = st.date_input("Data Scadenza", datetime.today(), format="DD/MM/YYYY")
                stato = st.selectbox("Stato", ["Da fare", "In corso", "Completata"])
            
                if st.form_submit_button("Pianifica Attività"):
                    if descrizione.strip():
                        esegui_query(
                            "INSERT INTO attivita (contatto_id, descrizione, data_scadenza, stato) VALUES (:cid, :desc, :scad, :stato)",
                            {"cid": int(contatto_id_scelto), "desc": descrizione, "scad": data_scadenza, "stato": stato}
                        )
                        st.cache_data.clear()
                        st.session_state.messaggio_successo_attivita = "✅ Nuova attività pianificata!"
                        st.session_state.activity_form_version += 1
                        st.rerun()
        else:
            st.warning("Nessun contatto disponibile. Aggiungi prima un contatto per poter pianificare un'attività.")

    # --- SOTTOMENU: GESTIONE ATTIVITÀ ---
    with sotto_tab_gest_a:
        if mostra_tutti:
            query_all_attivita = """
                SELECT a.id as attivita_id, c.cognome || ' ' || c.nome || ' (' || COALESCE(c.azienda, '') || ')' as contatto_info, a.descrizione, a.data_scadenza, a.stato
                FROM attivita a JOIN contatti c ON a.contatto_id = c.id 
                ORDER BY c.cognome ASC, c.nome ASC, a.data_scadenza ASC
            """
            attivita_totali_df = leggi_query(query_all_attivita)
        else:
            query_all_attivita = """
                SELECT a.id as attivita_id, c.cognome || ' ' || c.nome || ' (' || COALESCE(c.azienda, '') || ')' as contatto_info, a.descrizione, a.data_scadenza, a.stato
                FROM attivita a JOIN contatti c ON a.contatto_id = c.id 
                WHERE c.utente_id = :uid 
                ORDER BY c.cognome ASC, c.nome ASC, a.data_scadenza ASC
            """
            attivita_totali_df = leggi_query(query_all_attivita, {"uid": st.session_state.user_id})
    
        if not attivita_totali_df.empty:
            # Mappa ID Attività -> Stringa descrittiva
            mappa_attivita = {
                row['attivita_id']: f"[{row['stato']}] {row['contatto_info']} - {row['descrizione'][:40]}..."
                for _, row in attivita_totali_df.iterrows()
            }
        
            id_att_selezionata = st.selectbox(
                "Seleziona l'attività:", 
                options=list(mappa_attivita.keys()), 
                format_func=lambda aid: mappa_attivita[aid]
            )
        
            if id_att_selezionata:
                dati_att = attivita_totali_df[attivita_totali_df["attivita_id"] == id_att_selezionata].iloc[0]
            
                with st.form("modifica_attivita_form"):
                    nuova_descrizione = st.text_area("Descrizione *", value=dati_att["descrizione"])
                    nuova_data = st.date_input("Data Scadenza", pd.to_datetime(dati_att["data_scadenza"]).date(), format="DD/MM/YYYY")
                    stati_possibili = ["Da fare", "In corso", "Completata"]
                    nuovo_stato = st.selectbox("Stato", stati_possibili, index=stati_possibili.index(dati_att["stato"]))
                
                    if st.form_submit_button("Salva Modifiche"):
                        if nuova_descrizione.strip():
                            esegui_query(
                                "UPDATE attivita SET descrizione=:desc, data_scadenza=:scad, stato=:stato WHERE id=:id",
                                {"desc": nuova_descrizione, "scad": nuova_data, "stato": nuovo_stato, "id": int(id_att_selezionata)}
                            )
                            st.cache_data.clear()
                            st.success("Attività aggiornata!")
                            st.rerun()
            
                st.write("---")
                if st.button("Elimina definitivamente questa attività", type="primary"):
                    conferma_eliminazione_attivita_dialog(id_att_selezionata, dati_att["descrizione"][:30])
        else: 
            st.info("Nessuna attività trovata.")
