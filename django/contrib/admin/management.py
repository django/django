def get_page_permission_options():
    """Return permission metadata, deduplicated across admin sites."""
    from django.contrib.admin.sites import all_sites

    options = {}
    for site in list(all_sites):
        for page in site._page_registry.values():
            opts = page.get_admin_page_meta()
            options[opts.app_label, f"_admin_page_{opts.model_name}"] = opts
    return options
