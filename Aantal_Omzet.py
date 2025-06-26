import streamlit as st
import pandas as pd
import io

def app():
    st.title("Klantenoverzicht per Maand")

    st.write("""
    Upload uw Excel-bestand om een overzicht te krijgen van het aantal files en de totale omzet
    per klant, per maand.
    """)

    uploaded_file = st.file_uploader("Kies een Excel-bestand", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Lees het Excel-bestand in
            df = pd.read_excel(uploaded_file)

            # Controleer of de vereiste kolommen aanwezig zijn
            required_columns = ['Klantnaam', 'Laaddatum', 'Prest. Eigen Bedrijf']
            if not all(col in df.columns for col in required_columns):
                st.error(f"Het Excel-bestand moet de volgende kolommen bevatten: {', '.join(required_columns)}")
                return

            # Zorg ervoor dat 'Laaddatum' een datetime object is
            df['Laaddatum'] = pd.to_datetime(df['Laaddatum'])

            # Extraheer jaar en maand
            df['JaarMaand'] = df['Laaddatum'].dt.to_period('M')

            # Initialiseer een dictionary om de resultaten op te slaan
            klant_maand_data = {}

            for index, row in df.iterrows():
                klantnaam = row['Klantnaam']
                jaar_maand = str(row['JaarMaand']) # Convert Period to string for dictionary key
                omzet = row['Prest. Eigen Bedrijf']

                if klantnaam not in klant_maand_data:
                    klant_maand_data[klantnaam] = {}
                
                if jaar_maand not in klant_maand_data[klantnaam]:
                    klant_maand_data[klantnaam][jaar_maand] = {'aantal_files': 0, 'totale_omzet': 0}
                
                klant_maand_data[klantnaam][jaar_maand]['aantal_files'] += 1
                klant_maand_data[klantnaam][jaar_maand]['totale_omzet'] += omzet

            # Maak een lijst van alle unieke JaarMaand-combinaties
            all_jaarmaanden = sorted(df['JaarMaand'].unique())
            all_jaarmaanden_str = [str(jm) for jm in all_jaarmaanden]

            # Bereid de data voor de Streamlit tabel voor
            table_data = []
            for klant, maanden_data in klant_maand_data.items():
                row_data = {'Klant': klant}
                for jm in all_jaarmaanden_str:
                    aantal = maanden_data.get(jm, {}).get('aantal_files', 0)
                    omzet = maanden_data.get(jm, {}).get('totale_omzet', 0)
                    row_data[jm] = f"{aantal} files, €{omzet:,.2f}"
                table_data.append(row_data)

            # Converteer naar een DataFrame voor weergave in Streamlit
            result_df = pd.DataFrame(table_data)
            
            st.subheader("Overzicht per Klant en Maand")
            st.dataframe(result_df, hide_index=True)

        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}")

if __name__ == '__main__':
    app()
