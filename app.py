import streamlit as st
import pandas as pd
import os
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Validador CDMA", layout="wide")
PATH_MAESTRO = "data/maestro.csv"

def obtener_letra(fecha):
    if pd.isna(fecha): return "?"
    mapa = {0: 'L', 1: 'M', 2: 'X', 3: 'J', 4: 'V', 5: 'S', 6: 'D'}
    return mapa[fecha.weekday()]

# --- PANEL ADMIN (CLAVE: CDMA26) ---
with st.sidebar.expander("🔐 Editar Maestro"):
    clave = st.text_input("Clave", type="password")
    if clave == "CDMA26":
        if os.path.exists(PATH_MAESTRO):
            df_m = pd.read_csv(PATH_MAESTRO, sep=';', encoding='latin-1')
            id_t = st.number_input("ID Tienda (Pto Op)", min_value=0, step=1)
            if id_t in df_m['Pto Op'].values:
                idx = df_m[df_m['Pto Op'] == id_t].index[0]
                st.write(f"Tienda: {df_m.at[idx, 'Tienda']}")
                nuevo_val = st.text_input("Nuevo Día de Entrega", value=str(df_m.at[idx, 'DIA DE ENTREGA']))
                if st.button("Guardar"):
                    df_m.at[idx, 'DIA DE ENTREGA'] = nuevo_val
                    df_m.to_csv(PATH_MAESTRO, sep=';', index=False, encoding='latin-1')
                    st.success("Actualizado")
    elif clave: st.error("Incorrecta")

# --- FLUJO PRINCIPAL ---
st.title("🚚 Control de Entrega por Día")

if not os.path.exists(PATH_MAESTRO):
    st.error("No se encuentra data/maestro.csv")
    st.stop()

archivo = st.file_uploader("Subir Planning", type=['xlsx', 'csv'])

if archivo:
    try:
        # 1. Cargar Maestro y Planning
        df_maestro = pd.read_csv(PATH_MAESTRO, sep=';', encoding='latin-1')
        if archivo.name.endswith(('xlsx', 'xls')):
            df_plan = pd.read_excel(archivo)
        else:
            df_plan = pd.read_csv(archivo, sep=None, engine='python', encoding='latin-1')
        
        # 2. Procesar Fecha del Planning
        df_plan['FECHA_DT'] = pd.to_datetime(df_plan['FECHA'], errors='coerce')
        letra_dia = obtener_letra(df_plan['FECHA_DT'].iloc[0])
        
        # 3. Cruzar datos
        df_res = pd.merge(df_plan, df_maestro[['Pto Op', 'Tienda', 'DIA DE ENTREGA']], 
                          left_on='TIENDA', right_on='Pto Op', how='left')

        # 4. Validar
        def validar(row):
            if pd.isna(row['DIA DE ENTREGA']): return "No corresponde"
            # Limpiar el texto del maestro (quitar espacios y comas)
            m_ent = str(row['DIA DE ENTREGA']).upper().replace(" ", "").replace(",", "")
            return "Corresponde" if letra_dia in m_ent else "No corresponde"

        df_res['RESULTADO'] = df_res.apply(validar, axis=1)

        # 5. Mostrar
        st.subheader(f"Validando para el día: {letra_dia}")
        
        def color_val(val):
            color = '#c6efce' if val == "Corresponde" else '#ffc7ce'
            text = '#006100' if val == "Corresponde" else '#9c0006'
            return f'background-color: {color}; color: {text}; font-weight: bold'

        cols = ['RESULTADO', 'TIENDA', 'NOMBRE_TIENDA', 'DIA DE ENTREGA']
        st.dataframe(df_res[cols].style.applymap(color_val, subset=['RESULTADO']), use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")