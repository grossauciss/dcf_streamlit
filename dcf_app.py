
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="Analyse Financière Complète", layout="centered")
st.title("📊 Analyse Financière : DCF, Ratios, Score & Cours")

devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]
ticker_input = st.text_input("🔍 Ticker boursier", "AAPL")

fcf = ebitda = debt = shares = price = net_income = None
valeurs = {}
cours = 0
info = {}

if ticker_input:
    try:
        ticker = yf.Ticker(ticker_input)
        info = ticker.info
        hist_10y = ticker.history(period="10y")
        hist_10y["SMA_200"] = hist_10y["Close"].rolling(window=200).mean()
        fcf = info.get("freeCashflow")
        ebitda = info.get("ebitda")
        debt = info.get("totalDebt")
        shares = info.get("sharesOutstanding")
        price = info.get("currentPrice")
        net_income = info.get("netIncome")
        cours = price
        st.success(f"Données récupérées pour {info.get('longName') or ticker_input}")
    except:
        st.error("Erreur lors de la récupération des données.")

# --- Graphique du cours sur 10 ans + moyenne mobile
if 'hist_10y' in locals() and not hist_10y.empty:
    st.subheader("📈 Cours de l'action sur 10 ans (avec moyenne mobile 200 jours)")
    fig_long = go.Figure()
    fig_long.add_trace(go.Scatter(x=hist_10y.index, y=hist_10y["Close"], name="Cours de clôture"))
    fig_long.add_trace(go.Scatter(x=hist_10y.index, y=hist_10y["SMA_200"], name="Moyenne mobile 200j", line=dict(dash="dash")))
    fig_long.update_layout(title="Cours boursier sur 10 ans", xaxis_title="Date", yaxis_title=f"Cours ({symbole})")
    st.plotly_chart(fig_long, use_container_width=True)

# --- Mini dashboard de ratios
if info:
    st.subheader("📊 Ratios Financiers Clés")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("ROE (%)", round(info.get("returnOnEquity", 0)*100, 2))
        st.metric("Marge nette (%)", round(info.get("netMargins", 0)*100, 2))
    with col2:
        st.metric("Endettement (%)", round(info.get("debtToEquity", 0), 2))
        st.metric("Croissance CA (%)", round(info.get("revenueGrowth", 0)*100, 2))
    with col3:
        st.metric("P/B", round(info.get("priceToBook", 0), 2))
        st.metric("ROA (%)", round(info.get("returnOnAssets", 0)*100, 2))

tab_dcf, tab_ratios = st.tabs(["🔍 Analyse DCF", "📊 Analyse par Ratios"])

# --- Analyse DCF ---
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

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[2025+i for i in range(5)], y=fcf_proj, name="FCF projeté"))
        fig.add_trace(go.Scatter(x=[2025+i for i in range(5)], y=fcf_actu, name="FCF actualisé"))
        fig.update_layout(title="Projection FCF", xaxis_title="Année", yaxis_title=f"Montant ({symbole})")
        st.plotly_chart(fig)

# --- Analyse par Ratios ---
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

        fig = go.Figure()
        fig.add_trace(go.Bar(x=["PER"], y=[valeur_per]))
        fig.add_trace(go.Bar(x=["EV/EBITDA"], y=[valeur_ebitda]))
        fig.update_layout(title="Valorisation par Ratios", yaxis_title=f"{symbole}/action")
        st.plotly_chart(fig)

# --- Score de valorisation ---
if valeurs and cours:
    scores = []
    for methode, val in valeurs.items():
        marge = (val - cours) / cours * 100
        score = min(max((marge / 2) + 50, 0), 100)
        scores.append(score)
    score_final = round(sum(scores) / len(scores), 1)

    st.markdown("## 🧠 Score de Valorisation")
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
