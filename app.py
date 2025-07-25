import streamlit as st
import pandas as pd
import openai
import plotly.graph_objects as go
import plotly.express as px

# 🔑 API key ophalen uit Streamlit secrets
client = openai.OpenAI(api_key=st.secrets["openai"]["api_key"])

st.set_page_config(page_title="Afvalwater Analyse", layout="wide")
st.title("💧 Afvalwater Data-analyse Assistent")

# 📁 Upload CSV-bestand
uploaded_file = st.file_uploader("Upload een CSV-bestand", type=["csv"])

if uploaded_file:
    # 📊 Inlezen en tonen van data
    df = pd.read_csv(uploaded_file)
    st.subheader("🔍 Eerste 5 rijen van de data")
    st.dataframe(df.head())

    # 📈 Visualisatie met anomalieën
    st.subheader("📈 Kolom visualisatie")
    kolommen = df.columns.tolist()
    kolom = st.selectbox("Kies een kolom", kolommen)

    if pd.api.types.is_numeric_dtype(df[kolom]):
        mu = df[kolom].mean()
        sigma = df[kolom].std()
        boven = df[kolom] > mu + 2 * sigma
        onder = df[kolom] < mu - 2 * sigma
        outliers = df[boven | onder]
    
        fig = go.Figure()

        # Normale lijn
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[kolom],
            mode='lines+markers',
            name='Meetwaarden',
            marker=dict(color='blue')
        ))

        # Anomalieën in rood
        if not outliers.empty:
            fig.add_trace(go.Scatter(
                x=outliers.index,
                y=outliers[kolom],
                mode='markers',
                name='Afwijkingen',
                marker=dict(color='red', size=10, symbol='circle-open'),
                hovertext=[f"Waarde: {v}" for v in outliers[kolom]]
            ))

        fig.update_layout(
            title=f"Waarden voor {kolom}",
            xaxis_title="Index (rijvolgorde)",
            yaxis_title=kolom,
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Geselecteerde kolom is niet numeriek en kan niet worden geplot.")

    # 🧠 Automatische GPT-analyse
    st.subheader("🧠 AI Inzichten")
    if st.button("Analyseer met GPT"):
        with st.spinner("GPT analyseert de data..."):
            summary = df.describe().to_string()
            prompt = f"""Je bent een expert in biologische afvalwaterzuivering.
Hier zijn statistieken van een dataset met gemeten waarden (zoals BZV, CZV, stikstof, fosfaat en flow):

{summary}

Geef in duidelijke en beknopte taal een analyse van wat opvalt. Richt je op trends, afwijkingen en mogelijke procesconclusies."""
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                )
                antwoord = response.choices[0].message.content
                st.success("AI-analyse succesvol!")
                st.markdown(antwoord)
            except Exception as e:
                st.error(f"Fout bij AI-analyse: {e}")

    # 💬 Interactieve vragen stellen
    st.subheader("💬 Stel een vraag over je data")
    vraag = st.text_input("Bijvoorbeeld: Wat valt op in de fosfaatwaarden?")
    if vraag:
        with st.spinner("GPT denkt na..."):
            summary = df.describe().to_string()
            prompt = f"""
Je bent een dataspecialist in biologische afvalwaterzuivering.
Hieronder zie je een samenvatting van meetdata:

{summary}

Gebruiker stelt de volgende vraag:
\"{vraag}\"

Beantwoord deze vraag helder, feitelijk, en als mogelijk met context uit afvalwaterprocessen.
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                )
                antwoord = response.choices[0].message.content
                st.markdown("**🤖 Antwoord van GPT:**")
                st.markdown(antwoord)
            except Exception as e:
                st.error(f"Fout bij AI-vraag: {e}")
    st.subheader("📊 Correlatie tussen kolommen")

numeric_df = df.select_dtypes(include="number")

if numeric_df.shape[1] < 2:
    st.info("Minstens twee numerieke kolommen nodig voor correlatie.")
else:
    corr = numeric_df.corr()
    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        aspect="auto",
        title="Correlatiematrix",
        labels=dict(color="Correlatie")
    )
    st.plotly_chart(fig, use_container_width=True)

    if st.button("🧠 Analyseer correlaties met AI"):
        corr_text = corr.to_string()
        prompt = f"""
Je bent een dataspecialist in biologische afvalwaterzuivering.
Hieronder zie je de correlatiematrix tussen meetparameters:

{corr_text}

Geef een beknopte uitleg van opvallende correlaties, met mogelijke oorzaken.
Vermeld of bepaalde parameters elkaars gedrag kunnen verklaren (bijv. stijgende BZV en CZV).
"""
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            st.markdown("**🤖 GPT-analyse van correlaties:**")
            st.markdown(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Fout bij AI-analyse: {e}")



    # 🔎 Fase 4: Automatische anomaly detection
st.subheader("🚨 Detecteer en verklaar afwijkingen")

if "anomalie_antwoord" not in st.session_state:
    st.session_state["anomalie_antwoord"] = None

if st.button("Analyseer afwijkingen met AI"):
    with st.spinner("Zoekt naar afwijkende waarden..."):
        anomalieën = []
        for kol in df.select_dtypes(include="number").columns:
            mu = df[kol].mean()
            sigma = df[kol].std()
            boven = df[kol] > mu + 2 * sigma
            onder = df[kol] < mu - 2 * sigma
            afwijkend = df[boven | onder]
            if not afwijkend.empty:
                anomalieën.append((kol, afwijkend[[kol]].to_dict(orient="records")))

        if not anomalieën:
            st.session_state["anomalie_antwoord"] = "✅ Er zijn geen opvallende afwijkingen gevonden."
        else:
            beschrijving = ""
            for kol, lijst in anomalieën:
                beschrijving += f"\n• Kolom: {kol}, Afwijkende waarden:\n{lijst}\n"

            prompt = f"""
Je bent een expert in biologische afvalwaterzuivering.
We hebben de volgende afwijkingen gedetecteerd in meetdata:

{beschrijving}

Geef per afwijking een mogelijke verklaring, bijvoorbeeld:
- meetfouten
- overbelasting
- biologisch probleem
- veranderde influentkwaliteit
- hydraulische pieken

Leg kort en duidelijk uit wat mogelijke oorzaken zijn.
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                st.session_state["anomalie_antwoord"] = response.choices[0].message.content
            except Exception as e:
                st.session_state["anomalie_antwoord"] = f"❌ Fout bij AI-analyse: {e}"

# Toon het antwoord, ook na andere interacties
if st.session_state["anomalie_antwoord"]:
    st.markdown("**🧠 AI-verklaring voor afwijkingen:**")
    st.markdown(st.session_state["anomalie_antwoord"])
else:
    st.info("👆 Upload een CSV-bestand om te starten.")



st.subheader("🧠 AI-advies per parameter")

if uploaded_file:
    numeriek = df.select_dtypes(include="number")

    if st.button("Genereer advies per kolom"):
        with st.spinner("GPT analyseert elke parameter afzonderlijk..."):
            for kolom in numeriek.columns:
                waarden = df[kolom].dropna().to_list()

                prompt = f"""
Je bent een expert in biologische afvalwaterzuivering. 
Hier zijn de metingen voor de parameter '{kolom}' uit een tijdsreeks van een zuiveringsinstallatie:

{waarden}

1. Wat valt op in de spreiding en het niveau?
2. Zijn er mogelijke pieken of problemen?
3. Wat zijn mogelijke verklaringen (biologisch, hydraulisch, extern)?
4. Welke actie of controle raad je aan?

Formuleer het antwoord duidelijk en beknopt.
"""

                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                    )
                    advies = response.choices[0].message.content
                    st.markdown(f"### 🔎 Analyse van **{kolom}**")
                    st.markdown(advies)
                except Exception as e:
                    st.error(f"Fout bij AI-analyse voor {kolom}: {e}")

from fpdf import FPDF
import tempfile

st.subheader("📄 Genereer PDF-rapport")

if uploaded_file:
    if st.button("📤 Maak rapport met AI-analyse"):
        with st.spinner("Rapport wordt gegenereerd..."):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            # Titel
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Afvalwater Analyse Rapport", ln=True)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Bestand: {uploaded_file.name}", ln=True)

            # Statistiek
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "📊 Statistiekoverzicht", ln=True)
            pdf.set_font("Courier", "", 8)
            stat_text = df.describe().round(2).to_string()
            for line in stat_text.split("\n"):
                pdf.cell(0, 5, line, ln=True)

            # AI-analyse per kolom
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "🧠 AI-advies per parameter", ln=True)
            pdf.set_font("Arial", "", 10)
            numeriek = df.select_dtypes(include="number")

            for kolom in numeriek.columns:
                waarden = df[kolom].dropna().to_list()
                prompt = f"""
Je bent een expert in biologische afvalwaterzuivering. 
Hier zijn de metingen voor de parameter '{kolom}':

{waarden}

1. Wat valt op?
2. Zijn er problemen?
3. Wat zijn mogelijke verklaringen?
4. Welke actie raad je aan?
"""
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                    )
                    advies = response.choices[0].message.content
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, f"🔹 {kolom}", ln=True)
                    pdf.set_font("Arial", "", 9)
                    for line in advies.split("\n"):
                        pdf.multi_cell(0, 5, line)
                        pdf.ln(0.5)
                except Exception as e:
                    pdf.set_font("Arial", "I", 9)
                    pdf.cell(0, 6, f"[Fout bij {kolom}]: {e}", ln=True)

            # Opslaan naar tijdelijk bestand
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
                pdf.output(tmpfile.name)
                st.success("✅ Rapport klaar voor download")
                st.download_button(
                    label="📥 Download PDF",
                    data=open(tmpfile.name, "rb").read(),
                    file_name="rapport_afvalwater_ai.pdf",
                    mime="application/pdf"
                )
