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
