frappe.ui.form.on('Work Order', {

    refresh(frm) {
        if (frm.doc.docstatus !== 1 || frm.doc.status !== 'In Process') {
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

                frm.add_custom_button(__('🖨 Print QR Codes'), () => {
                    print_qr_codes(frm, batch_no);
                }).css({
                    'background-color': '#5e64ff',
                    'color': 'white',
                    'font-weight': 'bold',
                    'border': 'none'
                });

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
            open_print_window(r.message, company, batch_no, frm.doc.name, false);

            frappe.call({
                method: 'batch_qr_code.utils.qr_generator.mark_as_printed',
                args: { batch_no }
            });
        }
    });
}


// ── Preview ────────────────────────────────────────────────────

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

    const labels_html = qr_codes.map((qr, idx) => `
        <div class="qr-label" id="label-${idx}">
            <img
                src="${escHtml(qr.qr_image)}"
                alt="${escHtml(qr.qr_code_id)}"
                onerror="this.style.display='none'"
            />
            <div class="label-actions no-print">
                <button class="btn-single-print" onclick="printSingle(${idx})">
                    🖨 Print this label
                </button>
            </div>
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
    padding: 14px 20px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
  }
  .toolbar-left h2 { font-size: 16px; color: #111827; margin-bottom: 2px; }
  .toolbar-left p  { font-size: 12px; color: #6b7280; }
  .toolbar-right   { display: flex; gap: 8px; align-items: center; }

  .btn-print-all {
    padding: 8px 18px; font-size: 13px; font-weight: bold;
    background: #5e64ff; color: #fff; border: none;
    border-radius: 5px; cursor: pointer;
  }
  .btn-print-all:hover { background: #4a50e0; }

  .btn-close {
    padding: 8px 18px; font-size: 13px;
    background: #fff; color: #374151;
    border: 1px solid #d1d5db; border-radius: 5px; cursor: pointer;
  }
  .btn-close:hover { background: #f9fafb; }

  .size-selector {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #374151;
  }
  .size-selector select {
    padding: 6px 10px;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    font-size: 13px;
    background: #fff;
    cursor: pointer;
  }

  .qr-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    justify-content: flex-start;
  }

  .qr-label {
    background: #fff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .qr-label img {
    width: 100%;
    height: auto;
    display: block;
  }

  .label-actions { width: 100%; }

  .btn-single-print {
    width: 100%;
    padding: 6px;
    font-size: 12px;
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #e5e7eb;
    border-radius: 5px;
    cursor: pointer;
    text-align: center;
  }
  .btn-single-print:hover {
    background: #5e64ff;
    color: #fff;
    border-color: #5e64ff;
  }

  .size-small  .qr-label { width: 80mm;  }
  .size-medium .qr-label { width: 100mm; }
  .size-large  .qr-label { width: 120mm; }

  .printing-single .qr-label          { display: none !important; }
  .printing-single .qr-label.printing { display: flex !important; }

  @media print {
    body { background: #fff; padding: 0; }
    .toolbar { display: none; }
    .no-print { display: none !important; }
    .qr-grid { gap: 0; }

    .qr-label {
      border: none;
      border-radius: 0;
      padding: 4mm;
      page-break-inside: avoid;
      break-inside: avoid;
      page-break-after: always;
      break-after: page;
    }

    .printing-single .qr-label.printing {
      width: 100% !important;
      padding: 8mm;
    }
    .printing-single .qr-label.printing img {
      width: 100%;
      max-width: 120mm;
      margin: 0 auto;
      display: block;
    }

    @page { margin: 5mm; size: auto; }
  }
</style>
</head>
<body>

<div class="toolbar no-print">
  <div class="toolbar-left">
    <h2>QR Labels — Batch ${escHtml(batch_no)}</h2>
    <p>Work Order: ${escHtml(wo_name)} &nbsp;|&nbsp; ${qr_codes.length} label(s) &nbsp;|&nbsp; Click a label to print individually</p>
  </div>
  <div class="toolbar-right">
    <div class="size-selector">
      <span>Sticker size:</span>
      <select onchange="changeSize(this.value)">
        <option value="small">Small (80mm)</option>
        <option value="medium" selected>Medium (100mm)</option>
        <option value="large">Large (120mm)</option>
      </select>
    </div>
    <button class="btn-print-all" onclick="printAll()">🖨 Print All</button>
    <button class="btn-close" onclick="window.close()">✕ Close</button>
  </div>
</div>

<div class="qr-grid size-medium" id="qr-grid">
  ${labels_html}
</div>

<script>
  function changeSize(size) {
    document.getElementById('qr-grid').className = 'qr-grid size-' + size;
  }

  function printSingle(idx) {
    var grid  = document.getElementById('qr-grid');
    var label = document.getElementById('label-' + idx);
    grid.classList.add('printing-single');
    label.classList.add('printing');
    window.print();
    setTimeout(function() {
      grid.classList.remove('printing-single');
      label.classList.remove('printing');
    }, 1000);
  }

  function printAll() {
    var grid = document.getElementById('qr-grid');
    grid.classList.remove('printing-single');
    document.querySelectorAll('.qr-label').forEach(function(l) {
      l.classList.remove('printing');
    });
    window.print();
  }

  ${auto_print ? 'window.onload = function() { setTimeout(printAll, 600); };' : ''}
<\/script>

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
