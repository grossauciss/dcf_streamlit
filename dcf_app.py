import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import base64
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import tempfile

st.set_page_config(page_title="Analyse Financiere", layout="centered")

col1, col2 = st.columns([1, 8])
with col1:
    st.image("https://upload.wikedia.org/wikipedia/commons/thumb/1/10/Streamlit_logo_mark.svg/120px-Streamlit_logo_mark.svg.png", width=50)
with col2:
    st.markdown("<h1 style='margin-bottom:0;'>📊 DCF & Ratios Analyzer</h1>", unsafe_allow_html=True)
    st.caption("Une app simple pour estimer la valeur d'une entreprise par différentes méthodes")

st.markdown("---")

tabs = st.tabs(["🔍 Analyse DCF", "📊 Analyse par Ratios"])
with tabs[0]:
    methode = "Analyse DCF"
with tabs[1]:
    methode = "Analyse par Ratios"

devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]

with st.form("formulaire"):
    entreprise = st.text_input("Nom de l'entreprise", "Entreprise X")

    if methode == "Analyse DCF":
        col1, col2, col3 = st.columns(3)
        with col1:
            fcf_initial = st.number_input(f"FCF de départ ({symbole})", value=2900000000.0)
            croissance = st.number_input("Croissance FCF (%)", value=10.0) / 100
        with col2:
            wacc = st.number_input("WACC (%)", value=8.0) / 100
            croissance_terminale = st.number_input("Croissance terminale (%)", value=2.5) / 100
        with col3:
            dette_nette = st.number_input(f"Dette nette ({symbole})", value=-3000000000.0)
            actions = st.number_input("Nombre d'actions", value=428000000.0)
        cours_reel = st.number_input("Cours actuel de l'action", value=130.0)

    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            benefice_net = st.number_input(f"Bénéfice net annuel ({symbole})", value=2500000000.0)
            per = st.number_input("PER moyen", value=15.0)
        with col2:
            ebitda = st.number_input(f"EBITDA ({symbole})", value=5000000000.0)
            ev_ebitda = st.number_input("EV/EBITDA moyen", value=12.0)
        with col3:
            dette_nette = st.number_input(f"Dette nette ({symbole})", value=-2000000000.0)
            actions = st.number_input("Nombre d'actions", value=428000000.0)

    submitted = st.form_submit_button("Lancer l'analyse")

if submitted:
    if 'entreprises' not in st.session_state:
        st.session_state.entreprises = []

    resultats_comparables = []

    if methode == "Analyse DCF":
        annees = [2025 + i for i in range(5)]
        fcf_projete = [fcf_initial * (1 + croissance) ** i for i in range(1, 6)]
        fcf_actualise = [fcf / (1 + wacc) ** i for i, fcf in enumerate(fcf_projete, 1)]
        cumul_fcf_actualise = sum(fcf_actualise)

        fcf_final = fcf_projete[-1]
        valeur_terminale = fcf_final * (1 + croissance_terminale) / (wacc - croissance_terminale)
        valeur_terminale_actualisee = valeur_terminale / (1 + wacc) ** 5

        valeur_entreprise = cumul_fcf_actualise + valeur_terminale_actualisee
        valeur_capitaux_propres = valeur_entreprise + dette_nette
        valeur_par_action = valeur_capitaux_propres / actions

        marge_securite = ((valeur_par_action - cours_reel) / cours_reel) * 100

        nouvelle_entreprise = {
            'nom': entreprise,
            'valeur_par_action': valeur_par_action,
            'cours_reel': cours_reel
        }
        st.session_state.entreprises.append(nouvelle_entreprise)

        st.success(f"✅ Résultats DCF pour {entreprise}")
        st.metric("Valeur entreprise", f"{valeur_entreprise:,.0f} {symbole}")
        st.metric("Valeur des capitaux propres", f"{valeur_capitaux_propres:,.0f} {symbole}")
        st.metric("Valeur par action", f"{valeur_par_action:.2f} {symbole}")
        st.metric("Cours actuel", f"{cours_reel:.2f} {symbole}")
        st.metric("Marge de sécurité", f"{marge_securite:.1f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annees, y=fcf_projete, mode='lines+markers', name='FCF projeté'))
        fig.add_trace(go.Scatter(x=annees, y=fcf_actualise, mode='lines+markers', name='FCF actualisé'))
        fig.update_layout(title="Projection des FCF", xaxis_title="Année", yaxis_title=f"Montant ({symbole})")
        st.plotly_chart(fig)

    # --- EXPORT COMPARATIF MULTI-ENTREPRISES ---
    if st.session_state.entreprises:
        st.markdown("### 📋 Comparaison entre entreprises")
        df_comp = pd.DataFrame([
            {
                "Entreprise": e["nom"],
                "Valeur par action": e["valeur_par_action"],
                "Cours actuel": e["cours_reel"],
                "Marge de sécurité (%)": ((e["valeur_par_action"] - e["cours_reel"]) / e["cours_reel"]) * 100
            }
            for e in st.session_state.entreprises
        ])

        st.dataframe(df_comp.style.format({
            "Valeur par action": "{:.2f}",
            "Cours actuel": "{:.2f}",
            "Marge de sécurité (%)": "{:.1f}"
        }))

        output_comp = BytesIO()
        with pd.ExcelWriter(output_comp, engine='xlsxwriter') as writer:
            df_comp.to_excel(writer, index=False, sheet_name="Comparaison")
        st.download_button("📥 Télécharger le comparatif Excel", output_comp.getvalue(), file_name="comparaison_entreprises.xlsx")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as full_pdf:
            c = canvas.Canvas(full_pdf.name, pagesize=A4)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(2 * cm, 27 * cm, "Comparaison multi-entreprises")
            y = 25.5 * cm
            c.setFont("Helvetica", 12)
            for row in df_comp.itertuples(index=False):
                try:
                    c.drawString(2 * cm, y, f"{row.Entreprise}: VPA {row._1:.2f} {symbole}, Cours {row._2:.2f}, Marge {row._3:.1f}%")
                except Exception:
                    c.drawString(2 * cm, y, "[Erreur données]")
                y -= 0.7 * cm
                if y < 3 * cm:
                    c.showPage()
                    y = 27 * cm
            c.save()
            full_pdf.seek(0)
            st.download_button(
                label="📄 Télécharger le PDF comparatif",
                data=full_pdf.read(),
                file_name="rapport_comparatif.pdf",
                mime="application/pdf"
            )
