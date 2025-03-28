
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
import os

st.set_page_config(page_title="Simulateur de Cuves", layout="wide")

# === Simulation ===

def simuler_volume_et_weekend(debut, niveau_initial, productions, debits_journaliers):
    fin = (debut + timedelta(days=7 - debut.weekday())).replace(hour=5)
    heures = pd.date_range(start=debut, end=fin, freq='H')
    volume = niveau_initial
    historique = []

    for h in heures:
        jour = h.strftime('%A')
        heure = h.time()

        if jour in productions and time(5, 0) <= heure < time(21, 0):
            production = productions[jour] / 16
        else:
            production = 0

        if jour in debits_journaliers:
            debit = debits_journaliers[jour]
        elif jour in ['Saturday', 'Sunday']:
            debit = debits_journaliers.get('Friday', 24)
        else:
            debit = 0

        volume += debit - production
        volume = max(0, min(volume, 1400))

        historique.append({
            'Heure': h,
            'Jour': jour,
            'Volume (m³)': volume,
            'Débit (m³/h)': debit,
            'Production (m³/h)': production
        })

    return pd.DataFrame(historique)

# === Optimisation IA ===

def optimiser_debit_journalier(productions, niveau_depart=1400, debut=None):
    if not debut:
        debut = datetime.now()
        while debut.weekday() != 0:
            debut += timedelta(days=1)
        debut = debut.replace(hour=5)

    meilleure_solution = None
    meilleur_score = float('inf')
    essais = 300
    jours = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    for _ in range(essais):
        debits_journaliers = {jour: np.random.uniform(19, 30) for jour in jours}
        df = simuler_volume_et_weekend(debut, niveau_depart, productions, debits_journaliers)

        vendredi_21h = df[(df['Jour'] == 'Friday') & (df['Heure'].dt.hour == 21)]
        volume_final = vendredi_21h.iloc[0]['Volume (m³)'] if not vendredi_21h.empty else 0

        volume_max = df['Volume (m³)'].max()
        volume_min = df['Volume (m³)'].min()
        penalty = 0

        if volume_final < 200 or volume_final > 300:
            penalty += abs(volume_final - 250) * 2
        if volume_max > 1440:
            penalty += (volume_max - 1440) * 5
        if volume_min < 0:
            penalty += abs(volume_min) * 10

        if penalty < meilleur_score:
            meilleur_score = penalty
            meilleure_solution = (df, debits_journaliers)

    return meilleure_solution

# === Interface ===

st.title("💧 Simulateur REE - La Salvetat")
mode = st.radio("Mode de simulation :", ["Débit fixe", "Optimisé", "Suivi en cours de semaine"])

jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
jours_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
cols = st.columns(5)
productions = {}
for i, jour in enumerate(jours):
    productions[jours_en[i]] = cols[i].number_input(f"Production {jour}", min_value=0.0, max_value=1000.0, value=300.0, step=10.0)

if mode == "Débit fixe" or mode == "Suivi en cours de semaine":
    debit_fixe = st.slider("Débit constant (m³/h)", 10.0, 35.0, 24.0, 0.5)

if mode == "Suivi en cours de semaine":
    niveau_initial = st.number_input("Niveau actuel des cuves (m³)", min_value=0.0, max_value=1500.0, value=1000.0, step=10.0)
    date_str = st.text_input("Date/Heure actuelle (AAAA-MM-JJ HH:MM)", value=datetime.now().strftime("%Y-%m-%d %H:%M"))
    try:
        debut = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except:
        st.error("Format de date invalide. Utilisez AAAA-MM-JJ HH:MM")
        debut = None
else:
    niveau_initial = 1400
    debut = None

# === Simulation ===
df = None
if st.button("Lancer la simulation"):
    if not debut:
        debut = datetime.now()
        while debut.weekday() != 0:
            debut += timedelta(days=1)
        debut = debut.replace(hour=5)

    if mode == "Débit fixe" or mode == "Suivi en cours de semaine":
        debits = {j: debit_fixe for j in jours_en}
        df = simuler_volume_et_weekend(debut, niveau_initial, productions, debits)
    else:
        df, debits = optimiser_debit_journalier(productions, niveau_initial, debut)

    # === Graphique ===
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Heure'], y=df['Volume (m³)'], mode='lines', name='Volume', yaxis='y1'))
    fig.add_trace(go.Scatter(x=df['Heure'], y=df['Débit (m³/h)'], mode='lines', name='Débit forage', yaxis='y2', line=dict(dash='dot')))
    fig.add_trace(go.Scatter(x=df['Heure'], y=df['Production (m³/h)'], mode='lines', name='Production', yaxis='y2', line=dict(dash='dot')))

    fig.update_layout(
        title="Évolution du volume des cuves",
        xaxis_title="Heure",
        yaxis=dict(title="Volume (m³)", side="left"),
        yaxis2=dict(title="Débit / Production (m³/h)", overlaying='y', side='right', showgrid=False),
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Enregistrement HTML
    file_path = "simulation_result.html"
    fig.write_html(file_path)
    st.success("Simulation terminée ✅")
    st.markdown(f"[🔗 Voir le graphique dans le navigateur]({file_path})", unsafe_allow_html=True)

    # Export Excel
    excel_file = "simulation_result.xlsx"
    df.to_excel(excel_file, index=False)
    with open(excel_file, "rb") as f:
        st.download_button(label="📥 Télécharger les données Excel", data=f, file_name=excel_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
