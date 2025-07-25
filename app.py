import streamlit as st
import pandas as pd

st.set_page_config(page_title="Afvalwater Data‑analyse", layout="wide")
st.title("💧 Afvalwater Analyse Assistent")

uploaded_file = st.file_uploader("Upload een CSV-bestand", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("Datavoorbeeld (eerste 5 rijen)")
    st.dataframe(df.head())

    st.subheader("Kolom visualisatie")
    col = st.selectbox("Kies een kolom om te plotten", df.columns.tolist())
    st.line_chart(df[col])
else:
    st.info("Upload een CSV om te beginnen.")
