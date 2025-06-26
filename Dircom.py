import streamlit as st
import pandas as pd
import numpy as np
import io

def app():
    st.title("Verzenddata Analyse: Enkel Aantallen")

    st.write("""
    Upload uw Excel-bestand om uw verzenddata te analyseren.
    De app bundelt data per unieke 'Verzending-ID'.
    Er wordt een nieuwe 'Dienst_Categorie' kolom aangemaakt op basis van 'Verzending-ID' en 'Type'.
    Vervolgens worden de **totalen van unieke zendingen** getoond voor alle zendingen en per 'Dienst_Categorie'.
    """)

    uploaded_file = st.file_uploader("Kies een Excel-bestand", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Lees het Excel-bestand in
            df = pd.read_excel(uploaded_file)

            # --- Controleer op vereiste kolommen ---
            # 'Kg', 'm³', 'LM' zijn nu niet meer strikt nodig voor de output,
            # maar 'Verzending-ID' en 'Type' wel voor de categorisatie en telling.
            required_columns_for_processing = ['Verzending-ID', 'Type']
            
            # Voeg Kg, m³, LM toe als ze bestaan, zodat pd.to_numeric geen fout geeft als ze ontbreken
            # en de aggregatie correct verloopt als ze wel aanwezig zijn maar niet getoond.
            # Echter, als ze niet nodig zijn voor *verwerking* behalve voor het aanmaken van df_grouped,
            # en je ze niet aggregeert, hoeven ze hier niet perse als 'required_columns'.
            # Voor de zekerheid laten we ze hier nog staan als je ze onverhoopt toch zou gebruiken elders.
            # Maar voor de huidige vraag: enkel 'Verzending-ID' en 'Type' zijn kritisch.
            
            # Echter, als je 'Kg', 'm³', 'LM' volledig negeert, dan moet je opletten dat de bron geen fouten geeft.
            # We gaan er vanuit dat ze wel in het bestand staan, maar we ze gewoon niet aggregeren.
            # Als ze niet bestaan, dan zou df['Kg'] bijvoorbeeld een KeyError geven.
            # We passen de required_columns aan naar wat we *echt* nodig hebben voor dit rapport.
            required_columns_for_this_report = ['Verzending-ID', 'Type'] 
            
            # Controleer of 'Kg', 'm³', 'LM' bestaan als je ze toch nog zou willen verwerken als numeriek
            # ook al worden ze niet getoond. Voor dit rapport zijn ze niet strikt noodzakelijk meer.
            # We focussen enkel op de kolommen die we echt nodig hebben voor de telling en categorisatie.
            
            missing_columns = [col for col in required_columns_for_this_report if col not in df.columns]

            if missing_columns:
                st.error(f"Het Excel-bestand mist de volgende vereiste kolommen voor dit rapport: {', '.join(missing_columns)}. Gelieve een bestand te uploaden met alle benodigde kolommen.")
                return

            # --- Data Voorbereiding ---
            # 'Verzending-ID' moet numeriek zijn voor de categorisatie
            df['Verzending-ID'] = pd.to_numeric(df['Verzending-ID'], errors='coerce')
            
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

            # --- Dataverwerking: Bundel op 'Verzending-ID' en bewaar de nieuwe 'Dienst_Categorie' ---
            # We aggregeren nu alleen op 'size' om het aantal unieke Verzending-ID's te tellen per combinatie
            # van Verzending-ID en Dienst_Categorie. De andere numerieke kolommen worden niet meegenomen.
            df_grouped = df.groupby(['Verzending-ID', 'Dienst_Categorie']).size().reset_index(name='Aantal items per Verzending-ID')
            # De kolom 'Aantal items per Verzending-ID' is hier niet direct relevant voor de outputs,
            # maar het reset_index() zorgt ervoor dat we df_grouped weer kunnen gebruiken.
            # Het belangrijkste is dat df_grouped nu een lijst van unieke Verzending-ID's met hun Dienst_Categorie is.

            # --- Totaaloverzicht alle zendingen (enkel aantal) ---
            st.subheader("1. Totaal Aantal Unieke Zendingen (Algemeen)")

            total_zendingen = len(df_grouped) # Telt het aantal unieke Verzending-ID's
            
            st.metric(label="Totaal Aantal Unieke Zendingen", value=f"{total_zendingen:,.0f}")

            st.write("---") # Visuele scheiding

            # --- Totaaloverzicht per Dienst_Categorie (enkel aantal) ---
            st.subheader("2. Totaal Aantal Unieke Zendingen per Dienst Categorie")

            # Groepeer nu op de NIEUWE 'Dienst_Categorie' kolom en tel het aantal unieke Verzending-ID's
            df_summary_by_category = df_grouped.groupby('Dienst_Categorie').agg(
                Aantal_Unieke_Zendingen=('Verzending-ID', 'size')
            ).reset_index()

            # Hernoem kolommen voor duidelijkheid
            df_summary_by_category.columns = ['Dienst Categorie', 'Aantal Unieke Zendingen']

            # Formatteer de numerieke kolommen voor weergave
            df_summary_by_category['Aantal Unieke Zendingen'] = df_summary_by_category['Aantal Unieke Zendingen'].map(lambda x: f"{x:,.0f}")
            
            st.dataframe(df_summary_by_category, hide_index=True)


        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}. Controleer of het Excel-bestand de juiste opmaak en kolommen bevat.")
            st.error("Gedetailleerde foutmelding: " + str(e))

if __name__ == '__main__':
    app()
