
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import tempfile

st.set_page_config(page_title="Analyse Financière", layout="centered")
st.title("📊 Analyse DCF & Ratios")

# --- Devise ---
devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]

# --- Ticker boursier ---
ticker_input = st.text_input("🔍 Ticker boursier (ex: AAPL, SAF.PA, MSFT)")

fcf = ebitda = debt = shares = price = net_income = None
valeur_dcf = valeur_per = valeur_ebitda = None

if ticker_input:
    try:
        ticker = yf.Ticker(ticker_input)
        info = ticker.info
        fcf = info.get("freeCashflow")
        ebitda = info.get("ebitda")
        debt = info.get("totalDebt")
        shares = info.get("sharesOutstanding")
        price = info.get("currentPrice")
        net_income = info.get("netIncome")

        st.success(f"Données récupérées pour {info.get('longName') or ticker_input}")
        st.write(f"💰 Free Cash Flow : {fcf}")
        st.write(f"🏭 EBITDA : {ebitda}")
        st.write(f"📉 Dette totale : {debt}")
        st.write(f"📊 Actions en circulation : {shares}")
        st.write(f"💵 Cours actuel : {price}")
        st.write(f"📈 Bénéfice net : {net_income}")

    except Exception as e:
        st.error(f"Erreur : {e}")

tab_dcf, tab_ratios = st.tabs(["🔍 Analyse DCF", "📊 Analyse par Ratios"])

# --- DCF ---
with tab_dcf:
    with st.form("form_dcf"):
        entreprise = st.text_input("Nom de l'entreprise", ticker_input or "Entreprise X")
        col1, col2, col3 = st.columns(3)
        with col1:
            fcf_initial = st.number_input("FCF de départ", value=fcf or 0.0)
            croissance = st.number_input("Croissance FCF (%)", value=10.0) / 100
        with col2:
            wacc = st.number_input("WACC (%)", value=8.0) / 100
            croissance_terminale = st.number_input("Croissance terminale (%)", value=2.5) / 100
        with col3:
            dette_nette = st.number_input("Dette nette", value=-(debt or 0.0))
            actions = st.number_input("Nombre d'actions", value=shares or 1.0)
        cours_reel = st.number_input("Cours actuel de l'action", value=price or 0.0)
        submitted_dcf = st.form_submit_button("Lancer l'analyse DCF")

    if submitted_dcf:
        annees = [2025 + i for i in range(5)]
        fcf_projete = [fcf_initial * (1 + croissance) ** i for i in range(1, 6)]
        fcf_actualise = [fcf / (1 + wacc) ** i for i, fcf in enumerate(fcf_projete, 1)]
        cumul_fcf_actualise = sum(fcf_actualise)
        fcf_final = fcf_projete[-1]
        valeur_terminale = fcf_final * (1 + croissance_terminale) / (wacc - croissance_terminale)
        valeur_terminale_actualisee = valeur_terminale / (1 + wacc) ** 5
        valeur_entreprise = cumul_fcf_actualise + valeur_terminale_actualisee
        valeur_capitaux_propres = valeur_entreprise + dette_nette
        valeur_dcf = valeur_par_action = valeur_capitaux_propres / actions
        marge_securite = ((valeur_par_action - cours_reel) / cours_reel) * 100

        st.metric("Valeur par action (DCF)", f"{valeur_par_action:.2f} {symbole}")
        st.metric("Marge de sécurité", f"{marge_securite:.1f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annees, y=fcf_projete, mode='lines+markers', name='FCF projeté'))
        fig.add_trace(go.Scatter(x=annees, y=fcf_actualise, mode='lines+markers', name='FCF actualisé'))
        fig.update_layout(title="Projection des FCF", xaxis_title="Année", yaxis_title=f"Montant ({symbole})")
        st.plotly_chart(fig)

# --- Ratios ---
with tab_ratios:
    with st.form("form_ratios"):
        entreprise = st.text_input("Nom de l'entreprise (Ratios)", ticker_input or "Entreprise X")
        col1, col2, col3 = st.columns(3)
        with col1:
            benefice_net = st.number_input("Bénéfice net annuel", value=net_income or 0.0)
            per = st.number_input("PER moyen", value=15.0)
        with col2:
            ebitda_val = st.number_input("EBITDA", value=ebitda or 0.0)
            ev_ebitda = st.number_input("EV/EBITDA moyen", value=12.0)
        with col3:
            dette_nette = st.number_input("Dette nette", value=-(debt or 0.0))
            actions = st.number_input("Nombre d'actions", value=shares or 1.0)
        submitted_ratios = st.form_submit_button("Lancer l'analyse Ratios")

    if submitted_ratios:
        valeur_per = (benefice_net * per) / actions
        valeur_entreprise_ebitda = ebitda_val * ev_ebitda
        valeur_capitaux_propres = valeur_entreprise_ebitda + dette_nette
        valeur_ebitda = valeur_capitaux_propres / actions

        st.metric("Valeur par action (PER)", f"{valeur_per:.2f} {symbole}")
        st.metric("Valeur par action (EV/EBITDA)", f"{valeur_ebitda:.2f} {symbole}")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=["PER"], y=[valeur_per], name="PER"))
        fig.add_trace(go.Bar(x=["EV/EBITDA"], y=[valeur_ebitda], name="EV/EBITDA"))
        fig.update_layout(title="Valorisation par multiples", yaxis_title=f"{symbole} par action")
        st.plotly_chart(fig)

# --- Comparatif si les 3 valeurs existent ---
if all(x is not None for x in [valeur_dcf, valeur_per, valeur_ebitda]):
    st.markdown("### 🧠 Comparaison des valorisations par méthode")
    df_compare = pd.DataFrame({
        "Méthode": ["DCF", "PER", "EV/EBITDA"],
        "Valeur par action": [valeur_dcf, valeur_per, valeur_ebitda]
    })
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(x=df_compare["Méthode"], y=df_compare["Valeur par action"], marker_color='indigo'))
    fig_compare.update_layout(title="Comparatif DCF vs Ratios", yaxis_title=f"{symbole} par action")
    st.plotly_chart(fig_compare)
