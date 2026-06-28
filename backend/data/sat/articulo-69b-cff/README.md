# Artículo 69-B CFF — EFOS (Empresas que Facturan Operaciones Simuladas)

**Fuente oficial:** Portal Datos Abiertos del SAT
**URL:** https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html
**Carpeta:** `Documents_AGAFF/`

Este directorio contiene los listados de contribuyentes del Artículo 69-B
del CFF (EFOS — Empresas que Facturan Operaciones Simuladas), también
conocidos como "listados de operaciones presuntamente inexistentes".

## Archivos

| Archivo                           | Descripción                                        | Registros | Actualizado a |
|-----------------------------------|----------------------------------------------------|-----------|---------------|
| `Definitivos.csv`                 | Contribuyentes definitivos (art69b_substate=definitivo) | 11,771 | Mayo 2026 |
| `Presuntos.csv`                   | Contribuyentes presuntos (art69b_substate=presunto)     | 754    | Mayo 2026 |
| `Desvirtuados.csv`                | Contribuyentes que desvirtuaron (art69b_substate=desvirtuado) | 340 | Mayo 2026 |
| `SentenciasFavorables.csv`        | Sentencia favorable (art69b_substate=sentencia_favorable) | 1,658 | Mayo 2026 |
| `Listado_completo_69-B.csv`       | Listado completo (todos los sub-estados)           | 14,523 | Mayo 2026 |

## Columnas

- **No.**: Número consecutivo
- **RFC**: Registro Federal de Contribuyentes
- **Nombre del Contribuyente**: Razón social
- **Situación del contribuyente**: Definitivo / Presunto / Desvirtuado / Sentencia Favorable
- **Número y fecha de oficio global**: Referencia del oficio SAT/DOF para cada etapa
- **Publicación página SAT/DOF**: Fechas de publicación

## Scoring

En el motor de scoring:
- `art69b_substate="definitivo"` → **100 puntos** (CRITICAL BLOCK, factor `sat_69b_definitivo`)
- `art69b_substate="presunto"` → **40 puntos** (factor `sat_69b_presunto`)
- `art69b_substate="desvirtuado"` → **0 puntos** (no penaliza)
- `art69b_substate="sentencia_favorable"` → **0 puntos** (no penaliza)
