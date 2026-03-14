app_name = "batch_qr_code"
app_title = "Batch qr code"
app_publisher = "soria systems"
app_description = "qr code generation for batches"
app_email = "info@soriasystems.co.ke"
app_license = "mit"

# ── DocType Events ────────────────────────────────────────────
doc_events = {
    "Batch": {
        "after_insert": "batch_qr_code.utils.qr_generator.generate_qr_codes_for_batch",
        "on_update":    "batch_qr_code.utils.qr_generator.on_batch_update",
    },
    "Work Order": {
        "after_submit": "batch_qr_code.utils.qr_generator.generate_qr_from_work_order",
    }
}

# ── JS includes ───────────────────────────────────────────────
doctype_js = {
    "Stock Entry": "public/js/stock_entry_qr.js",
    "Batch":       "public/js/batch_qr.js",
    "Work Order":  "public/js/work_order_qr.js",
}

# ── Jinja helpers for Print Formats ──────────────────────────
jinja = {
    "methods": [
        "batch_qr_code.utils.qr_generator.get_qr_codes_for_batch",
        "batch_qr_code.utils.qr_generator.get_qr_image_base64",
    ]
}
# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "batch_qr_code",
# 		"logo": "/assets/batch_qr_code/logo.png",
# 		"title": "Batch qr code",
# 		"route": "/batch_qr_code",
# 		"has_permission": "batch_qr_code.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/batch_qr_code/css/batch_qr_code.css"
# app_include_js = "/assets/batch_qr_code/js/batch_qr_code.js"

# include js, css files in header of web template
# web_include_css = "/assets/batch_qr_code/css/batch_qr_code.css"
# web_include_js = "/assets/batch_qr_code/js/batch_qr_code.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "batch_qr_code/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "batch_qr_code/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "batch_qr_code.utils.jinja_methods",
# 	"filters": "batch_qr_code.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "batch_qr_code.install.before_install"
# after_install = "batch_qr_code.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "batch_qr_code.uninstall.before_uninstall"
# after_uninstall = "batch_qr_code.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "batch_qr_code.utils.before_app_install"
# after_app_install = "batch_qr_code.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "batch_qr_code.utils.before_app_uninstall"
# after_app_uninstall = "batch_qr_code.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "batch_qr_code.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"batch_qr_code.tasks.all"
# 	],
# 	"daily": [
# 		"batch_qr_code.tasks.daily"
# 	],
# 	"hourly": [
# 		"batch_qr_code.tasks.hourly"
# 	],
# 	"weekly": [
# 		"batch_qr_code.tasks.weekly"
# 	],
# 	"monthly": [
# 		"batch_qr_code.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "batch_qr_code.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "batch_qr_code.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "batch_qr_code.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["batch_qr_code.utils.before_request"]
# after_request = ["batch_qr_code.utils.after_request"]

# Job Events
# ----------
# before_job = ["batch_qr_code.utils.before_job"]
# after_job = ["batch_qr_code.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"batch_qr_code.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

