frappe.ui.form.on('Batch', {

    refresh(frm) {
        if (frm.is_new()) return;

        const qr_count = (frm.doc.qr_codes || []).length;

        if (qr_count > 0) {
            frm.dashboard.set_headline(
                ` ${qr_count} QR code(s) generated for this batch`
            );

            frm.add_custom_button(__('🖨 Print QR Codes'), () => {
                print_qr_codes(frm);
            }).css({
                'background-color': '#5e64ff',
                'color': 'white',
                'font-weight': 'bold',
                'border': 'none'
            });

        } else {
            frm.dashboard.set_headline(
                `⚠ No QR codes found — click Regenerate to create them`
            );
        }

        frm.add_custom_button(__('🔄 Regenerate QR Codes'), () => {
            frappe.confirm(
                __('This will delete all existing QR codes and regenerate. Continue?'),
                () => {
                    frappe.call({
                        method: 'batch_qr_code.utils.qr_generator.regenerate_qr_codes',
                        args: { batch_no: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Generating QR codes...'),
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
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        }, __('Actions'));

    }

});


function print_qr_codes(frm) {
    frappe.call({
        method: 'batch_qr_code.utils.qr_generator.get_qr_codes_for_batch',
        args: { batch_no: frm.doc.name },
        freeze: true,
        freeze_message: __('Loading QR codes...'),
        callback(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint({
                    title: __('No QR Codes'),
                    message: __('No QR codes found for this batch. Try clicking Regenerate QR Codes.'),
                    indicator: 'orange'
                });
                return;
            }

            const company = frappe.boot.sysdefaults.company || '';
            open_print_window(r.message, company, frm.doc.name, frm.doc.name, false);

            frappe.call({
                method: 'batch_qr_code.utils.qr_generator.mark_as_printed',
                args: { batch_no: frm.doc.name }
            });
        }
    });
}



function open_print_window(qr_codes, company, batch_no, ref_name, auto_print) {

    const labels_html = qr_codes.map((qr, idx) => `
        <div class="qr-label" id="label-${idx}">
            <div class="qr-side">
                <img
                    src="${escHtml(qr.qr_image)}"
                    alt="${escHtml(qr.qr_code_id)}"
                    onerror="this.style.display='none'"
                />
            </div>
            <div class="detail-side">
                <div class="detail-item-name">${escHtml(qr.item_name || qr.item_code)}</div>
                <div class="detail-row"><span class="detail-label">Batch:</span> ${escHtml(qr.batch_no)}</div>
                <div class="detail-row"><span class="detail-label">Unit:</span> ${escHtml(String(qr.unit_number))} / ${escHtml(String(qr.total_qty))}</div>
                <div class="detail-row"><span class="detail-label">Date:</span> ${escHtml(qr.production_date)}</div>
            </div>
            <div class="label-actions no-print">
                <button class="btn-single-print" onclick="printSingle(${idx})">🖨</button>
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
    gap: 12px;
    justify-content: flex-start;
  }

  .qr-label {
    background: #fff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    display: flex;
    flex-direction: row;
    align-items: stretch;
    width: 320px;
    height: 160px;
    overflow: hidden;
    position: relative;
  }

  .qr-side {
    flex-shrink: 0;
    width: 160px;
    height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
    border-right: 1px solid #e5e7eb;
  }

  .qr-side img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }

  .detail-side {
    flex: 1;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    overflow: hidden;
  }

  .detail-item-name {
    font-size: 12px;
    font-weight: bold;
    color: #111827;
    line-height: 1.2;
    margin-bottom: 4px;
    word-break: break-word;
  }

  .detail-row {
    font-size: 11px;
    color: #374151;
    line-height: 1.3;
  }

  .detail-label {
    color: #6b7280;
    font-size: 10px;
  }

  .label-actions {
    position: absolute;
    bottom: 4px;
    right: 4px;
  }

  .btn-single-print {
    padding: 4px 8px;
    font-size: 12px;
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    cursor: pointer;
  }
  .btn-single-print:hover {
    background: #5e64ff;
    color: #fff;
    border-color: #5e64ff;
  }

  .printing-single .qr-label          { display: none !important; }
  .printing-single .qr-label.printing { display: flex !important; }

  @media print {
    body { background: #fff; padding: 0; margin: 0; }
    .toolbar { display: none; }
    .no-print { display: none !important; }
    .qr-grid { display: block; }

    .qr-label {
      display: flex;
      flex-direction: row;
      width: 2in;
      height: 1in;
      border: none;
      border-radius: 0;
      page-break-after: always;
      break-after: page;
      page-break-inside: avoid;
      break-inside: avoid;
      overflow: hidden;
    }

    .qr-side {
      width: 1in;
      height: 1in;
      border-right: none;
    }

    .qr-side img {
      width: 1in;
      height: 1in;
      object-fit: contain;
    }

    .detail-side {
      width: 1in;
      padding: 2mm 3mm;
      gap: 1mm;
    }

    .detail-item-name {
      font-size: 6.5pt;
      margin-bottom: 1mm;
    }

    .detail-row {
      font-size: 6pt;
    }

    .detail-label {
      font-size: 5.5pt;
    }

    @page { size: 2in 1in; margin: 0; }
  }
</style>
</head>
<body>

<div class="toolbar no-print">
  <div class="toolbar-left">
    <h2>QR Labels — Batch ${escHtml(batch_no)}</h2>
    <p>${qr_codes.length} label(s) &nbsp;|&nbsp; Click a label to print individually</p>
  </div>
  <div class="toolbar-right">
    <div class="size-selector">
      <span style="font-size:12px;color:#6b7280;">Sticker: 2in × 1in</span>
    </div>
    <button class="btn-print-all" onclick="printAll()">🖨 Print All</button>
    <button class="btn-close" onclick="window.close()">✕ Close</button>
  </div>
</div>

<div class="qr-grid size-medium" id="qr-grid">
  ${labels_html}
</div>

<script>
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
