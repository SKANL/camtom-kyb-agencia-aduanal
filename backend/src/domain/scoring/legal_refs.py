LEGAL_REFS: dict[str, dict] = {
    "sat_69b_definitivo": {
        "ref": "Art. 69-B CFF — Listado definitivo de EFOS (Empresas que Facturan Operaciones Simuladas). Operar con un EFOS definitivo invalida los CFDIs emitidos y genera responsabilidad solidaria.",
        "category": "sat",
    },
    "sat_69b_presunto": {
        "ref": "Art. 69-B CFF — Listado presunto EFOS, pendiente de resolución SAT. El contribuyente puede desvirtuar ante el SAT en el plazo legal.",
        "category": "sat",
    },
    "sat_69b_bis": {
        "ref": "Art. 69-B Bis CFF — Transmisión indebida de pérdidas fiscales. El SAT puede rechazar las pérdidas transmitidas y aplicar recargos.",
        "category": "sat",
    },
    "sat_69_incumplido": {
        "ref": "Art. 69 CFF — Contribuyente con obligaciones fiscales incumplidas (créditos firmes, exigibles, CSD sin efectos, no localizados o con sentencia).",
        "category": "sat",
    },
    "rfc_formato_invalido": {
        "ref": "Art. 27 CFF y Resolución Miscelánea Fiscal — El RFC debe cumplir la estructura oficial (3-4 letras + 6 dígitos fecha + 3 homoclave) con dígito verificador válido.",
        "category": "sat",
    },
    "art_49bis_no_verificable": {
        "ref": "Art. 49 Bis CFF (Contrabando técnico) — No existe listado público consultable. Se requiere declaración bajo protesta del contribuyente y revisión manual por el agente aduanal.",
        "category": "sat",
    },
    "disc_rfc": {
        "ref": "Regla 1.4.14 RGCE 2026 — El RFC es el identificador fiscal vinculante. La discrepancia entre documentos indica posible suplantación o error en el expediente.",
        "category": "discrepancia",
    },
    "disc_razon_social": {
        "ref": "Regla 1.4.14 RGCE 2026 — La razón social debe coincidir de forma material en todos los documentos del expediente. Variaciones menores (abreviaturas societarias) son causa de revisión.",
        "category": "discrepancia",
    },
    "disc_domicilio": {
        "ref": "Regla 1.4.14 RGCE 2026 — El domicilio fiscal declarado debe ser consistente entre la CSF, comprobante de domicilio y demás documentos del expediente.",
        "category": "discrepancia",
    },
    "disc_representante": {
        "ref": "Regla 1.4.14 RGCE 2026 — El nombre del representante legal debe coincidir entre el poder notarial, la identificación oficial y el encargo conferido.",
        "category": "discrepancia",
    },
    "disc_fechas": {
        "ref": "Regla 1.4.14 RGCE 2026 — Las fechas de emisión, vigencia y vencimiento de los documentos deben ser congruentes entre sí y con el período evaluado.",
        "category": "discrepancia",
    },
    "doc_missing": {
        "ref": "Regla 1.4.14 RGCE 2026 — La documentación completa es requisito para inscribirse y operar en el Padrón de Importadores/Exportadores.",
        "category": "completitud",
    },
    "doc_expired": {
        "ref": "Regla 1.4.14 RGCE 2026 — El comprobante de domicilio tiene vigencia máxima de 90 días naturales a partir de su fecha de emisión.",
        "category": "completitud",
    },
    "csf_stale": {
        "ref": "SAT / Regla 1.4.14 RGCE 2026 — La Constancia de Situación Fiscal debe corresponder al mes calendario en curso para acreditar la situación fiscal vigente.",
        "category": "completitud",
    },
    "doc_data_incomplete": {
        "ref": "Regla 1.4.14 RGCE 2026 — Todos los campos obligatorios del documento deben estar capturados y verificados para que el expediente sea evaluable.",
        "category": "completitud",
    },
    "manifestacion_incompleta": {
        "ref": "Regla 1.4.14 RGCE 2026 — La Manifestación bajo Protesta de Decir Verdad debe incluir la cláusula explícita de no encontrarse en los listados del Art. 69-B y Art. 49 Bis CFF.",
        "category": "completitud",
    },
    "socios_incompletos": {
        "ref": "Regla 1.4.14 RGCE 2026 y LFPIORPI — Se requiere identificar a todos los socios, accionistas y beneficiario controlador del acta constitutiva para cumplir con los controles antilavado.",
        "category": "completitud",
    },
    "rep_legal_incompleto": {
        "ref": "Regla 1.4.14 RGCE 2026 — El nombre completo del representante legal debe capturarse desde la identificación oficial para vincularlo con el poder notarial y el encargo conferido.",
        "category": "completitud",
    },
}
