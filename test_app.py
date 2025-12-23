import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Mini Streamlit Test", layout="wide")

st.title("Mini Streamlit Test App")
st.write("If you see this, Streamlit and pandas/plotly are working.")

# Simple dataframe and plot
df = pd.DataFrame({
    "week": [f"W{i}" for i in range(1, 6)],
    "value": [3, 5, 2, 6, 4],
})

st.dataframe(df, width=" stretch\)

fig = px.bar(df, x="week", y="value", title="Sample bar chart")
st.plotly_chart(fig, width=" stretch\, config={"displayModeBar": False})

st.success("Everything loaded fine. If this runs, your install is OK.")

