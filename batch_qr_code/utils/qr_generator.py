import io
import base64
import frappe
from frappe.utils import today


# ─────────────────────────────────────────────────────────────
# HOOKS
# ─────────────────────────────────────────────────────────────

def generate_qr_codes_for_batch(doc, method=None):
    """Fires on Batch.after_insert — only runs if batch_qty is already set."""
    try:
        qty = int(doc.batch_qty or 0)
    except (ValueError, TypeError):
        qty = 0

    if qty <= 0:
        return

    if doc.get("qr_codes"):
        return

    _create_qr_codes(doc, qty)


def on_batch_update(doc, method=None):
    """Fires on Batch.on_update — generates if qty set after insert."""
    if doc.get("qr_codes"):
        return

    try:
        qty = int(doc.batch_qty or 0)
    except (ValueError, TypeError):
        qty = 0

    if qty > 0:
        _create_qr_codes(doc, qty)


def generate_qr_from_work_order(doc, method=None):
    """
    Fires on Work Order.on_submit.
    Reads qty_to_manufacture and the batch linked to the
    finished goods item, then generates QR codes for that batch.
    """
    # Work Order must have a batch set on the finished item
    batch_no = doc.batch_no  # this is the FG batch on the Work Order

    if not batch_no:
        # Try to find batch from work order item rows if not on header
        for item in doc.get("required_items", []):
            if item.get("batch_no"):
                batch_no = item.batch_no
                break

    if not batch_no:
        frappe.msgprint(
            "⚠ No Batch No found on this Work Order. QR codes were not generated.",
            alert=True,
            indicator="orange"
        )
        return

    qty = int(doc.qty_to_manufacture or 0)

    if qty <= 0:
        frappe.msgprint(
            "⚠ Qty to Manufacture is 0. QR codes were not generated.",
            alert=True,
            indicator="orange"
        )
        return

    # Check if QR codes already exist for this batch
    batch = frappe.get_doc("Batch", batch_no)
    if batch.get("qr_codes"):
        frappe.msgprint(
            f"ℹ QR codes already exist for Batch {batch_no}.",
            alert=True,
            indicator="blue"
        )
        return

    # Set batch_qty from Work Order qty if not already set
    if not batch.batch_qty:
        batch.batch_qty = qty
        batch.save(ignore_permissions=True)
        frappe.db.commit()
        batch.reload()

    _create_qr_codes(batch, qty)


# ─────────────────────────────────────────────────────────────
# CORE GENERATION
# ─────────────────────────────────────────────────────────────

def _create_qr_codes(doc, qty):
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H
    from PIL import Image, ImageDraw, ImageFont

    company   = frappe.defaults.get_global_default("company") or ""
    item_doc  = frappe.get_doc("Item", doc.item)
    item_name = item_doc.item_name or doc.item
    prod_date = str(doc.manufacturing_date or today())
    batch_no  = doc.name

    rows = []

    for unit in range(1, qty + 1):
        qr_id = f"{batch_no}-{unit:04d}"

        # ── Payload (what scanner reads) ──────────────────────
        payload = (
            f"Company: {company}\n"
            f"Item Code: {doc.item}\n"
            f"Date of Production: {prod_date}\n"
            f"Batch No: {batch_no}\n"
            f"Unit: {unit} of {qty}\n"
            f"ID: {qr_id}\n"
            f"----------------------------------------\n"
            f"ITEM: {item_name}"
        )

        # ── Generate QR image ─────────────────────────────────
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_H,
            box_size=8,
            border=2,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # ── Add item name text below the QR image ─────────────
        qr_width, qr_height = qr_img.size
        label_height = 40
        final_img = Image.new("RGB", (qr_width, qr_height + label_height), "white")
        final_img.paste(qr_img, (0, 0))

        draw = ImageDraw.Draw(final_img)

        # Load font — tries Linux, then macOS, then falls back to default
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
            )
        except Exception:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            except Exception:
                font = ImageFont.load_default()

        # Truncate if too long
        display_name = item_name if len(item_name) <= 35 else item_name[:32] + "..."

        # Centre the text in the white strip
        bbox = draw.textbbox((0, 0), display_name, font=font)
        text_width  = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = max((qr_width - text_width) // 2, 4)
        text_y = qr_height + (label_height - text_height) // 2

        draw.text((text_x, text_y), display_name, fill="black", font=font)

        # ── Save final image to bytes ─────────────────────────
        buf = io.BytesIO()
        final_img.save(buf, format="PNG")
        buf.seek(0)
        img_bytes = buf.read()

        # ── Save as File attachment ───────────────────────────
        file_name = f"QR_{batch_no}_{unit:04d}.png"
        file_doc = frappe.get_doc({
            "doctype":             "File",
            "file_name":           file_name,
            "attached_to_doctype": "Batch",
            "attached_to_name":    batch_no,
            "content":             img_bytes,
            "is_private":          0,
        })
        file_doc.flags.ignore_permissions = True
        file_doc.insert()

        rows.append({
            "qr_code_id":      qr_id,
            "batch_no":        batch_no,
            "item_code":       doc.item,
            "item_name":       item_name,
            "production_date": prod_date,
            "unit_number":     unit,
            "total_qty":       qty,
            "qr_image":        file_doc.file_url,
            "qr_payload":      payload,
            "is_printed":      0,
        })

    for row in rows:
        doc.append("qr_codes", row)

    doc.flags.ignore_validate_update_after_submit = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.msgprint(
        f"✅ {qty} QR code(s) generated for Batch <b>{batch_no}</b>.",
        alert=True,
        indicator="green",
    )


# ─────────────────────────────────────────────────────────────
# WHITELISTED API
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_qr_codes_for_batch(batch_no):
    if not frappe.db.exists("Batch", batch_no):
        frappe.throw(f"Batch {batch_no} not found.")

    batch    = frappe.get_doc("Batch", batch_no)
    item_doc = frappe.get_doc("Item", batch.item)

    result = []
    for row in batch.get("qr_codes", []):
        result.append({
            "qr_code_id":      row.qr_code_id,
            "batch_no":        batch_no,
            "item_code":       batch.item,
            "item_name":       item_doc.item_name,
            "production_date": str(row.production_date or batch.manufacturing_date or ""),
            "unit_number":     row.unit_number,
            "total_qty":       row.total_qty,
            "qr_image":        row.qr_image,
            "is_printed":      row.is_printed,
        })

    return result


@frappe.whitelist()
def mark_as_printed(batch_no):
    batch = frappe.get_doc("Batch", batch_no)
    for row in batch.get("qr_codes", []):
        row.is_printed = 1
    batch.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "batch_no": batch_no}


@frappe.whitelist()
def regenerate_qr_codes(batch_no):
    batch = frappe.get_doc("Batch", batch_no)

    # Delete old File attachments
    old_files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Batch",
            "attached_to_name":    batch_no,
            "file_name":           ["like", "QR_%"],
        },
        pluck="name",
    )
    for f in old_files:
        frappe.delete_doc("File", f, ignore_permissions=True)

    # Clear child table
    batch.set("qr_codes", [])
    batch.save(ignore_permissions=True)

    # Re-generate
    qty = int(batch.batch_qty or 0)
    if qty > 0:
        _create_qr_codes(batch, qty)

    return {"status": "ok", "generated": qty}


def get_qr_image_base64(file_url):
    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        content  = file_doc.get_content()
        b64      = base64.b64encode(content).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""
