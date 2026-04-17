{
    "name": "Tourism WhatsApp Portal",
    "summary": "Onboarding turístico 100% por WhatsApp + comité + portal social",
    "version": "18.0.1.0.0",
    "category": "Website",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "portal", "website", "auth_signup"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/tourism_post_views.xml",
        "views/tourism_portal_templates.xml"
    ],
    "installable": True,
    "application": True,
}
