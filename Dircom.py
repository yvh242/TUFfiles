import streamlit as st
import pandas as pd
import numpy as np # Importeer numpy voor np.select
import io

def app():
    st.title("Verzenddata Analyse met Categorieën")

    st.write("""
    Upload uw Excel-bestand om uw verzenddata te analyseren.
    De app bundelt data per unieke 'Verzending-ID' en telt de numerieke kolommen 'Kg', 'm³' en 'LM' samen.
    Er wordt een nieuwe 'Dienst_Categorie' kolom aangemaakt op basis van 'Verzending-ID' en 'Type'.
    Vervolgens worden de totalen getoond voor alle zendingen en per 'Dienst_Categorie'.
    """)

    uploaded_file = st.file_uploader("Kies een Excel-bestand", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Lees het Excel-bestand in
            df = pd.read_excel(uploaded_file)

            # --- Controleer op vereiste kolommen ---
            # Nu is 'Type' ook een vereiste kolom voor de categorisatie
            required_columns = ['Verzending-ID', 'Kg', 'm³', 'LM', 'Type']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                st.error(f"Het Excel-bestand mist de volgende vereiste kolommen: {', '.join(missing_columns)}. Gelieve een bestand te uploaden met alle benodigde kolommen.")
                return

            # --- Data Voorbereiding ---
            # Zorg ervoor dat numerieke kolommen de juiste datatype hebben, forceer naar numeric
            for col in ['Kg', 'm³', 'LM']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # 'coerce' zet niet-numerieke waarden om in NaN, fillna(0) vult deze met 0

            # Zorg ervoor dat 'Verzending-ID' numeriek is, nodig voor vergelijkingen
            df['Verzending-ID'] = pd.to_numeric(df['Verzending-ID'], errors='coerce')
            # Optioneel: vul NaN 'Verzending-ID's op als je ze wilt behouden, anders worden ze genegeerd door de condities
            # df['Verzending-ID'].fillna(-1, inplace=True) # Bijvoorbeeld, -1 of een andere waarde die niet botst

            # --- Aanmaken van de nieuwe Dienst_Categorie kolom met np.select ---
            # Definieer de condities en de corresponderende keuzes
            conditions = [
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'levering'), # 'levering' -> 'Levering' voor consistentie
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'Transport'),
                (df['Verzending-ID'] < 2510000000) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] > 2510999999) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] < 2510000000) & (df['Type'] != 'Laden'),
                (df['Verzending-ID'] > 2510999999) & (df['Type'] != 'Laden')
            ]

            choices = ['ICL AFH', 'ICL LEV', 'ICL DIRECT', 'TUF EXPORT', 'TUF EXPORT', 'TUF IMPORT', 'TUF IMPORT']
            
            # Voeg een standaardwaarde toe voor gevallen die niet aan een conditie voldoen
            df['Dienst_Categorie'] = np.select(conditions, choices, default='Overig/Onbekend')

            st.success("Bestand succesvol ingelezen en verwerkt!")

            # --- Dataverwerking: Bundel op 'Verzending-ID' en bewaar de nieuwe 'Dienst_Categorie' ---
            # Nu groeperen we ook op de 'Dienst_Categorie' voor de aggregatie
            df_grouped = df.groupby(['Verzending-ID', 'Dienst_Categorie']).agg(
                Kg=('Kg', 'sum'),
                m3=('m³', 'sum'),
                LM=('LM', 'sum')
            ).reset_index()

            # --- Totaaloverzicht alle zendingen (gebaseerd op unieke Verzending-ID's na bundeling) ---
            st.subheader("1. Totaaloverzicht van alle zendingen")

            total_zendingen = len(df_grouped)
            total_kg = df_grouped['Kg'].sum()
            total_lm = df_grouped['LM'].sum()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Totaal Aantal Unieke Zendingen", value=f"{total_zendingen:,.0f}")
            with col2:
                st.metric(label="Totaal Gewicht (Kg)", value=f"{total_kg:,.2f} Kg")
            with col3:
                st.metric(label="Totale Laadmeter (LM)", value=f"{total_lm:,.2f} LM")

            st.write("---") # Visuele scheiding

            # --- Totaaloverzicht per Dienst_Categorie ---
            st.subheader("2. Totaaloverzicht per Dienst Categorie")

            # Groepeer nu op de NIEUWE 'Dienst_Categorie' kolom
            df_summary_by_category = df_grouped.groupby('Dienst_Categorie').agg(
                Aantal_Zendingen=('Verzending-ID', 'size'), # 'size' telt het aantal items in elke groep
                Totaal_Kg=('Kg', 'sum'),
                Totaal_LM=('LM', 'sum')
            ).reset_index()

            # Hernoem kolommen voor duidelijkheid
            df_summary_by_category.columns = ['Dienst Categorie', 'Aantal Zendingen', 'Totaal Kg', 'Totaal LM']

            # Formatteer de numerieke kolommen voor weergave
            df_summary_by_category['Totaal Kg'] = df_summary_by_category['Totaal Kg'].map(lambda x: f"{x:,.2f} Kg")
            df_summary_by_category['Totaal LM'] = df_summary_by_category['Totaal LM'].map(lambda x: f"{x:,.2f} LM")
            df_summary_by_category['Aantal Zendingen'] = df_summary_by_category['Aantal Zendingen'].map(lambda x: f"{x:,.0f}")

            st.dataframe(df_summary_by_category, hide_index=True)


        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}. Controleer of het Excel-bestand de juiste opmaak en kolommen bevat.")
            st.error("Gedetailleerde foutmelding: " + str(e))

if __name__ == '__main__':
    app()
