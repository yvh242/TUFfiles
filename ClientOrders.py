import streamlit as st
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="Verzendingsoverzicht per Opdrachtgever", layout="wide")

# ---------------------------------------------------------------------------
# HARDCODED: koppeling Opdrachtgever-code -> (e-mailadres, klantnaam)
# Pas/vul deze lijst hier verder aan.
# LET OP: 'Opdrachtgever' is een numeriek veld in het Excel-bestand.
# Zet de codes hieronder toch als STRING (bv. "1004438", niet 1004438);
# de code zet de kolom uit Excel automatisch om naar hetzelfde stringformaat.
# ---------------------------------------------------------------------------
OPDRACHTGEVER_INFO = {
    "1004438": {"email": "yves.vanholsbeke@transuniverse.be", "naam": "Cargoliner"},
    "1001764": {"email": "yves.vanholsbeke@transuniverse.be", "naam": "ECU"},
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


def normaliseer_opdrachtgever(x):
    """Zet Opdrachtgever om naar een schone string, ook als het een
    numerieke waarde is (voorkomt bv. '123.0' i.p.v. '123')."""
    if pd.isna(x):
        return x
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x).strip()


def bouw_html_tabel(overzicht: pd.DataFrame) -> str:
    """Bouwt een mooi opgemaakte, uitgelijnde HTML-tabel voor in de mail."""
    kolom_stijl = (
        "border:1px solid #cccccc; padding:6px 10px; "
        "font-family:Calibri,Arial,sans-serif; font-size:11pt;"
    )
    header_stijl = kolom_stijl + " background-color:#1F4E78; color:#ffffff; text-align:left;"

    html = [
        '<table style="border-collapse:collapse; width:100%;">',
        "<tr>",
    ]
    for kol in KOLOMMEN_OVERZICHT:
        html.append(f'<th style="{header_stijl}">{kol}</th>')
    html.append("</tr>")

    for i, (_, row) in enumerate(overzicht.iterrows()):
        rij_kleur = "#ffffff" if i % 2 == 0 else "#F2F2F2"
        html.append("<tr>")
        for kol in KOLOMMEN_OVERZICHT:
            waarde = row[kol]
            waarde = "" if pd.isna(waarde) else waarde
            html.append(
                f'<td style="{kolom_stijl} background-color:{rij_kleur};">{waarde}</td>'
            )
        html.append("</tr>")

    html.append("</table>")
    return "".join(html)


def bouw_eml(to_email: str, subject: str, html_body: str) -> bytes:
    """Bouwt een .eml-bestand dat Outlook als bewerkbare, klaarstaande
    mail opent (X-Unsent: 1 zorgt dat het als concept opent i.p.v.
    als gelezen bericht)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to_email
    msg["X-Unsent"] = "1"

    plain_fallback = "Deze mail bevat een overzicht in tabelvorm. Open dit bestand in Outlook om de opgemaakte versie te zien."
    msg.attach(MIMEText(plain_fallback, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    return msg.as_bytes()


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

    df["Opdrachtgever"] = df["Opdrachtgever"].apply(normaliseer_opdrachtgever)

    opdrachtgevers_in_bestand = set(df["Opdrachtgever"].dropna().unique())
    onbekende_opdrachtgevers = opdrachtgevers_in_bestand - set(OPDRACHTGEVER_INFO.keys())
    if onbekende_opdrachtgevers:
        st.warning(
            "Volgende opdrachtgever-codes staan in het bestand maar hebben geen "
            f"gekoppeld e-mailadres in de code: {', '.join(sorted(onbekende_opdrachtgevers))}"
        )

    for code, info in OPDRACHTGEVER_INFO.items():
        email = info["email"]
        naam = info["naam"]

        subset = df[df["Opdrachtgever"] == code]
        if subset.empty:
            continue

        st.markdown("---")
        st.subheader(f"📋 {naam}  (code {code})  ·  {email}")

        overzicht = subset[KOLOMMEN_OVERZICHT].copy()
        st.dataframe(overzicht, use_container_width=True, hide_index=True)

        # ---- HTML-mail opbouwen ----
        tabel_html = bouw_html_tabel(overzicht)
        mail_html = f"""
        <html>
        <body style="font-family:Calibri,Arial,sans-serif; font-size:11pt;">
            <p>Beste,</p>
            <p>Hieronder vindt u het overzicht van de uit te voeren zendingen voor <b>{naam}</b>:</p>
            {tabel_html}
            <p>Met vriendelijke groeten,</p>
        </body>
        </html>
        """

        mail_subject = f"Overzicht uit te voeren zendingen - {naam}"

        with st.expander("✉️ Mail voorbereiden"):
            st.markdown("**Voorbeeld van de mail:**")
            st.markdown(mail_html, unsafe_allow_html=True)

            eml_bytes = bouw_eml(email, mail_subject, mail_html)

            st.download_button(
                label="📥 Download als Outlook-mail (.eml)",
                data=eml_bytes,
                file_name=f"Overzicht_{naam}_{code}.eml",
                mime="message/rfc822",
                key=f"eml_{code}",
            )
            st.caption(
                "Open het gedownloade .eml-bestand met een dubbelklik: het opent "
                "automatisch als een nieuw, bewerkbaar concept-bericht in Outlook, "
                "met de tabel al opgemaakt en klaar om te verzenden."
            )
else:
    st.info("Upload een Excel-bestand om te starten.")
