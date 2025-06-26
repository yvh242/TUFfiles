import streamlit as st
import pandas as pd
import io
from datetime import datetime, date

def app():
    st.title("Klantenoverzicht en Omzetanalyse")

    st.write("""
    Upload uw Excel-bestand om een overzicht te krijgen van het aantal files en de totale omzet
    per klant, per maand. Files met 'Dossier Fin. Status' = 20 worden genegeerd in beide overzichten.
    De eerste tabel toont ook het percentage van het maximale aantal files per maand voor elke klant.
    Daarnaast wordt een aparte tabel getoond met files waar 'Prest. Eigen Bedrijf' = 0, inclusief het dossiernummer,
    met de mogelijkheid om op periode te filteren.
    """)

    uploaded_file = st.file_uploader("Kies een Excel-bestand", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Lees het Excel-bestand in
            df = pd.read_excel(uploaded_file)

            # Controleer of de vereiste kolommen aanwezig zijn
            required_columns = ['Klantnaam', 'Laaddatum', 'Prest. Eigen Bedrijf', 'Dossier Fin. Status']
            # 'Dossiernr' is optioneel, dus controleren we die apart
            if not all(col in df.columns for col in required_columns):
                st.error(f"Het Excel-bestand moet de volgende kolommen bevatten: {', '.join(required_columns)}")
                return

            # Filter de data: negeer rijen waar 'Dossier Fin. Status' 20 is voor alle volgende analyses
            # Maak hier direct een kopie om waarschuwingen te voorkomen
            df_processed = df[df['Dossier Fin. Status'] != 20].copy()

            if df_processed.empty:
                st.info("Na filtering op 'Dossier Fin. Status' (exclusief 20) zijn er geen gegevens meer om te analyseren.")
                return # Stop de uitvoering als er geen data is na de filtering

            # Zorg ervoor dat 'Laaddatum' een datetime object is voor de gehele df_processed
            df_processed['Laaddatum'] = pd.to_datetime(df_processed['Laaddatum'])

            st.subheader("Overzicht per Klant en Maand (Exclusief Status 20)")

            # Extraheer jaar en maand voor de eerste tabel
            df_processed['JaarMaand'] = df_processed['Laaddatum'].dt.to_period('M')

            # Aggregeer data met pivot_table
            pivot_aantal = df_processed.pivot_table(index='Klantnaam', columns='JaarMaand', aggfunc='size', fill_value=0)
            pivot_omzet = df_processed.pivot_table(index='Klantnaam', columns='JaarMaand', values='Prest. Eigen Bedrijf', aggfunc='sum', fill_value=0)

            # Bereken het maximum aantal files per klant over alle maanden
            # We moeten de pivot_aantal tijdelijk 'unstacken' om de max per klant te vinden over alle maanden
            max_files_per_klant = pivot_aantal.max(axis=1)

            # Sorteer de maanden voor consistente kolomvolgorde
            all_jaarmaanden = sorted(df_processed['JaarMaand'].unique())

            # Bereid de kolommen voor het uiteindelijke DataFrame voor
            final_columns_order = ['Klantnaam']
            for jm in all_jaarmaanden:
                final_columns_order.append(f"{jm.strftime('%Y-%m')} A")
                final_columns_order.append(f"{jm.strftime('%Y-%m')} O")
                final_columns_order.append(f"{jm.strftime('%Y-%m')} P") # Nieuwe kolom voor percentage
            
            # Maak een leeg DataFrame met de juiste kolommen
            result_df = pd.DataFrame(columns=final_columns_order)

            # Vul het resultaat DataFrame
            for klantnaam in df_processed['Klantnaam'].unique():
                row_data = {'Klantnaam': klantnaam}
                max_files = max_files_per_klant.get(klantnaam, 0) # Haal de max files voor deze klant op
                
                for jm in all_jaarmaanden:
                    aantal = pivot_aantal.loc[klantnaam, jm] if jm in pivot_aantal.columns and klantnaam in pivot_aantal.index else 0
                    omzet = pivot_omzet.loc[klantnaam, jm] if jm in pivot_omzet.columns and klantnaam in pivot_omzet.index else 0
                    
                    percentage = (aantal / max_files * 100) if max_files > 0 else 0 # Bereken percentage
                    
                    row_data[f"{jm.strftime('%Y-%m')} A"] = aantal
                    row_data[f"{jm.strftime('%Y-%m')} O"] = f"€{omzet:,.2f}" # Opmaak als valuta
                    row_data[f"{jm.strftime('%Y-%m')} P"] = f"{percentage:,.0f} %" # Opmaak als percentage zonder decimalen

                result_df = pd.concat([result_df, pd.DataFrame([row_data])], ignore_index=True)

            # Hernoem de eerste kolom
            result_df = result_df.rename(columns={'Klantnaam': 'Klant'})
            
            # Toon de eerste tabel
            st.dataframe(result_df, hide_index=True)

            st.subheader("Files met 'Prest. Eigen Bedrijf' = 0 (Exclusief Status 20)")

            # Filter de *reeds gefilterde* data (df_processed) voor rijen waar 'Prest. Eigen Bedrijf' 0 is
            df_zero_omzet = df_processed[df_processed['Prest. Eigen Bedrijf'] == 0].copy()

            if df_zero_omzet.empty:
                st.info("Geen files gevonden met 'Prest. Eigen Bedrijf' = 0 na filtering op status 20.")
            else:
                # Datumfilter voor de tweede tabel
                st.sidebar.subheader("Filter voor Files met 0 Omzet")
                
                # Bepaal de minimale en maximale datum in de data voor de datumselector
                min_date = df_zero_omzet['Laaddatum'].min().date()
                max_date = df_zero_omzet['Laaddatum'].max().date()

                # Datum input velden
                start_date = st.sidebar.date_input("Startdatum", min_value=min_date, max_value=max_date, value=min_date)
                end_date = st.sidebar.date_input("Einddatum", min_value=min_date, max_value=max_date, value=max_date)

                # Zorg ervoor dat de einddatum niet voor de startdatum ligt
                if start_date > end_date:
                    st.sidebar.error("Einddatum kan niet voor startdatum liggen.")
                    return

                # Filter de df_zero_omzet op de geselecteerde periode
                df_zero_omzet_filtered_by_date = df_zero_omzet[
                    (df_zero_omzet['Laaddatum'].dt.date >= start_date) &
                    (df_zero_omzet['Laaddatum'].dt.date <= end_date)
                ].copy()

                if df_zero_omzet_filtered_by_date.empty:
                    st.info(f"Geen files gevonden met 'Prest. Eigen Bedrijf' = 0 in de periode van {start_date} tot {end_date}.")
                else:
                    # Selecteer de relevante kolommen voor de tweede tabel
                    display_columns_zero_omzet = ['Klantnaam', 'Laaddatum', 'Prest. Eigen Bedrijf', 'Dossier Fin. Status']
                    
                    # Voeg 'Dossiernr' toe als het bestaat
                    if 'Dossiernr' in df_zero_omzet_filtered_by_date.columns:
                        display_columns_zero_omzet.insert(0, 'Dossiernr') # Voeg 'Dossiernr' vooraan toe

                    st.dataframe(df_zero_omzet_filtered_by_date[display_columns_zero_omzet], hide_index=True)

        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}")

if __name__ == '__main__':
    app()
