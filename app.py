import streamlit as st
import pandas as pd
import openai

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

    # 📈 Visualisatie van kolom
    st.subheader("📈 Kolom visualisatie")
    kolommen = df.columns.tolist()
    kolom = st.selectbox("Kies een kolom", kolommen)

    if pd.api.types.is_numeric_dtype(df[kolom]):
        st.line_chart(df[kolom])
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

else:
    st.info("👆 Upload een CSV-bestand om te starten.")
