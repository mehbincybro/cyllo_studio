# -*- coding: utf-8 -*-
from odoo import http, fields
from datetime import timedelta
from odoo.http import request
import json
import logging
_logger = logging.getLogger(__name__)


def _html_page(title, body_html, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/remixicon@3.5.0/fonts/remixicon.css" rel="stylesheet">
  {extra_head}
  <link href="/cyllo_analytics/static/src/css/public_share.css" rel="stylesheet">
</head>
<body>{body_html}</body>
</html>"""


def _not_found_html():
    body = """
<div class="cy-page-container">
  <div class="cy-error-card">
    <div class="cy-error-code">404</div>
    <h2 class="cy-error-title">Dashboard Not Found</h2>
    <p class="cy-error-msg">This share link is invalid, expired or has been revoked.</p>
  </div>
</div>"""
    return _html_page("Dashboard Not Found", body)


def _expired_html(name):
    body = f"""
<div class="cy-page-container">
  <div class="cy-error-card">
    <div class="cy-error-icon"><i class="ri-time-line"></i></div>
    <h2 class="cy-error-title">Link Expired</h2>
    <p class="cy-error-msg">The shared link for <strong>{name}</strong> has expired and is no longer accessible.</p>
  </div>
</div>"""
    return _html_page("Link Expired", body)


def _dashboard_html(dashboard_name, token):
    extra_head = """
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.3.0/exceljs.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
"""

    body = f"""
<div id="app" data-token="{token}" data-name="{dashboard_name}">
  <header class="cy-header">
    <div>
      <h1 id="dash-title">{dashboard_name}</h1>
      <div class="cy-period" id="period-display"><i class="ri-calendar-line"></i> Loading period...</div>
    </div>
    <div class="cy-actions">
      <button id="btn-pdf"  class="cy-btn cy-btn-pdf"  onclick="exportToPDF()"><i class="ri-file-pdf-line"></i>Download PDF</button>
      <button id="btn-xlsx" class="cy-btn cy-btn-xlsx" onclick="exportToExcel()"><i class="ri-file-excel-2-line"></i>Download XLSX</button>
      <span class="cy-brand">Cyllo <span>Analytics</span></span>
    </div>
  </header>

  <div class="cy-content">
    <div id="main-grid" class="cy-grid">
      <div class="cy-loader">
        <div class="cy-spinner"></div>
        <span>Preparing Analytics...</span>
      </div>
    </div>
  </div>

  <footer class="cy-footer">Powered by <strong style="color:#344BD2">Cyllo Analytics</strong> · Intelligence Reimagined</footer>
</div>

<script>
(function () {{
  var liveData = {{ sheets: [], name: '{dashboard_name}' }};
  var chartInstances = {{}};

  // ── Theme ────────────────────────────────────────────────────────
  function applyTheme(theme) {{
    theme = theme || {{}};
    var root = document.documentElement;
    var colors = theme.theme_color_ids || ['#5c5fe3','#344BD2','#10B981','#F59E0B','#EF4444'];
    liveData.colors = colors;
    liveData.primary = colors[0] || '#5c5fe3';
    liveData.sheetBg = theme.body_header_background || '#f0f1ff';
    liveData.sheetTitle = theme.header_title_color || '#0f172a';

    root.style.setProperty('--primary', liveData.primary);
    if (theme.background) root.style.setProperty('--bg', theme.background);

    echarts.registerTheme('cyllo', {{
      color: colors,
      backgroundColor: 'transparent',
      textStyle: {{ color: theme.label_text || '#334155' }},
      legend: {{ textStyle: {{ color: theme.subtitle || '#64748b' }} }},
      categoryAxis: {{ axisLabel: {{ color: theme.subtitle || '#64748b' }} }},
      valueAxis: {{ axisLabel: {{ color: theme.subtitle || '#64748b' }} }}
    }});
  }}

  // ── Render dashboard ─────────────────────────────────────────────
  function renderDashboard(data) {{
    var grid = document.getElementById('main-grid');
    grid.innerHTML = '';
    var sheets = data.sheets || [];
    if (!sheets.length) {{
      grid.innerHTML = '<div class="cy-loader"><span>No charts found in this dashboard.</span></div>';
      return;
    }}
    var colors = liveData.colors || ['#5c5fe3','#344BD2','#10B981','#F59E0B'];
    sheets.forEach(function (sheet) {{
      var card = document.createElement('div');
      card.className = 'cy-card';
      var isKpi = sheet.type === 'kpi' || sheet.type === 'financial_kpi';
      card.innerHTML =
        '<div class="cy-card-header" style="background:' + liveData.sheetBg +
          ';color:' + liveData.sheetTitle + '">' +
          '<span class="cy-card-title">' + (sheet.name || 'Chart') + '</span>' +
          '<i class="ri-download-2-line cy-card-dl sheet-png-dl-btn" title="Export PNG"></i>' +
        '</div>' +
        '<div class="cy-card-body">' +
          '<div id="box-' + sheet.id + '" class="' + (isKpi ? 'cy-kpi-box' : 'cy-chart-box') + '"></div>' +
        '</div>';
      grid.appendChild(card);
      var dlBtn = card.querySelector('.sheet-png-dl-btn');
      if (dlBtn) dlBtn.onclick = function() {{ exportSingleSheetPNG(String(sheet.id)); }};

      var box = document.getElementById('box-' + sheet.id);
      try {{
        if (isKpi) renderKPI(box, sheet, liveData.primary);
        else drawChart(box, sheet, colors);
      }} catch (e) {{
        console.error('Render error for ' + sheet.name, e);
        box.innerHTML = '<span style="color:#ef4444;font-size:13px">Render Failed: ' + e.message + '</span>';
      }}
    }});
  }}

  function renderKPI(container, sheet, color) {{
    var res = sheet.result || [];
    var val = 0;
    if (res.length && res[0]) {{
      var firstVal = Object.values(res[0]).find(function (v) {{ return typeof v === 'number'; }});
      val = (firstVal !== undefined) ? firstVal : 0;
    }}
    container.innerHTML =
      '<div class="cy-kpi-val">' + Number(val).toLocaleString() + '</div>' +
      '<div class="cy-kpi-bar"><div class="cy-kpi-fill" style="background:' + color + '"></div></div>';
  }}

  function drawChart(container, sheet, colors) {{
    var chart = echarts.init(container, 'cyllo');
    chartInstances[sheet.id] = chart;
    var results = sheet.result || [];
    if (!results.length) {{
      container.innerHTML = '<div class="cy-loader"><span>No data available</span></div>';
      return;
    }}
    var keys = Object.keys(results[0]);
    var dimKey = keys.find(function (k) {{
      return k.toLowerCase().includes('name') || k.toLowerCase().includes('label');
    }}) || keys[0];
    var measureKeys = keys.filter(function (k) {{
      return k !== dimKey && typeof results[0][k] === 'number' && !k.endsWith('_id');
    }});
    if (!measureKeys.length) measureKeys = [keys[1] || keys[0]];

    var type = (sheet.type || 'bar').toLowerCase();
    var isPie = type === 'pie' || type === 'doughnut';
    var series = measureKeys.map(function (mKey) {{
      return {{
        name: mKey.replace(/_/g, ' ').replace(/\\b\\w/g, function (c) {{ return c.toUpperCase(); }}),
        type: isPie ? 'pie' : type,
        radius: type === 'doughnut' ? ['40%','70%'] : (type === 'pie' ? '65%' : undefined),
        data: results.map(function (r) {{ return {{ name: String(r[dimKey] || ''), value: r[mKey] || 0 }}; }})
      }};
    }});

    chart.setOption({{
      color: colors,
      tooltip: {{ trigger: isPie ? 'item' : 'axis' }},
      legend: {{ bottom: 0 }},
      grid: {{ containLabel: true, bottom: 50, top: 20, left: 10, right: 10 }},
      xAxis: isPie ? undefined : {{ type: 'category', data: results.map(function (r) {{ return String(r[dimKey] || ''); }}), axisLabel: {{ interval: 0, rotate: results.length > 8 ? 30 : 0, overflow: 'truncate', width: 90 }} }},
      yAxis: isPie ? undefined : {{ type: 'value' }},
      series: series
    }});

    window.addEventListener('resize', function () {{ chart.resize(); }});
  }}

  // ── Exports ──────────────────────────────────────────────────────
  window.exportToExcel = async function () {{
    var btn = document.getElementById('btn-xlsx');
    var orig = btn.innerHTML;
    btn.innerHTML = '<i class="ri-loader-4-line"></i>Preparing...';
    btn.disabled = true;
    try {{
      var wb = new ExcelJS.Workbook();
      for (var s of (liveData.sheets || [])) {{
        var ws = wb.addWorksheet((s.name || 'Sheet').substring(0, 31).replace(/[\\[\\]\\?\\*\\\\\\/]/g, ''));
        var title = ws.getCell('A1');
        title.value = s.name; title.font = {{ bold: true, size: 14, color: {{ argb: 'FF344BD2' }} }};
        ws.getColumn(1).width = 28; ws.getColumn(2).width = 16; ws.getColumn(3).width = 16;
        var chart = chartInstances[s.id];
        if (chart) {{
          var b64 = chart.getDataURL({{ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' }});
          var imgId = wb.addImage({{ base64: b64, extension: 'png' }});
          ws.addImage(imgId, {{ tl: {{ col: 0.2, row: 2.5 }}, ext: {{ width: 900, height: 420 }} }});
        }}
      }}
      var buf = await wb.xlsx.writeBuffer();
      var blob = new Blob([buf], {{ type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }});
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (liveData.name || 'Dashboard').replace(/\\s/g, '_') + '.xlsx';
      a.click();
    }} catch (e) {{ console.error('XLSX error', e); alert('Export failed: ' + e.message); }}
    finally {{ btn.innerHTML = orig; btn.disabled = false; }}
  }};

  window.exportSingleSheet = async function (sheetId) {{
    var sheet = (liveData.sheets || []).find(function (s) {{ return String(s.id) === sheetId; }});
    if (!sheet) return;
    try {{
      var wb = new ExcelJS.Workbook();
      var ws = wb.addWorksheet((sheet.name || 'Sheet').substring(0, 31).replace(/[\\[\\]\\?\\*\\\\\\/]/g, ''));
      ws.getCell('A1').value = sheet.name;
      ws.getCell('A1').font = {{ bold: true, size: 14, color: {{ argb: 'FF344BD2' }} }};
      ws.getColumn(1).width = 28;
      var chart = chartInstances[sheetId];
      if (chart) {{
        var b64 = chart.getDataURL({{ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' }});
        var imgId = wb.addImage({{ base64: b64, extension: 'png' }});
        ws.addImage(imgId, {{ tl: {{ col: 0.2, row: 2.5 }}, ext: {{ width: 900, height: 420 }} }});
      }}
      var buf = await wb.xlsx.writeBuffer();
      var blob = new Blob([buf], {{ type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }});
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (sheet.name || 'Chart').replace(/\\s/g, '_') + '.xlsx';
      a.click();
    }} catch (e) {{ console.error('Single XLSX error', e); }}
  }};

  window.exportSingleSheetPNG = async function (sheetId) {{
    var sheet = (liveData.sheets || []).find(function (s) {{ return String(s.id) === sheetId; }});
    var chart = chartInstances[sheetId];
    if (chart) {{
      var b64 = chart.getDataURL({{ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' }});
      var a = document.createElement('a');
      a.href = b64;
      a.download = (sheet ? sheet.name : 'Chart').replace(/\\s/g, '_') + '.png';
      a.click();
    }} else {{
      var cardBox = document.getElementById('box-' + sheetId);
      var cardContainer = cardBox ? cardBox.closest('.cy-card') : null;
      if (cardContainer && typeof html2canvas !== 'undefined') {{
        try {{
          var canvas = await html2canvas(cardContainer, {{ scale: 2, backgroundColor: '#ffffff' }});
          var b64 = canvas.toDataURL('image/png');
          var a = document.createElement('a');
          a.href = b64;
          a.download = (sheet ? sheet.name : 'KPI').replace(/\\s/g, '_') + '.png';
          a.click();
        }} catch(e) {{
          console.error("KPI export error", e);
        }}
      }}
    }}
  }};

  window.exportToPDF = async function () {{
    var btn = document.getElementById('btn-pdf');
    var orig = btn.innerHTML;
    btn.innerHTML = '<i class="ri-loader-4-line"></i>Generating...';
    btn.disabled = true;
    try {{
      var grid = document.getElementById('main-grid');
      var canvas = await html2canvas(grid, {{ scale: 2, useCORS: true, logging: false, backgroundColor: '#f1f5fb' }});
      var imgData = canvas.toDataURL('image/png');
      var {{ jsPDF }} = window.jspdf;
      var pdf = new jsPDF('p', 'mm', 'a4');
      var pgW = pdf.internal.pageSize.getWidth();
      var imgW = pgW - 20;
      var imgH = (canvas.height * imgW) / canvas.width;
      pdf.setFont('helvetica', 'bold'); pdf.setFontSize(16);
      pdf.text(liveData.name || 'Dashboard Report', 10, 15);
      pdf.setFont('helvetica', 'normal'); pdf.setFontSize(9);
      pdf.text(document.getElementById('period-display').innerText, 10, 22);
      pdf.addImage(imgData, 'PNG', 10, 30, imgW, imgH);
      pdf.save((liveData.name || 'Dashboard').replace(/\\s/g, '_') + '.pdf');
    }} catch (e) {{ console.error('PDF error', e); alert('PDF export failed: ' + e.message); }}
    finally {{ btn.innerHTML = orig; btn.disabled = false; }}
  }};

  // ── Bootstrap ────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', async function () {{
    var token = document.getElementById('app').dataset.token;
    try {{
      var res = await fetch('/dashboard/share/data/' + token);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var data = await res.json();
      if (data.error) throw new Error(data.error);
      liveData = data;
      applyTheme(data.theme);
      renderDashboard(data);
      if (data.date_from && data.date_to) {{
        document.getElementById('period-display').innerHTML =
          '<i class="ri-calendar-line"></i> ' + data.date_from + ' to ' + data.date_to;
      }}
    }} catch (e) {{
      console.error('Dashboard load error', e);
      document.getElementById('main-grid').innerHTML =
        '<div class="cy-loader">' +
          '<i class="ri-error-warning-line" style="font-size:40px;color:#ef4444"></i>' +
          '<span style="color:#ef4444">Failed to load dashboard: ' + e.message + '</span>' +
          '<button class="cy-btn cy-btn-pdf" style="margin-top:12px" onclick="location.reload()">' +
            '<i class="ri-refresh-line"></i>Retry</button>' +
        '</div>';
    }}
  }});
}})();
</script>"""
    return _html_page(f"{dashboard_name} · Cyllo Analytics", body, extra_head)


class DashboardPublicShare(http.Controller):

    @http.route('/dashboard/share/data/<string:token>', type='http',
                auth='public', website=False, csrf=False)
    def share_dashboard_data(self, token, **kwargs):
        """JSON endpoint to fetch public dashboard data."""
        share_link = request.env['dashboard.share.link'].sudo().search([
            ('access_token', '=', token),
            ('is_active', '=', True),
        ], limit=1)

        if not share_link or (share_link.expiry_date and share_link.expiry_date < fields.Datetime.now()):
            return request.make_response(
                json.dumps({'error': 'Unauthorized or Expired'}),
                headers=[('Content-Type', 'application/json; charset=utf-8')]
            )

        dashboard = share_link.dashboard_id.sudo()
        if dashboard.company_id:
            dashboard = dashboard.with_company(dashboard.company_id)

        sheets_data = dashboard.get_data()
        theme_data = {}
        if dashboard.theme_id:
            theme_data = dashboard.theme_id.read_theme()

        for sheet_data in sheets_data:
            opts = sheet_data.get('dashboard_sheet_option_ids', [])
            attr_vals = opts[0].get('attributes', {}) if opts else {}
            sheet_data['y'] = attr_vals.get('y', 0)
            sheet_data['x'] = attr_vals.get('x', 0)

            sql = sheet_data.get('query')
            if sql:
                try:
                    res = dashboard.with_context(bypass_dashboard_security=True).sql_execute(sql)
                    limit = sheet_data.get('limit')
                    if limit and isinstance(limit, int) and limit > 0:
                        res = res[:limit]
                    sheet_data['result'] = res if isinstance(res, list) else []
                except Exception:
                    _logger.exception("SQL error for sheet '%s'", sheet_data.get('name'))
                    sheet_data['result'] = []
            else:
                sheet_data['result'] = []

        sheets_data.sort(key=lambda s: (s.get('y', 0), s.get('x', 0)))

        today = fields.Date.today()
        date_from = today.replace(month=1, day=1)
        date_to = today.replace(month=12, day=31)

        payload = {
            'sheets': sheets_data,
            'theme': theme_data,
            'name': dashboard.name,
            'date_from': date_from.strftime('%Y/%m/%d'),
            'date_to': date_to.strftime('%Y/%m/%d'),
        }

        return request.make_response(
            json.dumps(payload, default=str),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/dashboard/share/<string:token>', type='http',
                auth='public', website=False, csrf=False)
    def share_dashboard(self, token, **kwargs):
        """Public route to view a shared dashboard by token."""
        share_link = request.env['dashboard.share.link'].sudo().search([
            ('access_token', '=', token),
            ('is_active', '=', True),
        ], limit=1)

        if not share_link:
            _logger.warning("Public share: token not found or inactive: %s", token)
            html = _not_found_html()
            return request.make_response(
                html,
                headers=[('Content-Type', 'text/html; charset=utf-8')]
            )

        if share_link.expiry_date and share_link.expiry_date < fields.Datetime.now():
            share_link.sudo().write({'is_active': False})
            html = _expired_html(share_link.dashboard_id.name)
            return request.make_response(
                html,
                headers=[('Content-Type', 'text/html; charset=utf-8')]
            )

        dashboard = share_link.dashboard_id.sudo()
        html = _dashboard_html(dashboard.name, token)
        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html; charset=utf-8')]
        )
