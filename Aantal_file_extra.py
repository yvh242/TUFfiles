import streamlit as st
import pandas as pd
import io
from datetime import datetime, date

def app():
    st.title("Klantenoverzicht en Omzetanalyse")

    st.write("""
    Upload uw Excel-bestand(en) om een overzicht te krijgen van het aantal files en de totale omzet
    per klant, per maand. Files met 'Dossier Fin. Status' = 20 worden genegeerd in beide overzichten.
    De eerste tabel toont ook het percentage van het maximale aantal files per maand voor elke klant, en kan gefilterd worden op periode.
    Daarnaast wordt een aparte tabel getoond met files waar 'Prest. Eigen Bedrijf' = 0, inclusief het dossiernummer,
    met de mogelijkheid om op periode te filteren.
    """)

    # --- Upload meerdere bestanden ---
    uploaded_files = st.file_uploader("Kies een of meerdere Excel-bestanden", type=["xlsx", "xls"], accept_multiple_files=True)

    if not uploaded_files:
        st.info("Upload uw Excel-bestand(en) om te beginnen.")
        return

    # The main try-except block now wraps all file processing
    try:
        # --- Combineer alle geüploade bestanden ---
        all_dfs = []
        for uploaded_file in uploaded_files:
            try:
                df_single = pd.read_excel(uploaded_file)
                all_dfs.append(df_single)
            except Exception as e:
                st.warning(f"Kon bestand '{uploaded_file.name}' niet lezen: {e}. Dit bestand wordt overgeslagen.")
                continue # Ga door naar het volgende bestand

        if not all_dfs:
            st.error("Geen geldig Excel-bestand gevonden om te verwerken.")
            return

        df = pd.concat(all_dfs, ignore_index=True)

        # Controleer of de vereiste kolommen aanwezig zijn in de gecombineerde DataFrame
        required_columns = ['Klantnaam', 'Laaddatum', 'Prest. Eigen Bedrijf', 'Dossier Fin. Status']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            st.error(f"Een of meer geüploade Excel-bestanden missen de volgende vereiste kolommen: {', '.join(missing_cols)}")
            return

        # Filter de data: negeer rijen waar 'Dossier Fin. Status' 20 is voor alle volgende analyses
        df_processed = df[df['Dossier Fin. Status'] != 20].copy()

        if df_processed.empty:
            st.info("Na filtering op 'Dossier Fin. Status' (exclusief 20) zijn er geen gegevens meer om te analyseren.")
            return

        # Zorg ervoor dat 'Laaddatum' een datetime object is voor de gehele df_processed
        df_processed['Laaddatum'] = pd.to_datetime(df_processed['Laaddatum'])

        # Extraheer jaar en maand voor de eerste tabel
        df_processed['JaarMaand'] = df_processed['Laaddatum'].dt.to_period('M')

        # --- Filtering voor Tabel 1 in de sidebar ---
        st.sidebar.subheader("Filter voor Hoofdrapport (Tabel 1)")
        
        # Bepaal alle unieke jaren en maanden in de data
        all_years = sorted(df_processed['Laaddatum'].dt.year.unique())
        all_months = sorted(df_processed['Laaddatum'].dt.month.unique())

        # Formatteer maanden naar namen voor de dropdown
        month_names = {
            1: "Januari", 2: "Februari", 3: "Maart", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Augustus", 9: "September", 10: "Oktober", 11: "November", 12: "December"
        }
        
        # Gebruik selectbox of multiselect voor jaar en maand
        selected_year_t1 = st.sidebar.selectbox("Selecteer Jaar", all_years, index=len(all_years)-1 if all_years else 0)
        
        # Filter de maanden die beschikbaar zijn voor het geselecteerde jaar
        available_months_in_selected_year = sorted(df_processed[df_processed['Laaddatum'].dt.year == selected_year_t1]['Laaddatum'].dt.month.unique())
        selected_month_names = [month_names[m] for m in available_months_in_selected_year] # Standaard alle maanden in dat jaar

        selected_months_t1_str = st.sidebar.multiselect(
            "Selecteer Maand(en)",
            options=selected_month_names,
            default=selected_month_names if selected_month_names else [] # Selecteer standaard alle maanden van het jaar
        )
        
        # Converteer geselecteerde maandnamen terug naar nummers
        selected_months_t1_num = [k for k, v in month_names.items() if v in selected_months_t1_str]

        # Maak een lijst van 'JaarMaand' periodes die moeten worden weergegeven
        filtered_jaarmaanden_t1 = []
        for month_num in selected_months_t1_num:
            try:
                period_str = f"{selected_year_t1}-{month_num:02d}"
                filtered_jaarmaanden_t1.append(pd.Period(period_str, freq='M'))
            except ValueError:
                # Dit kan gebeuren als een maandnummer niet valide is (hoort niet als goed geselecteerd)
                continue
        filtered_jaarmaanden_t1 = sorted(filtered_jaarmaanden_t1)


        st.subheader("Overzicht per Klant en Maand (Exclusief Status 20)")

        # Aggregeer data met pivot_table
        pivot_aantal = df_processed.pivot_table(index='Klantnaam', columns='JaarMaand', aggfunc='size', fill_value=0)
        pivot_omzet = df_processed.pivot_table(index='Klantnaam', columns='JaarMaand', values='Prest. Eigen Bedrijf', aggfunc='sum', fill_value=0)

        # Bereken het maximum aantal files per klant over alle maanden in de GEFILTERDE data (voor consistentie)
        # Gebruik hiervoor pivot_aantal omdat die al rekening houdt met de status 20 filter
        max_files_per_klant = pivot_aantal.max(axis=1)


        # Bereid de kolommen voor het uiteindelijke DataFrame voor
        # We tonen alleen de geselecteerde maanden
        final_columns_order_t1 = ['Klantnaam']
        
        # Check of er gefilterde jaarmaanden zijn
        if not filtered_jaarmaanden_t1:
            st.info("Selecteer minimaal één maand in de sidebar voor het hoofdrapport.")
            # Toon een lege dataframe of stop hier de weergave van de eerste tabel
            st.dataframe(pd.DataFrame(columns=['Klant']))
        else:
            for jm in filtered_jaarmaanden_t1:
                final_columns_order_t1.append(f"{jm.strftime('%Y-%m')} A")
                final_columns_order_t1.append(f"{jm.strftime('%Y-%m')} O")
                final_columns_order_t1.append(f"{jm.strftime('%Y-%m')} P") # Nieuwe kolom voor percentage
            
            # Maak een leeg DataFrame met de juiste kolommen
            result_df = pd.DataFrame(columns=final_columns_order_t1)

            # Vul het resultaat DataFrame
            for klantnaam in df_processed['Klantnaam'].unique():
                row_data = {'Klantnaam': klantnaam}
                max_files = max_files_per_klant.get(klantnaam, 0) # Haal de max files voor deze klant op
                
                for jm in filtered_jaarmaanden_t1:
                    # Zorg ervoor dat de maand daadwerkelijk in pivot_aantal/omzet voorkomt voordat je opzoekt
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
            # Voorkom errors als df_zero_omzet leeg is (wat kan gebeuren na filtering)
            min_date_t2 = df_zero_omzet['Laaddatum'].min().date() if not df_zero_omzet.empty else date.today()
            max_date_t2 = df_zero_omzet['Laaddatum'].max().date() if not df_zero_omzet.empty else date.today()

            # Datum input velden
            start_date_t2 = st.sidebar.date_input("Startdatum (Tabel 2)", min_value=min_date_t2, max_value=max_date_t2, value=min_date_t2)
            end_date_t2 = st.sidebar.date_input("Einddatum (Tabel 2)", min_value=min_date_t2, max_value=max_date_t2, value=max_date_t2)

            # Zorg ervoor dat de einddatum niet voor de startdatum ligt
            if start_date_t2 > end_date_t2:
                st.sidebar.error("Einddatum kan niet voor startdatum liggen.")
                return

            # Filter de df_zero_omzet op de geselecteerde periode
            df_zero_omzet_filtered_by_date = df_zero_omzet[
                (df_zero_omzet['Laaddatum'].dt.date >= start_date_t2) &
                (df_zero_omzet['Laaddatum'].dt.date <= end_date_t2)
            ].copy()

            if df_zero_omzet_filtered_by_date.empty:
                st.info(f"Geen files gevonden met 'Prest. Eigen Bedrijf' = 0 in de periode van {start_date_t2} tot {end_date_t2}.")
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
