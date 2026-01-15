import streamlit as st
import pandas as pd
import os
import io

st.set_page_config(page_title="Validador Logístico", layout="wide")

# --- CONFIGURACIÓN DE RUTAS ---
PATH_MAESTRO = "data/maestro.csv" 

st.title("🚚 Validador de Planning")

if not os.path.exists(PATH_MAESTRO):
    st.error(f"⚠️ No se encontró el archivo maestro en: {PATH_MAESTRO}")
    st.stop()

# --- CARGA DEL PLANNING DIARIO ---
st.subheader("1. Subir Planning diario de Tráfico")
file_planning = st.file_uploader("Arrastra aquí el Excel de Tráfico", type=['xlsx', 'csv'])

def obtener_letra_dia(fecha):
    mapa = {0: 'L', 1: 'M', 2: 'X', 3: 'J', 4: 'V', 5: 'S', 6: 'D'}
    return mapa[fecha.weekday()]

if file_planning:
    try:
        # Cargar Maestro (con motor robusto)
        df_maestro = pd.read_csv(PATH_MAESTRO, sep=None, engine='python', encoding='latin-1')
        
        # Cargar Planning (Excel o CSV con detección automática)
        if file_planning.name.endswith(('xlsx', 'xls')):
            df_planning = pd.read_excel(file_planning)
        else:
            # Aquí está el truco: sep=None hace que Python adivine si es coma o punto y coma
            df_planning = pd.read_csv(file_planning, sep=None, engine='python', encoding='latin-1')

        # --- PROCESAMIENTO ---
        # Aseguramos nombres de columnas (limpieza de espacios)
        df_maestro.columns = df_maestro.columns.str.strip()
        df_planning.columns = df_planning.columns.str.strip()

        # Renombrar columnas clave
        df_maestro = df_maestro.rename(columns={'Pto Op': 'ID_Tienda', 'CALENDARIZADO': 'Frecuencia'})
        
        # Convertir Fecha a objeto fecha real
        df_planning['Fecha_Entrega'] = pd.to_datetime(df_planning['FECHA'], errors='coerce')
        df_planning['Dia_Semana'] = df_planning['Fecha_Entrega'].apply(obtener_letra_dia)
        
        # Convertir IDs a números limpios
        df_planning['ID_Tienda'] = pd.to_numeric(df_planning['TIENDA'], errors='coerce').fillna(0).astype(int)
        df_maestro['ID_Tienda'] = pd.to_numeric(df_maestro['ID_Tienda'], errors='coerce').fillna(0).astype(int)

        # Cruce
        df_final = pd.merge(df_planning, df_maestro[['ID_Tienda', 'Frecuencia']], on='ID_Tienda', how='left')

        # Validación
        def validar(row):
            if pd.isna(row['Frecuencia']) or row['Frecuencia'] == "": return "⚠️ No en Maestro"
            return "✅ OK" if str(row['Dia_Semana']) in str(row['Frecuencia']) else "❌ No Reparte"

        df_final['Estado'] = df_final.apply(validar, axis=1)

        # --- VISUALIZACIÓN ---
        solo_errores = st.checkbox("Mostrar solo errores")
        df_resultado = df_final if not solo_errores else df_final[df_final['Estado'] != "✅ OK"]
        
        # Estilo visual
        st.dataframe(df_resultado.style.applymap(
            lambda v: 'background-color: #ffcccc' if '❌' in str(v) else ('background-color: #fff4cc' if '⚠️' in str(v) else ''),
            subset=['Estado']
        ), use_container_width=True)

        # --- BOTÓN DE DESCARGA ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Descargar Reporte",
            data=output.getvalue(),
            file_name="Resultado_Validacion.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.info("💡 Consejo: Asegúrate de que el archivo no esté abierto en Excel mientras lo subes.")