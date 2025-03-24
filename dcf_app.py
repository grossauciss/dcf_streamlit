
# ⚠️ Ce code commence après les blocs d'analyse DCF & Ratios déjà exécutés

# --- Score de valorisation (déjà calculé si DCF ou Ratios soumis)
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

    # --- Bloc de commentaire automatique ---
    st.subheader("📝 Interprétation automatique")
    try:
        roe = info.get("returnOnEquity", 0) * 100
        net_margin = info.get("netMargins", 0) * 100
        debt_ratio = info.get("debtToEquity", 0)
        rev_growth = info.get("revenueGrowth", 0) * 100

        commentaire = "L'entreprise semble "
        if score_final >= 85:
            commentaire += "**très sous-valorisée** selon les différentes approches."
        elif score_final >= 70:
            commentaire += "**sous-valorisée** selon la plupart des méthodes."
        elif score_final >= 50:
            commentaire += "**correctement valorisée**, avec un potentiel modéré."
        else:
            commentaire += "**surévaluée** selon l'analyse actuelle."

        commentaire += f" Le score global atteint **{score_final}/100**."

        if roe > 15:
            commentaire += f" La rentabilité est solide (ROE : {roe:.1f}%)."
        if net_margin > 10:
            commentaire += f" La marge nette est élevée ({net_margin:.1f}%)."
        if debt_ratio > 100:
            commentaire += f" ⚠️ Le taux d’endettement est important ({debt_ratio:.0f}%), ce qui appelle à la prudence."
        if rev_growth > 5:
            commentaire += f" 📈 La croissance du chiffre d'affaires est positive ({rev_growth:.1f}%)."

        st.markdown(commentaire)
    except Exception as e:
        st.warning("⚠️ Impossible de générer un résumé automatique pour cette entreprise.")
