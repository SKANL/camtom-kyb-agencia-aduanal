# Datos SAT — Portal Datos Abiertos

Este directorio contiene los archivos CSV descargados del
[Portal Datos Abiertos del SAT](https://www.sat.gob.mx/minisitio/DatosAbiertos/)
con las listas públicas de contribuyentes para los Artículos 69, 69-B y 69-B Bis del CFF.

## Estructura

```
data/sat/
├── articulo-69-cff/            ← Contribuyentes incumplidos (Art. 69 CFF)
│   ├── README.md
│   ├── contribuyentes-incumplidos/   ← 7 sub-archivos por categoría
│   └── cifras/                       ← Cifras complementarias (condonaciones, etc.)
├── articulo-69b-cff/           ← EFOS (Art. 69-B CFF) — 5 archivos
│   └── README.md
└── articulo-69b-bis-cff/       ← Pérdidas fiscales indebidas (Art. 69-B Bis CFF)
    └── README.md
```

## Uso

Para importar todos los datos a Supabase:

```bash
cd backend
uv run python scripts/import_sat_data.py
```

## Actualización de datos

Los datos del SAT se actualizan periódicamente (fechas indicadas en cada archivo).
Para actualizar:
1. Descargar los archivos actualizados del portal Datos Abiertos
2. Reemplazar los archivos en las carpetas correspondientes
3. Re-ejecutar `scripts/import_sat_data.py`

## Fecha de descarga

**28 de junio de 2026**
