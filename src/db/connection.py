import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def get_engine():
    try:
        import streamlit as st
        host = st.secrets["DB_HOST"]
        port = st.secrets["DB_PORT"]
        name = st.secrets["DB_NAME"]
        user = st.secrets["DB_USER"]
        pw   = st.secrets["DB_PASSWORD"]
    except Exception:
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        pw   = os.getenv("DB_PASSWORD")

    url = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{name}"
    return create_engine(url)