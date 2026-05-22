# Pipeline de Datos – Clínica Veterinaria 

## Estructura del Proyecto

```
pipeline_mascotas/
├── data/
│   ├── raw/
│   │   └── mascotas.csv         
│   └── processed/
│       └── mascotas_clean.csv   
├── pipeline.py                  
├── pipeline.log                  
└── README.md                     
```

---

## Cómo ejecutar

```bash
pip install pandas numpy

python3 pipeline.py
```

El script genera automáticamente:
- `data/processed/mascotas_clean.csv`
- `pipeline.log` con el registro completo de cada paso


## Decisiones Técnicas

### 1. Duplicados

**Decisión:** Se aplica `drop_duplicates()` para duplicados exactos y se elimina la fila totalmente vacía (id=6).

**Justificación:** Los registros id=1 (Firulais) e id=2 (FIRULAIS) no son duplicados exactos (difieren en capitalización). Se asume que son dos visitas del mismo animal con datos de ingreso distintos (error de digitación en el id). Se conservan ambos pero la especie/nombre queda estandarizada en pasos posteriores. Una clínica real necesitaría resolución manual de este caso.

---

### 2. Imputación de `edad_años`

**Decisión:** Se imputa con la **mediana por especie**.

**Justificación:** 
- La media es sensible a outliers (un perro de 15 años inflaría el promedio).
- La mediana es más representativa de la distribución real.
- Imputar por especie es más preciso que imputar globalmente, ya que gatos y perros tienen distribuciones de edad diferentes.
- Alternativa descartada: eliminación de filas → perdería el 20% del dataset.

---

### 3. Corrección de Fechas

**Decisión:** Se detectan y normalizan 3 formatos a `datetime`:
- `YYYY-MM-DD` → formato ISO estándar (ya correcto)
- `DD/MM/YYYY` → re-parseado con `format="%d/%m/%Y"`
- `YYYYMMDD` → re-parseado con `format="%Y%m%d"`

**Justificación:** pandas `to_datetime` con `infer_datetime_format` puede producir errores silenciosos al mezclar formatos (especialmente confundiendo DD/MM vs MM/DD). Se prefiere parseo explícito por patrón regex para máxima confiabilidad.

---

### 4. Estandarización de `especie`

**Decisión:** Se mapean 13 variantes a 5 categorías canónicas: `perro`, `gato`, `pez`, `loro`, `otro`.

**Mapa aplicado:**
```
perro / Perro / PERRO / perra / PERRA → perro
gato  / GATO  / gata  / GATA         → gato
Cat   / cat                           → gato
pez                                   → pez
Loro  / loro                          → loro
NaN   / desconocido                   → otro
```

**Justificación:** Se unifica género (gata→gato, perra→perro) porque en análisis epidemiológico veterinario la especie es la variable relevante; el sexo se maneja por otra columna si fuera necesario. "Cat" en inglés se mapea a "gato" (clínica hispanohablante, fue error de ingreso).

---


### 6. Creación de `rango_peso`

**Decisión:** Clasificación con umbrales fijos por especie (bajo / normal / alto / obeso).

**Justificación:** Los umbrales porcentuales (IQR) son dinámicos y cambiarían con cada ejecución. Los umbrales fijos basados en referencias veterinarias son reproducibles y clínicamente interpretables. Se definen por especie porque un peso "normal" para un perro es muy diferente al de un gato.

---

### 7. Codificación de `especie` con `get_dummies`

**Decisión:** Se aplica `pd.get_dummies(df["especie"], prefix="especie")` y se conserva también la columna original.

**Justificación:** La codificación one-hot es necesaria para algoritmos de ML que no aceptan variables categóricas de texto. Se conserva la columna original para mantener legibilidad humana del dataset. No se aplica `drop_first=True` en esta etapa (decisión que corresponde al modelado, no a la limpieza).

---

### 8. Cálculo de `años_cliente`

**Decisión:** Se calcula como la diferencia entre la fecha de consulta máxima del dataset y la primera visita de cada dueño (agrupado por email).

**Justificación:** El email es el identificador más estable del dueño. La fecha máxima del dataset se usa como "hoy" para reproducibilidad (si se usara `datetime.now()`, el resultado cambiaría cada ejecución).

---

### 9. Logging y Trazabilidad

**Decisión:** Se usa el módulo estándar `logging` de Python con dos handlers: consola y archivo `pipeline.log`.

**Justificación:** El logging permite auditar cada transformación con timestamp, incluyendo conteos antes/después de cada paso. Esto es fundamental para validar que el pipeline funciona correctamente y para detectar regresiones si el dataset cambia.

---

## Resumen de Resultados

| Métrica | Antes | Después |
|---|---|---|
| Filas | 50 | 49 |
| Columnas | 11 | 20 |
| Nulos en edad_años | 10 | 2* |
| Nulos en peso_kg | 1 | 0 |
| Variantes de especie | 13 | 5 |
| Formatos de fecha | 3 | 1 (datetime) |


"# Limpieza-y-Transformaci-n-del-Dataset" 
