import streamlit as st
import pandas as pd

# Configuración de la página (título en la pestaña del navegador, icono, etc.)
st.set_page_config(
    page_title="Finanzas Familiares",
    page_icon="💰",
    layout="wide"
)

# Título principal de la app
st.title("💸 Gestión de Gastos Familiares")

# Mensaje de bienvenida
st.markdown("""
Esta aplicación nos ayudará a:
* 📊 Visualizar nuestros gastos e ingresos.
* 🗓️ Controlar vencimientos.
* 🤖 Cargar facturas automáticamente con IA.
""")

st.success("¡El sistema está online! El siguiente paso es conectar la Google Sheet.")

# Un botón de prueba
if st.button("Hacer una prueba"):
    st.balloons()
