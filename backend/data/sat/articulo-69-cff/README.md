# Artículo 69 CFF — Contribuyentes Incumplidos

**Fuente oficial:** Portal Datos Abiertos del SAT
**URL:** https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html
**Carpetas:** `Documents_AGR/` (contribuyentes incumplidos), `Cifras_SAT/` (cifras complementarias)

Este directorio contiene los listados de contribuyentes incumplidos del
Artículo 69 del Código Fiscal de la Federación (CFF). Incluye tanto los
archivos por subcategoría (`contribuyentes-incumplidos/`) como las cifras
complementarias (`cifras/`).

## Subcarpetas

### `contribuyentes-incumplidos/` — Listas por categoría de incumplimiento

| Archivo                  | Descripción                              | Registros | Actualizado a     |
|--------------------------|------------------------------------------|-----------|-------------------|
| `Cancelados.csv`         | Créditos cancelados                      | 183,664   | Mayo 2026         |
| `Firmes.csv`             | Créditos firmes                          | 258,256   | Mayo 2026         |
| `Exigibles.csv`          | Créditos exigibles                       | 5,873     | Mayo 2026         |
| `No_localizados.csv`     | Contribuyentes no localizados            | 53,390    | Mayo 2026         |
| `Sentencias.csv`         | Créditos con sentencia                   | 610       | Mayo 2026         |
| `CSDsinefectos.csv`      | CSD sin efectos (Fracción X)             | 58,195    | Mayo 2026         |
| `EntespublicosydeGobiernoomisos.csv` | Entes públicos omisos (Fracción VII) | 3,910     | Mayo 2026         |

### `cifras/` — Cifras complementarias

Cifras estadísticas sobre condonaciones, cancelaciones y reducciones.
No son listas de contribuyentes individuales — no se importan para el scoring.

## Columnas comunes

Los archivos CSV comparten estas columnas (orden y nombre exacto varían por archivo):
- **RFC**: Registro Federal de Contribuyentes
- **RAZÓN SOCIAL** / **RAZON SOCIAL**: Nombre o razón social del contribuyente
- **TIPO PERSONA**: M (Moral) o F (Física)
- **SUPUESTO**: Categoría de incumplimiento (Cancelados, Firmes, Exigibles, etc.)
- **FECHA DE PUBLICACIÓN** / **FECHA DE PRIMERA PUBLICACION**: Fecha de publicación en DOF
- **ENTIDAD FEDERATIVA**: Estado del domicilio fiscal

## Scoring

En el motor de scoring, estos registros se evalúan con `list_type="art_69"`
y otorgan **25 puntos** cada uno (factor `sat_69_incumplido`).
No hay `art69b_substate` para Art. 69 — la presencia en cualquier subcategoría
es suficiente para aplicar el puntaje.

Excepción: Si el contribuyente solo aparece con `fraccion="VI"`, no se aplica
el puntaje (Regla 1.4.14 RGCE 2026).
