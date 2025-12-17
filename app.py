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

# --- 3. FUNCIONES ---

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
            if "descrip" not in col.lower() and "moneda" not in col.lower() and "fuente" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
    return df

def encontrar_filas_con_meses(df_raw):
    """
    Busca todas las filas que contengan la palabra 'Enero' y 'Febrero'.
    Devuelve una lista con los índices de esas filas.
    Ejemplo: [2, 24, 37] (Fila Evolución, Fila Saldos, Fila Dólares)
    """
    filas_encontradas = []
    try:
        # Convertimos a string y buscamos
        # Iteramos solo la columna 1 a 10 para ser eficientes
        for r_idx, row in df_raw.iterrows():
            fila_texto = " ".join(row.astype(str).values).lower()
            if "enero" in fila_texto and "febrero" in fila_texto:
                filas_encontradas.append(r_idx)
    except:
        pass
    return filas_encontradas

def encontrar_coordenadas(df_raw, palabras_clave):
    """Buscador simple por contenido"""
    try:
        for r_idx, row in df_raw.iterrows():
            fila_texto = " ".join(row.astype(str).values).lower()
            for p in palabras_clave:
                if p.lower() in fila_texto:
                    # Encontramos la fila, ahora buscamos la columna exacta
                    for c_idx, val in enumerate(row):
                        if p.lower() in str(val).lower():
                            return r_idx, c_idx
        return None, None
    except:
        return None, None

def cortar_tabla(df_raw, fila, col, num_cols, filas_datos=None):
    try:
        # Headers
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        inicio_datos = fila + 1
        
        if filas_datos:
            df = df_raw.iloc[inicio_datos : inicio_datos + filas_datos, col : col + num_cols].copy()
        else:
            df = df_raw.iloc[inicio_datos:, col : col + num_cols].copy()
            # Cortamos solo si la primera columna está vacía
            df = df[df.iloc[:, 0].ne("nan") & df.iloc[:, 0].ne("")]
            
        df.columns = headers
        return df
    except:
        return pd.DataFrame()

# --- 4. APP PRINCIPAL ---

lista_pestanas = ["Resumen Anual"] + MESES[6:] + MESES[:6]
hoja_seleccionada = st.sidebar.selectbox("📅 Selecciona Período:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)
df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)

# === VISTA RESUMEN ANUAL ===
if hoja_seleccionada == "Resumen Anual":
    st.header("📊 Resumen Anual")

    # ESTRATEGIA: BUSCAR LAS FILAS QUE TIENEN "ENERO"
    filas_meses = encontrar_filas_con_meses(df_raw)
    
    # 1. EVOLUCIÓN GASTOS (Debe ser la primera aparición de "Enero")
    if len(filas_meses) > 0:
        f_evolucion = filas_meses[0]
        st.subheader("📉 Evolución de Gastos")
        # Asumimos que empieza en col 0 (A)
        df_ev = cortar_tabla(df_raw, f_evolucion, 0, 14) 
        st.dataframe(limpiar_y_formatear(df_ev), hide_index=True)
    else:
        st.warning("No encontré la tabla de Evolución (no veo 'Enero' en ninguna fila).")

    st.divider()

    # 2. SALDOS MENSUALES (Debe ser la segunda aparición de "Enero")
    if len(filas_meses) > 1:
        f_saldos = filas_meses[1]
        st.subheader("💰 Saldos Mensuales")
        # Saldos es solo 1 fila de datos
        df_sal = cortar_tabla(df_raw, f_saldos, 0, 14, filas_datos=1)
        st.dataframe(limpiar_y_formatear(df_sal), hide_index=True)

    st.divider()

    c1, c2 = st.columns([1, 2])

    # 3. MIS AHORROS (No tiene meses, buscamos "Paypal" o "Fuente")
    with c1:
        st.subheader("🏦 Mis Ahorros")
        # Buscamos "Paypal" (dato seguro)
        r_ah, c_ah = encontrar_coordenadas(df_raw, ["Paypal"])
        
        if r_ah is not None:
            # Si encontramos Paypal, el header "Fuente" está 1 fila arriba
            df_ah = cortar_tabla(df_raw, r_ah - 1, c_ah, 5)
            st.dataframe(limpiar_y_formatear(df_ah), hide_index=True)
        else:
            # Plan B: buscar "Fuente"
            r_fuente, c_fuente = encontrar_coordenadas(df_raw, ["Fuente"])
            if r_fuente is not None:
                df_ah = cortar_tabla(df_raw, r_fuente, c_fuente, 5)
                st.dataframe(limpiar_y_formatear(df_ah), hide_index=True)
            else:
                st.info("No encontré la tabla de Ahorros.")

    # 4. CAMBIO DE DÓLARES (Debe ser la tercera aparición de "Enero")
    with c2:
        st.subheader("🔄 Cambio de Dólares")
        if len(filas_meses) > 2:
            f_dolares = filas_meses[2]
            # Esta tabla empieza donde dice "Enero"
            df_dol = cortar_tabla(df_raw, f_dolares, 0, 14)
            st.dataframe(limpiar_y_formatear(df_dol), hide_index=True)
        else:
            # Si no hubo 3ra aparición, probamos buscando "Cotizacion"
            r_cot, c_cot = encontrar_coordenadas(df_raw, ["Cotizacion", "Dolares"])
            if r_cot is not None:
                 # Si encontramos el dato, subimos filas para pillar el header
                 # (Aproximación: 2 filas arriba suele estar el header)
                 df_dol = cortar_tabla(df_raw, r_cot - 2, 0, 14)
                 st.dataframe(limpiar_y_formatear(df_dol), hide_index=True)
            else:
                 st.info("No encontré la tabla de Cambio.")

# === VISTA MESES ===
else:
    st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")
    
    # KPIs
    r_bal, c_bal = encontrar_coordenadas(df_raw, ["Gastos fijos"])
    balance = pd.DataFrame()
    if r_bal is not None:
        # A veces lo encuentra en col I (8), a veces J... cortamos 3 cols
        balance = cortar_tabla(df_raw, r_bal, c_bal, 3, filas_datos=1)

    # Gastos
    r_gas, c_gas = encontrar_coordenadas(df_raw, ["Vencimiento", "Categoría"])
    gastos = pd.DataFrame()
    if r_gas is not None:
        gastos = cortar_tabla(df_raw, r_gas, c_gas, 5)

    # Ingresos (Buscamos "Fecha" pero a la derecha para no confundir con gastos)
    # Hacemos un recorte virtual para buscar
    r_ing = None
    try:
        sub_df = df_raw.iloc[4:, 5:] # Desde fila 4, columna F en adelante
        r_sub, c_sub = encontrar_coordenadas(sub_df, ["Fecha", "Descripcion"])
        if r_sub is not None:
            r_ing = r_sub + 4 # Ajustamos indice
            c_ing = c_sub + 5
    except: pass
    
    ingresos = pd.DataFrame()
    if r_ing is not None:
        ingresos = cortar_tabla(df_raw, r_ing, c_ing, 6)

    # Visualización Mes
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
        except: st.warning("Formato balance inesperado")
    else: st.warning("No encontrado")

    st.divider()
    c1, c2 = st.columns(2)
    with c1: 
        st.subheader("📉 Gastos")
        if not gastos.empty: st.dataframe(limpiar_y_formatear(gastos), hide_index=True)
    with c2: 
        st.subheader("📈 Ingresos")
        if not ingresos.empty: st.dataframe(limpiar_y_formatear(ingresos), hide_index=True)
