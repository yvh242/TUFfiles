import streamlit as st
import pandas as pd

st.set_page_config(page_title="CS Genk Dashboard", layout="wide")

st.title("📊 Dashboard Genk CS")
st.markdown("Upload je Excel-bestand voor een cijfermatige analyse.")

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

    # --- SECTIE 1: DAGELIJKS OVERZICHT ---
    st.subheader("📅 Ritten en Laadmeters per Dag")
    daily_stats = df.groupby(df['Date'].dt.date).agg({'Tripnr': 'nunique', 'LM': 'sum'}).reset_index()
    daily_stats.columns = ['Datum', 'Aantal Ritten', 'Totaal LM']
    st.dataframe(daily_stats, use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # --- SECTIE 2: WACHTUREN PER MAAND ---
        st.subheader("⏳ Gem. Wachturen per Maand")
        monthly_wait = df.groupby('Maand')['Wait_Hours'].mean().reset_index()
        monthly_wait.columns = ['Maand', 'Gem. Wachturen (u)']
        st.table(monthly_wait.round(2))

    with col2:
        # --- SECTIE 3: WACHTUREN PER KLANT ---
        st.subheader("👥 Gem. Wachturen per Klant")
        client_wait = df.groupby('Client')['Wait_Hours'].mean().sort_values(ascending=False).reset_index()
        client_wait.columns = ['Klant', 'Gem. Wachturen (u)']
        st.table(client_wait.round(2))

    st.divider()

    # --- SECTIE 4: LAADMETERS PER KLANT PER MAAND ---
    st.subheader("🚛 Laadmeters per Klant per Maand")
    client_lm_stats = df.groupby(['Maand', 'Client'])['LM'].agg(['sum', 'mean']).reset_index()
    client_lm_stats.columns = ['Maand', 'Klant', 'Totaal LM', 'Gemiddelde LM']
    
    # Weergeven als een interactieve tabel (dataframe) zodat je kunt sorteren
    st.dataframe(client_lm_stats.round(2), use_container_width=True)

    # Optioneel: Ruwe data onderaan
    with st.expander("Klik hier om de brongegevens te bekijken"):
        st.write(df)

else:
    st.info("Upload een Excel-bestand om de tabellen te genereren.")
