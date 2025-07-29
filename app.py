import streamlit as st
import pandas as pd
import openai
import plotly.graph_objects as go
import plotly.express as px
from fpdf import FPDF
import tempfile
import os

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
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[kolom],
            mode='lines+markers',
            name='Meetwaarden',
            marker=dict(color='blue')
        ))
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
            xaxis_title="Index",
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
Hier zijn statistieken van een dataset met gemeten waarden:

{summary}

Geef een duidelijke en beknopte analyse van trends, afwijkingen en mogelijke conclusies."""
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                )
                antwoord = response.choices[0].message.content
                st.success("AI-analyse succesvol!")
                st.markdown(antwoord)
            except Exception as e:
                st.error(f"Fout bij AI-analyse: {e}")

    # 💬 Vraag aan AI
    st.subheader("💬 Stel een vraag over je data")
    vraag = st.text_input("Bijvoorbeeld: Wat valt op in de fosfaatwaarden?")
    if vraag:
        with st.spinner("GPT denkt na..."):
            summary = df.describe().to_string()
            prompt = f"""
Je bent een dataspecialist in biologische afvalwaterzuivering.
Hieronder een samenvatting van meetdata:

{summary}

Gebruiker stelt de vraag:
\"{vraag}\"

Beantwoord duidelijk en feitelijk.
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                )
                antwoord = response.choices[0].message.content
                st.markdown("**🤖 Antwoord van GPT:**")
                st.markdown(antwoord)
            except Exception as e:
                st.error(f"Fout bij AI-vraag: {e}")

    # 📊 Correlatiematrix
    st.subheader("📊 Correlatie tussen kolommen")
    numeric_df = df.select_dtypes(include="number")

    if numeric_df.shape[1] < 2:
        st.info("Minstens twee numerieke kolommen nodig.")
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
Hieronder de correlatiematrix tussen meetparameters:

{corr_text}

Geef een uitleg van opvallende verbanden.
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                st.markdown("**🤖 GPT-analyse van correlaties:**")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Fout bij AI-analyse: {e}")

    # 🚨 Anomalieën
    st.subheader("🚨 Detecteer en verklaar afwijkingen")
    if "anomalie_antwoord" not in st.session_state:
        st.session_state["anomalie_antwoord"] = None

    if st.button("Analyseer afwijkingen met AI"):
        with st.spinner("Zoekt naar afwijkingen..."):
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
                st.session_state["anomalie_antwoord"] = "✅ Geen opvallende afwijkingen gevonden."
            else:
                beschrijving = ""
                for kol, lijst in anomalieën:
                    beschrijving += f"\n• {kol}:\n{lijst}\n"
                prompt = f"""
Je bent een expert in afvalwaterzuivering.
Deze afwijkingen werden gevonden:

{beschrijving}

Wat kunnen mogelijke oorzaken zijn?
"""
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                    )
                    st.session_state["anomalie_antwoord"] = response.choices[0].message.content
                except Exception as e:
                    st.session_state["anomalie_antwoord"] = f"Fout bij AI-analyse: {e}"

    if st.session_state["anomalie_antwoord"]:
        st.markdown("**🧠 AI-verklaring voor afwijkingen:**")
        st.markdown(st.session_state["anomalie_antwoord"])

    # 🧠 Advies per parameter
    st.subheader("🧠 AI-advies per parameter")
    numeriek = df.select_dtypes(include="number")

    if st.button("Genereer advies per kolom"):
        with st.spinner("GPT analyseert per parameter..."):
            for kolom in numeriek.columns:
                waarden = df[kolom].dropna().to_list()
                prompt = f"""
Je bent een expert in biologische afvalwaterzuivering. 
Hier zijn de metingen voor '{kolom}':

{waarden}

1. Wat valt op?
2. Zijn er problemen?
3. Mogelijke oorzaken?
4. Aanbeveling?
"""
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                    )
                    advies = response.choices[0].message.content
                    st.markdown(f"### 🔎 Analyse van **{kolom}**")
                    st.markdown(advies)
                except Exception as e:
                    st.error(f"Fout bij analyse van {kolom}: {e}")

    # 📄 PDF-rapport

    st.subheader("📄 Genereer PDF-rapport")

    if uploaded_file:
        if st.button("📤 Maak rapport met AI-analyse"):
            with st.spinner("Rapport wordt gegenereerd..."):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)

                # ✅ Unicode-compatibel lettertype
                font_path = "DejaVuSans.ttf"
                if not os.path.exists(font_path):
                    st.error("❌ Fontbestand 'DejaVuSans.ttf' niet gevonden.")
                else:
                    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
                    pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
                    pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf", uni=True)
                    pdf.add_font("DejaVu", "BI", "DejaVuSans-BoldOblique.ttf", uni=True)
                    pdf.set_font("DejaVu", "", 12)

                    # Titel
                    pdf.set_font("DejaVu", "B", 16)
                    pdf.cell(0, 10, "Afvalwater Analyse Rapport", ln=True)
                    pdf.set_font("DejaVu", "", 12)
                    pdf.cell(0, 10, f"Bestand: {uploaded_file.name}", ln=True)

                    # Statistiek
                    pdf.ln(5)
                    pdf.set_font("DejaVu", "B", 12)
                    pdf.cell(0, 10, "Statistiekoverzicht", ln=True)
                    pdf.set_font("DejaVu", "", 9)
                    stat_text = df.describe().round(2).to_string()
                    for line in stat_text.split("\n"):
                        pdf.cell(0, 5, line, ln=True)

                    # AI-analyse per kolom
                    pdf.ln(5)
                    pdf.set_font("DejaVu", "B", 12)
                    pdf.cell(0, 10, "AI-advies per parameter", ln=True)
                    pdf.set_font("DejaVu", "", 10)
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
                            pdf.set_font("DejaVu", "B", 10)
                            pdf.cell(0, 8, f"{kolom}", ln=True)
                            pdf.set_font("DejaVu", "", 9)
                            for line in advies.split("\n"):
                                pdf.multi_cell(0, 5, line)
                                pdf.ln(0.5)
                        except Exception as e:
                            pdf.set_font("DejaVu", "I", 9)
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
else:
    st.info("👆 Upload een CSV-bestand om te starten.")
