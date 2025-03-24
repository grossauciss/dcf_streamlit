
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import tempfile
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="Analyse Financière PDF", layout="centered")
st.title("📊 Analyse Financière avec Export PDF")

devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]
ticker_input = st.text_input("🔍 Ticker boursier", "AAPL")

valeurs = {}
fcf = ebitda = debt = shares = price = net_income = cours = score_final = 0
info = {}

# Récupération des données
if ticker_input:
    try:
        ticker = yf.Ticker(ticker_input)
        info = ticker.info
        fcf = info.get("freeCashflow", 0)
        ebitda = info.get("ebitda", 0)
        debt = info.get("totalDebt", 0)
        shares = info.get("sharesOutstanding", 1)
        price = info.get("currentPrice", 0)
        net_income = info.get("netIncome", 0)
        cours = price
        st.success(f"Données récupérées pour {info.get('longName') or ticker_input}")
    except:
        st.error("Erreur lors de la récupération des données.")

# Formulaire de calcul
with st.form("formulaire"):
    fcf_input = st.number_input("FCF initial", value=fcf or 0.0)
    croissance = st.number_input("Croissance (%)", value=10.0) / 100
    wacc = st.number_input("WACC (%)", value=8.0) / 100
    croissance_term = st.number_input("Croissance terminale (%)", value=2.5) / 100
    dette = st.number_input("Dette nette", value=-(debt or 0.0))
    nb_actions = st.number_input("Nombre d'actions", value=shares or 1.0)
    benefice = st.number_input("Bénéfice net", value=net_income or 0.0)
    per = st.number_input("PER", value=15.0)
    ebitda_input = st.number_input("EBITDA", value=ebitda or 0.0)
    ev_ebitda = st.number_input("EV/EBITDA", value=12.0)
    submit = st.form_submit_button("Calculer")

# Résultats et score
if submit:
    valeur_per = (benefice * per) / nb_actions
    valeur_ebitda = ((ebitda_input * ev_ebitda) + dette) / nb_actions

    fcf_proj = [fcf_input * (1 + croissance) ** i for i in range(1, 6)]
    fcf_actu = [fcf / (1 + wacc) ** i for i, fcf in enumerate(fcf_proj, 1)]
    valeur_terminale = fcf_proj[-1] * (1 + croissance_term) / (wacc - croissance_term)
    valeur_term_actu = valeur_terminale / (1 + wacc) ** 5
    valeur_ent = sum(fcf_actu) + valeur_term_actu
    capitaux = valeur_ent + dette
    valeur_dcf = capitaux / nb_actions

    valeurs = {
        "DCF": valeur_dcf,
        "PER": valeur_per,
        "EV/EBITDA": valeur_ebitda
    }

    # Score
    scores = []
    for methode, val in valeurs.items():
        marge = (val - cours) / cours * 100
        score = min(max((marge / 2) + 50, 0), 100)
        scores.append(score)
    score_final = round(sum(scores) / len(scores), 1)

    # Résumé
    st.subheader("🧠 Résumé exécutif")
    commentaire = "L'entreprise semble "
    if score_final >= 85:
        commentaire += "**très sous-valorisée**."
    elif score_final >= 70:
        commentaire += "**sous-valorisée**."
    elif score_final >= 50:
        commentaire += "**correctement valorisée**."
    else:
        commentaire += "**surévaluée**."
    commentaire += f" Score global : **{score_final}/100**."
    st.markdown(commentaire)

    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Analyse de valorisation financière", ln=1, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.ln(5)
    pdf.multi_cell(0, 10, commentaire)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Synthèse des méthodes :", ln=1)
    pdf.set_font("Arial", "", 12)
    for k, v in valeurs.items():
        pdf.cell(0, 10, f"{k} : {v:.2f} {symbole}", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, f"Généré le {datetime.today().strftime('%d/%m/%Y')}", ln=1)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)

    with open(temp_file.name, "rb") as file:
        btn = st.download_button(
            label="📥 Télécharger le rapport PDF",
            data=file,
            file_name="analyse_valorisation.pdf",
            mime="application/pdf"
        )
