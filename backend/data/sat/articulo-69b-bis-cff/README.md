# Artículo 69-B Bis CFF — Transmisión Indebida de Pérdidas Fiscales

**Fuente oficial:** Portal Datos Abiertos del SAT
**URL:** https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html
**Carpeta:** `Documents_AGGC/`

Este directorio contiene los listados de contribuyentes del Artículo 69-B Bis
del CFF, relativos a la transmisión indebida de pérdidas fiscales.

## Archivos

| Archivo                                    | Descripción                                    | Registros | Actualizado a  |
|--------------------------------------------|------------------------------------------------|-----------|----------------|
| `Listado_69_B_Bis_Completo.csv`            | Listado completo (todos los sub-estados)       | 3         | Marzo 2026     |
| `Listado_69_B_Bis_Definitivo.csv`          | Contribuyentes definitivos                     | 2         | Marzo 2026     |
| `Listado_69_B_Bis_SentenciaFa.csv`         | Sentencia favorable                            | 1         | Marzo 2026     |

## Columnas

Misma estructura que Art. 69-B:
- **No.**: Número consecutivo
- **RFC**: Registro Federal de Contribuyentes
- **Nombre del Contribuyente**: Razón social
- **Situación del contribuyente**: Definitivo / Sentencia Favorable

## Scoring

En el motor de scoring, cualquier presencia en el listado 69-B Bis otorga
**35 puntos** (factor `sat_69b_bis`), independientemente del sub-estado.
