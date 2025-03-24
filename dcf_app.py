
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime

st.set_page_config(page_title="Analyse Financière Complète", layout="centered")
st.title("📊 Analyse Financière : DCF, Ratios, Score & PDF")

devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]
ticker_input = st.text_input("🔍 Ticker boursier", "AAPL")

valeurs = {}
fcf = ebitda = debt = shares = price = net_income = cours = score_final = 0
info = {}

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

tab_dcf, tab_ratios = st.tabs(["🔍 Analyse DCF", "📊 Analyse par Ratios"])

with tab_dcf:
    with st.form("form_dcf"):
        fcf_input = st.number_input("FCF initial", value=fcf or 0.0)
        croissance = st.number_input("Croissance (%)", value=10.0) / 100
        wacc = st.number_input("WACC (%)", value=8.0) / 100
        croissance_term = st.number_input("Croissance terminale (%)", value=2.5) / 100
        dette = st.number_input("Dette nette", value=-(debt or 0.0))
        nb_actions = st.number_input("Nombre d'actions", value=shares or 1.0)
        cours = st.number_input("Cours actuel", value=price or 0.0)
        submit_dcf = st.form_submit_button("Lancer l'analyse DCF")

    if submit_dcf:
        fcf_proj = [fcf_input * (1 + croissance) ** i for i in range(1, 6)]
        fcf_actu = [fcf / (1 + wacc) ** i for i, fcf in enumerate(fcf_proj, 1)]
        valeur_terminale = fcf_proj[-1] * (1 + croissance_term) / (wacc - croissance_term)
        valeur_term_actu = valeur_terminale / (1 + wacc) ** 5
        valeur_ent = sum(fcf_actu) + valeur_term_actu
        capitaux = valeur_ent + dette
        valeur_dcf = capitaux / nb_actions
        valeurs["DCF"] = valeur_dcf
        st.metric("Valeur par action (DCF)", f"{valeur_dcf:.2f} {symbole}")

        st.line_chart(pd.DataFrame(fcf_proj, index=[f"Année {i}" for i in range(1, 6)], columns=["FCF Projeté"]))

with tab_ratios:
    with st.form("form_ratios"):
        benefice = st.number_input("Bénéfice net", value=net_income or 0.0)
        per = st.number_input("PER", value=15.0)
        ebitda_input = st.number_input("EBITDA", value=ebitda or 0.0)
        ev_ebitda = st.number_input("EV/EBITDA", value=12.0)
        nb_actions_ratios = st.number_input("Nombre d'actions (ratios)", value=shares or 1.0)
        dette_ratios = st.number_input("Dette nette (ratios)", value=-(debt or 0.0))
        submit_ratios = st.form_submit_button("Lancer l'analyse Ratios")

    if submit_ratios:
        valeur_per = (benefice * per) / nb_actions_ratios
        valeur_ebitda = ((ebitda_input * ev_ebitda) + dette_ratios) / nb_actions_ratios
        valeurs["PER"] = valeur_per
        valeurs["EV/EBITDA"] = valeur_ebitda
        st.metric("Valeur par action (PER)", f"{valeur_per:.2f} {symbole}")
        st.metric("Valeur par action (EV/EBITDA)", f"{valeur_ebitda:.2f} {symbole}")

if valeurs and cours:
    scores = []
    for methode, val in valeurs.items():
        marge = (val - cours) / cours * 100
        score = min(max((marge / 2) + 50, 0), 100)
        scores.append(score)
    score_final = round(sum(scores) / len(scores), 1)

    st.subheader("🧠 Score de Valorisation")
    st.metric("Score global", f"{score_final} / 100")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_final,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Score de Valorisation"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "red"},
                {'range': [30, 50], 'color': "orange"},
                {'range': [50, 70], 'color': "yellow"},
                {'range': [70, 85], 'color': "lightgreen"},
                {'range': [85, 100], 'color': "green"},
            ],
        }
    ))
    st.plotly_chart(fig)

    st.subheader("📝 Interprétation automatique")
    try:
        roe = info.get("returnOnEquity", 0) * 100
        net_margin = info.get("netMargins", 0) * 100
        debt_ratio = info.get("debtToEquity", 0)
        rev_growth = info.get("revenueGrowth", 0) * 100

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

        if roe > 15:
            commentaire += f" ROE élevé ({roe:.1f}%)."
        if net_margin > 10:
            commentaire += f" Marge nette : {net_margin:.1f}%."
        if debt_ratio > 100:
            commentaire += f" ⚠️ Endettement élevé ({debt_ratio:.0f}%)."
        if rev_growth > 5:
            commentaire += f" 📈 Croissance du CA : {rev_growth:.1f}%."

        st.markdown(commentaire)

        # PDF export
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        c = canvas.Canvas(temp_file.name, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, height - 60, "Analyse de valorisation financière")

        c.setFont("Helvetica", 11)
        c.drawString(50, height - 100, f"Date : {datetime.today().strftime('%d/%m/%Y')}")
        c.drawString(50, height - 120, "Résumé :")
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(60, height - 140, commentaire.replace("**", ""))

        y = height - 180
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Méthodes de valorisation :")
        c.setFont("Helvetica", 11)
        y -= 20
        for k, v in valeurs.items():
            c.drawString(60, y, f"{k} : {v:.2f} {symbole}")
            y -= 18

        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.grey)
        c.drawString(50, 40, "Rapport généré automatiquement - à titre informatif")

        c.save()

        with open(temp_file.name, "rb") as file:
            st.download_button("📥 Télécharger le rapport PDF", file, file_name="analyse_valorisation.pdf", mime="application/pdf")

    except:
        st.warning("⚠️ Résumé automatique indisponible.")
