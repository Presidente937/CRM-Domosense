import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# CONFIGURAZIONE SUPABASE
DATABASE_URL="postgresql://postgres.ruwbodnfktfcppxfjkxq:MC.D0m0s3ns3@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

# Connessione robusta al database PostgreSQL
engine = create_engine(DATABASE_URL)

st.set_page_config(page_title="Domosense CRM", layout="wide")
st.title("Domosense CRM")

# Inizializzazione delle variabili di stato per la pulizia selettiva dei form
if "contact_form_version" not in st.session_state:
    st.session_state.contact_form_version = 0

if "activity_form_version" not in st.session_state:
    st.session_state.activity_form_version = 0

# Funzione per eseguire query di scrittura in sicurezza
def esegui_query(query, params=None):
    with engine.begin() as conn:
        conn.execute(text(query), params or {})

# Funzione per leggere i dati
def leggi_query(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})

# Finestra modale di conferma eliminazione CONTATTO
@st.dialog("Conferma Eliminazione Contatto")
def conferma_eliminazione_dialog(contatto_id, nome_completo):
    st.warning(f"Sei sicuro di voler eliminare definitivamente **{nome_completo}**?")
    st.write("Questa azione cancellerà anche tutte le attività collegate e non potrà essere annullata.")
    
    col_conferma, col_annulla = st.columns(2)
    with col_conferma:
        if st.button("Sì, elimina", type="primary", use_container_width=True):
            esegui_query("DELETE FROM contatti WHERE id = :id", {"id": int(contatto_id)})
            st.success("Contatto eliminato!")
            st.rerun()
    with col_annulla:
        if st.button("Annulla", use_container_width=True):
            st.rerun()

# Finestra modale di conferma eliminazione ATTIVITÀ
@st.dialog("Conferma Eliminazione Attività")
def conferma_eliminazione_attivita_dialog(attivita_id, descrizione_breve):
    st.warning(f"Sei sicuro di voler eliminare l'attività: **\"{descrizione_breve}\"**?")
    st.write("Questa azione non può essere annullata.")
    
    col_conferma, col_annulla = st.columns(2)
    with col_conferma:
        if st.button("Sì, elimina", type="primary", use_container_width=True):
            esegui_query("DELETE FROM attivita WHERE id = :id", {"id": int(attivita_id)})
            st.success("Attività eliminata con successo!")
            st.rerun()
    with col_annulla:
        if st.button("Annulla", use_container_width=True):
            st.rerun()


# ==================== STRUTTURA DI NAVIGAZIONE A DUE LIVELLI ====================
st.sidebar.title("📁 Menu Principale")
macro_sezione = st.sidebar.radio("Seleziona Area:", ["👥 Contatti", "📅 Attività"])

st.sidebar.write("---")

# Opzioni fisse per la provenienza dei lead
OPZIONI_PROVENIENZA = ["Social", "BNI", "Fiere/Eventi in presenza"]

if macro_sezione == "👥 Contatti":
    st.sidebar.subheader("Sottosezioni Contatti")
    sotto_sezione = st.sidebar.radio(
        "Scegli Azione:", 
        ["ℹ️ Info e Gestione Contatto", "➕ Aggiungi Contatto"]
    )
elif macro_sezione == "📅 Attività":
    st.sidebar.subheader("Sottosezioni Attività")
    sotto_sezione = st.sidebar.radio(
        "Scegli Azione:", 
        ["🔍 Riepilogo Scadenze", "➕ Aggiungi Attività", "⚙️ Gestione Attività"]
    )


# ==================== LOGICA DELLE SOTTOSEZIONI ====================

# --- SOTTOSEZIONE: INFO E GESTIONE CONTATTO ---
if macro_sezione == "👥 Contatti" and sotto_sezione == "ℹ️ Info e Gestione Contatto":
    st.header("👤 Scheda e Storico Contatti")
    
    contatti_df = leggi_query("SELECT * FROM contatti")
    
    if not contatti_df.empty:
        contatti_df["nominativo"] = contatti_df["nome"] + " " + contatti_df["cognome"] + " (" + contatti_df["azienda"].fillna("") + ")"
        selezionato = st.selectbox("Seleziona un contatto per consultare la scheda:", contatti_df["nominativo"])
        
        if selezionato:
            contatto_id = contatti_df[contatti_df["nominativo"] == selezionato]["id"].values[0]
            info_contatto = contatti_df[contatti_df["id"] == contatto_id].iloc[0]
            nome_completo = f"{info_contatto['nome']} {info_contatto['cognome']}"
            
            # Visualizzazione dati attuali (Inclusi Lavoro e Provenienza Lead)
            st.info(f"""
            **Dettagli Anagrafica Attuali:**
            * **Nome e Cognome:** {info_contatto['nome']} {info_contatto['cognome']}
            * **Ruolo / Lavoro:** {info_contatto['ruolo'] if pd.notna(info_contatto['ruolo']) and info_contatto['ruolo'] != '' else 'Non specificato'}
            * **Azienda:** {info_contatto['azienda'] if pd.notna(info_contatto['azienda']) else 'Non specificata'}
            * **Provenienza Lead:** {info_contatto['provenienza_lead'] if pd.notna(info_contatto['provenienza_lead']) else 'Non specificata'}
            * **Email:** {info_contatto['email'] if pd.notna(info_contatto['email']) else 'Non specificata'}
            * **Telefono:** {info_contatto['telefono'] if pd.notna(info_contatto['telefono']) else 'Non specificato'}
            """)
            
            with st.expander("📝 Modifica dati anagrafici contatto"):
                with st.form(f"modifica_contatto_{contatto_id}"):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        nuovo_nome = st.text_input("Nome *", value=info_contatto['nome'])
                        nuovo_cognome = st.text_input("Cognome *", value=info_contatto['cognome'])
                        nuovo_ruolo = st.text_input("Ruolo / Lavoro", value=info_contatto['ruolo'] if pd.notna(info_contatto['ruolo']) else "")
                        nuova_azienda = st.text_input("Azienda", value=info_contatto['azienda'] if pd.notna(info_contatto['azienda']) else "")
                    with col_m2:
                        nuova_email = st.text_input("Email", value=info_contatto['email'] if pd.notna(info_contatto['email']) else "")
                        nuovo_telefono = st.text_input("Telefono", value=info_contatto['telefono'] if pd.notna(info_contatto['telefono']) else "")
                        
                        # Calcolo indice provenienza attuale
                        prov_attuale = info_contatto['provenienza_lead']
                        idx_prov = OPZIONI_PROVENIENZA.index(prov_attuale) if prov_attuale in OPZIONI_PROVENIENZA else 0
                        nuova_provenienza = st.selectbox("Provenienza Lead", OPZIONI_PROVENIENZA, index=idx_prov)
                    
                    submit_modifica = st.form_submit_button("Aggiorna Anagrafica")
                    if submit_modifica:
                        if nuovo_nome.strip() and nuovo_cognome.strip():
                            query_update_contatto = """
                            UPDATE contatti 
                            SET nome = :nome, cognome = :cognome, azienda = :azienda, email = :email, telefono = :telefono, ruolo = :ruolo, provenienza_lead = :prov
                            WHERE id = :id
                            """
                            esegui_query(query_update_contatto, {
                                "nome": nuovo_nome, "cognome": nuovo_cognome, "azienda": nuova_azienda,
                                "email": nuova_email, "telefono": nuovo_telefono, "ruolo": nuovo_ruolo,
                                "prov": nuova_provenienza, "id": int(contatto_id)
                            })
                            st.success("Dati contatto aggiornati con successo!")
                            st.rerun()
                        else:
                            st.error("I campi Nome e Cognome non possono essere vuoti.")
            
            if st.button("Elimina questo contatto", type="primary"):
                conferma_eliminazione_dialog(contatto_id, nome_completo)

            st.write("---")
            st.write("### Storico Attività del Contatto")
            
            attivita_df = leggi_query(
                "SELECT descrizione as \"Attività\", data_scadenza as \"Scadenza\", stato as \"Stato\" FROM attivita WHERE contatto_id = :cid ORDER BY data_scadenza DESC",
                params={"cid": int(contatto_id)}
            )
            if not attivita_df.empty:
                attivita_df["Scadenza"] = pd.to_datetime(attivita_df["Scadenza"]).dt.strftime('%d/%m/%Y')
                st.dataframe(attivita_df, use_container_width=True)
            else:
                st.info("Nessuna attività registrata per questo contatto.")
    else:
        st.info("Nessun contatto presente nel database. Seleziona 'Aggiungi Contatto' dal menu a sinistra per inserire il primo.")

# --- SOTTOSEZIONE: AGGIUNGI CONTATTO ---
elif macro_sezione == "👥 Contatti" and sotto_sezione == "➕ Aggiungi Contatto":
    st.header("Inserimento Nuovo Contatto")
    
    with st.form(f"nuovo_contatto_{st.session_state.contact_form_version}"):
        st.write("Compila i campi per salvare un nuovo contatto in anagrafica:")
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
        
        submit = st.form_submit_button("Salva in Anagrafica")
        if submit:
            if nome.strip() and cognome.strip():
                query_insert = """
                INSERT INTO contatti (nome, cognome, azienda, email, telefono, ruolo, provenienza_lead) 
                VALUES (:nome, :cognome, :azienda, :email, :telefono, :ruolo, :prov)
                """
                esegui_query(query_insert, {
                    "nome": nome, "cognome": cognome, "azienda": azienda, 
                    "email": email, "telefono": telefono, "ruolo": ruolo, "prov": provenienza
                })
                
                st.session_state.contact_form_version += 1
                st.success(f"Contatto **{nome} {cognome}** salvato con successo!")
                st.rerun()
            else:
                st.error("I campi Nome e Cognome sono obbligatori.")

# --- SOTTOSEZIONE: RIEPILOGO SCADENZE ATTIVITÀ ---
elif macro_sezione == "📅 Attività" and sotto_sezione == "🔍 Riepilogo Scadenze":
    st.header("Riepilogo Scadenze Attività")
    
    oggi = datetime.today()
    tra_sette_giorni = oggi + timedelta(days=7)
    
    col1, col2 = st.columns(2)
    with col1:
        data_inizio = st.date_input("Da data", oggi, format="DD/MM/YYYY")
    with col2:
        data_fine = st.date_input("A data", tra_sette_giorni, format="DD/MM/YYYY")
        
    query = """
    SELECT 
        a.id as "ID Attività",
        c.nome || ' ' || c.cognome as "Contatto",
        c.azienda as "Azienda",
        a.descrizione as "Attività",
        a.data_scadenza as "Data Scadenza",
        a.stato as "Stato"
    FROM attivita a
    JOIN contatti c ON a.contatto_id = c.id
    WHERE a.data_scadenza BETWEEN :inizio AND :fine
    ORDER BY a.data_scadenza ASC
    """
    
    df_riepilogo = leggi_query(query, params={"inizio": data_inizio, "fine": data_fine})
    
    if not df_riepilogo.empty:
        df_riepilogo["Data Scadenza"] = pd.to_datetime(df_riepilogo["Data Scadenza"]).dt.strftime('%d/%m/%Y')
        st.write(f"Trovate {len(df_riepilogo)} attività nel periodo selezionato:")
        st.dataframe(df_riepilogo, use_container_width=True)
    else:
        st.info("Nessuna attività programmata in questo intervallo di date.")

# --- SOTTOSEZIONE: AGGIUNGI ATTIVITÀ ---
elif macro_sezione == "📅 Attività" and sotto_sezione == "➕ Aggiungi Attività":
    st.header("Pianifica Nuova Attività")
    
    contatti_df = leggi_query("SELECT id, nome, cognome, azienda FROM contatti")
    
    if not contatti_df.empty:
        contatti_df["nominativo"] = contatti_df["nome"] + " " + contatti_df["cognome"] + " (" + contatti_df["azienda"].fillna("") + ")"
        
        with st.form(f"nuova_attivita_{st.session_state.activity_form_version}"):
            contatto_scelto = st.selectbox("Associa a Contatto", contatti_df["nominativo"])
            descrizione = st.text_area("Descrizione dell'attività da fare *")
            data_scadenza = st.date_input("Data Scadenza", datetime.today(), format="DD/MM/YYYY")
            stato = st.selectbox("Stato", ["Da fare", "In corso", "Completata"])
            
            submit_att = st.form_submit_button("Pianifica Attività")
            if submit_att:
                if descrizione.strip():
                    contatto_id = contatti_df[contatti_df["nominativo"] == contatto_scelto]["id"].values[0]
                    query_att = """
                    INSERT INTO attivita (contatto_id, descrizione, data_scadenza, stato) 
                    VALUES (:cid, :desc, :scad, :stato)
                    """
                    esegui_query(query_att, {
                        "cid": int(contatto_id), "desc": descrizione, 
                        "scad": data_scadenza, "stato": stato
                    })
                    
                    st.session_state.activity_form_version += 1
                    st.success("Attività pianificata con successo!")
                    st.rerun()
                else:
                    st.error("La descrizione dell'attività è obbligatoria per procedere!")
    else:
        st.warning("Devi prima inserire almeno un contatto prima di poter programmare un'attività!")

# --- SOTTOSEZIONE: GESTIONE E MODIFICA ATTIVITÀ ---
elif macro_sezione == "📅 Attività" and sotto_sezione == "⚙️ Gestione Attività":
    st.header("Gestione e Modifica Attività")
    
    query_all_attivita = """
    SELECT 
        a.id as attivita_id,
        c.nome || ' ' || c.cognome || ' (' || COALESCE(c.azienda, '') || ')' as contatto_info,
        a.descrizione,
        a.data_scadenza,
        a.stato
    FROM attivita a
    JOIN contatti c ON a.contatto_id = c.id
    ORDER BY a.data_scadenza ASC
    """
    attivita_totali_df = leggi_query(query_all_attivita)
    
    if not attivita_totali_df.empty:
        attivita_totali_df["label_scelta"] = (
            "[" + attivita_totali_df["stato"] + "] " + 
            attivita_totali_df["contatto_info"] + " - " + 
            attivita_totali_df["descrizione"].str.slice(0, 40) + "..."
        )
        
        scelta_att = st.selectbox("Seleziona l'attività da modificare o eliminare:", attivita_totali_df["label_scelta"])
        
        if scelta_att:
            dati_att = attivita_totali_df[attivita_totali_df["label_scelta"] == scelta_att].iloc[0]
            id_att_selezionata = dati_att["attivita_id"]
            
            st.write("---")
            st.subheader("Modifica Dettagli")
            
            with st.form("modifica_attivita_form"):
                st.write(f"**Assegnato a:** {dati_att['contatto_info']}")
                nuova_descrizione = st.text_area("Descrizione dell'attività *", value=dati_att["descrizione"])
                
                col1, col2 = st.columns(2)
                with col1:
                    data_attuale_att = pd.to_datetime(dati_att["data_scadenza"]).date()
                    nuova_data = st.date_input("Data Scadenza", data_attuale_att, format="DD/MM/YYYY")
                with col2:
                    stati_possibili = ["Da fare", "In corso", "Completata"]
                    indice_stato_attuale = stati_possibili.index(dati_att["stato"])
                    nuovo_stato = st.selectbox("Stato", stati_possibili, index=indice_stato_attuale)
                
                col_btn1, col_btn2 = st.columns([1, 4])
                with col_btn1:
                    salva_modifiche = st.form_submit_button("Salva Modifiche")
                
                if salva_modifiche:
                    if nuova_descrizione.strip():
                        query_update = """
                        UPDATE attivita 
                        SET descrizione = :desc, data_scadenza = :scad, stato = :stato 
                        WHERE id = :id
                        """
                        esegui_query(query_update, {
                            "desc": nuova_descrizione,
                            "scad": nuova_data,
                            "stato": nuovo_stato,
                            "id": int(id_att_selezionata)
                        })
                        st.success("Attività aggiornata con successo!")
                        st.rerun()
                    else:
                        st.error("La descrizione dell'attività non può essere vuota!")
            
            st.write("---")
            if st.button("Elimina definitivamente questa attività", type="primary"):
                desc_breve = dati_att["descrizione"][:30] + "..." if len(dati_att["descrizione"]) > 30 else dati_att["descrizione"]
                conferma_eliminazione_attivita_dialog(id_att_selezionata, desc_breve)
                
    else:
        st.info("Nessuna attività programmata nel sistema al momento.")