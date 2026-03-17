"""
Harmoni ERP — Motor de Exportación Excel Reutilizable.

Genera archivos Excel formateados con branding Harmoni usando xlsxwriter.
Todos los módulos del ERP usan esta clase para exportar datos a Excel.

Uso:
    exporter = ExcelExporter('Reporte de Personal', 'Marzo 2026')
    exporter.add_sheet('Personal', headers, data, column_widths=[20, 30, 15])
    exporter.add_summary_sheet({'Total Empleados': 150, 'Masa Salarial': 'S/ 450,000'})
    response = exporter.as_response('personal_202603.xlsx')
"""
import io
import logging
from datetime import date, datetime
from decimal import Decimal

import xlsxwriter

logger = logging.getLogger('core.export_engine')

# ── Paleta Harmoni ──────────────────────────────────────────────────────────
TEAL_DARK = '#0d2b27'
TEAL_MID = '#0f766e'
TEAL_ACCENT = '#5eead4'
GREEN_LIGHT = '#ccfbf1'
ALT_ROW = '#f0fdfa'
WHITE = '#ffffff'
GRAY_LIGHT = '#f8fafc'
GRAY_BORDER = '#d1d5db'


def _load_empresa_info():
    """Load company info from ConfiguracionSistema singleton."""
    nombre = "Empresa"
    ruc = ""
    try:
        from asistencia.models import ConfiguracionSistema
        cfg = ConfiguracionSistema.get()
        if cfg:
            nombre = cfg.empresa_nombre or "Empresa"
            ruc = cfg.ruc or ""
    except Exception:
        pass
    return nombre, ruc


class ExcelExporter:
    """
    Reusable Excel export engine with Harmoni branding.

    Creates professionally formatted Excel workbooks with:
    - Company header (name, RUC)
    - Report title and generation date
    - Formatted headers (bold, colored)
    - Auto-width or manual column widths
    - Alternating row colors
    - Number/date formatting
    - Optional summary sheet
    """

    def __init__(self, titulo, subtitulo='', empresa=None, ruc=None):
        """
        Initialize the exporter.

        Args:
            titulo: Report title displayed in the header.
            subtitulo: Optional subtitle (e.g., date range, filters).
            empresa: Company name override. If None, loaded from config.
            ruc: RUC override. If None, loaded from config.
        """
        self.output = io.BytesIO()
        self.wb = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.titulo = titulo
        self.subtitulo = subtitulo

        if empresa is None:
            self.empresa, self.ruc = _load_empresa_info()
        else:
            self.empresa = empresa
            self.ruc = ruc or ''

        self._init_formats()
        self._sheets_added = 0

    def _init_formats(self):
        """Initialize all cell formats."""
        # Header band (dark teal)
        self.fmt_header_band = self.wb.add_format({
            'bold': True,
            'font_size': 14,
            'font_color': WHITE,
            'bg_color': TEAL_DARK,
            'valign': 'vcenter',
        })
        self.fmt_header_ruc = self.wb.add_format({
            'font_size': 9,
            'font_color': TEAL_ACCENT,
            'bg_color': TEAL_DARK,
            'valign': 'vcenter',
        })
        self.fmt_header_title = self.wb.add_format({
            'bold': True,
            'font_size': 12,
            'font_color': TEAL_ACCENT,
            'bg_color': TEAL_DARK,
            'align': 'right',
            'valign': 'vcenter',
        })
        self.fmt_header_sub = self.wb.add_format({
            'font_size': 9,
            'font_color': GREEN_LIGHT,
            'bg_color': TEAL_DARK,
            'align': 'right',
            'valign': 'vcenter',
        })
        self.fmt_header_fill = self.wb.add_format({
            'bg_color': TEAL_DARK,
        })

        # Column headers
        self.fmt_col_header = self.wb.add_format({
            'bold': True,
            'font_size': 10,
            'font_color': WHITE,
            'bg_color': TEAL_MID,
            'border': 1,
            'border_color': GRAY_BORDER,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        # Data cells - normal
        self.fmt_data = self.wb.add_format({
            'font_size': 10,
            'border': 1,
            'border_color': GRAY_BORDER,
            'valign': 'vcenter',
        })
        # Data cells - alternate row
        self.fmt_data_alt = self.wb.add_format({
            'font_size': 10,
            'bg_color': ALT_ROW,
            'border': 1,
            'border_color': GRAY_BORDER,
            'valign': 'vcenter',
        })

        # Number formats
        self.fmt_number = self.wb.add_format({
            'font_size': 10,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
        })
        self.fmt_number_alt = self.wb.add_format({
            'font_size': 10,
            'bg_color': ALT_ROW,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
        })

        # Currency format (S/)
        self.fmt_currency = self.wb.add_format({
            'font_size': 10,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '"S/ "#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
        })
        self.fmt_currency_alt = self.wb.add_format({
            'font_size': 10,
            'bg_color': ALT_ROW,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '"S/ "#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
        })

        # Date format
        self.fmt_date = self.wb.add_format({
            'font_size': 10,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': 'dd/mm/yyyy',
            'align': 'center',
            'valign': 'vcenter',
        })
        self.fmt_date_alt = self.wb.add_format({
            'font_size': 10,
            'bg_color': ALT_ROW,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': 'dd/mm/yyyy',
            'align': 'center',
            'valign': 'vcenter',
        })

        # Center aligned
        self.fmt_center = self.wb.add_format({
            'font_size': 10,
            'border': 1,
            'border_color': GRAY_BORDER,
            'align': 'center',
            'valign': 'vcenter',
        })
        self.fmt_center_alt = self.wb.add_format({
            'font_size': 10,
            'bg_color': ALT_ROW,
            'border': 1,
            'border_color': GRAY_BORDER,
            'align': 'center',
            'valign': 'vcenter',
        })

        # Percentage
        self.fmt_pct = self.wb.add_format({
            'font_size': 10,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '0.0%',
            'align': 'center',
            'valign': 'vcenter',
        })
        self.fmt_pct_alt = self.wb.add_format({
            'font_size': 10,
            'bg_color': ALT_ROW,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '0.0%',
            'align': 'center',
            'valign': 'vcenter',
        })

        # Totals row
        self.fmt_total = self.wb.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': GREEN_LIGHT,
            'border': 1,
            'border_color': GRAY_BORDER,
            'valign': 'vcenter',
        })
        self.fmt_total_number = self.wb.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': GREEN_LIGHT,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
        })
        self.fmt_total_currency = self.wb.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': GREEN_LIGHT,
            'border': 1,
            'border_color': GRAY_BORDER,
            'num_format': '"S/ "#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
        })

        # Summary sheet formats
        self.fmt_summary_label = self.wb.add_format({
            'bold': True,
            'font_size': 11,
            'font_color': TEAL_DARK,
            'border': 1,
            'border_color': GRAY_BORDER,
            'bg_color': GRAY_LIGHT,
            'valign': 'vcenter',
        })
        self.fmt_summary_value = self.wb.add_format({
            'font_size': 11,
            'border': 1,
            'border_color': GRAY_BORDER,
            'align': 'right',
            'valign': 'vcenter',
        })

    def _write_header(self, ws, total_cols):
        """Write the company header band at the top of a sheet."""
        # Merge cells for header
        last_col = max(total_cols - 1, 3)
        mid = last_col // 2

        # Left side: company name + RUC
        ws.merge_range(0, 0, 0, mid, self.empresa, self.fmt_header_band)
        ws.merge_range(1, 0, 1, mid, f'RUC: {self.ruc}' if self.ruc else '', self.fmt_header_ruc)

        # Right side: report title + subtitle + date
        ws.merge_range(0, mid + 1, 0, last_col, self.titulo, self.fmt_header_title)
        sub_text = self.subtitulo
        if sub_text:
            sub_text += f'  |  Generado: {date.today().strftime("%d/%m/%Y")}'
        else:
            sub_text = f'Generado: {date.today().strftime("%d/%m/%Y")}'
        ws.merge_range(1, mid + 1, 1, last_col, sub_text, self.fmt_header_sub)

        # Fill any gaps in header rows
        for col in range(last_col + 1):
            pass  # merge_range handles full coverage

        ws.set_row(0, 25)
        ws.set_row(1, 18)

        return 3  # Next available row (0=header, 1=sub, 2=empty spacer)

    def add_sheet(self, name, headers, data, column_widths=None,
                  column_types=None, freeze_panes=True):
        """
        Add a sheet with formatted headers and data.

        Args:
            name: Sheet name.
            headers: List of column header strings.
            data: List of lists (rows of values).
            column_widths: Optional list of column widths.
                           If None, auto-calculated from data.
            column_types: Optional list of column type hints.
                          Values: 'text', 'number', 'currency', 'date',
                                  'center', 'pct'. Default is 'text'.
            freeze_panes: Freeze the header row.

        Returns:
            The worksheet object for further customization.
        """
        ws = self.wb.add_worksheet(name[:31])  # Excel max sheet name = 31
        self._sheets_added += 1
        ncols = len(headers)

        # Write header band
        data_start_row = self._write_header(ws, ncols)

        # Column types defaults
        if column_types is None:
            column_types = ['text'] * ncols

        # Write column headers
        for col_idx, header in enumerate(headers):
            ws.write(data_start_row, col_idx, header, self.fmt_col_header)
        ws.set_row(data_start_row, 30)

        # Freeze panes below header
        if freeze_panes:
            ws.freeze_panes(data_start_row + 1, 0)

        # Write data rows
        for row_idx, row_data in enumerate(data):
            is_alt = row_idx % 2 == 1
            excel_row = data_start_row + 1 + row_idx

            for col_idx, value in enumerate(row_data):
                col_type = column_types[col_idx] if col_idx < len(column_types) else 'text'
                fmt = self._get_cell_format(col_type, is_alt)

                # Handle special value types
                value = self._convert_value(value, col_type)
                if value is None:
                    ws.write_blank(excel_row, col_idx, None, fmt)
                elif isinstance(value, (int, float, Decimal)):
                    ws.write_number(excel_row, col_idx, float(value), fmt)
                elif isinstance(value, (date, datetime)):
                    ws.write_datetime(excel_row, col_idx, value, fmt)
                else:
                    ws.write_string(excel_row, col_idx, str(value), fmt)

        # Set column widths
        if column_widths:
            for col_idx, width in enumerate(column_widths):
                ws.set_column(col_idx, col_idx, width)
        else:
            self._auto_width(ws, headers, data, ncols)

        return ws

    def add_totals_row(self, ws, row_idx, totals, column_types=None):
        """
        Add a totals row at the specified row index.

        Args:
            ws: Worksheet object.
            row_idx: Row to write totals (0-based, absolute).
            totals: List of values for each column (None for empty cells).
            column_types: List of type hints matching add_sheet.
        """
        if column_types is None:
            column_types = ['text'] * len(totals)

        for col_idx, value in enumerate(totals):
            col_type = column_types[col_idx] if col_idx < len(column_types) else 'text'

            if col_type == 'currency':
                fmt = self.fmt_total_currency
            elif col_type in ('number', 'pct'):
                fmt = self.fmt_total_number
            else:
                fmt = self.fmt_total

            if value is None:
                ws.write_blank(row_idx, col_idx, None, fmt)
            elif isinstance(value, (int, float, Decimal)):
                ws.write_number(row_idx, col_idx, float(value), fmt)
            else:
                ws.write_string(row_idx, col_idx, str(value), fmt)

    def add_summary_sheet(self, stats, sheet_name='Resumen'):
        """
        Add a summary/stats sheet with key-value pairs.

        Args:
            stats: dict of {label: value} pairs, or list of (label, value) tuples.
            sheet_name: Name of the summary sheet.
        """
        ws = self.wb.add_worksheet(sheet_name[:31])
        self._sheets_added += 1

        # Header
        ws.merge_range(0, 0, 0, 1, self.titulo, self.fmt_header_band)
        ws.merge_range(1, 0, 1, 1,
                       f'{self.subtitulo}  |  {date.today().strftime("%d/%m/%Y")}',
                       self.fmt_header_sub)
        ws.set_row(0, 25)
        ws.set_row(1, 18)

        # Stats
        if isinstance(stats, dict):
            items = stats.items()
        else:
            items = stats

        row = 3
        for label, value in items:
            ws.write(row, 0, str(label), self.fmt_summary_label)
            if isinstance(value, (int, float, Decimal)):
                ws.write_number(row, 1, float(value), self.fmt_summary_value)
            else:
                ws.write(row, 1, str(value), self.fmt_summary_value)
            row += 1

        ws.set_column(0, 0, 35)
        ws.set_column(1, 1, 25)

        return ws

    def _get_cell_format(self, col_type, is_alt):
        """Return the appropriate cell format based on type and alt row."""
        formats = {
            'text': (self.fmt_data, self.fmt_data_alt),
            'number': (self.fmt_number, self.fmt_number_alt),
            'currency': (self.fmt_currency, self.fmt_currency_alt),
            'date': (self.fmt_date, self.fmt_date_alt),
            'center': (self.fmt_center, self.fmt_center_alt),
            'pct': (self.fmt_pct, self.fmt_pct_alt),
        }
        normal, alt = formats.get(col_type, formats['text'])
        return alt if is_alt else normal

    def _convert_value(self, value, col_type):
        """Convert value to appropriate Python type for xlsxwriter."""
        if value is None or value == '' or value == '—':
            if col_type in ('number', 'currency'):
                return 0
            return value or ''

        if isinstance(value, Decimal):
            return float(value)

        if col_type == 'date' and isinstance(value, str):
            for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            return value

        return value

    def _auto_width(self, ws, headers, data, ncols):
        """Auto-calculate column widths from headers and data."""
        for col in range(ncols):
            max_len = len(str(headers[col])) if col < len(headers) else 8

            # Sample up to 100 rows for width calculation
            for row_data in data[:100]:
                if col < len(row_data) and row_data[col] is not None:
                    cell_len = len(str(row_data[col]))
                    if cell_len > max_len:
                        max_len = cell_len

            width = min(max_len + 3, 50)
            width = max(width, 10)
            ws.set_column(col, col, width)

    def generate(self):
        """
        Close the workbook and return Excel file bytes.

        Returns:
            bytes: The Excel file content.
        """
        self.wb.close()
        self.output.seek(0)
        return self.output.getvalue()

    def as_response(self, filename):
        """
        Return a Django HttpResponse with the Excel file as attachment.

        Args:
            filename: The download filename (e.g., 'reporte.xlsx').

        Returns:
            HttpResponse with the Excel file.
        """
        from django.http import HttpResponse

        content = self.generate()
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
