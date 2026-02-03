import streamlit as st
import pandas as pd

# Pagina instellingen
st.set_page_config(page_title="DASHBOARD CS Genk", layout="wide")

st.title("📊 DASHBOARD CS Genk")
st.markdown("Analyse van wachttijden en laadmeters op basis van unieke ritten.")

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
    df_unique_trips = df.groupby('Tripnr').agg({
        'Wait_Hours': 'max',
        'Maand': 'first',
        'Client': 'first',
        'Date': 'first'
    }).reset_index()

    # DATASET VOOR LM PER RIT (Som van LM per unieke rit voor gemiddelde berekening)
    df_lm_per_trip = df.groupby(['Tripnr', 'Client', 'Maand'])['LM'].sum().reset_index()

    # --- SECTIE 1: WACHTUREN (BOVENAAN) ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⏳ Gem. Wachturen per Maand")
        monthly_wait = df_unique_trips.groupby('Maand')['Wait_Hours'].mean().reset_index()
        monthly_wait.columns = ['Maand', 'Gem. Wachturen (u)']
        st.table(monthly_wait.round(2))

    with col2:
        st.subheader("👥 Gem. Wachturen per Klant")
        client_wait = df_unique_trips.groupby('Client')['Wait_Hours'].mean().sort_values(ascending=False).reset_index()
        client_wait.columns = ['Klant', 'Gem. Wachturen (u)']
        st.table(client_wait.round(2))

    st.divider()

    # --- SECTIE 2: LAADMETERS PER KLANT PER MAAND ---
    st.subheader("🚛 Laadmeters per Klant per Maand")
    
    # Totaal LM (som van alle regels)
    total_lm = df.groupby(['Maand', 'Client'])['LM'].sum().reset_index(name='Totaal LM')
    
    # Gemiddelde LM (gebaseerd op som per unieke rit)
    avg_lm = df_lm_per_trip.groupby(['Maand', 'Client'])['LM'].mean().reset_index(name='Gem. LM per Rit')
    
    # Samenvoegen voor overzicht
    client_lm_combined = pd.merge(total_lm, avg_lm, on=['Maand', 'Client'])
    st.dataframe(client_lm_combined.round(2), use_container_width=True)

    st.divider()

    # --- SECTIE 3: DAGELIJKS OVERZICHT (ONDERAAN) ---
    st.subheader("📅 Ritten en Laadmeters per Dag")
    # Aantal ritten uit unieke lijst, Totaal LM uit alle regels
    daily_trips = df_unique_trips.groupby(df_unique_trips['Date'].dt.date).size().reset_index(name='Aantal Ritten')
    daily_lm = df.groupby(df['Date'].dt.date)['LM'].sum().reset_index(name='Totaal LM')
    daily_stats = pd.merge(daily_trips, daily_lm, on='Date')
    
    st.dataframe(daily_stats, use_container_width=True)

    # Optioneel: Ruwe data
    with st.expander("Bekijk de volledige brongegevens"):
        st.write(df)

else:
    st.info("Upload een Excel-bestand om het dashboard te laden.")
