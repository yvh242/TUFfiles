import re
from io import BytesIO

import requests
import streamlit as st
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="Verzendingsoverzicht per Opdrachtgever", layout="wide")

# ---------------------------------------------------------------------------
# HARDCODED: koppeling Opdrachtgever-code -> (e-mailadres(sen), klantnaam)
# Pas/vul deze lijst hier verder aan.
# LET OP: 'Opdrachtgever' is een numeriek veld in het Excel-bestand.
# Zet de codes hieronder toch als STRING (bv. "1004438", niet 1004438);
# de code zet de kolom uit Excel automatisch om naar hetzelfde stringformaat.
# Meerdere e-mailadressen mogen gescheiden worden met ';' of ','.
# ---------------------------------------------------------------------------
OPDRACHTGEVER_INFO = {
    "1004438": {"email": "info@cargolinerbelgium.com", "naam": "CARGOLINER BELGIUM BVBA"},
    "1001764": {"email": "lindseyvangestel@ecuworldwide.com;customerserviceroadantwerp@ecuworldwide.com","naam": "ECU"},
    "1001251": {"email": "transport@denycargo.be", "naam": "DENY CARGO"},
}

# Basiskolommen die altijd in het overzicht moeten staan en verplicht
# aanwezig moeten zijn in het geuploade bestand.
BASIS_KOLOMMEN = [
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

SHAREPOINT_MAIL_LINK = (
    "https://transuniversegroup.sharepoint.com/:x:/s/test/"
    "IQAx-1WjSi8STprH4EdAnxkqAZIcMStzyLAi3jSMtQyQeac?e=aJYYVf"
)


def haal_sharepoint_excel_op(url: str) -> BytesIO:
    """Probeert een Excel-bestand rechtstreeks van een SharePoint-deel-link
    te downloaden. Werkt enkel als de link 'iedereen met de link'-toegang
    heeft; bij een link die login vereist, komt er een HTML-loginpagina
    terug in plaats van het bestand, en gooien we een duidelijke fout."""
    download_url = url + ("&download=1" if "?" in url else "?download=1")
    resp = requests.get(download_url, timeout=15)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "").lower()
    if "html" in content_type:
        raise ValueError(
            "SharePoint gaf een inlogpagina terug in plaats van het bestand. "
            "Automatisch ophalen werkt enkel als de link is ingesteld op "
            "'Iedereen met de link'. Gebruik anders de handmatige upload hieronder."
        )
    return BytesIO(resp.content)


def raad_kolom(kolommen, kandidaten):
    """Zoekt de eerste kolomnaam die (case-insensitief) overeenkomt met een
    van de kandidaat-namen, voor het vooraf invullen van de kolom-mapping."""
    kolommen_lower = {k.lower(): k for k in kolommen}
    for kandidaat in kandidaten:
        if kandidaat.lower() in kolommen_lower:
            return kolommen_lower[kandidaat.lower()]
    return kolommen[0] if len(kolommen) else None


def normaliseer_opdrachtgever(x):
    """Zet Opdrachtgever om naar een schone string, ook als het een
    numerieke waarde is (voorkomt bv. '123.0' i.p.v. '123')."""
    if pd.isna(x):
        return x
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x).strip()


st.title("📦 Verzendingsoverzicht per Opdrachtgever")

with st.expander("🔄 Mailadressen vernieuwen (enkel voor deze sessie)"):
    st.caption(
        "Haalt Code / Klantnaam / E-mail op uit een Excel-bestand en past dit "
        "tijdelijk toe, bovenop de hardcoded lijst in de code (die blijft ongewijzigd). "
        "Na een herstart van de app moet dit opnieuw ingeladen worden."
    )

    if "opdrachtgever_overrides" not in st.session_state:
        st.session_state["opdrachtgever_overrides"] = {}

    df_mail = None
    kol1, kol2 = st.columns(2)
    with kol1:
        if st.button("📡 Automatisch ophalen vanaf SharePoint"):
            try:
                bestand = haal_sharepoint_excel_op(SHAREPOINT_MAIL_LINK)
                df_mail = pd.read_excel(bestand)
                st.success(f"{len(df_mail)} rijen opgehaald van SharePoint.")
            except Exception as e:
                st.error(f"Automatisch ophalen is mislukt: {e}")
    with kol2:
        mail_upload = st.file_uploader(
            "...of upload het bestand hier manueel", type=["xlsx", "xls"], key="mail_upload"
        )
        if mail_upload is not None:
            try:
                df_mail = pd.read_excel(mail_upload)
                st.success(f"{len(df_mail)} rijen ingelezen uit geüpload bestand.")
            except Exception as e:
                st.error(f"Kon het bestand niet inlezen: {e}")

    if df_mail is not None:
        st.dataframe(df_mail.head(20), use_container_width=True, hide_index=True)

        kolommen = list(df_mail.columns)
        c1, c2, c3 = st.columns(3)
        with c1:
            kol_code = st.selectbox(
                "Kolom = Code", kolommen,
                index=kolommen.index(raad_kolom(kolommen, ["Code", "Opdrachtgever", "Klantnummer"])),
            )
        with c2:
            kol_naam = st.selectbox(
                "Kolom = Klantnaam", kolommen,
                index=kolommen.index(raad_kolom(kolommen, ["Klantnaam", "Naam"])),
            )
        with c3:
            kol_email = st.selectbox(
                "Kolom = E-mail", kolommen,
                index=kolommen.index(raad_kolom(kolommen, ["Email", "E-mail", "Mailadres", "Mail"])),
            )

        if st.button("✅ Toepassen op deze sessie"):
            nieuwe_overrides = {}
            for _, rij in df_mail.iterrows():
                code = normaliseer_opdrachtgever(rij[kol_code])
                if not code or pd.isna(rij[kol_code]):
                    continue
                nieuwe_overrides[code] = {
                    "naam": str(rij[kol_naam]).strip(),
                    "email": str(rij[kol_email]).strip(),
                }
            st.session_state["opdrachtgever_overrides"] = nieuwe_overrides
            st.success(f"{len(nieuwe_overrides)} opdrachtgevers toegepast voor deze sessie.")
            st.rerun()

EFFECTIEVE_OPDRACHTGEVER_INFO = {
    **OPDRACHTGEVER_INFO,
    **st.session_state.get("opdrachtgever_overrides", {}),
}

# ---------------------------------------------------------------------------
# Tabel met opdrachtgevers: hier kan je per opdrachtgever aan-
# of uitvinken of er een overzicht/mail voor gemaakt moet worden.
# ---------------------------------------------------------------------------
st.subheader("Opdrachtgevers")

df_opdrachtgevers = pd.DataFrame(
    [
        {
            "Code": code,
            "Klantnaam": info["naam"],
            "E-mail": info["email"],
            "Overzicht maken": True,
        }
        for code, info in EFFECTIEVE_OPDRACHTGEVER_INFO.items()
    ]
)

opdrachtgevers_selectie = st.data_editor(
    df_opdrachtgevers,
    column_config={
        "Overzicht maken": st.column_config.CheckboxColumn(
            "Overzicht maken", help="Vink af om deze opdrachtgever over te slaan"
        ),
    },
    disabled=["Code", "Klantnaam", "E-mail"],
    hide_index=True,
    use_container_width=True,
    key="opdrachtgevers_editor",
)

uploaded_file = st.file_uploader("Upload het Excel-bestand", type=["xlsx", "xls"])


def normaliseer_emails(email_veld: str) -> str:
    """Zet een e-mailveld met meerdere adressen (gescheiden door ';' of ',')
    om naar een correct geformatteerde, komma-gescheiden lijst voor de
    'To'-header van de mail."""
    if not email_veld:
        return ""
    onderdelen = re.split(r"[;,]", str(email_veld))
    onderdelen = [e.strip() for e in onderdelen if e.strip()]
    return ", ".join(onderdelen)


def bereken_afzender(row) -> str:
    """Bepaalt de weergave van de 'Afzender'-kolom op basis van 'Type':
    - Type = 'Laden'    -> '-> Afzender'
    - Type = 'levering' -> '<- Afzender'
    - andere waarden    -> leeg
    (niet hoofdlettergevoelig, spaties worden genegeerd)
    """
    type_waarde = str(row.get("Type", "")).strip().lower()
    afzender = row.get("Afzender", "")
    afzender = "" if pd.isna(afzender) else str(afzender).strip()

    if type_waarde == "laden":
        return f"-> {afzender}"
    elif type_waarde == "levering":
        return f"<- {afzender}"
    else:
        return ""


def bouw_overzicht(subset: pd.DataFrame) -> pd.DataFrame:
    """Bouwt het overzicht op met de basiskolommen, aangevuld met de
    optionele kolommen 'Klantnaam' (-> 'Naam'), 'LaadLosRef' en
    'Afzender' (berekend), telkens enkel als ze in het bestand aanwezig zijn."""
    overzicht = pd.DataFrame(index=subset.index)

    overzicht["Verzending-ID"] = subset["Verzending-ID"]
    overzicht["Type"] = subset["Type"]
    overzicht["PC"] = subset["PC"]
    overzicht["Plaatsnaam"] = subset["Plaatsnaam"]

    if "Klantnaam" in subset.columns:
        overzicht["Naam"] = subset["Klantnaam"]

    overzicht["Kg"] = subset["Kg"]
    overzicht["LM"] = subset["LM"]
    overzicht["Aantal"] = subset["Aantal"]
    overzicht["Goederen"] = subset["Goederen"]
    overzicht["ETA"] = subset["ETA"]

    if "LaadLosRef" in subset.columns:
        overzicht["LaadLosRef"] = subset["LaadLosRef"]

    if "Afzender" in subset.columns:
        overzicht["Afzender"] = subset.apply(bereken_afzender, axis=1)

    overzicht = overzicht.sort_values(by="Type", kind="stable").reset_index(drop=True)

    return overzicht


def bouw_html_tabel(overzicht: pd.DataFrame) -> str:
    """Bouwt een mooi opgemaakte, uitgelijnde HTML-tabel voor in de mail."""
    kolom_stijl = (
        "border:1px solid #cccccc; padding:6px 10px; "
        "font-family:Calibri,Arial,sans-serif; font-size:11pt;"
    )
    header_stijl = kolom_stijl + " background-color:#1F4E78; color:#ffffff; text-align:left;"

    html = ['<table style="border-collapse:collapse; width:100%;">', "<tr>"]
    for kol in overzicht.columns:
        html.append(f'<th style="{header_stijl}">{kol}</th>')
    html.append("</tr>")

    for i, (_, row) in enumerate(overzicht.iterrows()):
        rij_kleur = "#ffffff" if i % 2 == 0 else "#F2F2F2"
        html.append("<tr>")
        for kol in overzicht.columns:
            waarde = row[kol]
            waarde = "" if pd.isna(waarde) else waarde
            html.append(f'<td style="{kolom_stijl} background-color:{rij_kleur};">{waarde}</td>')
        html.append("</tr>")

    html.append("</table>")
    return "".join(html)


def bouw_eml(to_email: str, subject: str, html_body: str) -> bytes:
    """Bouwt een .eml-bestand dat Outlook als bewerkbare, klaarstaande
    mail opent (X-Unsent: 1 zorgt dat het als concept opent i.p.v.
    als gelezen bericht). 'to_email' mag meerdere, komma-gescheiden
    adressen bevatten."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to_email
    msg["X-Unsent"] = "1"

    plain_fallback = (
        "Deze mail bevat een overzicht in tabelvorm. "
        "Open dit bestand in Outlook om de opgemaakte versie te zien."
    )
    msg.attach(MIMEText(plain_fallback, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    return msg.as_bytes()


if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Kon het bestand niet inlezen: {e}")
        st.stop()

    # Check of alle verplichte basiskolommen aanwezig zijn
    verplichte_kolommen = set(BASIS_KOLOMMEN + ["Opdrachtgever"])
    ontbrekend = verplichte_kolommen - set(df.columns)
    if ontbrekend:
        st.error(f"Volgende kolommen ontbreken in het bestand: {', '.join(sorted(ontbrekend))}")
        st.stop()

    st.success(f"Bestand ingelezen: {len(df)} rijen gevonden.")

    # Info over welke optionele kolommen gevonden werden
    optionele_kolommen_gevonden = [
        k for k in ["Klantnaam", "Afzender", "LaadLosRef"] if k in df.columns
    ]
    if optionele_kolommen_gevonden:
        st.caption(f"Extra kolommen gevonden en verwerkt: {', '.join(optionele_kolommen_gevonden)}")

    df["Opdrachtgever"] = df["Opdrachtgever"].apply(normaliseer_opdrachtgever)

    for _, opdrachtgever_rij in opdrachtgevers_selectie.iterrows():
        if not opdrachtgever_rij["Overzicht maken"]:
            continue

        code = opdrachtgever_rij["Code"]
        naam = opdrachtgever_rij["Klantnaam"]
        email = normaliseer_emails(opdrachtgever_rij["E-mail"])

        subset = df[df["Opdrachtgever"] == code]
        if subset.empty:
            continue

        st.markdown("---")
        st.subheader(f"📋 {naam}  (code {code})  ·  {email}")

        overzicht = bouw_overzicht(subset)
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
