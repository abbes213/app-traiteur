from supabase import create_client
import streamlit as st

# Connexion Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_client():
    """Retourne le client Supabase"""
    return supabase


def créer_tables():
    """
    Les tables sont créées directement sur Supabase
    Cette fonction existe pour compatibilité avec le code existant
    """
    pass