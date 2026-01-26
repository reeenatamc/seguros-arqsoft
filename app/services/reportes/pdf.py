"""

Servicio de generación de reportes PDF con diseño editorial profesional e institucional.

Estilo minimalista, sobrio y atemporal, priorizando claridad y legibilidad.

"""

import io
from datetime import datetime
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch, mm
from reportlab.platypus import (
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# =============================================================================

# PALETA DE COLORES EDITORIAL

# =============================================================================


class Colors:
    """Paleta limitada y profesional para documentos institucionales."""

    # Neutros principales

    BLACK = colors.HexColor("#000000")

    GRAY_900 = colors.HexColor("#1a1a1a")  # Texto principal

    GRAY_700 = colors.HexColor("#4a4a4a")  # Texto secundario

    GRAY_500 = colors.HexColor("#6b6b6b")  # Texto terciario

    GRAY_300 = colors.HexColor("#d1d1d1")  # Bordes ligeros

    GRAY_100 = colors.HexColor("#f5f5f5")  # Fondos sutiles

    WHITE = colors.HexColor("#ffffff")

    # Acentos mínimos (solo para jerarquía, no decoración)

    ACCENT = colors.HexColor("#2c3e50")  # Azul oscuro institucional

    ACCENT_LIGHT = colors.HexColor("#ecf0f1")  # Fondo muy sutil

    # Para gráficos (colores suaves y profesionales)

    CHART = [
        colors.HexColor("#34495e"),  # Gris azulado oscuro
        colors.HexColor("#7f8c8d"),  # Gris medio
        colors.HexColor("#95a5a6"),  # Gris claro
        colors.HexColor("#bdc3c7"),  # Gris muy claro
        colors.HexColor("#2c3e50"),  # Azul oscuro
        colors.HexColor("#34495e"),  # Gris azulado
    ]


# =============================================================================

# SERVICIO PRINCIPAL

# =============================================================================


class PDFReportesService:
    """Generador de reportes PDF con diseño editorial profesional."""

    PAGE_SIZE = A4  # A4 es más estándar para documentos institucionales

    MARGIN = 2 * cm  # Márgenes amplios (2cm = ~0.79 inch)

    WIDTH = PAGE_SIZE[0] - 2 * MARGIN

    @classmethod
    def _styles(cls):
        """Estilos tipográficos editoriales - una sola familia, jerarquía clara."""

        s = getSampleStyleSheet()

        # Título principal

        s.add(
            ParagraphStyle(
                "RptMainTitle",
                fontName="Helvetica-Bold",
                fontSize=20,  # Tamaño equilibrado
                textColor=Colors.GRAY_900,
                alignment=TA_LEFT,  # Alineación izquierda
                spaceAfter=8,
                leading=24,
            )
        )

        # Subtítulo

        s.add(
            ParagraphStyle(
                "RptSubtitle",
                fontName="Helvetica",
                fontSize=10,
                textColor=Colors.GRAY_500,
                alignment=TA_LEFT,
                spaceAfter=30,  # Espacio generoso
                leading=14,
            )
        )

        # Título de sección

        s.add(
            ParagraphStyle(
                "RptSection",
                fontName="Helvetica-Bold",
                fontSize=13,
                textColor=Colors.GRAY_900,
                spaceBefore=35,  # Espaciado amplio entre secciones
                spaceAfter=15,
                leading=16,
            )
        )

        # Subtítulo de sección

        s.add(
            ParagraphStyle(
                "RptSubSection",
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=Colors.GRAY_700,
                spaceBefore=25,
                spaceAfter=10,
                leading=14,
            )
        )

        # Texto de cuerpo

        s.add(
            ParagraphStyle(
                "RptBody",
                fontName="Helvetica",
                fontSize=10,
                textColor=Colors.GRAY_700,
                spaceAfter=12,  # Interlineado cómodo
                leading=14,  # 1.4x el tamaño de fuente
                alignment=TA_LEFT,
            )
        )

        # Texto destacado

        s.add(
            ParagraphStyle(
                "RptHighlight",
                fontName="Helvetica-Bold",
                fontSize=10,
                textColor=Colors.GRAY_900,
                spaceAfter=8,
                leading=14,
            )
        )

        # Valores KPI

        s.add(
            ParagraphStyle(
                "RptKPIValue",
                fontName="Helvetica-Bold",
                fontSize=18,  # Tamaño moderado
                textColor=Colors.GRAY_900,
                alignment=TA_CENTER,
                leading=22,
            )
        )

        # Etiquetas KPI

        s.add(
            ParagraphStyle(
                "RptKPILabel",
                fontName="Helvetica",
                fontSize=9,
                textColor=Colors.GRAY_500,
                alignment=TA_CENTER,
                leading=12,
            )
        )

        # Pie de página

        s.add(
            ParagraphStyle(
                "RptFooter",
                fontName="Helvetica",
                fontSize=8,
                textColor=Colors.GRAY_500,
                alignment=TA_CENTER,
                leading=10,
            )
        )

        # Celdas de tabla - texto

        s.add(ParagraphStyle("RptCell", fontName="Helvetica", fontSize=9, textColor=Colors.GRAY_700, leading=12))

        # Celdas de tabla - negrita

        s.add(
            ParagraphStyle("RptCellBold", fontName="Helvetica-Bold", fontSize=9, textColor=Colors.GRAY_900, leading=12)
        )

        # Celdas de tabla - alineación derecha (números)

        s.add(
            ParagraphStyle(
                "RptCellRight",
                fontName="Helvetica",
                fontSize=9,
                textColor=Colors.GRAY_700,
                alignment=TA_RIGHT,
                leading=12,
            )
        )

        # Encabezado de tabla

        s.add(
            ParagraphStyle(
                "RptCellHeader",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=Colors.GRAY_900,
                alignment=TA_LEFT,  # Alineación izquierda
                leading=12,
            )
        )

        return s

    @classmethod
    def _fmt(cls, val, currency=False, short=False):
        """Formatea números de forma clara y legible."""

        if val is None:

            return "$0" if currency else "0"

        v = float(val) if isinstance(val, Decimal) else float(val or 0)

        if currency:

            if short and v >= 1_000_000:

                return f"${v / 1_000_000:.1f}M"

            elif short and v >= 1_000:

                return f"${v / 1_000:.0f}K"

            return f"${v:,.2f}"

        return f"{int(v):,}"

    # =========================================================================

    # COMPONENTES DE DISEÑO EDITORIAL

    # =========================================================================

    @classmethod
    def _header_banner(cls, title, subtitle=None):
        """Encabezado limpio y profesional."""

        elements = []

        # Línea sutil superior (muy delgada)

        d = Drawing(cls.WIDTH, 0.5)

        d.add(Rect(0, 0, cls.WIDTH, 0.5, fillColor=Colors.GRAY_300, strokeColor=None))

        elements.append(d)

        elements.append(Spacer(1, 25))  # Espacio generoso

        # Título

        s = cls._styles()

        elements.append(Paragraph(title, s["RptMainTitle"]))

        # Subtítulo con fecha (formato simple)

        fecha = timezone.now().strftime("%d de %B de %Y, %H:%M")

        sub_text = ""

        if subtitle:

            sub_text = f"{subtitle}<br/>"

        sub_text += f"Generado el {fecha}"

        elements.append(Paragraph(sub_text, s["RptSubtitle"]))

        # Línea sutil inferior

        elements.append(Spacer(1, 20))

        d = Drawing(cls.WIDTH, 0.5)

        d.add(Rect(0, 0, cls.WIDTH, 0.5, fillColor=Colors.GRAY_300, strokeColor=None))

        elements.append(d)

        elements.append(Spacer(1, 30))  # Espacio antes del contenido

        return elements

    @classmethod
    def _kpi_cards(cls, kpis):
        """Tarjetas KPI minimalistas y limpias."""

        s = cls._styles()

        cards = []

        for kpi in kpis:

            # Tabla simple para cada KPI

            value_style = ParagraphStyle("KPIVal", parent=s["RptKPIValue"])

            card_data = [[Paragraph(str(kpi["value"]), value_style)], [Paragraph(kpi["label"], s["RptKPILabel"])]]

            card = Table(card_data, colWidths=[cls.WIDTH / len(kpis) - 15])

            card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), Colors.WHITE),  # Fondo blanco limpio
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, 0), 20),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("TOPPADDING", (0, 1), (-1, 1), 5),
                        ("BOTTOMPADDING", (0, 1), (-1, 1), 20),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        # Borde sutil
                        ("LINEBELOW", (0, 0), (-1, 0), 1, Colors.GRAY_300),
                        ("LINEBELOW", (0, -1), (-1, -1), 1, Colors.GRAY_300),
                        ("LINEBEFORE", (0, 0), (0, -1), 0.5, Colors.GRAY_300),
                        ("LINEAFTER", (-1, 0), (-1, -1), 0.5, Colors.GRAY_300),
                    ]
                )
            )

            cards.append(card)

        # Contenedor con espaciado uniforme

        container = Table([cards], colWidths=[(cls.WIDTH / len(kpis))] * len(kpis))

        container.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        return container

    @classmethod
    def _section_title(cls, text):
        """Título de sección limpio, sin iconos decorativos."""

        s = cls._styles()

        return Paragraph(text, s["RptSection"])

    @classmethod
    def _data_table(cls, headers, rows, col_widths=None):
        """Tabla de datos con diseño simple y legible."""

        s = cls._styles()

        # Procesar headers

        header_row = [Paragraph(h, s["RptCellHeader"]) for h in headers]

        # Procesar datos

        data_rows = []

        for row in rows:

            cells = []

            for i, cell in enumerate(row):

                txt = str(cell) if cell is not None else "—"

                # Detectar si es número/moneda para alineación derecha

                style = (
                    s["RptCellRight"]
                    if (txt.startswith("$") or (txt.replace(",", "").replace(".", "").isdigit()))
                    else s["RptCell"]
                )

                cells.append(Paragraph(txt, style))

            data_rows.append(cells)

        all_data = [header_row] + data_rows

        # Calcular anchos si no se proporcionan

        if col_widths is None:

            col_widths = [cls.WIDTH / len(headers)] * len(headers)

        table = Table(all_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            # Encabezado - fondo sutil, texto oscuro
            ("BACKGROUND", (0, 0), (-1, 0), Colors.GRAY_100),
            ("TEXTCOLOR", (0, 0), (-1, 0), Colors.GRAY_900),
            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            # Cuerpo
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TOPPADDING", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            # Bordes sutiles
            ("LINEBELOW", (0, 0), (-1, 0), 1, Colors.GRAY_300),  # Borde inferior del header
            ("LINEBELOW", (0, 1), (-1, -2), 0.5, Colors.GRAY_300),  # Líneas entre filas
            ("LINEBELOW", (0, -1), (-1, -1), 1, Colors.GRAY_300),  # Borde inferior final
        ]

        # Alternar colores de fondo muy sutiles (opcional, puede comentarse)

        for i in range(1, len(all_data)):

            if i % 2 == 0:

                style_cmds.append(("BACKGROUND", (0, i), (-1, i), Colors.WHITE))  # Blanco puro

        table.setStyle(TableStyle(style_cmds))

        return table

    @classmethod
    def _pie_chart(cls, data, labels, title=None, width=260, height=180):
        """Gráfico de pastel simple y profesional."""

        if not data or sum(data) == 0:

            return Spacer(1, 10)

        d = Drawing(width, height)

        # Título si se proporciona

        if title:

            d.add(
                String(
                    width / 2,
                    height - 10,
                    title,
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    fillColor=Colors.GRAY_700,
                    textAnchor="middle",
                )
            )

        pie = Pie()

        pie.x = 30

        pie.y = 20

        pie.width = 100

        pie.height = 100

        pie.data = data

        pie.labels = None  # Sin labels en el pie

        # Colores suaves y profesionales

        for i in range(len(data)):

            pie.slices[i].fillColor = Colors.CHART[i % len(Colors.CHART)]

            pie.slices[i].strokeColor = Colors.WHITE

            pie.slices[i].strokeWidth = 1  # Borde fino

            pie.slices[i].popout = 0  # Sin efectos

        d.add(pie)

        # Leyenda simple

        legend = Legend()

        legend.x = 150

        legend.y = height - 50

        legend.fontName = "Helvetica"

        legend.fontSize = 8

        legend.boxAnchor = "nw"

        legend.columnMaximum = 6

        legend.strokeWidth = 0

        legend.deltax = 8

        legend.deltay = 10

        legend.autoXPadding = 4

        legend.dxTextSpace = 6

        legend.colorNamePairs = [
            (Colors.CHART[i % len(Colors.CHART)], f"{labels[i]} ({data[i]})") for i in range(len(labels))
        ]

        d.add(legend)

        return d

    @classmethod
    def _bar_chart(cls, data, labels, title=None, width=280, height=160):
        """Gráfico de barras horizontal simple."""

        if not data:

            return Spacer(1, 10)

        d = Drawing(width, height)

        # Título

        if title:

            d.add(
                String(
                    width / 2,
                    height - 8,
                    title,
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    fillColor=Colors.GRAY_700,
                    textAnchor="middle",
                )
            )

        bc = HorizontalBarChart()

        bc.x = 90

        bc.y = 20

        bc.width = width - 110

        bc.height = height - 45

        bc.data = [data]

        bc.categoryAxis.categoryNames = [label[:15] for label in labels]  # Truncar si es necesario

        # Color simple y profesional

        bc.bars[0].fillColor = Colors.ACCENT

        bc.bars[0].strokeColor = Colors.GRAY_300

        bc.bars[0].strokeWidth = 0.5

        bc.categoryAxis.labels.fontName = "Helvetica"

        bc.categoryAxis.labels.fontSize = 8

        bc.categoryAxis.labels.textAnchor = "end"

        bc.categoryAxis.labels.dx = -6

        bc.categoryAxis.strokeColor = Colors.GRAY_300

        bc.categoryAxis.strokeWidth = 0.5

        bc.valueAxis.labels.fontName = "Helvetica"

        bc.valueAxis.labels.fontSize = 8

        bc.valueAxis.strokeColor = Colors.GRAY_300

        bc.valueAxis.strokeWidth = 0.5

        bc.valueAxis.gridStrokeColor = Colors.GRAY_300

        bc.valueAxis.gridStrokeWidth = 0.5

        bc.valueAxis.visibleGrid = 1

        bc.barWidth = 12

        bc.barSpacing = 5

        d.add(bc)

        return d

    @classmethod
    def _footer(cls):
        """Pie de página minimalista."""

        s = cls._styles()

        elements = []

        elements.append(Spacer(1, 40))  # Espacio generoso antes del footer

        # Línea sutil

        d = Drawing(cls.WIDTH, 0.5)

        d.add(Rect(0, 0, cls.WIDTH, 0.5, fillColor=Colors.GRAY_300, strokeColor=None))

        elements.append(d)

        elements.append(Spacer(1, 8))

        elements.append(
            Paragraph(
                f"Seguros UTPL • Sistema de Gestión • {timezone.now().strftime('%d/%m/%Y %H:%M')}", s["RptFooter"]
            )
        )

        return elements

    @classmethod
    def _indicator_box(cls, text):
        """Caja de indicador simple, sin colores llamativos."""

        s = cls._styles()

        data = [[Paragraph(text, ParagraphStyle("Ind", parent=s["RptBody"], textColor=Colors.GRAY_700, leftIndent=8))]]

        t = Table(data, colWidths=[cls.WIDTH - 20])

        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), Colors.GRAY_100),  # Fondo muy sutil
                    ("LINEBEFORE", (0, 0), (0, -1), 2, Colors.GRAY_700),  # Borde izquierdo sutil
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )

        return t

    # =========================================================================

    # REPORTE DE PÓLIZAS

    # =========================================================================

    @classmethod
    def generar_reporte_polizas_pdf(cls, reporte_data, filtros_texto=None):
        """Reporte de pólizas con diseño editorial."""

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=cls.PAGE_SIZE,
            leftMargin=cls.MARGIN,
            rightMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        s = cls._styles()

        elements = []

        # === HEADER ===

        subtitle = f"Filtros aplicados: {filtros_texto}" if filtros_texto else None

        elements.extend(cls._header_banner("Reporte de Pólizas", subtitle))

        # === KPIs ===

        totales = reporte_data.get("totales", {})

        kpis = [
            {"value": cls._fmt(totales.get("cantidad", 0)), "label": "Total Pólizas"},
            {"value": cls._fmt(totales.get("vigentes", 0)), "label": "Vigentes"},
            {"value": cls._fmt(totales.get("por_vencer", 0)), "label": "Por Vencer"},
            {"value": cls._fmt(totales.get("vencidas", 0)), "label": "Vencidas"},
        ]

        elements.append(cls._kpi_cards(kpis))

        elements.append(Spacer(1, 15))

        # KPI de suma asegurada

        suma_kpi = [
            {
                "value": cls._fmt(totales.get("suma_total", 0), currency=True, short=True),
                "label": "Suma Total Asegurada",
            }
        ]

        elements.append(cls._kpi_cards(suma_kpi))

        elements.append(Spacer(1, 30))

        # === GRÁFICOS ===

        elements.append(cls._section_title("Análisis Visual"))

        charts = []

        # Pie de estados

        estados_data = []

        estados_labels = []

        if totales.get("vigentes", 0) > 0:

            estados_data.append(totales["vigentes"])

            estados_labels.append("Vigentes")

        if totales.get("por_vencer", 0) > 0:

            estados_data.append(totales["por_vencer"])

            estados_labels.append("Por Vencer")

        if totales.get("vencidas", 0) > 0:

            estados_data.append(totales["vencidas"])

            estados_labels.append("Vencidas")

        if estados_data:

            charts.append(cls._pie_chart(estados_data, estados_labels, "Distribución por Estado"))

        # Barras por compañía

        por_compania = reporte_data.get("por_compania", [])[:5]

        if por_compania:

            comp_data = [item.get("cantidad", 0) for item in por_compania]

            comp_labels = [item.get("compania_aseguradora__nombre", "N/A") for item in por_compania]

            charts.append(cls._bar_chart(comp_data, comp_labels, "Top 5 Compañías"))

        if charts:

            chart_table = Table([charts], colWidths=[cls.WIDTH / 2] * len(charts) if len(charts) > 1 else [cls.WIDTH])

            chart_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )

            elements.append(chart_table)

        elements.append(Spacer(1, 25))

        # === TABLAS DE DISTRIBUCIÓN ===

        if por_compania:

            elements.append(cls._section_title("Por Compañía Aseguradora"))

            rows = [
                [
                    item.get("compania_aseguradora__nombre", "Sin nombre"),
                    cls._fmt(item.get("cantidad", 0)),
                    cls._fmt(item.get("suma", 0), currency=True),
                ]
                for item in reporte_data.get("por_compania", [])[:8]
            ]

            elements.append(
                cls._data_table(
                    ["Compañía", "Pólizas", "Suma Asegurada"],
                    rows,
                    [cls.WIDTH * 0.50, cls.WIDTH * 0.20, cls.WIDTH * 0.30],
                )
            )

            elements.append(Spacer(1, 20))

        por_tipo = reporte_data.get("por_tipo", [])

        if por_tipo:

            elements.append(cls._section_title("Por Tipo de Póliza"))

            rows = [
                [
                    item.get("tipo_poliza__nombre", "Sin tipo"),
                    cls._fmt(item.get("cantidad", 0)),
                    cls._fmt(item.get("suma", 0), currency=True),
                ]
                for item in por_tipo[:8]
            ]

            elements.append(
                cls._data_table(
                    ["Tipo", "Cantidad", "Suma Asegurada"], rows, [cls.WIDTH * 0.50, cls.WIDTH * 0.20, cls.WIDTH * 0.30]
                )
            )

            elements.append(Spacer(1, 20))

        # === DETALLE ===

        elements.append(PageBreak())

        elements.append(cls._section_title("Detalle de Pólizas"))

        queryset = list(reporte_data.get("queryset", []))

        total = len(queryset)

        if total > 35:

            elements.append(
                Paragraph(f"Mostrando 35 de {total} registros. Exporte a Excel para ver todos.", s["RptBody"])
            )

            elements.append(Spacer(1, 12))

        rows = []

        for p in queryset[:35]:

            estado = p.get_estado_display() if hasattr(p, "get_estado_display") else str(p.estado)

            rows.append(
                [
                    p.numero_poliza,
                    str(p.compania_aseguradora)[:20] if p.compania_aseguradora else "—",
                    str(p.tipo_poliza)[:15] if p.tipo_poliza else "—",
                    cls._fmt(p.suma_asegurada, currency=True),
                    f"{p.fecha_inicio.strftime('%d/%m/%y')} - {p.fecha_fin.strftime('%d/%m/%y')}",
                    estado,
                ]
            )

        if rows:

            elements.append(
                cls._data_table(
                    ["N° Póliza", "Compañía", "Tipo", "Suma", "Vigencia", "Estado"],
                    rows,
                    [
                        cls.WIDTH * 0.15,
                        cls.WIDTH * 0.22,
                        cls.WIDTH * 0.13,
                        cls.WIDTH * 0.18,
                        cls.WIDTH * 0.18,
                        cls.WIDTH * 0.14,
                    ],
                )
            )

        else:

            elements.append(Paragraph("No hay pólizas con los filtros aplicados.", s["RptBody"]))

        # Footer

        elements.extend(cls._footer())

        doc.build(elements)

        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")

        response["Content-Disposition"] = (
            f'attachment; filename="reporte_polizas_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        )

        return response

    # =========================================================================

    # REPORTE DE SINIESTROS

    # =========================================================================

    @classmethod
    def generar_reporte_siniestros_pdf(cls, reporte_data, filtros_texto=None):
        """Reporte de siniestros con diseño editorial."""

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=cls.PAGE_SIZE,
            leftMargin=cls.MARGIN,
            rightMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        s = cls._styles()

        elements = []

        # === HEADER ===

        subtitle = f"Filtros aplicados: {filtros_texto}" if filtros_texto else None

        elements.extend(cls._header_banner("Reporte de Siniestros", subtitle))

        # === KPIs ===

        totales = reporte_data.get("totales", {})

        kpis = [
            {"value": cls._fmt(totales.get("cantidad", 0)), "label": "Total Siniestros"},
            {"value": cls._fmt(totales.get("activos", 0)), "label": "En Proceso"},
            {"value": cls._fmt(totales.get("cerrados", 0)), "label": "Cerrados"},
            {"value": cls._fmt(totales.get("rechazados", 0)), "label": "Rechazados"},
        ]

        elements.append(cls._kpi_cards(kpis))

        elements.append(Spacer(1, 15))

        # KPIs de montos

        kpis_montos = [
            {"value": cls._fmt(totales.get("monto_estimado", 0), currency=True, short=True), "label": "Monto Estimado"},
            {"value": cls._fmt(totales.get("monto_indemnizado", 0), currency=True, short=True), "label": "Indemnizado"},
        ]

        elements.append(cls._kpi_cards(kpis_montos))

        elements.append(Spacer(1, 25))

        # Indicadores

        monto_est = float(totales.get("monto_estimado", 0) or 0)

        monto_ind = float(totales.get("monto_indemnizado", 0) or 0)

        if monto_est > 0:

            ratio = (monto_ind / monto_est) * 100

            elements.append(
                cls._indicator_box(
                    f"<b>Ratio de Indemnización:</b> {ratio:.1f}% del monto estimado ha sido indemnizado."
                )
            )

            elements.append(Spacer(1, 12))

        if totales.get("rechazados") and totales.get("cantidad"):

            tasa = (totales["rechazados"] / totales["cantidad"]) * 100

            elements.append(
                cls._indicator_box(f"<b>Tasa de Rechazo:</b> {tasa:.1f}% de los siniestros han sido rechazados.")
            )

        elements.append(Spacer(1, 20))

        # === GRÁFICOS ===

        elements.append(cls._section_title("Análisis Visual"))

        charts = []

        # Pie por tipo

        por_tipo = reporte_data.get("por_tipo", [])[:6]

        if por_tipo:

            tipo_data = [item.get("cantidad", 0) for item in por_tipo]

            tipo_labels = [(item.get("tipo_siniestro__nombre") or "Sin tipo") for item in por_tipo]

            charts.append(cls._pie_chart(tipo_data, tipo_labels, "Distribución por Tipo"))

        # Barras por estado

        por_estado = reporte_data.get("por_estado", [])[:6]

        if por_estado:

            estado_map = {
                "registrado": "Registrado",
                "documentacion_pendiente": "Documentación Pendiente",
                "enviado_aseguradora": "Enviado",
                "en_evaluacion": "En Evaluación",
                "aprobado": "Aprobado",
                "rechazado": "Rechazado",
                "liquidado": "Liquidado",
                "cerrado": "Cerrado",
            }

            est_data = [item.get("cantidad", 0) for item in por_estado]

            est_labels = [estado_map.get(item.get("estado"), item.get("estado", "?")) for item in por_estado]

            charts.append(cls._bar_chart(est_data, est_labels, "Distribución por Estado"))

        if charts:

            chart_table = Table([charts], colWidths=[cls.WIDTH / 2] * len(charts) if len(charts) > 1 else [cls.WIDTH])

            chart_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )

            elements.append(chart_table)

        elements.append(Spacer(1, 25))

        # === TABLAS ===

        if por_tipo:

            elements.append(cls._section_title("Por Tipo de Siniestro"))

            rows = [
                [
                    (item.get("tipo_siniestro__nombre") or "Sin tipo").title(),
                    cls._fmt(item.get("cantidad", 0)),
                    cls._fmt(item.get("monto", 0), currency=True),
                ]
                for item in reporte_data.get("por_tipo", [])[:8]
            ]

            elements.append(
                cls._data_table(
                    ["Tipo", "Casos", "Monto Estimado"], rows, [cls.WIDTH * 0.50, cls.WIDTH * 0.20, cls.WIDTH * 0.30]
                )
            )

            elements.append(Spacer(1, 20))

        # === DETALLE ===

        elements.append(PageBreak())

        elements.append(cls._section_title("Detalle de Siniestros"))

        queryset = list(reporte_data.get("queryset", []))

        total = len(queryset)

        if total > 35:

            elements.append(Paragraph(f"Mostrando 35 de {total} registros.", s["RptBody"]))

            elements.append(Spacer(1, 12))

        rows = []

        for sin in queryset[:35]:

            estado = sin.get_estado_display() if hasattr(sin, "get_estado_display") else str(sin.estado)

            rows.append(
                [
                    sin.numero_siniestro,
                    sin.poliza.numero_poliza if sin.poliza else "—",
                    str(sin.tipo_siniestro)[:12] if sin.tipo_siniestro else "—",
                    sin.fecha_siniestro.strftime("%d/%m/%y"),
                    cls._fmt(sin.monto_estimado, currency=True),
                    cls._fmt(sin.monto_indemnizado or 0, currency=True),
                    estado[:15],
                ]
            )

        if rows:

            elements.append(
                cls._data_table(
                    ["N° Siniestro", "Póliza", "Tipo", "Fecha", "Estimado", "Indemnizado", "Estado"],
                    rows,
                    [
                        cls.WIDTH * 0.12,
                        cls.WIDTH * 0.12,
                        cls.WIDTH * 0.12,
                        cls.WIDTH * 0.10,
                        cls.WIDTH * 0.15,
                        cls.WIDTH * 0.15,
                        cls.WIDTH * 0.24,
                    ],
                )
            )

        elements.extend(cls._footer())

        doc.build(elements)

        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")

        response["Content-Disposition"] = (
            f'attachment; filename="reporte_siniestros_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        )

        return response

    # =========================================================================

    # REPORTE DE FACTURAS

    # =========================================================================

    @classmethod
    def generar_reporte_facturas_pdf(cls, reporte_data, filtros_texto=None):
        """Reporte de facturas con diseño editorial."""

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=cls.PAGE_SIZE,
            leftMargin=cls.MARGIN,
            rightMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        s = cls._styles()

        elements = []

        # Header

        subtitle = f"Filtros aplicados: {filtros_texto}" if filtros_texto else None

        elements.extend(cls._header_banner("Reporte de Facturas", subtitle))

        # KPIs

        totales = reporte_data.get("totales", {})

        kpis = [
            {"value": cls._fmt(totales.get("cantidad", 0)), "label": "Total Facturas"},
            {"value": cls._fmt(totales.get("pendientes", 0)), "label": "Pendientes"},
            {"value": cls._fmt(totales.get("pagadas", 0)), "label": "Pagadas"},
            {"value": cls._fmt(totales.get("vencidas", 0)), "label": "Vencidas"},
        ]

        elements.append(cls._kpi_cards(kpis))

        elements.append(Spacer(1, 15))

        # KPIs montos

        kpis_montos = [
            {
                "value": cls._fmt(totales.get("total_facturado", 0), currency=True, short=True),
                "label": "Total Facturado",
            },
            {"value": cls._fmt(totales.get("total_pendiente", 0), currency=True, short=True), "label": "Por Cobrar"},
            {"value": cls._fmt(totales.get("total_vencido", 0), currency=True, short=True), "label": "Vencido"},
        ]

        elements.append(cls._kpi_cards(kpis_montos))

        elements.append(Spacer(1, 25))

        # Indicador

        total_fact = float(totales.get("total_facturado", 0) or 0)

        total_pend = float(totales.get("total_pendiente", 0) or 0)

        if total_fact > 0:

            pct = (total_pend / total_fact) * 100

            elements.append(
                cls._indicator_box(f"<b>Cartera Pendiente:</b> {pct:.1f}% del total facturado está por cobrar.")
            )

            elements.append(Spacer(1, 25))

        # Gráfico

        elements.append(cls._section_title("Distribución"))

        estados_data = []

        estados_labels = []

        if totales.get("pendientes", 0) > 0:

            estados_data.append(totales["pendientes"])

            estados_labels.append("Pendientes")

        if totales.get("pagadas", 0) > 0:

            estados_data.append(totales["pagadas"])

            estados_labels.append("Pagadas")

        if totales.get("vencidas", 0) > 0:

            estados_data.append(totales["vencidas"])

            estados_labels.append("Vencidas")

        if estados_data:

            elements.append(
                cls._pie_chart(estados_data, estados_labels, "Distribución por Estado", width=350, height=180)
            )

        elements.append(Spacer(1, 25))

        # Detalle

        elements.append(cls._section_title("Detalle de Facturas"))

        queryset = list(reporte_data.get("queryset", []))

        total = len(queryset)

        if total > 35:

            elements.append(Paragraph(f"Mostrando 35 de {total} facturas.", s["RptBody"]))

            elements.append(Spacer(1, 12))

        rows = []

        for f in queryset[:35]:

            estado = f.get_estado_display() if hasattr(f, "get_estado_display") else str(f.estado)

            rows.append(
                [
                    f.numero_factura,
                    f.poliza.numero_poliza if f.poliza else "—",
                    f.fecha_emision.strftime("%d/%m/%y"),
                    f.fecha_vencimiento.strftime("%d/%m/%y"),
                    cls._fmt(f.monto_total, currency=True),
                    cls._fmt(f.saldo_pendiente, currency=True),
                    estado,
                ]
            )

        if rows:

            elements.append(
                cls._data_table(
                    ["N° Factura", "Póliza", "Emisión", "Vence", "Total", "Saldo", "Estado"],
                    rows,
                    [
                        cls.WIDTH * 0.12,
                        cls.WIDTH * 0.12,
                        cls.WIDTH * 0.11,
                        cls.WIDTH * 0.11,
                        cls.WIDTH * 0.16,
                        cls.WIDTH * 0.16,
                        cls.WIDTH * 0.22,
                    ],
                )
            )

        elements.extend(cls._footer())

        doc.build(elements)

        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")

        response["Content-Disposition"] = (
            f'attachment; filename="reporte_facturas_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        )

        return response

    # =========================================================================

    # REPORTE EJECUTIVO

    # =========================================================================

    @classmethod
    def generar_reporte_ejecutivo_pdf(cls, dashboard_data):
        """Reporte ejecutivo con diseño editorial."""

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=cls.PAGE_SIZE,
            leftMargin=cls.MARGIN,
            rightMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        s = cls._styles()

        elements = []

        # Header

        elements.extend(cls._header_banner("Reporte Ejecutivo", "Resumen General del Sistema"))

        stats = dashboard_data.get("stats", {})

        # === PÓLIZAS ===

        elements.append(cls._section_title("Portafolio de Pólizas"))

        kpis = [
            {"value": cls._fmt(stats.get("total_polizas", 0)), "label": "Total"},
            {"value": cls._fmt(stats.get("polizas_vigentes", 0)), "label": "Vigentes"},
            {"value": cls._fmt(stats.get("polizas_por_vencer", 0)), "label": "Por Vencer"},
            {
                "value": cls._fmt(stats.get("suma_total_asegurada", 0), currency=True, short=True),
                "label": "Suma Asegurada",
            },
        ]

        elements.append(cls._kpi_cards(kpis))

        elements.append(Spacer(1, 30))

        # === FACTURACIÓN ===

        elements.append(cls._section_title("Estado de Facturación"))

        kpis = [
            {"value": cls._fmt(stats.get("total_facturas", 0)), "label": "Facturas"},
            {"value": cls._fmt(stats.get("facturas_pendientes", 0)), "label": "Pendientes"},
            {"value": cls._fmt(stats.get("total_facturado", 0), currency=True, short=True), "label": "Facturado"},
            {"value": cls._fmt(stats.get("total_por_cobrar", 0), currency=True, short=True), "label": "Por Cobrar"},
        ]

        elements.append(cls._kpi_cards(kpis))

        elements.append(Spacer(1, 30))

        # === SINIESTROS ===

        elements.append(cls._section_title("Gestión de Siniestros"))

        kpis = [
            {"value": cls._fmt(stats.get("total_siniestros", 0)), "label": "Total"},
            {"value": cls._fmt(stats.get("siniestros_activos", 0)), "label": "Activos"},
            {"value": cls._fmt(stats.get("monto_siniestros", 0), currency=True, short=True), "label": "Estimado"},
            {"value": cls._fmt(stats.get("monto_indemnizado", 0), currency=True, short=True), "label": "Indemnizado"},
        ]

        elements.append(cls._kpi_cards(kpis))

        elements.append(Spacer(1, 30))

        # === ALERTAS ===

        elements.append(cls._section_title("Alertas del Sistema"))

        kpis = [
            {"value": cls._fmt(stats.get("alertas_activas", 0)), "label": "Alertas Activas"},
            {"value": cls._fmt(stats.get("alertas_alta_prioridad", 0)), "label": "Alta Prioridad"},
        ]

        elements.append(cls._kpi_cards(kpis))

        elements.append(Spacer(1, 35))

        # Nota

        elements.append(
            Paragraph(
                "Este reporte proporciona una visión ejecutiva del sistema. "
                "Para información detallada, consulte los reportes específicos.",
                s["RptBody"],
            )
        )

        elements.extend(cls._footer())

        doc.build(elements)

        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")

        response["Content-Disposition"] = (
            f'attachment; filename="reporte_ejecutivo_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
        )

        return response
