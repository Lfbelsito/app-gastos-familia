import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")

# --- 2. LISTAS (CALENDARIO COMPLETO) ---
# Agregamos todos los meses del año para que no te falte ninguno
MESES_ORDENADOS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

COLUMNAS_DINERO = ["Monto", "Total", "Gastos", "Ingresos", "Ahorro", "Valor", "Pesos", "USD"]

# --- 3. FUNCIONES DE LIMPIEZA (CORREGIDO BUG DE MILLONES) ---
def limpiar_valor(val):
    """
    Limpia valores monetarios. 
    CORRECCIÓN: Detecta si ya es número para no borrar decimales por error.
    """
    # Si Excel ya nos manda un número puro (int o float), NO lo tocamos.
    # Esto evita que 4000000.0 se convierta en 40000000
    if isinstance(val, (int, float)):
        return float(val)
    
    # Si es texto, aplicamos la limpieza
    try:
        val_str = str(val).strip()
        if val_str in ["", "-", "nan", "None"]: return 0.0
        
        # 1. Quitamos símbolos de moneda y espacios
        val_str = val_str.replace("$", "").replace("USD", "").replace("Ars", "").strip()
        
        # 2. Manejo de Puntos y Comas (Formato Argentino/Europeo)
        # Asumimos que el punto es de miles y la coma es decimal
        val_str = val_str.replace(".", "") # Borrar punto de miles (1.000 -> 1000)
        val_str = val_str.replace(",", ".") # Cambiar coma decimal por punto (1000,50 -> 1000.50)
        
        return float(val_str)
    except:
        return 0.0

def formato_visual(val):
    """Para mostrar en pantalla bonito: $ 1.000"""
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
        
        # Filtro: Eliminar filas vacías
        df = df[~((df.iloc[:, 0].astype(str).isin(["nan", "", "None"])) & (df.iloc[:, 1].astype(str).isin(["nan", "", "None"])))]
        
        df.columns = headers
        return df
    except: return pd.DataFrame()

# --- 5. MOTOR DE DATOS ---
@st.cache_data(ttl=60) 
def cargar_todo_el_anio():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    resumen_kpi = []
    barra = st.progress(0, text="Analizando tu año financiero...")
    
    for i, mes in enumerate(MESES_ORDENADOS):
        barra.progress((i + 1) / len(MESES_ORDENADOS), text=f"Leyendo {mes}...")
        try:
            # Intentamos leer la hoja. Si no existe (ej: Enero vacío), pasamos al siguiente
            try:
                df_raw = conn.read(worksheet=mes, header=None)
            except:
                continue # Si falla la lectura, salta al siguiente mes
            
            # Buscamos Balance
            r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
            if r_bal is not None:
                bal = cortar_bloque(df_raw, r_bal, c_bal, 3, filas_aprox=1)
                if not bal.empty:
                    gastos = limpiar_valor(bal.iloc[0, 0])
                    ingresos = limpiar_valor(bal.iloc[0, 1])
                    ahorro = limpiar_valor(bal.iloc[0, 2])
                    
                    # Solo agregamos si hay datos reales (para no llenar el gráfico de ceros)
                    if gastos > 0 or ingresos > 0:
                        resumen_kpi.append({
                            "Mes": mes,
                            "Gastos": gastos,
                            "Ingresos": ingresos,
                            "Ahorro": ahorro
                        })
            
        except Exception as e:
            print(f"Error procesando {mes}: {e}")
            
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
            st.subheader("Curva de Ahorro
