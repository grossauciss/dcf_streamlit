import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import base64
from jinja2 import Template
import pdfkit
import os

st.set_page_config(page_title="Analyse Financiere", layout="centered")

# --- HEADER ---
col1, col2 = st.columns([1, 8])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Streamlit_logo_mark.svg/120px-Streamlit_logo_mark.svg.png", width=50)
with col2:
    st.markdown("<h1 style='margin-bottom:0;'>📊 DCF & Ratios Analyzer</h1>", unsafe_allow_html=True)
    st.caption("Une app simple pour estimer la valeur d'une entreprise par différentes méthodes")

st.markdown("---")

# --- SÉLECTEURS ---
methode = st.radio("Choisir la méthode d'analyse :", ["Analyse DCF", "Analyse par Ratios"])
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
        st.metric("Valeur par action", f"{valeur_par_action:.2f} {symbole}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annees, y=fcf_projete, mode='lines+markers', name='FCF projeté'))
        fig.add_trace(go.Scatter(x=annees, y=fcf_actualise, mode='lines+markers', name='FCF actualisé'))
        fig.update_layout(title="Projection des FCF", xaxis_title="Année", yaxis_title=f"Montant ({symbole})")
        st.plotly_chart(fig)

        df = pd.DataFrame({"Année": annees, "FCF Projeté": fcf_projete, "FCF Actualisé": fcf_actualise})
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name="Flux DCF", index=False)
            resume = pd.DataFrame({"Élément": ["Valeur entreprise", "Valeur des capitaux propres", "Valeur par action"],
                                   "Valeur": [valeur_entreprise, valeur_capitaux_propres, valeur_par_action]})
            resume.to_excel(writer, sheet_name="Résumé", index=False)
        st.download_button("📥 Exporter en Excel", output.getvalue(), file_name="DCF_resultats.xlsx")

        # Génération PDF
        st.markdown("### 📄 Rapport PDF")
        html_template = """
        <html><body style='font-family:Arial;padding:30px;'>
        <h1 style='color:#1d4ed8;'>Rapport DCF - {{ entreprise }}</h1>
        <p>Cette analyse utilise la méthode DCF pour estimer la valeur de l'entreprise {{ entreprise }}. Les FCF sont projetés sur 5 ans et actualisés.</p>
        <h2>Projection des FCF</h2>
        <table border='1' cellpadding='5'><tr><th>Année</th><th>FCF Projeté</th><th>FCF Actualisé</th></tr>
        {% for i in range(annees|length) %}<tr><td>{{ annees[i] }}</td><td>{{ fcf_proj[i]|round|int }}</td><td>{{ fcf_actu[i]|round|int }}</td></tr>{% endfor %}
        </table>
        <h2>Résultats</h2>
        <ul><li>Valeur entreprise : {{ ev|round|int }} {{ symbole }}</li>
        <li>Valeur capitaux propres : {{ equity|round|int }} {{ symbole }}</li>
        <li>Valeur par action : {{ vpa|round(2) }} {{ symbole }}</li></ul></body></html>
        """
        data = {
            "entreprise": entreprise,
            "annees": annees,
            "fcf_proj": fcf_projete,
            "fcf_actu": fcf_actualise,
            "ev": valeur_entreprise,
            "equity": valeur_capitaux_propres,
            "vpa": valeur_par_action,
            "symbole": symbole
        }
        rendered = Template(html_template).render(**data)
        try:
            pdf_bytes = pdfkit.from_string(rendered, False)
            st.download_button("📄 Télécharger le rapport PDF", data=pdf_bytes, file_name=f"rapport_{entreprise}.pdf", mime="application/pdf")
        except:
            st.warning("PDF non disponible sur le cloud. Fonctionne uniquement en local avec wkhtmltopdf installé.")

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
