import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Analyse DCF", layout="centered")

# --- HEADER ---

with st.container():
    col1, col2 = st.columns([1, 6])
    with col1:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Streamlit_logo_mark.svg/120px-Streamlit_logo_mark.svg.png", width=50)
    with col2:
        st.markdown("<h1 style='margin-bottom:0;'>📊 Analyse Financière DCF</h1>", unsafe_allow_html=True)
        st.markdown("💼 Estimation de la valeur d'une entreprise par flux de trésorerie actualisés", unsafe_allow_html=True)

st.markdown("---")

# --- PARAMÈTRES GÉNÉRAUX ---

devise = st.selectbox("Devise", ["€", "$", "CHF", "£"])
symboles = {"€": "€", "$": "$", "CHF": "CHF", "£": "£"}
symbole = symboles[devise]

# --- FORMULAIRE ---

with st.form("formulaire_dcf"):
    st.subheader("🔧 Paramètres de valorisation")

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

    submitted = st.form_submit_button("📈 Lancer l'analyse")

# --- TRAITEMENT DCF ---

if submitted:
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

    # Résultats
    st.success(f"✅ Résultats pour **{entreprise}**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Valeur de l'entreprise", f"{valeur_entreprise:,.0f} {symbole}")
    col2.metric("Valeur des capitaux propres", f"{valeur_capitaux_propres:,.0f} {symbole}")
    col3.metric("Valeur par action", f"{valeur_par_action:.2f} {symbole}")

    # Graphique
    st.markdown("### 📊 Projection des FCF")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=annees, y=fcf_projete, mode='lines+markers', name='FCF projeté'))
    fig.add_trace(go.Scatter(x=annees, y=fcf_actualise, mode='lines+markers', name='FCF actualisé'))
    fig.update_layout(xaxis_title="Année", yaxis_title=f"Montant ({symbole})", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # Tableau
    df = pd.DataFrame({
        "Année": annees,
        f"FCF Projeté ({symbole})": fcf_projete,
        f"FCF Actualisé ({symbole})": fcf_actualise
    })
    st.markdown("### 🧾 Détail des flux actualisés")
    st.dataframe(df.style.format("{:,.0f}"))

    # Export Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name="Flux DCF", index=False)
        pd.DataFrame({
            "Élément": [
                "Entreprise",
                "FCF initial",
                "Croissance FCF",
                "WACC",
                "Croissance terminale",
                "Dette nette",
                "Nombre d'actions",
                "Valeur entreprise",
                "Valeur capitaux propres",
                "Valeur par action"
            ],
            "Valeur": [
                entreprise,
                fcf_initial,
                f"{croissance * 100:.2f}%",
                f"{wacc * 100:.2f}%",
                f"{croissance_terminale * 100:.2f}%",
                dette_nette,
                actions,
                valeur_entreprise,
                valeur_capitaux_propres,
                valeur_par_action
            ]
        }).to_excel(writer, sheet_name="Résumé", index=False)

    st.download_button(
        label="📥 Télécharger les résultats en Excel",
        data=output.getvalue(),
        file_name=f"{entreprise.replace(' ', '_')}_DCF.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
