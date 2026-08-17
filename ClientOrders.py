import streamlit as st
import pandas as pd
import urllib.parse

st.set_page_config(page_title="Verzendingsoverzicht per Opdrachtgever", layout="wide")

# ---------------------------------------------------------------------------
# HARDCODED: koppeling Opdrachtgever -> e-mailadres
# Pas deze lijst hier aan naar wens.
# ---------------------------------------------------------------------------
OPDRACHTGEVER_EMAILS = {
    "Klant A": "klantA@example.com",
    "Klant B": "klantB@example.com",
    "Klant C": "klantC@example.com",
}

# Kolommen die in het overzicht per opdrachtgever moeten komen (in deze volgorde)
KOLOMMEN_OVERZICHT = [
    "Verzending-ID",
    "Type",
    "PC",
    "Plaatsnaam",
    "Kg",
    "LM",
    "Aantal",
    "Goederen",
    "ETA",
]

st.title("📦 Verzendingsoverzicht per Opdrachtgever")

uploaded_file = st.file_uploader("Upload het Excel-bestand", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Kon het bestand niet inlezen: {e}")
        st.stop()

    # Check of alle nodige kolommen aanwezig zijn
    verplichte_kolommen = set(KOLOMMEN_OVERZICHT + ["Opdrachtgever"])
    ontbrekend = verplichte_kolommen - set(df.columns)
    if ontbrekend:
        st.error(f"Volgende kolommen ontbreken in het bestand: {', '.join(sorted(ontbrekend))}")
        st.stop()

    st.success(f"Bestand ingelezen: {len(df)} rijen gevonden.")

    opdrachtgevers_in_bestand = set(df["Opdrachtgever"].dropna().unique())
    onbekende_opdrachtgevers = opdrachtgevers_in_bestand - set(OPDRACHTGEVER_EMAILS.keys())
    if onbekende_opdrachtgevers:
        st.warning(
            "Volgende opdrachtgevers staan in het bestand maar hebben geen "
            f"gekoppeld e-mailadres in de code: {', '.join(sorted(onbekende_opdrachtgevers))}"
        )

    for opdrachtgever, email in OPDRACHTGEVER_EMAILS.items():
        subset = df[df["Opdrachtgever"] == opdrachtgever]

        if subset.empty:
            continue

        st.markdown("---")
        st.subheader(f"📋 {opdrachtgever}  ·  {email}")

        overzicht = subset[KOLOMMEN_OVERZICHT].copy()
        st.dataframe(overzicht, use_container_width=True, hide_index=True)

        # ---- Mailtekst opbouwen (platte tekst tabel) ----
        mail_lines = []
        mail_lines.append("Beste,")
        mail_lines.append("")
        mail_lines.append(f"Hieronder vindt u het overzicht van de uit te voeren zendingen voor {opdrachtgever}:")
        mail_lines.append("")

        header = " | ".join(KOLOMMEN_OVERZICHT)
        mail_lines.append(header)
        mail_lines.append("-" * len(header))
        for _, row in overzicht.iterrows():
            regel = " | ".join(str(row[k]) for k in KOLOMMEN_OVERZICHT)
            mail_lines.append(regel)

        mail_lines.append("")
        mail_lines.append("Met vriendelijke groeten,")

        mail_body = "\n".join(mail_lines)
        mail_subject = f"Overzicht uit te voeren zendingen - {opdrachtgever}"

        with st.expander("✉️ Mail voorbereiden"):
            st.text_area(
                "Mailtekst (aanpasbaar vóór verzending)",
                mail_body,
                height=280,
                key=f"body_{opdrachtgever}",
            )

            mailto_link = (
                f"mailto:{email}"
                f"?subject={urllib.parse.quote(mail_subject)}"
                f"&body={urllib.parse.quote(mail_body)}"
            )
            st.markdown(f"[📧 Open deze mail in je mailprogramma]({mailto_link})")
            st.caption(
                "Let op: sommige mailprogramma's/browsers beperken de lengte van "
                "mailto-links. Bij een groot aantal zendingen kan het nodig zijn "
                "de tekst hierboven te kopiëren en manueel in je mailprogramma te plakken."
            )
else:
    st.info("Upload een Excel-bestand om te starten.")
