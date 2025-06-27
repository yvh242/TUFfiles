import streamlit as st
import pandas as pd
import numpy as np
import io

# Importeer de bibliotheek voor PDF-export
# Dit vereist dat je 'weasyprint' installeert: pip install weasyprint
# En ook dat de onderliggende pakketten voor WeasyPrint aanwezig zijn (zie toelichting na de code)
from weasyprint import HTML

def app():
    st.title("Verzenddata Analyse: Aantallen en Laadmeters")

    st.write("""
    Upload uw Excel-bestand om uw verzenddata te analyseren.
    De app bundelt data per unieke 'Verzending-ID'.
    Er wordt een nieuwe 'Afdeling' kolom aangemaakt op basis van 'Verzending-ID' en 'Type'.
    Vervolgens worden de **totalen van zendingen** en **totale Laadmeters (LM)** getoond voor alle zendingen en per 'Afdeling'.
    Daarnaast is er een sectie om de beschikbaarheid en werk van voertuigen in te voeren.
    """)

    uploaded_file = st.file_uploader("Kies een Excel-bestand", type=["xlsx", "xls"])

    df_grouped = pd.DataFrame() # Initialize df_grouped outside if/else

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
            
            # --- Aanmaken van de nieuwe Afdeling kolom met np.select ---
            conditions = [
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'levering'),
                (df['Verzending-ID'] >= 2510000000) & (df['Verzending-ID'] <= 2510999999) & (df['Type'] == 'Transport'),
                (df['Verzending-ID'] < 2510000000) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] > 2510999999) & (df['Type'] == 'Laden'),
                (df['Verzending-ID'] < 2510000000) & (df['Type'] != 'Laden'),
                (df['Verzending-ID'] > 2510999999) & (df['Type'] != 'Laden')
            ]

            choices = ['ICL AFH', 'ICL LEV', 'ICL DIRECT', 'TUF EXPORT', 'TUF EXPORT', 'TUF IMPORT', 'TUF IMPORT']
            
            df['Afdeling'] = np.select(conditions, choices, default='Overig/Onbekend') # Aangepast: 'Dienst_Categorie' -> 'Afdeling'

            st.success("Bestand succesvol ingelezen en verwerkt!")

            # --- Dataverwerking: Bundel op 'Verzending-ID' en bereken de som van LM ---
            df_grouped = df.groupby(['Verzending-ID', 'Afdeling']).agg( # Aangepast: 'Dienst_Categorie' -> 'Afdeling'
                LM=('LM', 'sum')
            ).reset_index()

            # --- Totaaloverzicht alle zendingen (Zendingen en LM) ---
            st.subheader("1. Totaal")

            total_zendingen = len(df_grouped)
            total_lm = df_grouped['LM'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Totaal Zendingen", value=f"{total_zendingen:,.0f}") # Aangepast label (geen bold)
            with col2:
                st.metric(label="Totale Laadmeter (LM)", value=f"{total_lm:,.2f} LM")

            st.write("---")

            # --- Totaaloverzicht per Afdeling (Zendingen en LM) ---
            st.subheader("2. Detail")

            df_summary_by_category = df_grouped.groupby('Afdeling').agg( # Aangepast: 'Dienst_Categorie' -> 'Afdeling'
                Zendingen=('Verzending-ID', 'size'),
                Totaal_LM=('LM', 'sum')
            ).reset_index()

            # Hernoem kolommen voor duidelijkheid
            df_summary_by_category.columns = ['Afdeling', 'Zendingen', 'Totaal LM'] # Aangepast: 'Dienst Categorie' -> 'Afdeling'
            
            # Formatteer de numerieke kolommen voor weergave
            df_summary_by_category['Zendingen'] = df_summary_by_category['Zendingen'].map(lambda x: f"{x:,.0f}")
            df_summary_by_category['Totaal LM'] = df_summary_by_category['Totaal LM'].map(lambda x: f"{x:,.2f} LM")
            
            st.dataframe(df_summary_by_category, hide_index=True)

        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}. Controleer of het Excel-bestand de juiste opmaak en kolommen bevat.")
            st.error("Gedetailleerde foutmelding: " + str(e))
    
    st.write("---")

    # --- Nieuwe sectie: Voertuigbezetting Input ---
    st.subheader("3. Voertuigen")

    # Kolomheaders voor de tabel
    col_labels = st.columns([0.2, 0.4, 0.4])
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
            input_values[f'{v_type}_Beschikbaar'] = st.number_input(
                " ", 
                min_value=0,
                value=0,
                key=f'{v_type}_Beschikbaar_input', 
                label_visibility="collapsed" 
            )
        with cols[2]:
            input_values[f'{v_type}_Werk'] = st.number_input(
                " ", 
                min_value=0,
                value=0,
                key=f'{v_type}_Werk_input', 
                label_visibility="collapsed" 
            )
    
    st.write("---") 

    # --- PDF Export Functie ---
    st.subheader("Rapport Exporteren")
    if st.button("Genereer PDF Rapport"):
        if uploaded_file is None:
            st.warning("Upload eerst een Excel-bestand om een rapport te genereren.")
        elif df_grouped.empty:
            st.warning("Geen data om te exporteren. Controleer uw Excel-bestand en filters.")
        else:
            # Vang de output van de Streamlit elementen op door ze in een aparte functie te wrappen
            # en deze functie later aan te rogen voor de PDF-generatie.
            # Dit is een vereenvoudigde aanpak; complexe layouts vereisen meer HTML/CSS.
            html_report = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Verzenddata Rapport</title>
                <style>
                    body {{ font-family: sans-serif; margin: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .metric {{ border: 1px solid #eee; padding: 10px; margin: 5px; border-radius: 5px; display: inline-block; min-width: 150px; text-align: center; }}
                    .metric label {{ font-size: 0.9em; color: #555; }}
                    .metric value {{ font-size: 1.5em; font-weight: bold; color: #000; }}
                </style>
            </head>
            <body>
                <h1>Verzenddata Analyse Rapport</h1>
                <p>Rapport gegenereerd op: {pd.Timestamp.now().strftime('%d-%m-%Y %H:%M')}</p>

                <h2>1. Totaal</h2>
                <div style="display: flex; justify-content: space-around;">
                    <div class="metric">
                        <label>Totaal Zendingen</label><br>
                        <span class="value">{total_zendingen:,.0f}</span>
                    </div>
                    <div class="metric">
                        <label>Totale Laadmeter (LM)</label><br>
                        <span class="value">{total_lm:,.2f} LM</span>
                    </div>
                </div>

                <h2>2. Detail</h2>
                {df_summary_by_category.to_html(index=False)}

                <h2>3. Voertuigen</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Type Voertuig</th>
                            <th>Beschikbaar</th>
                            <th>Werk</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for v_type in voertuig_types:
                html_report += f"""
                        <tr>
                            <td>{v_type}</td>
                            <td>{input_values.get(f'{v_type}_Beschikbaar', 0)}</td>
                            <td>{input_values.get(f'{v_type}_Werk', 0)}</td>
                        </tr>
                """
            html_report += """
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            # Genereer de PDF
            pdf_bytes = HTML(string=html_report).write_pdf()

            st.download_button(
                label="Download PDF Rapport",
                data=pdf_bytes,
                file_name="Verzenddata_Rapport.pdf",
                mime="application/pdf"
            )
            st.success("PDF rapport succesvol gegenereerd en beschikbaar voor download!")


if __name__ == '__main__':
    app()
