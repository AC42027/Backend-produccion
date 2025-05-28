# mi_formulario/ldap_auth.py
from ldap3 import Server, Connection, ALL, NTLM
from decouple import config

def autenticar_usuario(username, password):
    LDAP_SERVER = config('LDAP_SERVER')  
    LDAP_DOMAIN = config('LDAP_DOMAIN')  
    USER_DN = f"{username}@{LDAP_DOMAIN}"

    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=USER_DN, password=password, auto_bind=True)

        # Buscar datos del usuario en el LDAP
        conn.search(
            search_base=f"DC={LDAP_DOMAIN.replace('.', ',DC=')}",
            search_filter=f"(sAMAccountName={username})",
            attributes=[
                "givenName", "sn", "mail", "userPrincipalName",
                "title", "manager", "memberOf"
            ]
        )

        if not conn.entries:
            return False

        entry = conn.entries[0]
        data = entry.entry_attributes_as_dict

        conn.unbind()

        # Armar respuesta con los datos útiles
        return {
            "success": True,
            "username": username,
            "first_name": data.get("givenName", [""])[0],
            "last_name": data.get("sn", [""])[0],
            "email": data.get("userPrincipalName", [""])[0],
            "title": data.get("title", [""])[0],
            "manager_dn": data.get("manager", [""])[0],
            "groups": data.get("memberOf", []),
        }

    except Exception as e:
        print(f"[LDAP ERROR] {e}")
        return {"success": False, "error": str(e)}
