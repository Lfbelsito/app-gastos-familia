import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")
st.title("💸 Tablero de Control Familiar")

# --- LISTAS Y CONFIGURACIÓN ---
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
# Palabras que activan el formato moneda
COLUMNAS_DINERO = [
    "Monto", "Total", "Gastos", "Ingresos", "Ahorro", 
    "Cotizacion", "Saldo", "Valor", "Pesos", "USD", "Ars"
] + MESES

# --- FUNCIONES DE LIMPIEZA Y FORMATO ---

def formato_pesos(valor):
    """Convierte cualquier número a formato $ 1.000.000"""
    try:
        val_str = str(valor).strip()
        if val_str in ["", "-", "nan", "None", "0", "0.0"]: return "-"
        
        # Limpieza de símbolos
        val_str = val_str.replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".")
        
        val_float = float(val_str)
        return "$ " + "{:,.0f}".format(val_float).replace(",", ".")
    except:
        return valor

def limpiar_y_formatear(df):
    """Limpia NaNs y aplica formato pesos"""
    if df.empty: return df
    
    # Rellenar vacíos
    df = df.astype(str).replace(["nan", "None", "<NA>"], "-")
    
    for col in df.columns:
        # Si el nombre de la columna parece dinero, formateamos
        if any(k.lower() in col.lower() for k in COLUMNAS_DINERO):
            # Evitamos formatear columnas que sean "Descripción" o "Moneda" aunque contengan palabras clave
            if "descrip" not in col.lower() and "moneda" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
    return df

# --- FUNCIONES DE BÚSQUEDA TIPO "RADAR" ---

def encontrar_coordenadas(df_raw, palabras_clave, min_col=0, min_row=0):
    """
    Escanea TODA la hoja (respetando limites min_col/min_row) 
    y devuelve (fila, columna) de la primera coincidencia.
    """
    try:
        # Recortamos la zona de búsqueda para no perder tiempo
        # o para evitar encontrar cosas del lado equivocado (ej: Gastos vs Ingresos)
        zona = df_raw.iloc[min_row:, min_col:]
        
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for palabra in palabras_clave:
                    if palabra.lower() in val_str:
                        # Devolvemos indices absolutos (sumando lo que recortamos)
                        return r_idx, (c_idx + min_col)
        return None, None
    except:
        return None, None

def cortar_desde_coordenada(df_raw, fila, col, num_cols, filas_datos=None):
    """Corta una tabla empezando exactamente en (fila, col)"""
    try:
        # Headers están en la fila encontrada
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        inicio_datos = fila + 1
        
        if filas_datos:
            # Cantidad fija de filas
            df = df_raw.iloc[inicio_datos : inicio_datos + filas_datos, col : col + num_cols].copy()
        else:
            # Hasta encontrar vacío en la primera columna de la tabla
            df = df_raw.iloc[inicio_datos:, col : col + num_cols].copy()
            df = df[df.iloc[:, 0].ne("nan") & df.iloc[:, 0].ne("")]
            
        df.columns = headers
        return df
    except:
        return pd.DataFrame()

# --- APP PRINCIPAL ---

lista_pestanas = ["Resumen Anual"] + MESES[6:] + MESES[:6]
hoja_seleccionada = st.sidebar.selectbox("📅 Selecciona Período:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Carga de datos crudos
    df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
    
    # ---------------------------------------------------------
    # CASO 1: RESUMEN ANUAL
    # ---------------------------------------------------------
    if hoja_seleccionada == "Resumen Anual":
        st.header("📊 Resumen Anual")
        
        # 1. EVOLUCIÓN GASTOS (Busca en cualquier lado)
        r, c = encontrar_coordenadas(df_raw, ["Categoría", "Categoria"])
        if r is not None:
            st.subheader("📉 Evolución de Gastos")
            # Asumimos que empieza en col A (0) o donde la encuentre
            df = cortar_desde_coordenada(df_raw, r, c, num_cols=14)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        
        st.divider()
        
        # 2. SALDOS MENSUALES (Busca titulo verde -> Header está abajo)
        r, c = encontrar_coordenadas(df_raw, ["Saldos Mensuales"])
        if r is not None:
            # El header real está 1 fila mas abajo del título
            df = cortar_desde_coordenada(df_raw, r + 1, c, num_cols=14, filas_datos=1)
            st.subheader("💰 Saldos Mensuales")
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
            
        st.divider()
        
        # 3. TABLAS INFERIORES
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("🏦 Mis Ahorros")
            # Busca "Fuente" O "Ahorro" (título)
            r, c = encontrar_coordenadas(df_raw, ["Fuente", "Monto Inicial"])
            # Si no encuentra header, busca título "Ahorro" y baja 1
            if r is None:
                r_tit, c_tit = encontrar_coordenadas(df_raw, ["Ahorro"])
                if r_tit is not None: r, c = r_tit + 1, c_tit
            
            if r is not None:
                df = cortar_desde_coordenada(df_raw, r, c, num_cols=5)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)
        
        with c2:
            st.subheader("🔄 Cambio de Dólares")
            # Busca palabras clave varias
            r, c = encontrar_coordenadas(df_raw, ["Cambio de dolare", "Cambio de dolares"])
            if r is not None:
                # El header suele estar 1 fila abajo del titulo verde
                df = cortar_desde_coordenada(df_raw, r + 1, c, num_cols=13)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)

    # ---------------------------------------------------------
    # CASO 2: MESES INDIVIDUALES
    # ---------------------------------------------------------
    else:
        st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")

        # 1. BALANCE (KPIs)
        # Radar: Busca "Gastos fijos" en cualquier lugar, pero prefiriendo la derecha (min_col=4)
        r_bal, c_bal = encontrar_coordenadas(df_raw, ["Gastos fijos"], min_col=4)
        
        balance = pd.DataFrame()
        if r_bal is not None:
            # Cortamos exactamente donde lo encontró. Queremos 1 fila de datos.
            # Asumimos que son 3 columnas: Gastos fijos, Ingresos, Ahorro
            balance = cortar_desde_coordenada(df_raw, r_bal, c_bal, num_cols=3, filas_datos=1)

        # 2. GASTOS (Izquierda)
        # Radar: Busca "Vencimiento" o "Categoría" (min_col=0, es la izquierda)
        r_gastos, c_gastos = encontrar_coordenadas(df_raw, ["Vencimiento", "Categoría"])
        gastos = pd.DataFrame()
        if r_gastos is not None:
            gastos = cortar_desde_coordenada(df_raw, r_gastos, c_gastos, num_cols=5)

        # 3. INGRESOS (Derecha)
        # Radar: Busca "Fecha" o "Descripcion", pero OBLIGATORIAMENTE a la derecha (min_col=5)
        # y un poco más abajo (min_row=4) para no confundir con encabezados superiores
        r_ing, c_ing = encontrar_coordenadas(df_raw, ["Fecha", "Descripcion"], min_col=5, min_row=4)
        
        ingresos = pd.DataFrame()
        if r_ing is not None:
            ingresos = cortar_desde_coordenada(df_raw, r_ing, c_ing, num_cols=6)

        # --- VISUALIZACIÓN ---
        
        st.markdown("### 💰 Balance del Mes")
        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            try:
                # Obtenemos valores directos de la primera fila
                v1 = formato_pesos(balance.iloc[0, 0])
                v2 = formato_pesos(balance.iloc[0, 1])
                v3 = formato_pesos(balance.iloc[0, 2])
                
                c1.metric(balance.columns[0], v1)
                c2.metric(balance.columns[1], v2)
                c3.metric(balance.columns[2], v3)
            except:
                st.warning("Datos de balance encontrados pero con formato inesperado.")
        else:
            # Mensaje de depuración útil
            st.warning("⚠️ No encontré 'Gastos fijos'. Verifica que esté escrito así en el Excel.")

        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📉 Gastos")
            if not gastos.empty:
                st.dataframe(limpiar_y_formatear(gastos), hide_index=True)
            else:
                st.info("Sin gastos registrados.")
        
        with col2:
            st.subheader("📈 Ingresos")
            if not ingresos.empty:
                st.dataframe(limpiar_y_formatear(ingresos), hide_index=True)
            else:
                st.info("Sin ingresos registrados.")

except Exception as e:
    st.error("⚠️ Error crítico en la aplicación")
    st.code(str(e))
