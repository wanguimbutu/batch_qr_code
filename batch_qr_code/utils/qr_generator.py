import io
import base64
import uuid
import hashlib
import frappe
from frappe.utils import today

_SKIP_UPDATE_HOOK = {}

# ─────────────────────────────────────────────────────────────
# ITEM GROUP EXCLUSIONS
# ─────────────────────────────────────────────────────────────

EXCLUDED_ITEM_GROUPS = {
    "Packaging Materials",
    "Raw Material",
    "Work In Progress",
    "Others",
}

def _is_item_excluded(item_code):
    """Return True if the item belongs to an excluded item group."""
    item_group = frappe.db.get_value("Item", item_code, "item_group")
    if not item_group:
        return False
    # Also check parent groups up the tree
    group = item_group
    for _ in range(5):  # max 5 levels up
        if group in EXCLUDED_ITEM_GROUPS:
            return True
        parent = frappe.db.get_value("Item Group", group, "parent_item_group")
        if not parent or parent == group:
            break
        group = parent
    return False


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _generate_unique_id(batch_no, unit):
    """Generate a short unpredictable unique ID per unit."""
    raw = f"{batch_no}-{unit}-{uuid.uuid4()}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()[:10].upper()
    return hashed


def _should_use_background(qty):
    """Use background job for anything over 20 units."""
    return qty > 20


# ─────────────────────────────────────────────────────────────
# HOOKS
# ─────────────────────────────────────────────────────────────

def generate_qr_codes_for_batch(doc, method=None):
    if _is_item_excluded(doc.item):
        return

    try:
        qty = int(doc.batch_qty or 0)
    except (ValueError, TypeError):
        qty = 0

    if qty <= 0:
        wo_name = None

        if doc.get("reference_doctype") == "Work Order":
            wo_name = doc.get("reference_name")

        if not wo_name:
            wo_name = frappe.db.get_value(
                "Work Order",
                {"production_item": doc.item, "docstatus": 1},
                "name",
                order_by="modified desc"
            )

        if wo_name:
            qty = int(frappe.db.get_value("Work Order", wo_name, "qty") or 0)

    if qty <= 0:
        return

    if doc.get("qr_codes"):
        return

    if _should_use_background(qty):
        frappe.enqueue(
            "batch_qr_code.utils.qr_generator._create_qr_codes_background",
            queue="long",
            timeout=3600,
            batch_no=doc.name,
            qty=qty,
        )
        frappe.msgprint(
            f"⏳ Generating {qty} QR codes in the background for Batch <b>{doc.name}</b>. "
            f"Refresh the Batch form to see them when done.",
            alert=True,
            indicator="blue",
        )
    else:
        _create_qr_codes(doc, qty)


def on_batch_update(doc, method=None):
    if _SKIP_UPDATE_HOOK.get(doc.name):
        return

    if doc.get("qr_codes"):
        return

    if _is_item_excluded(doc.item):
        return

    try:
        qty = int(doc.batch_qty or 0)
    except (ValueError, TypeError):
        qty = 0

    if qty > 0:
        if _should_use_background(qty):
            frappe.enqueue(
                "batch_qr_code.utils.qr_generator._create_qr_codes_background",
                queue="long",
                timeout=3600,
                batch_no=doc.name,
                qty=qty,
            )
            frappe.msgprint(
                f"⏳ Generating {qty} QR codes in the background for Batch <b>{doc.name}</b>. "
                f"Refresh to see them when done.",
                alert=True,
                indicator="blue",
            )
        else:
            _create_qr_codes(doc, qty)


def generate_qr_from_work_order(doc, method=None):
    if _is_item_excluded(doc.production_item):
        return

    qty = int(doc.qty or 0)

    if qty <= 0:
        frappe.msgprint(
            "⚠ Qty is 0. QR codes were not generated.",
            alert=True,
            indicator="orange"
        )
        return

    batch_no = frappe.db.get_value(
        "Batch",
        {
            "item": doc.production_item,
            "reference_doctype": "Work Order",
            "reference_name": doc.name,
        },
        "name"
    )

    if not batch_no:
        batch_no = doc.get("custom_work_order_batch") or None

    if not batch_no:
        batch_no = frappe.db.get_value(
            "Batch",
            {"item": doc.production_item, "disabled": 0},
            "name",
            order_by="creation desc"
        )

    if not batch_no:
        frappe.msgprint(
            f"⚠ No Batch found for item <b>{doc.production_item}</b> "
            f"on Work Order <b>{doc.name}</b>. QR codes were not generated.<br><br>"
            f"Go to the Batch and click <b>Actions → Regenerate QR Codes</b>.",
            title="QR Generation Skipped",
            indicator="orange"
        )
        return

    batch = frappe.get_doc("Batch", batch_no)

    if batch.get("qr_codes"):
        frappe.msgprint(
            f"ℹ QR codes already exist for Batch <b>{batch_no}</b>.",
            alert=True,
            indicator="blue"
        )
        return

    if not batch.batch_qty:
        frappe.db.set_value("Batch", batch_no, "batch_qty", qty)
        batch.reload()
    else:
        qty = int(batch.batch_qty)

    if _should_use_background(qty):
        frappe.enqueue(
            "batch_qr_code.utils.qr_generator._create_qr_codes_background",
            queue="long",
            timeout=3600,
            batch_no=batch_no,
            qty=qty,
        )
        frappe.msgprint(
            f"⏳ Generating {qty} QR codes in the background for Batch <b>{batch_no}</b>. "
            f"Refresh the Batch form to see them when done.",
            alert=True,
            indicator="blue",
        )
    else:
        _create_qr_codes(batch, qty)


# ─────────────────────────────────────────────────────────────
# BACKGROUND WRAPPER
# ─────────────────────────────────────────────────────────────

def _create_qr_codes_background(batch_no, qty):
    try:
        batch = frappe.get_doc("Batch", batch_no)

        if batch.get("qr_codes"):
            return

        _create_qr_codes(batch, qty)

        frappe.publish_realtime(
            "msgprint",
            {
                "message": f"✅ {qty} QR codes generated for Batch {batch_no}. "
                           f"Please refresh the Batch form to view them.",
            },
            user=frappe.session.user if frappe.session else "Administrator",
        )

    except Exception:
        frappe.log_error(
            title=f"QR Generation Failed for Batch {batch_no}",
            message=frappe.get_traceback()
        )


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

        # ── Unique unpredictable ID ───────────────────────────
        qr_id = _generate_unique_id(batch_no, unit)

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

        # ── Add details below the QR image ────────────────────
        qr_width, qr_height = qr_img.size
        label_height = 130
        final_img = Image.new("RGB", (qr_width, qr_height + label_height), "white")
        final_img.paste(qr_img, (0, 0))

        draw = ImageDraw.Draw(final_img)

        # Load fonts
        try:
            font_bold   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
            font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
            font_small  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except Exception:
            try:
                font_bold   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
                font_normal = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
                font_small  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
            except Exception:
                font_bold   = ImageFont.load_default()
                font_normal = ImageFont.load_default()
                font_small  = ImageFont.load_default()

        # ── Draw a thin separator line ────────────────────────
        draw.line(
            [(4, qr_height + 4), (qr_width - 4, qr_height + 4)],
            fill="#cccccc",
            width=1
        )

        # ── Detail lines ──────────────────────────────────────
        details = [
            (company,                        font_bold,   "#333333"),
            (f"{doc.item} — {item_name}",    font_normal, "#111111"),
            (f"Batch: {batch_no}",           font_normal, "#111111"),
            (f"Date: {prod_date}",           font_normal, "#555555"),
            (f"Unit {unit} of {qty}",        font_bold,   "#111111"),
            (qr_id,                          font_small,  "#aaaaaa"),
        ]

        y = qr_height + 10
        padding_left = 6

        for text, font, color in details:
            # Truncate if too wide
            max_chars = 45
            display = text if len(text) <= max_chars else text[:max_chars - 3] + "..."
            draw.text((padding_left, y), display, fill=color, font=font)
            bbox = draw.textbbox((0, 0), display, font=font)
            line_h = bbox[3] - bbox[1]
            y += line_h + 3

        # ── Save final image to bytes ─────────────────────────
        buf = io.BytesIO()
        final_img.save(buf, format="PNG")
        buf.seek(0)
        img_bytes = buf.read()

        # ── Save as File attachment ───────────────────────────
        file_name = f"QR_{batch_no}_{qr_id}.png"
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

        # ── Commit every 50 rows ──────────────────────────────
        if unit % 50 == 0:
            for row in rows:
                doc.append("qr_codes", row)
            rows = []
            doc.flags.ignore_validate_update_after_submit = True
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            doc.reload()

    # ── Save remaining rows ───────────────────────────────────
    if rows:
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
def get_batch_for_work_order(wo_name, production_item):
    """Find the batch linked to a Work Order."""

    batch_no = frappe.db.get_value(
        "Batch",
        {
            "item": production_item,
            "reference_doctype": "Work Order",
            "reference_name": wo_name,
        },
        "name"
    )

    if not batch_no:
        batch_no = frappe.db.get_value(
            "Work Order", wo_name, "custom_work_order_batch"
        )

    if not batch_no:
        batch_no = frappe.db.get_value(
            "Batch",
            {"item": production_item, "disabled": 0},
            "name",
            order_by="creation desc"
        )

    return batch_no or None


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
    _SKIP_UPDATE_HOOK[batch_no] = True

    try:
        batch = frappe.get_doc("Batch", batch_no)

        if _is_item_excluded(batch.item):
            frappe.throw(
                f"Item group for {batch.item} is excluded from QR code generation."
            )

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

        batch.set("qr_codes", [])
        batch.flags.ignore_validate_update_after_submit = True
        batch.save(ignore_permissions=True)
        frappe.db.commit()

        qty = int(batch.batch_qty or 0)

        if qty <= 0:
            wo_name = None

            if batch.get("reference_doctype") == "Work Order":
                wo_name = batch.get("reference_name")

            if not wo_name:
                wo_name = frappe.db.get_value(
                    "Work Order",
                    {"production_item": batch.item, "docstatus": 1},
                    "name",
                    order_by="modified desc"
                )

            if wo_name:
                qty = int(frappe.db.get_value("Work Order", wo_name, "qty") or 0)

        if qty <= 0:
            frappe.throw(
                "Could not determine qty. "
                "Please set Batch Qty on the Batch and try again."
            )

        batch.reload()

        if _should_use_background(qty):
            frappe.enqueue(
                "batch_qr_code.utils.qr_generator._create_qr_codes_background",
                queue="long",
                timeout=3600,
                batch_no=batch_no,
                qty=qty,
            )
            return {
                "status":    "queued",
                "generated": qty,
                "message":   f"Generating {qty} QR codes in background. Refresh when done."
            }
        else:
            _create_qr_codes(batch, qty)

    finally:
        _SKIP_UPDATE_HOOK.pop(batch_no, None)

    return {"status": "ok", "generated": qty}


def get_qr_image_base64(file_url):
    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        content  = file_doc.get_content()
        b64      = base64.b64encode(content).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""
