import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")
st.title("💸 Tablero de Control Familiar")

# --- 2. LISTAS ---
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
COLUMNAS_DINERO = [
    "Monto", "Total", "Gastos", "Ingresos", "Ahorro", 
    "Cotizacion", "Saldo", "Valor", "Pesos", "USD", "Ars"
] + MESES

# --- 3. FUNCIONES DE LIMPIEZA ---
def formato_pesos(valor):
    try:
        val_str = str(valor).strip()
        if val_str in ["", "-", "nan", "None", "0", "0.0"]: return "-"
        val_str = val_str.replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".")
        val_float = float(val_str)
        return "$ " + "{:,.0f}".format(val_float).replace(",", ".")
    except:
        return valor

def limpiar_y_formatear(df):
    if df.empty: return df
    df = df.astype(str).replace(["nan", "None", "<NA>"], "-")
    for col in df.columns:
        if any(k.lower() in col.lower() for k in COLUMNAS_DINERO):
            # No formateamos si es descripcion
            if "descrip" not in col.lower() and "moneda" not in col.lower() and "fuente" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
    return df

# --- 4. BUSCADOR ---
def encontrar_coordenadas(df_raw, palabras_clave, min_col=0, min_row=0):
    """Escanea la hoja buscando alguna de las palabras clave"""
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for palabra in palabras_clave:
                    # 'match' simple: si la palabra está dentro de la celda
                    if palabra.lower() in val_str:
                        return r_idx, (c_idx + min_col)
        return None, None
    except:
        return None, None

def cortar_desde_coordenada(df_raw, fila, col, num_cols, filas_datos=None):
    try:
        # Headers
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        inicio_datos = fila + 1
        
        if filas_datos:
            df = df_raw.iloc[inicio_datos : inicio_datos + filas_datos, col : col + num_cols].copy()
        else:
            df = df_raw.iloc[inicio_datos:, col : col + num_cols].copy()
            # Cortamos solo si la PRIMERA columna está vacía (fin de tabla)
            df = df[df.iloc[:, 0].ne("nan") & df.iloc[:, 0].ne("")]
            
        df.columns = headers
        return df
    except:
        return pd.DataFrame()

# --- 5. APP PRINCIPAL ---
lista_pestanas = ["Resumen Anual"] + MESES[6:] + MESES[:6]
hoja_seleccionada = st.sidebar.selectbox("📅 Selecciona Período:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
except:
    st.error("Error conectando con Google Sheets.")
    st.stop()

# === RESUMEN ANUAL ===
if hoja_seleccionada == "Resumen Anual":
    st.header("📊 Resumen Anual")
    
    # 1. GASTOS
    r, c = encontrar_coordenadas(df_raw, ["Categoría", "Categoria"])
    if r is not None:
        st.subheader("📉 Evolución de Gastos")
        df = cortar_desde_coordenada(df_raw, r, c, num_cols=14)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)
    
    st.divider()
    
    # 2. SALDOS
    # Buscamos título verde "Saldos Mensuales", header está +1 abajo
    r, c = encontrar_coordenadas(df_raw, ["Saldos Mensuales"])
    if r is not None:
        st.subheader("💰 Saldos Mensuales")
        df = cortar_desde_coordenada(df_raw, r + 1, c, num_cols=14, filas_datos=1)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)
        
    st.divider()
    
    # 3. TABLAS INFERIORES
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("🏦 Mis Ahorros")
        # ESTRATEGIA: Buscar directamente la palabra "Fuente" que es el encabezado de la columna A
        r, c = encontrar_coordenadas(df_raw, ["Fuente"])
        
        if r is not None:
            # Encontró el header "Fuente", cortamos desde ahí
            df = cortar_desde_coordenada(df_raw, r, c, num_cols=5)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            st.info("No encontré la columna 'Fuente'.")
    
    with c2:
        st.subheader("🔄 Cambio de Dólares")
        # ESTRATEGIA: Buscar "Dolares" (el dato de la fila 39) y subir 1 fila para agarrar los meses
        # O buscar "Cotizacion" y subir 2 filas.
        # "Dolares" es seguro porque está en la columna A.
        r, c = encontrar_coordenadas(df_raw, ["Dolares"]) 
        
        if r is not None:
            # Si encontró "Dolares" (etiqueta), los headers (Meses) están 1 fila ARRIBA
            df = cortar_desde_coordenada(df_raw, r - 1, c, num_cols=14)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            # Fallback: buscar el título verde plural o singular
            r, c = encontrar_coordenadas(df_raw, ["Cambio de dolares", "Cambio de dolare"])
            if r is not None:
                # Si encontró titulo verde, header está +1 abajo
                df = cortar_desde_coordenada(df_raw, r + 1, c, num_cols=14)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)
            else:
                st.info("No encontré la tabla de Cambio.")

# === MESES INDIVIDUALES ===
else:
    st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")
    
    # KPIs
    r_bal, c_bal = encontrar_coordenadas(df_raw, ["Gastos fijos"], min_col=4)
    balance = pd.DataFrame()
    if r_bal is not None:
        balance = cortar_desde_coordenada(df_raw, r_bal, c_bal, num_cols=3, filas_datos=1)

    # Gastos
    r_gastos, c_gastos = encontrar_coordenadas(df_raw, ["Vencimiento", "Categoría"])
    gastos = pd.DataFrame()
    if r_gastos is not None:
        gastos = cortar_desde_coordenada(df_raw, r_gastos, c_gastos, num_cols=5)

    # Ingresos
    r_ing, c_ing = encontrar_coordenadas(df_raw, ["Fecha", "Descripcion"], min_col=5, min_row=4)
    ingresos = pd.DataFrame()
    if r_ing is not None:
        ingresos = cortar_desde_coordenada(df_raw, r_ing, c_ing, num_cols=6)

    # VISUALIZACIÓN
    st.markdown("### 💰 Balance del Mes")
    if not balance.empty:
        c1, c2, c3 = st.columns(3)
        try:
            v1 = formato_pesos(balance.iloc[0, 0])
            v2 = formato_pesos(balance.iloc[0, 1])
            v3 = formato_pesos(balance.iloc[0, 2])
            c1.metric(balance.columns[0], v1)
            c2.metric(balance.columns[1], v2)
            c3.metric(balance.columns[2], v3)
        except: st.warning("Datos encontrados pero formato incorrecto.")
    else: st.warning("No se encontró tabla de Balance.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📉 Gastos")
        if not gastos.empty: st.dataframe(limpiar_y_formatear(gastos), hide_index=True)
        else: st.info("Sin gastos.")
    with col2:
        st.subheader("📈 Ingresos")
        if not ingresos.empty: st.dataframe(limpiar_y_formatear(ingresos), hide_index=True)
        else: st.info("Sin ingresos.")
