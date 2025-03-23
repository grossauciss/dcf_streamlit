import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import pdfkit
from jinja2 import Template
import base64

st.set_page_config(page_title="Analyse DCF / Ratios", layout="centered")
st.title("Analyse financière : DCF ou multiples")

# Sidebar – choix de méthode
methode = st.sidebar.radio("Méthode de valorisation", ["Analyse DCF", "Analyse par ratios (multiples)"])

with st.form("formulaire_choisi"):
    st.subheader(f"{methode}")
    entreprise = st.text_input("Nom de l'entreprise", "Entreprise X")

    if methode == "Analyse DCF":
        fcf_initial = st.number_input("FCF de départ (€)", value=2900000000, step=1000000)
        croissance = st.number_input("Croissance FCF (%)", value=10.0, step=0.1) / 100
        wacc = st.number_input("WACC (%)", value=8.0, step=0.1) / 100
        croissance_terminale = st.number_input("Croissance terminale (%)", value=2.5, step=0.1) / 100
        dette_nette = st.number_input("Dette nette (€)", value=-3000000000, step=1000000)
        actions = st.number_input("Nombre d'actions", value=428000000, step=1000000)

    elif methode == "Analyse par ratios (multiples)":
        benefice_net = st.number_input("Bénéfice net annuel (€)", value=2500000000, step=1000000)
        ebitda = st.number_input("EBITDA (€)", value=5000000000, step=1000000)
        chiffre_affaires = st.number_input("Chiffre d'affaires (€)", value=30000000000, step=1000000)
        dette_nette = st.number_input("Dette nette (€)", value=-2000000000, step=1000000)
        actions = st.number_input("Nombre d'actions", value=428000000, step=1000000)
        per = st.number_input("PER sectoriel", value=15.0)
        ev_ebitda = st.number_input("EV/EBITDA moyen du secteur", value=12.0)

    submit = st.form_submit_button("Lancer l'analyse")

# Traitement après soumission
if submit:
    if methode == "Analyse DCF":
        annees = [2025 + i for i in range(5)]
        fcf_projete = [fcf_initial * (1 + croissance) ** i for i in range(1, 6)]
        fcf_actualise = [fcf / (1 + wacc) ** i for i, fcf in enumerate(fcf_projete, 1)]
        cumul_fcf_actualise = sum(fcf_actualise)

        fcf_final = fcf_projete[-1]
        valeur_terminale_brute = fcf_final * (1 + croissance_terminale) / (wacc - croissance_terminale)
        valeur_terminale_actualisee = valeur_terminale_brute / (1 + wacc) ** 5
        valeur_entreprise = cumul_fcf_actualise + valeur_terminale_actualisee
        valeur_capitaux_propres = valeur_entreprise + dette_nette
        valeur_par_action = valeur_capitaux_propres / actions

        # Résultats DCF
        st.subheader(f"Résultats DCF pour {entreprise}")
        st.metric("Valeur entreprise (EV)", f"{valeur_entreprise:,.0f} €")
        st.metric("Valeur des capitaux propres", f"{valeur_capitaux_propres:,.0f} €")
        st.metric("Valeur par action estimée", f"{valeur_par_action:.2f} €")

        # Graphique FCF
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annees, y=fcf_projete, mode='lines+markers', name='FCF projeté'))
        fig.add_trace(go.Scatter(x=annees, y=fcf_actualise, mode='lines+markers', name='FCF actualisé'))
        fig.update_layout(title="Projection des FCF", xaxis_title="Année", yaxis_title="Montant (€)")
        st.plotly_chart(fig)

        df = pd.DataFrame({
            "Année": annees,
            "FCF Projeté (€)": fcf_projete,
            "FCF Actualisé (€)": fcf_actualise
        })
        st.dataframe(df.style.format("{:,.0f}"))

        # Rapport PDF stylé avec logo
        if st.button("Générer un rapport PDF stylé"):
            with open("logo.png", "rb") as img_file:
                logo_base64 = base64.b64encode(img_file.read()).decode()

            template_html = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; padding: 30px; color: #2c3e50; }
                    header { display: flex; align-items: center; }
                    header img { width: 100px; margin-right: 20px; }
                    h1 { font-size: 28px; }
                    h2 { margin-top: 40px; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
                    th { background-color: #3498db; color: white; }
                    .summary { background-color: #ecf0f1; padding: 10px; border-radius: 8px; }
                </style>
            </head>
            <body>
                <header>
                    <img src="data:image/png;base64,{{ logo }}">
                    <div>
                        <h1>Rapport DCF - {{ entreprise }}</h1>
                        <p><strong>Résumé exécutif</strong></p>
                    </div>
                </header>

                <div class="summary">
                    <p>Ce rapport présente une analyse de valorisation DCF basée sur les flux de trésorerie futurs de l'entreprise {{ entreprise }}.</p>
                </div>

                <h2>Tableau des flux de trésorerie</h2>
                <table>
                    <tr><th>Année</th><th>FCF Projeté (€)</th><th>FCF Actualisé (€)</th></tr>
                    {% for i in range(5) %}
                    <tr>
                        <td>{{ annees[i] }}</td>
                        <td>{{ fcf_proj[i]:,.0f }}</td>
                        <td>{{ fcf_actu[i]:,.0f }}</td>
                    </tr>
                    {% endfor %}
                </table>

                <h2>Résumé des résultats</h2>
                <table>
                    <tr><th>Élément</th><th>Valeur</th></tr>
                    <tr><td>Valeur entreprise (EV)</td><td>{{ ev:,.0f }} €</td></tr>
                    <tr><td>Valeur capitaux propres</td><td>{{ equity:,.0f }} €</td></tr>
                    <tr><td>Valeur par action</td><td>{{ vpa:.2f }} €</td></tr>
                </table>
            </body>
            </html>
            """

            html_content = Template(template_html).render(
                logo=logo_base64,
                entreprise=entreprise,
                annees=annees,
                fcf_proj=fcf_projete,
                fcf_actu=fcf_actualise,
                ev=valeur_entreprise,
                equity=valeur_capitaux_propres,
                vpa=valeur_par_action
            )

            pdf_bytes = pdfkit.from_string(html_content, False)
            st.download_button(
                label="Télécharger le PDF",
                data=pdf_bytes,
                file_name=f"rapport_dcf_{entreprise}.pdf",
                mime="application/pdf"
            )

    elif methode == "Analyse par ratios (multiples)":
        st.subheader(f"Résultats par ratios pour {entreprise}")

        valeur_par_action_per = (benefice_net * per) / actions
        valeur_entreprise_ev_ebitda = ebitda * ev_ebitda
        valeur_capitaux_propres = valeur_entreprise_ev_ebitda + dette_nette
        valeur_par_action_ebitda = valeur_capitaux_propres / actions

        st.metric("Valeur par action (PER)", f"{valeur_par_action_per:.2f} €")
        st.metric("Valeur par action (EV/EBITDA)", f"{valeur_par_action_ebitda:.2f} €")

        fig = go.Figure()
        fig.add_trace(go.Bar(name="PER", x=["PER"], y=[valeur_par_action_per]))
        fig.add_trace(go.Bar(name="EV/EBITDA", x=["EV/EBITDA"], y=[valeur_par_action_ebitda]))
        fig.update_layout(title="Comparatif des valorisations", yaxis_title="€", barmode="group")
        st.plotly_chart(fig)