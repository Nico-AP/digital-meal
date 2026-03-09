"""
There are two main url configurations depending on the context:

- main_conf.py: Used when MDM_ROUTING_TYPE == "URL_PREFIX" for all urls/domains,
    and for DM url when MDM_ROUTING_TYPE == "SUBDOMAIN"
    (served under MDM_MAIN_DOMAIN/<urls>).
- mdm_conf.py: Used when MDM_ROUTING_TYPE == "SUBDOMAIN" to serve My Digital Meal
    urls (served under MDM_SUBDOMAIN/<urls>).
"""
