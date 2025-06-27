import streamlit as st
import pandas as pd
import numpy as np
import io

def app():
    st.title("Verzenddata Analyse: Aantallen en Laadmeters")

    st.write("""
    Upload uw Excel-bestand om uw verzenddata te analyseren.
    De app bundelt data per unieke 'Verzending-ID'.
    Er wordt een nieuwe 'Dienst_Categorie' kolom aangemaakt op basis van 'Verzending-ID' en 'Type'.
    Vervolgens worden de **totalen van unieke zendingen** en **totale Laadmeters (LM)** getoond voor alle zendingen en per 'Dienst_Categorie'.
    Daarnaast is er een sectie om de beschikbaarheid en werk van voertuigen in te voeren.
    """)

    uploaded_file = st.file_uploader("Kies een Excel-bestand", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Lees het Excel-bestand in
            df = pd.read_excel(uploaded_file)

            # --- Controleer op vereiste kolommen ---
            required_columns_for_this_report = ['Verzending-ID', 'LM', 'Type'] 
            
            missing_columns = [col for col in required_columns_for_this_report if col not in df.columns]

            if missing_columns:
                st.error(f"Het Excel-bestand mist de volgende vereiste kolommen voor dit rapport: {', '.join(missing_columns)}. Gelieve een bestand te uploaden met alle benodigde kolommen.")
                return

            # --- Data Voorbereiding ---
            # Zorg ervoor dat 'Verzending-ID' en 'LM' numeriek zijn
            df['Verzending-ID'] = pd.to_numeric(df['Verzending-ID'], errors='coerce')
            df['LM'] = pd.to_numeric(df['LM'], errors='coerce').fillna(0) # Vul NaN met 0 voor optelling
            
            # --- Aanmaken van de nieuwe Dienst_Categorie kolom met np.select ---
            conditions = [
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'Levering'),
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'Transport'),
                (df['Verzending-ID'] < 2510000000) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] > 2510999999) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] < 2510000000) & (df['Type'] != 'Laden'),
                (df['Verzending-ID'] > 2510999999) & (df['Type'] != 'Laden')
            ]

            choices = ['ICL AFH', 'ICL LEV', 'ICL DIRECT', 'TUF EXPORT', 'TUF EXPORT', 'TUF IMPORT', 'TUF IMPORT']
            
            df['Dienst_Categorie'] = np.select(conditions, choices, default='Overig/Onbekend')

            st.success("Bestand succesvol ingelezen en verwerkt!")

            # --- Dataverwerking: Bundel op 'Verzending-ID' en bereken de som van LM ---
            df_grouped = df.groupby(['Verzending-ID', 'Dienst_Categorie']).agg(
                LM=('LM', 'sum') # Aggregeer nu wel LM
            ).reset_index()

            # --- Totaaloverzicht alle zendingen (Aantallen en LM) ---
            st.subheader("1. Totaal Aantal Unieke Zendingen en Laadmeters (Algemeen)")

            total_zendingen = len(df_grouped) # Telt het aantal unieke Verzending-ID's
            total_lm = df_grouped['LM'].sum() # Totaal LM van alle gebundelde zendingen
            
            col1, col2 = st.columns(2) # Twee kolommen voor aantallen en LM
            with col1:
                st.metric(label="Totaal Aantal Unieke Zendingen", value=f"{total_zendingen:,.0f}")
            with col2:
                st.metric(label="Totale Laadmeter (LM)", value=f"{total_lm:,.2f} LM")

            st.write("---") # Visuele scheiding

            # --- Totaaloverzicht per Dienst_Categorie (Aantallen en LM) ---
            st.subheader("2. Totaal Aantal Unieke Zendingen en Laadmeters per Dienst Categorie")

            # Groepeer nu op de NIEUWE 'Dienst_Categorie' kolom en tel het aantal unieke Verzending-ID's + som LM
            df_summary_by_category = df_grouped.groupby('Dienst_Categorie').agg(
                Aantal_Unieke_Zendingen=('Verzending-ID', 'size'), # Telt het aantal unieke Verzending-ID's per categorie
                Totaal_LM=('LM', 'sum') # Telt de som van LM per categorie
            ).reset_index()

            # Hernoem kolommen voor duidelijkheid
            df_summary_by_category.columns = ['Dienst Categorie', 'Aantal Unieke Zendingen', 'Totaal LM']

            # Formatteer de numerieke kolommen voor weergave
            df_summary_by_category['Aantal Unieke Zendingen'] = df_summary_by_category['Aantal Unieke Zendingen'].map(lambda x: f"{x:,.0f}")
            df_summary_by_category['Totaal LM'] = df_summary_by_category['Totaal LM'].map(lambda x: f"{x:,.2f} LM")
            
            st.dataframe(df_summary_by_category, hide_index=True)

        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}. Controleer of het Excel-bestand de juiste opmaak en kolommen bevat.")
            st.error("Gedetailleerde foutmelding: " + str(e))
    
    st.write("---") # Visuele scheiding voor de nieuwe sectie

    # --- Nieuwe sectie: Voertuigbezetting Input ---
    st.subheader("3. Voertuigbezetting Invoer")

    # Kolomheaders voor de tabel
    col_labels = st.columns([0.2, 0.4, 0.4]) # Pas de breedte aan indien nodig
    with col_labels[0]:
        st.write("**Type Voertuig**")
    with col_labels[1]:
        st.write("**Beschikbaar**")
    with col_labels[2]:
        st.write("**Werk**")

    voertuig_types = ["Trekker", "Vrachtwagens", "Bestelwagens"]
    input_values = {}

    for v_type in voertuig_types:
        cols = st.columns([0.2, 0.4, 0.4])
        with cols[0]:
            st.write(v_type)
        with cols[1]:
            # Gebruik een unieke sleutel voor elk inputveld
            input_values[f'{v_type}_Beschikbaar'] = st.number_input(
                " ", # Label is leeg want de kolomheader is al aanwezig
                min_value=0,
                value=0,
                key=f'{v_type}_Beschikbaar_input', # Unieke sleutel
                label_visibility="collapsed" # Verberg het label van de number_input
            )
        with cols[2]:
            input_values[f'{v_type}_Werk'] = st.number_input(
                " ", # Label is leeg
                min_value=0,
                value=0,
                key=f'{v_type}_Werk_input', # Unieke sleutel
                label_visibility="collapsed" # Verberg het label van de number_input
            )
    
    st.write("---") # Visuele scheiding

    # Optioneel: Toon de ingevoerde waarden (voor debugging of bevestiging)
    # st.write("Ingevoerde waarden:")
    # st.write(input_values)


if __name__ == '__main__':
    app()
