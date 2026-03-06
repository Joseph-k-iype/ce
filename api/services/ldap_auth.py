import re
import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

# Allow only alphanumeric and safe characters for employee IDs
_SAFE_ID_RE = re.compile(r'^[a-zA-Z0-9_\-\.]+$')


def authenticate_ldap(employee_id: str, password: str) -> Optional[dict]:
    """
    Authenticate against LDAP using an employee ID.

    Constructs the bind DN from the LDAP_BASE_DN_TEMPLATE setting, performs
    a bind with the supplied password, then searches for the user's displayName
    and mail attributes.

    Returns:
        dict with {employee_id, display_name, email} on success.
        None on authentication failure or when LDAP is disabled.

    Security note: the password is only held as a local variable during the
    bind call and is never persisted or logged.
    """
    if not settings.auth.enable_ldap:
        logger.info("LDAP authentication is disabled.")
        return None

    if not _SAFE_ID_RE.match(employee_id):
        logger.warning("LDAP bind rejected: invalid characters in employee_id")
        return None

    try:
        from ldap3 import Server, Connection, ALL, SUBTREE

        user_dn = settings.auth.ldap_base_dn_template.format(employee_id)
        server = Server(settings.auth.ldap_server_url, get_info=ALL)
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)

        # Search for user attributes after successful bind
        search_filter = settings.auth.ldap_search_filter_template.format(employee_id)
        conn.search(
            search_base=settings.auth.ldap_search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=["displayName", "mail"],
        )

        display_name = employee_id  # fallback if attribute not found
        email = ""
        if conn.entries:
            entry = conn.entries[0]
            if entry.displayName:
                display_name = str(entry.displayName)
            if entry.mail:
                email = str(entry.mail)

        conn.unbind()
        logger.info("LDAP authentication successful for employee_id=%s", employee_id)
        return {"employee_id": employee_id, "display_name": display_name, "email": email}

    except Exception as e:
        logger.warning("LDAP authentication failed for employee_id=%s: %s", employee_id, e)
        return None
