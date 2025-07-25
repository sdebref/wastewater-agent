import streamlit as st
import pandas as pd

st.set_page_config(page_title="Afvalwater Analyse", layout="wide")
st.title("💧 Afvalwater Data-analyse Assistent")

uploaded_file = st.file_uploader("📁 Upload een CSV-bestand", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("🔍 Eerste 5 rijen van de data")
    st.dataframe(df.head())

    st.subheader("📈 Kolom visualiseren")
    kolommen = df.columns.tolist()
    kolom = st.selectbox("Kies een kolom", kolommen)

    if pd.api.types.is_numeric_dtype(df[kolom]):
        st.line_chart(df[kolom])
    else:
        st.warning("Geselecteerde kolom is niet numeriek en kan niet worden geplot.")
else:
    st.info("👆 Upload een bestand om te starten")
