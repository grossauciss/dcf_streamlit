
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="Analyse Financière Complète", layout="centered")
st.title("📊 Analyse Financière : DCF, Ratios, Score & Commentaire")

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

# Analyse DCF
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

# Analyse par Ratios
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

# Score et commentaire
if valeurs and cours:
    scores = []
    for methode, val in valeurs.items():
        marge = (val - cours) / cours * 100
        score = min(max((marge / 2) + 50, 0), 100)
        scores.append(score)
    score_final = round(sum(scores) / len(scores), 1)

    st.subheader("🧠 Score de Valorisation")
    st.metric("Score global", f"{score_final} / 100")

    if score_final >= 85:
        st.success("🔥 Très sous-valorisée")
    elif score_final >= 70:
        st.success("✅ Sous-valorisée")
    elif score_final >= 50:
        st.info("🟡 Équitable")
    elif score_final >= 30:
        st.warning("🔻 Légèrement surévaluée")
    else:
        st.error("🔴 Surévaluée")

    st.subheader("📝 Interprétation automatique")
    try:
        roe = info.get("returnOnEquity", 0) * 100
        net_margin = info.get("netMargins", 0) * 100
        debt_ratio = info.get("debtToEquity", 0)
        rev_growth = info.get("revenueGrowth", 0) * 100

        commentaire = "L'entreprise semble "
        if score_final >= 85:
            commentaire += "**très sous-valorisée** selon les différentes approches."
        elif score_final >= 70:
            commentaire += "**sous-valorisée** selon la plupart des méthodes."
        elif score_final >= 50:
            commentaire += "**correctement valorisée**, avec un potentiel modéré."
        else:
            commentaire += "**surévaluée** selon l'analyse actuelle."

        commentaire += f" Le score global atteint **{score_final}/100**."

        if roe > 15:
            commentaire += f" La rentabilité est solide (ROE : {roe:.1f}%)."
        if net_margin > 10:
            commentaire += f" La marge nette est élevée ({net_margin:.1f}%)."
        if debt_ratio > 100:
            commentaire += f" ⚠️ Le taux d’endettement est important ({debt_ratio:.0f}%)."
        if rev_growth > 5:
            commentaire += f" 📈 Croissance du CA : {rev_growth:.1f}%."

        st.markdown(commentaire)
    except:
        st.warning("⚠️ Résumé automatique non disponible.")
