import pandas as pd
import numpy as np
import logging
import os
import re
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("pipeline.log", mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

RAW_PATH    = "data/raw/mascotas.csv"
OUTPUT_PATH = "data/processed/mascotas_clean.csv"


def cargar_datos(ruta: str) -> pd.DataFrame:
    logger.info("INICIO PIPELINE")
    logger.info(f"Leyendo archivo: {ruta}")

    df = pd.read_csv(ruta)
    return df


def detectar_duplicados(df: pd.DataFrame) -> None:
    logger.info("Duplicados")

    dup_exactos = df.duplicated().sum()
    dup_id = df.duplicated(subset=["id_mascota"]).sum()

    logger.info(f"  Filas duplicadas : {dup_exactos}")
    logger.info(f"  id_mascota duplicados          : {dup_id}")



def detectar_nulos(df: pd.DataFrame) -> None:
    logger.info("Valores nulos por columna:")
    nulos = df.isnull().sum()
    for col, n in nulos.items():
        if n > 0:
            logger.info(f"  {col:<20}: {n} nulos")


def detectar_outliers(df: pd.DataFrame) -> None:
    logger.info("outliers ne la columna  peso_kg:")

    imposibles = df[(df["peso_kg"] > 500) | (df["edad_años"] < 0)]
    logger.info(f"  Valores imposibles (peso>500 o edad<0) : {len(imposibles)}")


def detectar_fechas_malformadas(df: pd.DataFrame) -> None:
    logger.info("Fechas malformadas en fecha_consulta:")
    patron_iso = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    malformadas = df[
        df["fecha_consulta"].notna() &
        ~df["fecha_consulta"].astype(str).str.match(patron_iso)
    ]
    logger.info(f"  Fechas no ISO encontradas: {len(malformadas)}")
    for _, row in malformadas.iterrows():
        logger.info(f"    id={row['id_mascota']} | fecha='{row['fecha_consulta']}'")



def eliminar_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Eliminando duplicado")
    antes = len(df)
    df = df.drop_duplicates()
    despues = len(df)
    logger.info(f"  Filas antes  : {antes}")
    logger.info(f"  Filas después: {despues}")
    logger.info(f"  Eliminadas   : {antes - despues}")
    return df


def eliminar_filas_vacias(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Eliminando filas completamente vacías")
    columnas = ["nombre", "especie", "raza", "fecha_consulta", "dueño_nombre"]
    antes = len(df)
    df = df.dropna(subset=columnas, how="all")
    despues = len(df)
    logger.info(f"  Eliminadas: {antes - despues}")
    return df


def corregir_fechas(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("corregir fechas malformadas")

    def parsear_fecha(valor):
        if pd.isna(valor) or valor == "":
            return pd.NaT
        valor = str(valor).strip()
        if re.match(r"^\d{8}$", valor):
            return pd.to_datetime(valor, format="%Y%m%d", errors="coerce")
        if re.match(r"^\d{2}/\d{2}/\d{4}$", valor):
            return pd.to_datetime(valor, format="%d/%m/%Y", errors="coerce")
        return pd.to_datetime(valor, format="%Y-%m-%d", errors="coerce")

    df["fecha_consulta"] = df["fecha_consulta"].apply(parsear_fecha)
    invalidas = df["fecha_consulta"].isnull().sum()
    logger.info(f"  Fechas no parseables (NaT): {invalidas}")
    return df

def corregir_edad_negativa(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Corrigiendo edades negativas")
    mask = df["edad_años"] < 0
    n = mask.sum()
    df.loc[mask, "edad_años"] = np.nan
    for especie in df["especie"].unique():
        mediana = df.loc[df["especie"] == especie, "edad_años"].median()
        mask2 = (df["especie"] == especie) & df["edad_años"].isnull()
        df.loc[mask2, "edad_años"] = mediana
    logger.info(f"  Edades negativas corregidas vía mediana: {n}")
    return df


def transformar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("extrayendo mes y año de fecha_consulta")
    df["mes_consulta"] = df["fecha_consulta"].dt.month
    df["año_consulta"] = df["fecha_consulta"].dt.year
    logger.info(f"  Rango de fechas: {df['fecha_consulta'].min()} → {df['fecha_consulta'].max()}")
    return df


def calcular_años_cliente(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Calculando años_cliente")

    primera_visita = (
        df.dropna(subset=["dueño_email", "fecha_consulta"])
        .groupby("dueño_email")["fecha_consulta"]
        .min()
        .rename("primera_visita")
    )
    df = df.merge(primera_visita, on="dueño_email", how="left")
    fecha_ref = df["fecha_consulta"].max()
    df["años_cliente"] = ((fecha_ref - df["primera_visita"]).dt.days / 365.25).round(2)
    df.drop(columns=["primera_visita"], inplace=True)
    logger.info(f"  Fecha de referencia usada: {fecha_ref.date()}")
    return df


def codificar_especie(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Codificando especie")
    dummies = pd.get_dummies(df["especie"], prefix="especie", dtype=int)
    df = pd.concat([df, dummies], axis=1)
    logger.info(f"  Columnas  creadas: {list(dummies.columns)}")
    return df

def exportar_datos(df: pd.DataFrame, ruta: str) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    logger.info(f"Dataset limpio guardado en: {ruta}")
    logger.info(f"  Shape final: {df.shape}")
    logger.info(f"  Columnas   : {list(df.columns)}")


def reporte_final(df_original: pd.DataFrame, df_clean: pd.DataFrame) -> None:
    logger.info("*" * 55)
    logger.info("REPORTE FINAL – RESUMEN COMPARATIVO")
    logger.info(f"  Filas originales  : {len(df_original)}")
    logger.info(f"  Filas finales     : {len(df_clean)}")
    logger.info(f"  Columnas originales: {df_original.shape[1]}")
    logger.info(f"  Columnas finales   : {df_clean.shape[1]}")
    logger.info(f"  Nulos restantes    : {df_clean.isnull().sum().sum()}")

    logger.info("FIN PIPELINE")
    logger.info("*" * 55)



def ejecutar_pipeline():

    df_original = cargar_datos(RAW_PATH)
    df = df_original.copy()

    
    detectar_duplicados(df)
    detectar_nulos(df)
    detectar_outliers(df)
    detectar_fechas_malformadas(df)

   
    df = eliminar_duplicados(df)
    df = eliminar_filas_vacias(df)
    df = corregir_fechas(df)        
    df = corregir_edad_negativa(df)

   
   

    df = transformar_fechas(df)
    df = calcular_años_cliente(df)
    df = codificar_especie(df)

  
    exportar_datos(df, OUTPUT_PATH)
    reporte_final(df_original, df)

    return df


if __name__ == "__main__":
    df_clean = ejecutar_pipeline()
    print("\n pipeline listo. Dataset limpio disponible en:", OUTPUT_PATH)
