from flask import Flask, render_template, jsonify, redirect, url_for, session, request, abort
from dotenv import load_dotenv
import os
import psutil
import msal

# -----------------------------
# 1. Basisconfiguratie
# -----------------------------
load_dotenv()  # leest waarden uit je .env bestand

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Entra ID / MSAL instellingen
CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ENTRA_CLIENT_SECRET")
TENANT_ID = os.getenv("ENTRA_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/auth/callback")
SCOPES = ["User.Read"]

# -----------------------------
# 2. Hulpfuncties
# -----------------------------
def _build_msal_app(cache=None):
    """Maak een MSAL ConfidentialClientApplication aan."""
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache
    )

def _build_auth_url():
    """Genereer de login-URL naar Microsoft."""
    return _build_msal_app().initiate_auth_code_flow(
        scopes=SCOPES, redirect_uri=REDIRECT_URI
    )

def login_required(view):
    """Decorator die toegang beperkt tot ingelogde gebruikers."""
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            session["post_login_redirect"] = request.url
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    wrapped_view.__name__ = view.__name__
    return wrapped_view

# -----------------------------
# 3. Routes
# -----------------------------
@app.route("/login")
def login():
    flow = _build_auth_url()
    session["flow"] = flow
    return redirect(flow["auth_uri"])

@app.route("/auth/callback")
def authorized():
    """Wordt aangeroepen na succesvolle login bij Microsoft."""
    if "flow" not in session:
        return redirect(url_for("login"))

    result = _build_msal_app().acquire_token_by_auth_code_flow(
        session.pop("flow"), request.args
    )

    if "error" in result:
        return f"Login mislukt: {result.get('error_description')}", 400

    user_claims = result.get("id_token_claims", {})
    session["user"] = {
        "name": user_claims.get("name"),
        "email": user_claims.get("preferred_username"),
        "oid": user_claims.get("oid")
    }
    return redirect(session.pop("post_login_redirect", url_for("dashboard")))

@app.route("/logout")
def logout():
    session.clear()
    logout_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/logout"
    post_logout_redirect = url_for("dashboard", _external=True)
    return redirect(f"{logout_url}?post_logout_redirect_uri={post_logout_redirect}")

# -----------------------------
# 4. Monitoring functies
# -----------------------------
def get_metrics():
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }

@app.route("/")
@login_required
def dashboard():
    data = get_metrics()
    user = session.get("user", {})
    return render_template("dashboard.html", data=data, user=user)

@app.route("/api/metrics")
@login_required
def api_metrics():
    return jsonify(get_metrics())

# -----------------------------
# 5. Start de applicatie
# -----------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)