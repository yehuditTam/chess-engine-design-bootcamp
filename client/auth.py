from client.server_bridge import ServerBridge


def prompt_auth(bridge: ServerBridge) -> str:
    """Terminal auth loop. Returns the authenticated username."""
    while True:
        action_raw = input("(l)ogin or (r)egister? ").strip().lower()
        action = "register" if action_raw.startswith("r") else "login"
        username = input("Username: ").strip()
        import getpass
        password = getpass.getpass("Password: ")
        result = bridge.authenticate(username, password, action)
        if result["type"] == "auth_ok":
            print(f"Welcome, {result['username']}! Rating: {result['rating']}")
            bridge.send_join(username)
            return username
        print(f"Auth failed: {result.get('reason', 'unknown error')}")
