import streamlit as st
import pandas as pd
import io

def app():
    st.title("Verzenddata Analyse")

    st.write("""
    Upload uw Excel-bestand om uw verzenddata te analyseren.
    De app bundelt data per unieke 'Verzending-ID' en telt de numerieke kolommen 'Kg', 'm³' en 'LM' samen.
    Vervolgens worden de totalen getoond voor alle zendingen en per 'Type'.
    """)

    uploaded_file = st.file_uploader("Kies een Excel-bestand", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Lees het Excel-bestand in
            df = pd.read_excel(uploaded_file)

            # --- Controleer op vereiste kolommen ---
            required_columns = ['Verzending-ID', 'Kg', 'm³', 'LM', 'Type']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                st.error(f"Het Excel-bestand mist de volgende vereiste kolommen: {', '.join(missing_columns)}. Gelieve een bestand te uploaden met alle benodigde kolommen.")
                return

            # --- Dataverwerking ---
            # Zorg ervoor dat numerieke kolommen de juiste datatype hebben, forceer naar numeric
            for col in ['Kg', 'm³', 'LM']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # 'coerce' zet niet-numerieke waarden om in NaN, fillna(0) vult deze met 0

            # Bundel op 'Verzending-ID' en tel de numerieke kolommen samen
            # Voor 'Type' nemen we de eerste waarde die we tegenkomen, ervan uitgaande dat deze consistent is per Verzending-ID
            # Als 'Type' per 'Verzending-ID' kan variëren en je een specifieke logica wilt (bijv. meest voorkomende), dan moet dit aangepast worden.
            df_grouped = df.groupby('Verzending-ID').agg(
                Kg=('Kg', 'sum'),
                m3=('m³', 'sum'),
                LM=('LM', 'sum'),
                Type=('Type', 'first') # Neem het eerste type dat bij deze Verzending-ID hoort
            ).reset_index()

            st.success("Bestand succesvol ingelezen en verwerkt!")

            # --- Totaaloverzicht alle zendingen ---
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

            # --- Totaaloverzicht per Type ---
            st.subheader("2. Totaaloverzicht per Type")

            # Groepeer op 'Type' en bereken de totalen
            df_summary_by_type = df_grouped.groupby('Type').agg(
                Aantal_Zendingen=('Verzending-ID', 'size'),
                Totaal_Kg=('Kg', 'sum'),
                Totaal_LM=('LM', 'sum')
            ).reset_index()

            # Hernoem kolommen voor duidelijkheid
            df_summary_by_type.columns = ['Type', 'Aantal Zendingen', 'Totaal Kg', 'Totaal LM']

            # Formatteer de numerieke kolommen voor weergave
            df_summary_by_type['Totaal Kg'] = df_summary_by_type['Totaal Kg'].map(lambda x: f"{x:,.2f} Kg")
            df_summary_by_type['Totaal LM'] = df_summary_by_type['Totaal LM'].map(lambda x: f"{x:,.2f} LM")
            df_summary_by_type['Aantal Zendingen'] = df_summary_by_type['Aantal Zendingen'].map(lambda x: f"{x:,.0f}")


            st.dataframe(df_summary_by_type, hide_index=True)


        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}. Controleer of het Excel-bestand de juiste opmaak en kolommen bevat.")
            st.error("Mogelijke oorzaak: Ontbrekende bladen, verkeerde kolomnamen, of onverwachte data in numerieke kolommen.")

if __name__ == '__main__':
    app()
