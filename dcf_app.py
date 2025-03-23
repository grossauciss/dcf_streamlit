import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import base64
from jinja2 import Template
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import tempfile

st.set_page_config(page_title="Analyse Financiere", layout="centered")

# --- HEADER ---
col1, col2 = st.columns([1, 8])
with col1:
    st.image("https://upload.wikedia.org/wikipedia/commons/thumb/1/10/Streamlit_logo_mark.svg/120px-Streamlit_logo_mark.svg.png", width=50)
with col2:
    st.markdown("<h1 style='margin-bottom:0;'>📊 DCF & Ratios Analyzer</h1>", unsafe_allow_html=True)
    st.caption("Une app simple pour estimer la valeur d'une entreprise par différentes méthodes")

st.markdown("---")

# --- SÉLECTEURS ---
tabs = st.tabs(["🔍 Analyse DCF", "📊 Analyse par Ratios"])
with tabs[0]:
    methode = "Analyse DCF"
with tabs[1]:
    methode = "Analyse par Ratios"
devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]

# --- FORMULAIRE ---
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

    else:  # Analyse par ratios
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

# --- TRAITEMENT ---
if submitted:
    # Gestion de plusieurs entreprises
    if 'entreprises' not in st.session_state:
        st.session_state.entreprises = []

    nouvelle_entreprise = {
        'nom': entreprise,
        'fcf_initial': fcf_initial,
        'croissance': croissance,
        'wacc': wacc,
        'croissance_terminale': croissance_terminale,
        'dette_nette': dette_nette,
        'actions': actions,
        'cours_reel': cours_reel
    }

    st.session_state.entreprises.append(nouvelle_entreprise)
    entreprises = st.session_state.entreprises
    resultats_comparables = []

    st.markdown("### ➕ Ajouter d'autres entreprises")
    st.info("Clique sur 'Lancer l'analyse' à nouveau pour ajouter plusieurs entreprises au comparatif.")

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

        st.success(f"✅ Résultats DCF pour {entreprise}")
        st.metric("Valeur entreprise", f"{valeur_entreprise:,.0f} {symbole}")
        st.metric("Valeur des capitaux propres", f"{valeur_capitaux_propres:,.0f} {symbole}")
        cours_reel = st.number_input("Cours actuel de l'action", value=130.0)
        marge_securite = ((valeur_par_action - cours_reel) / cours_reel) * 100
        st.metric("Valeur par action", f"{valeur_par_action:.2f} {symbole}")
        st.metric("Cours actuel", f"{cours_reel:.2f} {symbole}")
        st.metric("Marge de sécurité", f"{marge_securite:.1f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annees, y=fcf_projete, mode='lines+markers', name='FCF projeté'))
        fig.add_trace(go.Scatter(x=annees, y=fcf_actualise, mode='lines+markers', name='FCF actualisé'))
        fig.update_layout(title="Projection des FCF", xaxis_title="Année", yaxis_title=f"Montant ({symbole})")
        st.plotly_chart(fig)

        # Module de sensibilité DCF
        st.subheader("📉 Analyse de sensibilité")
        wacc_range = [wacc - 0.01, wacc, wacc + 0.01]
        growth_range = [croissance_terminale - 0.01, croissance_terminale, croissance_terminale + 0.01]

        data = []
        for g in growth_range:
            row = []
            for w in wacc_range:
                vt = fcf_final * (1 + g) / (w - g)
                vt_actual = vt / (1 + w) ** 5
                ve = cumul_fcf_actualise + vt_actual
                eq = ve + dette_nette
                vpa = eq / actions
                row.append(vpa)
            data.append(row)

        df_sensi = pd.DataFrame(data, columns=[f"WACC {w*100:.1f}%" for w in wacc_range], index=[f"Croissance {g*100:.1f}%" for g in growth_range])
        st.dataframe(df_sensi.style.format("{:.2f}"))

        fig_sensi = go.Figure()
        for i, row in enumerate(data):
            fig_sensi.add_trace(go.Bar(
                name=df_sensi.index[i],
                x=df_sensi.columns,
                y=row
            ))
        fig_sensi.update_layout(barmode='group', title="Sensibilité de la valeur par action", yaxis_title=f"Valeur par action ({symbole})")
        st.plotly_chart(fig_sensi)

        # Export Excel
        df = pd.DataFrame({"Année": annees, "FCF Projeté": fcf_projete, "FCF Actualisé": fcf_actualise})
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name="Flux DCF", index=False)
            resume = pd.DataFrame({"Élément": ["Valeur entreprise", "Valeur des capitaux propres", "Valeur par action"],
                                   "Valeur": [valeur_entreprise, valeur_capitaux_propres, valeur_par_action]})
            resume.to_excel(writer, sheet_name="Résumé", index=False)
            df_sensi.to_excel(writer, sheet_name="Sensibilité")
        st.download_button(
    label="📄 Télécharger le PDF comparatif",
    data=full_pdf.read(),
    file_name="rapport_comparatif.pdf",
    mime="application/pdf"
), file_name="rapport_comparatif.pdf", mime="application/pdf")

    else:
        valeur_par_action_per = (benefice_net * per) / actions
        valeur_entreprise_ebitda = ebitda * ev_ebitda
        valeur_capitaux_propres = valeur_entreprise_ebitda + dette_nette
        valeur_par_action_ebitda = valeur_capitaux_propres / actions

        st.success(f"✅ Résultats par multiples pour {entreprise}")
        st.metric("Valeur par action (PER)", f"{valeur_par_action_per:.2f} {symbole}")
        st.metric("Valeur par action (EV/EBITDA)", f"{valeur_par_action_ebitda:.2f} {symbole}")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=["PER"], y=[valeur_par_action_per], name="PER"))
        fig.add_trace(go.Bar(x=["EV/EBITDA"], y=[valeur_par_action_ebitda], name="EV/EBITDA"))
        fig.update_layout(title="Comparatif des valorisations", yaxis_title=f"{symbole} par action", barmode='group')
        st.plotly_chart(fig)

        df = pd.DataFrame({"Méthode": ["PER", "EV/EBITDA"], "Valeur par action": [valeur_par_action_per, valeur_par_action_ebitda]})
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Comparatif Multiples")
        st.download_button("📥 Exporter en Excel", output.getvalue(), file_name="Ratios_resultats.xlsx")
