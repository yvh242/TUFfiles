import streamlit as st
import pandas as pd

st.set_page_config(page_title="Logistiek Overzicht", layout="wide")

st.title("📊 Logistiek Transport Overzicht")
st.markdown("Upload je Excel-bestand voor een cijfermatige analyse op basis van unieke ritten.")

# 1. Bestand uploaden
uploaded_file = st.file_uploader("Kies een Excel bestand", type=['xlsx'])

if uploaded_file:
    # Inlezen data
    df = pd.read_excel(uploaded_file)
    
    # Data Cleaning & Voorbereiding
    df['Date'] = pd.to_datetime(df['Date'])
    df['Maand'] = df['Date'].dt.month_name()
    
    # Wachttijd berekenen (Departure - Arrival)
    df['Arrival_td'] = pd.to_timedelta(df['Arrival'].astype(str))
    df['Departure_td'] = pd.to_timedelta(df['Departure'].astype(str))
    df['Wait_Hours'] = (df['Departure_td'] - df['Arrival_td']).dt.total_seconds() / 3600

    # DATASET VOOR WACHTUREN (Ontdubbelen op Tripnr)
    # We groeperen op Tripnr en nemen de max van de wachttijd en de eerste waarde van Maand/Client
    df_unique_trips = df.groupby('Tripnr').agg({
        'Wait_Hours': 'max',
        'Maand': 'first',
        'Client': 'first',
        'Date': 'first'
    }).reset_index()

    # --- SECTIE 1: DAGELIJKS OVERZICHT ---
    st.subheader("📅 Ritten en Laadmeters per Dag")
    # Aantal ritten komt uit de unieke lijst, LM komt uit de volledige lijst (alles optellen)
    daily_trips = df_unique_trips.groupby(df_unique_trips['Date'].dt.date).size().reset_index(name='Aantal Ritten')
    daily_lm = df.groupby(df['Date'].dt.date)['LM'].sum().reset_index(name='Totaal LM')
    daily_stats = pd.merge(daily_trips, daily_lm, left_on='Date', right_on='Date')
    
    st.dataframe(daily_stats, use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # --- SECTIE 2: WACHTUREN PER MAAND (Unieke ritten) ---
        st.subheader("⏳ Gem. Wachturen per Maand")
        monthly_wait = df_unique_trips.groupby('Maand')['Wait_Hours'].mean().reset_index()
        monthly_wait.columns = ['Maand', 'Gem. Wachturen (u)']
        st.table(monthly_wait.round(2))

    with col2:
        # --- SECTIE 3: WACHTUREN PER KLANT (Unieke ritten) ---
        st.subheader("👥 Gem. Wachturen per Klant")
        client_wait = df_unique_trips.groupby('Client')['Wait_Hours'].mean().sort_values(ascending=False).reset_index()
        client_wait.columns = ['Klant', 'Gem. Wachturen (u)']
        st.table(client_wait.round(2))

    st.divider()

    # --- SECTIE 4: LAADMETERS PER KLANT PER MAAND (Alle regels tellen mee) ---
    st.subheader("🚛 Laadmeters per Klant per Maand")
    client_lm_stats = df.groupby(['Maand', 'Client'])['LM'].agg(['sum', 'mean']).reset_index()
    client_lm_stats.columns = ['Maand', 'Klant', 'Totaal LM', 'Gemiddelde LM']
    
    st.dataframe(client_lm_stats.round(2), use_container_width=True)

    # Optioneel: Ruwe data onderaan
    with st.expander("Klik hier om de brongegevens te bekijken"):
        st.write(df)

else:
    st.info("Upload een Excel-bestand om de tabellen te genereren.")
