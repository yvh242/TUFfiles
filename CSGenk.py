import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Logistiek Dashboard", layout="wide")

st.title("🚚 CS GENK Dashboard")
st.markdown("Upload je Excel-bestand om de prestaties te analyseren.")

# 1. Bestand uploaden
uploaded_file = st.file_uploader("Kies een Excel bestand", type=['xlsx'])

if uploaded_file:
    # Inlezen data
    df = pd.read_excel(uploaded_file)
    
    # Data Cleaning & Voorbereiding
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    
    # Wachttijd berekenen (Departure - Arrival)
    # We gaan ervan uit dat dit tijd-objecten zijn
    df['Arrival'] = pd.to_timedelta(df['Arrival'].astype(str))
    df['Departure'] = pd.to_timedelta(df['Departure'].astype(str))
    df['Wait_Hours'] = (df['Departure'] - df['Arrival']).dt.total_seconds() / 3600

    # Layout: Kolommen voor filters of statistieken
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ritten en Laadmeters per Dag")
        # Groeperen per dag: aantal unieke ritten en som van LM
        daily_stats = df.groupby('Date').agg({'Tripnr': 'nunique', 'LM': 'sum'}).reset_index()
        daily_stats.columns = ['Datum', 'Aantal Ritten', 'Totaal LM']
        
        fig_daily = px.bar(daily_stats, x='Datum', y='Totaal LM', hover_data=['Aantal Ritten'],
                           title="Totaal Laadmeters per Dag", color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig_daily, use_container_width=True)

    with col2:
        st.subheader("Gemiddelde Wachttijd per Maand")
    
        # Berekening: Groeperen op maandnaam en gemiddelde berekenen
        # 'dt.month_name()' geeft de volledige naam (bijv. January)
        df['Maandnaam'] = df['Date'].dt.month_name()
        monthly_wait_table = df.groupby('Maandnaam')['Wait_Hours'].mean().reset_index()
    
        # Kolomnamen vertalen voor de tabel
        monthly_wait_table.columns = ['Maand', 'Gem. Wachturen']
    
        # Afronden op 2 decimalen voor de leesbaarheid
        monthly_wait_table['Gem. Wachturen'] = monthly_wait_table['Gem. Wachturen'].round(2)
    
        # Tabel weergeven in Streamlit
        st.table(monthly_wait_table)

    st.divider()

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Wachttijd per Klant")
        client_wait = df.groupby('Client')['Wait_Hours'].mean().sort_values(ascending=False).reset_index()
        fig_client_wait = px.bar(client_wait, x='Wait_Hours', y='Client', orientation='h',
                                 title="Gem. Wachturen per Klant", color='Wait_Hours')
        st.plotly_chart(fig_client_wait, use_container_width=True)

    with col4:
        st.subheader("Laadmeters per Klant (Totaal vs Gemiddelde)")
        client_lm = df.groupby(['Month', 'Client'])['LM'].agg(['sum', 'mean']).reset_index()
        
        # Keuze voor de gebruiker
        option = st.selectbox('Bekijk voor LM:', ('Totaal per Maand', 'Gemiddelde per Maand'))
        y_val = 'sum' if option == 'Totaal per Maand' else 'mean'
        
        fig_lm_client = px.bar(client_lm, x='Month', y=y_val, color='Client', barmode='group',
                               title=f"{option} per Klant")
        st.plotly_chart(fig_lm_client, use_container_width=True)

    # Toon ruwe data optie
    if st.checkbox("Toon ruwe data"):
        st.write(df)

else:
    st.info("Wachten op upload van bestand...")
