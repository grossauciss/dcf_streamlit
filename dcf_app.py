
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import tempfile
import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

st.set_page_config(page_title="Analyse Financière", layout="wide")
st.title("📊 Analyse Financière avec DCF & Ratios")

def generer_graphique_cours_png(ticker):
    df = yf.download(ticker, period="10y")
    df["MA200"] = df["Close"].rolling(window=200).mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df.index, df["Close"], label="Cours", linewidth=1.5)
    ax.plot(df.index, df["MA200"], label="MA 200j", linestyle="--", color="orange")
    ax.set_title("Cours sur 10 ans avec Moyenne Mobile")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cours")
    ax.legend()
    fig.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return buffer

devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]
ticker = st.text_input("🔍 Ticker boursier", "AAPL")

if ticker:
    try:
        info = yf.Ticker(ticker).info
        st.success(f"Données récupérées pour {info.get('longName', ticker)}")
        cours = info.get("currentPrice", 0)
        fcf = info.get("freeCashflow", 0)
        ebitda = info.get("ebitda", 0)
        debt = info.get("totalDebt", 0)
        shares = info.get("sharesOutstanding", 1)
        net_income = info.get("netIncome", 0)
    except:
        st.error("Erreur de récupération des données.")
        st.stop()

    onglet_dcf, onglet_ratios = st.tabs(["📘 Analyse DCF", "📗 Analyse par Ratios"])

    with onglet_dcf:
        with st.form("form_dcf"):
            fcf_input = st.number_input("FCF initial", value=fcf or 0.0)
            croissance = st.number_input("Croissance (%)", value=10.0) / 100
            wacc = st.number_input("WACC (%)", value=8.0) / 100
            croissance_term = st.number_input("Croissance terminale (%)", value=2.5) / 100
            dette = st.number_input("Dette nette", value=-(debt or 0.0))
            nb_actions = st.number_input("Nombre d'actions", value=shares or 1.0)
            submit_dcf = st.form_submit_button("Lancer DCF")

        if submit_dcf:
            fcf_proj = [fcf_input * (1 + croissance) ** i for i in range(1, 6)]
            fcf_actu = [fcf / (1 + wacc) ** i for i, fcf in enumerate(fcf_proj, 1)]
            valeur_terminale = fcf_proj[-1] * (1 + croissance_term) / (wacc - croissance_term)
            valeur_term_actu = valeur_terminale / (1 + wacc) ** 5
            valeur_ent = sum(fcf_actu) + valeur_term_actu
            capitaux = valeur_ent + dette
            valeur_dcf = capitaux / nb_actions

            st.metric("Valeur par action (DCF)", f"{valeur_dcf:.2f} {symbole}")
            df_fcf = pd.DataFrame(fcf_proj, index=[f"Année {i}" for i in range(1, 6)], columns=["FCF Projeté"])
            st.line_chart(df_fcf)

    with onglet_ratios:
        with st.form("form_ratios"):
            benefice = st.number_input("Bénéfice net", value=net_income or 0.0)
            per = st.number_input("PER", value=15.0)
            ebitda_input = st.number_input("EBITDA", value=ebitda or 0.0)
            ev_ebitda = st.number_input("EV/EBITDA", value=12.0)
            nb_actions_ratios = st.number_input("Nombre d'actions (ratios)", value=shares or 1.0)
            dette_ratios = st.number_input("Dette nette (ratios)", value=-(debt or 0.0))
            submit_ratios = st.form_submit_button("Lancer analyse Ratios")

        if submit_ratios:
            valeur_per = (benefice * per) / nb_actions_ratios
            valeur_ebitda = ((ebitda_input * ev_ebitda) + dette_ratios) / nb_actions_ratios
            valeurs = {"PER": valeur_per, "EV/EBITDA": valeur_ebitda}

            st.metric("Valeur par action (PER)", f"{valeur_per:.2f} {symbole}")
            st.metric("Valeur par action (EV/EBITDA)", f"{valeur_ebitda:.2f} {symbole}")

            score_final = round(sum([(val - cours) / cours * 100 / 2 + 50 for val in valeurs.values()]), 1)
            commentaire = "L'entreprise semble "
            if score_final >= 85:
                commentaire += "très sous-valorisée."
            elif score_final >= 70:
                commentaire += "sous-valorisée."
            elif score_final >= 50:
                commentaire += "correctement valorisée."
            else:
                commentaire += "surévaluée."
            commentaire += f" Score global : {score_final}/100."

            st.subheader("🧠 Score")
            fig_score = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score_final,
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
            st.plotly_chart(fig_score)

            st.subheader("📉 Cours sur 10 ans + MA 200")
            df = yf.download(ticker, period="10y")
            df["MA200"] = df["Close"].rolling(window=200).mean()
            fig_cours = go.Figure()
            fig_cours.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Cours"))
            fig_cours.add_trace(go.Scatter(x=df.index, y=df["MA200"], mode="lines", name="MA 200j", line=dict(color="orange")))
            fig_cours.update_layout(title="📈 Historique du cours", xaxis_title="Date", yaxis_title="Cours", template="plotly_dark")
            st.plotly_chart(fig_cours)

            st.subheader("📝 Résumé automatique")
            st.markdown(commentaire)

            graphique_bytes = generer_graphique_cours_png(ticker)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            c = canvas.Canvas(temp_file.name, pagesize=A4)
            width, height = A4
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2, height - 60, "Analyse financière")
            c.setFont("Helvetica", 11)
            c.drawString(50, height - 90, f"Société : {info.get('longName', ticker)}")
            c.drawString(50, height - 110, f"Cours actuel : {cours:.2f} {symbole}")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 140, commentaire)
            if graphique_bytes:
                c.drawImage(ImageReader(graphique_bytes), 50, height - 420, width=500, height=250)
            c.setFont("Helvetica-Oblique", 8)
            c.setFillColor(colors.grey)
            c.drawString(50, 40, f"Généré le {datetime.now().strftime('%d/%m/%Y')}")
            c.save()
            with open(temp_file.name, "rb") as file:
                st.download_button("📥 Télécharger le rapport PDF", file, file_name="analyse_valorisation.pdf", mime="application/pdf")
