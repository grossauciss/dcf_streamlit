
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import tempfile

st.set_page_config(page_title="Analyse Financière", layout="centered")

st.title("📊 DCF & Ratios Analyzer")
st.caption("Estimez la valeur d'une entreprise avec différentes méthodes.")

devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symbole = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}[devise]

tab_dcf, tab_ratios = st.tabs(["🔍 Analyse DCF", "📊 Analyse par Ratios"])

with tab_dcf:
    with st.form("formulaire_dcf"):
        entreprise = st.text_input("Nom de l'entreprise", "Entreprise X")
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
        valeur_par_action = valeur_capitaux_propres / actions
        marge_securite = ((valeur_par_action - cours_reel) / cours_reel) * 100

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

        df = pd.DataFrame({"Année": annees, "FCF Projeté": fcf_projete, "FCF Actualisé": fcf_actualise})
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name="Flux DCF", index=False)
        st.download_button(
            label="📥 Exporter en Excel",
            data=output.getvalue(),
            file_name="DCF_resultats.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as full_pdf:
            c = canvas.Canvas(full_pdf.name, pagesize=A4)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(2 * cm, 27 * cm, f"Rapport DCF - {entreprise}")
            c.setFont("Helvetica", 12)
            c.drawString(2 * cm, 25.5 * cm, f"Valeur entreprise : {valeur_entreprise:,.0f} {symbole}")
            c.drawString(2 * cm, 24.8 * cm, f"Valeur des capitaux propres : {valeur_capitaux_propres:,.0f} {symbole}")
            c.drawString(2 * cm, 24.1 * cm, f"Valeur par action : {valeur_par_action:.2f} {symbole}")
            c.drawString(2 * cm, 23.4 * cm, f"Cours actuel : {cours_reel:.2f} {symbole}")
            c.drawString(2 * cm, 22.7 * cm, f"Marge de sécurité : {marge_securite:.1f}%")
            y = 21.5 * cm
            for i in range(len(annees)):
                c.drawString(2 * cm, y, f"{annees[i]} : FCF projeté {fcf_projete[i]:,.0f}, actualisé {fcf_actualise[i]:,.0f}")
                y -= 0.6 * cm
            c.showPage()
            c.save()
            full_pdf.seek(0)
            st.download_button(
                label="📄 Télécharger le rapport PDF",
                data=full_pdf.read(),
                file_name=f"rapport_{entreprise}.pdf",
                mime="application/pdf"
            )
