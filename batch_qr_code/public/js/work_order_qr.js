frappe.ui.form.on('Work Order', {

    refresh(frm) {
        // Only show QR buttons when Work Order is In Process
        if (frm.doc.docstatus !== 1 || frm.doc.status !== 'In Process') {
            // Show a subtle indicator if submitted but not yet started
            if (frm.doc.docstatus === 1 && frm.doc.status !== 'In Process') {
                frm.dashboard.set_headline(
                    `⏸ QR printing is available once the Work Order status is <b>In Process</b>`
                );
            }
            return;
        }

        get_work_order_batch(frm.doc.name, frm.doc.production_item)
            .then(batch_no => {
                if (!batch_no) {
                    frm.dashboard.set_headline(
                        `⚠ No batch found for this Work Order. QR codes unavailable.`
                    );
                    return;
                }

                // ── Primary print button ───────────────────────
                frm.add_custom_button(__('🖨 Print QR Codes'), () => {
                    print_qr_codes(frm, batch_no);
                }).css({
                    'background-color': '#5e64ff',
                    'color': 'white',
                    'font-weight': 'bold',
                    'border': 'none'
                });

                // ── Actions menu ───────────────────────────────
                frm.add_custom_button(__('👁 Preview QR Codes'), () => {
                    preview_qr_codes(frm, batch_no);
                }, __('Actions'));

                frm.add_custom_button(__('🔄 Regenerate QR Codes'), () => {
                    frappe.confirm(
                        __(`Regenerate all QR codes for Batch <b>${batch_no}</b>?<br>This will delete existing ones.`),
                        () => {
                            frappe.call({
                                method: 'batch_qr_code.utils.qr_generator.regenerate_qr_codes',
                                args: { batch_no },
                                freeze: true,
                                freeze_message: __('Regenerating QR codes...'),
                                callback(r) {
                                    if (r.message) {
                                        if (r.message.status === 'queued') {
                                            frappe.show_alert({
                                                message: __(r.message.message),
                                                indicator: 'blue'
                                            });
                                        } else {
                                            frappe.show_alert({
                                                message: __(`✅ ${r.message.generated} QR code(s) generated`),
                                                indicator: 'green'
                                            });
                                        }
                                    }
                                }
                            });
                        }
                    );
                }, __('Actions'));

            });
    }

});


function get_work_order_batch(wo_name, production_item) {
    return new Promise((resolve) => {
        frappe.call({
            method: 'batch_qr_code.utils.qr_generator.get_batch_for_work_order',
            args: { wo_name, production_item },
            callback(r) {
                resolve(r.message || null);
            }
        });
    });
}


function print_qr_codes(frm, batch_no) {
    frappe.call({
        method: 'batch_qr_code.utils.qr_generator.get_qr_codes_for_batch',
        args: { batch_no },
        freeze: true,
        freeze_message: __('Loading QR codes...'),
        callback(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint({
                    title: __('No QR Codes Found'),
                    message: __(
                        `No QR codes found for Batch <b>${batch_no}</b>.<br><br>` +
                        `Try <b>Actions → Regenerate QR Codes</b>.`
                    ),
                    indicator: 'orange'
                });
                return;
            }

            const company = frappe.boot.sysdefaults.company || '';
            open_print_window(r.message, company, batch_no, frm.doc.name, true);

            frappe.call({
                method: 'batch_qr_code.utils.qr_generator.mark_as_printed',
                args: { batch_no }
            });
        }
    });
}


function preview_qr_codes(frm, batch_no) {
    frappe.call({
        method: 'batch_qr_code.utils.qr_generator.get_qr_codes_for_batch',
        args: { batch_no },
        freeze: true,
        freeze_message: __('Loading QR codes...'),
        callback(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint({
                    title: __('No QR Codes Found'),
                    message: __(
                        `No QR codes found for Batch <b>${batch_no}</b>.<br><br>` +
                        `Try <b>Actions → Regenerate QR Codes</b>.`
                    ),
                    indicator: 'orange'
                });
                return;
            }

            const company = frappe.boot.sysdefaults.company || '';
            open_print_window(r.message, company, batch_no, frm.doc.name, false);
        }
    });
}


function open_print_window(qr_codes, company, batch_no, wo_name, auto_print) {

    const labels_html = qr_codes.map(qr => `
        <div class="qr-label">
            <img
                src="${qr.qr_image}"
                alt="${escHtml(qr.qr_code_id)}"
                onerror="this.style.display='none'"
            />
        </div>
    `).join('');

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>QR Labels — ${escHtml(batch_no)}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: Arial, Helvetica, sans-serif;
    background: #f3f4f6;
    padding: 20px;
  }
  .toolbar {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .toolbar-left h2 { font-size: 16px; color: #111827; margin-bottom: 2px; }
  .toolbar-left p  { font-size: 12px; color: #6b7280; }
  .toolbar-right   { display: flex; gap: 8px; }
  .btn-print {
    padding: 9px 22px; font-size: 14px; font-weight: bold;
    background: #5e64ff; color: #fff; border: none;
    border-radius: 5px; cursor: pointer;
  }
  .btn-print:hover { background: #4a50e0; }
  .btn-close {
    padding: 9px 22px; font-size: 14px;
    background: #fff; color: #374151;
    border: 1px solid #d1d5db; border-radius: 5px; cursor: pointer;
  }
  .btn-close:hover { background: #f9fafb; }
  .qr-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: flex-start;
  }
  .qr-label {
    background: #fff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 8px;
    display: inline-block;
    page-break-inside: avoid;
    break-inside: avoid;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .qr-label img {
    width: 180px;
    height: auto;
    display: block;
  }
  @media print {
    body { background: #fff; padding: 5mm; }
    .toolbar { display: none; }
    .qr-grid { gap: 5mm; }
    .qr-label {
      border: 0.5px solid #ccc;
      border-radius: 4px;
      padding: 3mm;
      box-shadow: none;
    }
    .qr-label img { width: 50mm; height: auto; }
    @page { margin: 8mm; size: A4; }
  }
</style>
</head>
<body>
<div class="toolbar">
  <div class="toolbar-left">
    <h2>QR Labels — Batch ${escHtml(batch_no)}</h2>
    <p>Work Order: ${escHtml(wo_name)} &nbsp;|&nbsp; ${qr_codes.length} label(s)</p>
  </div>
  <div class="toolbar-right">
    <button class="btn-print" onclick="window.print()">🖨 Print</button>
    <button class="btn-close" onclick="window.close()">✕ Close</button>
  </div>
</div>
<div class="qr-grid">
  ${labels_html}
</div>
${auto_print ? '<script>window.onload = () => setTimeout(() => window.print(), 600);<\/script>' : ''}
</body>
</html>`;

    const w = window.open('', '_blank', 'width=1000,height=750,scrollbars=yes');
    if (!w) {
        frappe.msgprint({
            title: __('Popup Blocked'),
            message: __('Please allow popups for this site and try again.'),
            indicator: 'red'
        });
        return;
    }
    w.document.write(html);
    w.document.close();
}


function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
