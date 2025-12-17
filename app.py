import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")

# ==============================================================================
# 🔴 ¡IMPORTANTE! PEGA AQUÍ EL LINK DE TU GOOGLE SHEET ENTRE LAS COMILLAS 🔴
# ==============================================================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-f2J1S78msG56qWHtBFqFKOQ3nKmF_qo0952_vBar1o/edit?gid=880489958#gid=880489958" 
# (He puesto el link que vi en tus capturas, pero verifícalo si cambió)

# --- 2. LISTAS ---
MESES_ORDENADOS = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
COLUMNAS_DINERO = ["Monto", "Total", "Gastos", "Ingresos", "Ahorro", "Valor", "Pesos", "USD"]

# --- 3. FUNCIONES DE LIMPIEZA ---
def limpiar_valor(val):
    try:
        val_str = str(val).strip().replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".")
        return float(val_str)
    except:
        return 0.0

def formato_visual(val):
    return "$ {:,.0f}".format(val).replace(",", ".")

# --- 4. FUNCIONES DE EXTRACCIÓN ---
def encontrar_celda(df_raw, palabras_clave, min_col=0, min_row=0):
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for p in palabras_clave:
                    if p.lower() in val_str:
                        return r_idx, (c_idx + min_col)
        return None, None
    except: return None, None

def cortar_bloque(df_raw, fila, col, num_cols, filas_aprox=30):
    try:
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        start = fila + 1
        df = df_raw.iloc[start : start + filas_aprox, col : col + num_cols].copy()
        df = df[~((df.iloc[:, 0].astype(str).isin(["nan", "", "None"])) & (df.iloc[:, 1].astype(str).isin(["nan", "", "None"])))]
        df.columns = headers
        return df
    except: return pd.DataFrame()

# --- 5. MOTOR DE DATOS (CON URL EXPLÍCITA) ---
@st.cache_data(ttl=60) 
def cargar_todo_el_anio():
    # Creamos la conexión
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    datos_anuales = []
    resumen_kpi = []

    barra = st.progress(0, text="Analizando tu año financiero...")
    
    for i, mes in enumerate(MESES_ORDENADOS):
        barra.progress((i + 1) / len(MESES_ORDENADOS), text=f"Leyendo {mes}...")
        try:
            # AQUÍ ESTABA EL ERROR: Ahora le pasamos spreadsheet=SHEET_URL
            df_raw = conn.read(spreadsheet=SHEET_URL, worksheet=mes, header=None)
            
            # 1. Extraer KPI (Balance)
            r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
            if r_bal is not None:
                bal = cortar_bloque(df_raw, r_bal, c_bal, 3, filas_aprox=1)
                if not bal.empty:
                    gastos = limpiar_valor(bal.iloc[0, 0])
                    ingresos = limpiar_valor(bal.iloc[0, 1])
                    ahorro = limpiar_valor(bal.iloc[0, 2])
                    
                    resumen_kpi.append({
                        "Mes": mes,
                        "Gastos": gastos,
                        "Ingresos": ingresos,
                        "Ahorro": ahorro
                    })
            
        except Exception as e:
            print(f"Error leyendo {mes}: {e}")
            
    barra.empty()
    return pd.DataFrame(resumen_kpi)

# --- 6. INTERFAZ PRINCIPAL ---

st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📊 Dashboard General", "📅 Ver Mensual"])

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# DASHBOARD
# ==========================================
if opcion == "📊 Dashboard General":
    st.title("💸 Tablero de Control Familiar")
    st.markdown("### Panorama Anual")
    
    df_resumen = cargar_todo_el_anio()
    
    if not df_resumen.empty:
        total_ingresos = df_resumen["Ingresos"].sum()
        total_gastos = df_resumen["Gastos"].sum()
        total_ahorro = df_resumen["Ahorro"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos Año", formato_visual(total_ingresos), border=True)
        c2.metric("Total Gastos Año", formato_visual(total_gastos), delta_color="inverse", border=True)
        c3.metric("Ahorro Neto Acumulado", formato_visual(total_ahorro), border=True)
        
        st.divider()
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Ingresos vs Gastos")
            df_melted = df_resumen.melt(id_vars=["Mes"], value_vars=["Ingresos", "Gastos"], var_name="Tipo", value_name="Monto")
            fig = px.bar(df_melted, x="Mes", y="Monto", color="Tipo", barmode="group", 
                         text_auto='.2s', color_discrete_map={"Ingresos": "#00CC96", "Gastos": "#EF553B"})
            st.plotly_chart(fig, use_container_width=True)

        with col_graf2:
            st.subheader("Curva de Ahorro")
            fig2 = px.line(df_resumen, x="Mes", y="Ahorro", markers=True)
            fig2.update_traces(line_color="#636EFA")
            st.plotly_chart(fig2, use_container_width=True)
            
        with st.expander("Ver tabla de datos consolidada"):
            st.dataframe(df_resumen, use_container_width=True)
            
    else:
        st.info("Aún no se pudieron cargar datos. Verifica el link de la hoja en el código.")


# ==========================================
# VER MENSUAL
# ==========================================
elif opcion == "📅 Ver Mensual":
    mes_seleccionado = st.sidebar.selectbox("Selecciona Mes:", MESES_ORDENADOS)
    st.title(f"Detalle de {mes_seleccionado}")
    
    try:
        # AQUÍ TAMBIÉN AGREGAMOS LA URL EXPLÍCITA
        df_raw = conn.read(spreadsheet=SHEET_URL, worksheet=mes_seleccionado, header=None)
        
        r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
        balance = cortar_bloque(df_raw, r_bal, c_bal, 3, 1) if r_bal is not None else pd.DataFrame()
        
        r_gas, c_gas = encontrar_celda(df_raw, ["Vencimiento", "Categoría"], min_col=0)
        gastos = cortar_bloque(df_raw, r_gas, c_gas, 5, 40) if r_gas is not None else pd.DataFrame()
        
        r_ing, c_ing = encontrar_celda(df_raw, ["Fecha", "Descripcion"], min_col=6, min_row=3)
        ingresos = cortar_bloque(df_raw, r_ing, c_ing, 6, 20) if r_ing is not None else pd.DataFrame()

        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            try:
                v1 = balance.iloc[0,0]; v2 = balance.iloc[0,1]; v3 = balance.iloc[0,2]
                c1.metric("Gastos Fijos", str(v1)); c2.metric("Ingresos", str(v2)); c3.metric("Ahorro", str(v3))
            except: pass
            
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Gastos")
            st.dataframe(gastos, hide_index=True)
        with col2:
            st.subheader("Ingresos")
            st.dataframe(ingresos, hide_index=True)
            
    except Exception as e:
        st.error(f"Error cargando el mes: {e}")
