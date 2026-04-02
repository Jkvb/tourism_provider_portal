{
    "name": "Tourism Provider Portal",
    "summary": "Registro, validación y publicación de prestadores turísticos municipales",
    "version": "19.0.1.0.0",
    "category": "Website",
    "author": "Municipio Atemajac de Brizuela",
    "website": "https://atemajacdebrizuela.gob.mx",
    "license": "LGPL-3",
    "depends": ["base", "mail", "portal", "website"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/tourism_provider_data.xml",
        "views/tourism_provider_views.xml",
        "views/tourism_category_views.xml",
        "views/tourism_menus.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "tourism_provider_portal/static/src/scss/tourism_provider.scss",
        ],
    },
    "application": True,
    "installable": True,
}
