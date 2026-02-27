import logging
from config.settings import settings

logger = logging.getLogger(__name__)

def authenticate_ldap(username: str, password: str) -> bool:
    """
    Attempts to bind to the LDAP server with the given credentials.
    If ENABLE_LDAP is False, returns False immediately.
    """
    if not settings.auth.enable_ldap:
        logger.info("LDAP authentication is disabled.")
        return False
        
    # Prevent basic LDAP injection by restricting characters
    # (assuming UPN or standard sAMAccountName limits in AD)
    import re
    if not re.match(r'^[a-zA-Z0-9_\-\.\@]+$', username):
        logger.warning(f"LDAP bind failed: invalid characters in username: {username}")
        return False
        
    server_url = settings.auth.ldap_server_url
    # Depending on setup, username might need to be domain\\username or username@domain.com
    # This is highly dependent on the Active Directory / LDAP setup. We will assume UPN/simple for now.
    user_dn = username  
    
    try:
        from ldap3 import Server, Connection, ALL
        server = Server(server_url, get_info=ALL)
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        if conn.bind():
            logger.info(f"LDAP bind successful for {username}")
            conn.unbind()
            return True
        else:
            logger.warning(f"LDAP bind failed for {username}")
            return False
    except Exception as e:
        logger.error(f"LDAP authentication error: {e}")
        return False
