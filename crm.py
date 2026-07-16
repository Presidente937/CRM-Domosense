#python -m streamlit run crm.py --server.address 0.0.0.0
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# CONFIGURAZIONE SUPABASE
# Sostituisci questa stringa con l'URI copiato dalle impostazioni di Supabase
DATABASE_URL="postgresql://postgres.ruwbodnfktfcppxfjkxq:MC.D0m0s3ns3@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

# Connessione robusta al database PostgreSQL
engine = create_engine(DATABASE_URL)

st.set_page_config(page_title="Mini CRM Cloud", layout="wide")
st.title("💼 Il mio Mini CRM Cloud")

# Funzione per eseguire query di scrittura in sicurezza
def esegui_query(query, params=None):
    with engine.begin() as conn:
        conn.execute(text(query), params or {})

# Funzione per leggere i dati
def leggi_query(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})

# Funzione per la finestra modale di conferma eliminazione
@st.dialog("Conferma Eliminazione")
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

# Sidebar
menu = st.sidebar.radio("Navigazione", ["Riepilogo Attività", "Info Contatto", "Aggiungi Contatto", "Aggiungi Attività"])

# ==================== SEZIONE 1: GESTIONE CONTATTI ====================
if menu == "Aggiungi Contatto":
    st.header("👤 Gestione Anagrafica Contatti")
    
    with st.form("nuovo_contatto"):
        st.subheader("Inserisci Nuovo Contatto")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            cognome = st.text_input("Cognome *")
            azienda = st.text_input("Azienda")
        with col2:
            email = st.text_input("Email")
            telefono = st.text_input("Telefono")
        
        submit = st.form_submit_button("Salva Contatto")
        if submit:
            if nome and cognome:
                query_insert = """
                INSERT INTO contatti (nome, cognome, azienda, email, telefono) 
                VALUES (:nome, :cognome, :azienda, :email, :telefono)
                """
                esegui_query(query_insert, {
                    "nome": nome, "cognome": cognome, "azienda": azienda, 
                    "email": email, "telefono": telefono
                })
                st.success(f"Contatto {nome} {cognome} salvato!")
                st.rerun()
            else:
                st.error("Nome e Cognome sono obbligatori.")

elif menu=="Info Contatto":
    st.subheader("Lista Contatti e Storico Attività")
    contatti_df = leggi_query("SELECT * FROM contatti")
    
    if not contatti_df.empty:
        contatti_df["nominativo"] = contatti_df["nome"] + " " + contatti_df["cognome"] + " (" + contatti_df["azienda"].fillna("") + ")"
        selezionato = st.selectbox("Seleziona un contatto per vedere i dettagli, lo storico o per eliminarlo:", contatti_df["nominativo"])
        
        if selezionato:
            contatto_id = contatti_df[contatti_df["nominativo"] == selezionato]["id"].values[0]
            info_contatto = contatti_df[contatti_df["id"] == contatto_id].iloc[0]
            nome_completo = f"{info_contatto['nome']} {info_contatto['cognome']}"
            
            st.markdown(f"**Email:** {info_contatto['email']} | **Telefono:** {info_contatto['telefono']} | **Azienda:** {info_contatto['azienda']}")
            st.write("---")
            
            if st.button("🗑️ Elimina questo contatto", type="primary"):
                conferma_eliminazione_dialog(contatto_id, nome_completo)

            st.write("---")
            st.write("### 📜 Storico Attività del Contatto")
            
            attivita_df = leggi_query(
                "SELECT descrizione, data_scadenza, stato FROM attivita WHERE contatto_id = :cid ORDER BY data_scadenza DESC",
                params={"cid": int(contatto_id)}
            )
            if not attivita_df.empty:
                st.dataframe(attivita_df, use_container_width=True)
            else:
                st.info("Nessuna attività registrata per questo contatto.")
    else:
        st.info("Nessun contatto presente nel database.")

# ==================== SEZIONE 2: AGGIUNGI ATTIVITÀ ====================
elif menu == "Aggiungi Attività":
    st.header("📅 Nuova Attività")
    
    contatti_df = leggi_query("SELECT id, nome, cognome, azienda FROM contatti")
    
    if not contatti_df.empty:
        contatti_df["nominativo"] = contatti_df["nome"] + " " + contatti_df["cognome"] + " (" + contatti_df["azienda"].fillna("") + ")"
        
        with st.form("nuova_attivita"):
            contatto_scelto = st.selectbox("Associa a Contatto", contatti_df["nominativo"])
            descrizione = st.text_area("Descrizione dell'attività da fare")
            data_scadenza = st.date_input("Data Scadenza", datetime.today())
            stato = st.selectbox("Stato", ["Da fare", "In corso", "Completata"])
            
            submit_att = st.form_submit_button("Pianifica Attività")
            if submit_att:
                contatto_id = contatti_df[contatti_df["nominativo"] == contatto_scelto]["id"].values[0]
                query_att = """
                INSERT INTO attivita (contatto_id, descrizione, data_scadenza, stato) 
                VALUES (:cid, :desc, :scad, :stato)
                """
                esegui_query(query_att, {
                    "cid": int(contatto_id), "desc": descrizione, 
                    "scad": data_scadenza, "stato": stato
                })
                st.success("Attività pianificata con successo!")
    else:
        st.warning("Devi prima inserire almeno un contatto in anagrafica!")

# ==================== SEZIONE 3: RIEPILOGO ATTIVITÀ (FILTRATO) ====================
elif menu == "Riepilogo Attività":
    st.header("🔍 Riepilogo Scadenze Attività")
    
    col1, col2 = st.columns(2)
    with col1:
        data_inizio = st.date_input("Da data", datetime.today())
    with col2:
        data_fine = st.date_input("A data", datetime.today())
        
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
        st.write(f"Trovate {len(df_riepilogo)} attività nel periodo selezionato:")
        st.dataframe(df_riepilogo, use_container_width=True)
    else:
        st.info("Nessuna attività programmata in questo intervallo di date.")