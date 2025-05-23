# -*- coding: utf-8 -*-
{
    "name": "Cloud Sync for Enterprise Documents",
    "version": "17.0.1.1.8",
    "category": "Document Management",
    "author": "faOtools",
    "website": "https://faotools.com/apps/17.0/cloud-sync-for-enterprise-documents-17-0-cloud-base-documents-841",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "cloud_base",
        "documents"
    ],
    "data": [
        "data/data.xml",
        "security/ir.model.access.csv",
        "views/documents_document.xml",
        "views/sync_model.xml",
        "views/templates.xml"
    ],
    "assets": {
        "web.assets_backend": [
                "cloud_base_documents/static/src/views/*.js",
                "cloud_base_documents/static/src/views/kanban/*.js",
                "cloud_base_documents/static/src/views/kanban/*.scss",
                "cloud_base_documents/static/src/views/list/*.js",
                "cloud_base_documents/static/src/views/inspector/*.xml",
                "cloud_base_documents/static/src/views/inspector/*.js"
        ]
},
    "demo": [
        
    ],
    "external_dependencies": {},
    "summary": "The extension to Cloud Storage Solutions to reflect Odoo Enterprise Documents and sync those with Google Drive, OneDrive/SharePoint, Nextcloud/ownCloud, Dropbox",
    "description": """
For the full details look at static/description/index.html
* Features *
#odootools_proprietary""",
    "images": [
        "static/description/main.png"
    ],
    "price": "44.0",
    "currency": "EUR",
    "live_test_url": "https://faotools.com/my/tickets/newticket?&url_app_id=81&ticket_version=17.0&ticket_license=enterpise&url_type_id=3",
}