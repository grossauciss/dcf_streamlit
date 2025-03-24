
# [...] Le code complet de l'application jusqu'à la fin du score de valorisation est supposé ici

# --- Bloc de commentaire automatique ---
if valeurs and cours and info:
    st.subheader("📝 Interprétation automatique")
    try:
        # Extraction de variables clés
        roe = info.get("returnOnEquity", 0) * 100
        net_margin = info.get("netMargins", 0) * 100
        debt_ratio = info.get("debtToEquity", 0)
        rev_growth = info.get("revenueGrowth", 0) * 100

        # Catégorisation simplifiée
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
        
        # Ajouts contextuels
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
