from flask import Flask, render_template, jsonify, redirect, url_for, session, request
from dotenv import load_dotenv
import os
import psutil
import msal
import datetime

# Azure monitoring imports
from azure.identity import ClientSecretCredential
from azure.mgmt.monitor import MonitorManagementClient

# -----------------------------
# 1. Basisconfiguratie
# -----------------------------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Entra ID instellingen
CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ENTRA_CLIENT_SECRET")
TENANT_ID = os.getenv("ENTRA_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/auth/callback")
SCOPES = ["User.Read"]

# Azure Monitor instellingen (Task 5)
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP")
CONTAINERAPP_NAME = os.getenv("AZURE_CONTAINERAPP_NAME")

RESOURCE_ID = (
    f"/subscriptions/{SUBSCRIPTION_ID}"
    f"/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/Microsoft.App/containerApps/{CONTAINERAPP_NAME}"
)


# -----------------------------
# 2. MSAL functies
# -----------------------------
def _build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache
    )


def _build_auth_url():
    return _build_msal_app().initiate_auth_code_flow(
        scopes=SCOPES, redirect_uri=REDIRECT_URI
    )


def login_required(view):
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            session["post_login_redirect"] = request.url
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    wrapped_view.__name__ = view.__name__
    return wrapped_view


# -----------------------------
# 3. Azure Container Metrics (Task 5)
# -----------------------------
def get_container_platform_metrics():
    """Haalt CPU en Memory metrics op van Azure Container Apps via Azure Monitor."""

    try:
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )

        monitor_client = MonitorManagementClient(credential, SUBSCRIPTION_ID)

        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(minutes=10)

        cpu_query = monitor_client.metrics.list(
            RESOURCE_ID,
            timespan=f"{start}/{end}",
            interval="PT1M",
            metricnames="CpuUsage",
            aggregation="Average"
        )

        mem_query = monitor_client.metrics.list(
            RESOURCE_ID,
            timespan=f"{start}/{end}",
            interval="PT1M",
            metricnames="MemoryWorkingSet",
            aggregation="Average"
        )

        # Extract CPU
        try:
            cpu = cpu_query.value[0].timeseries[0].data[-1].average
        except:
            cpu = None

        # Extract memory (in MB)
        try:
            mem = mem_query.value[0].timeseries[0].data[-1].average / (1024 * 1024)
        except:
            mem = None

        return {
            "azure_cpu": round(cpu, 2) if cpu else None,
            "azure_memory": round(mem, 2) if mem else None,
            "error": None
        }

    except Exception as e:
        return {
            "azure_cpu": None,
            "azure_memory": None,
            "error": str(e)
        }


# -----------------------------
# 4. Lokale systeem-metrics
# -----------------------------
def get_system_metrics():
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }


# -----------------------------
# 5. Combineer metrics
# -----------------------------
def get_metrics():
    system = get_system_metrics()
    azure = get_container_platform_metrics()

    return {
        **system,
        **azure
    }


# -----------------------------
# 6. Routes
# -----------------------------
@app.route("/login")
def login():
    flow = _build_auth_url()
    session["flow"] = flow
    return redirect(flow["auth_uri"])


@app.route("/auth/callback")
def authorized():
    if "flow" not in session:
        return redirect(url_for("login"))

    result = _build_msal_app().acquire_token_by_auth_code_flow(
        session.pop("flow"), request.args
    )

    if "error" in result:
        return f"Login mislukt: {result.get('error_description')}", 400

    claims = result.get("id_token_claims", {})
    session["user"] = {
        "name": claims.get("name"),
        "email": claims.get("preferred_username")
    }

    return redirect(session.pop("post_login_redirect", url_for("dashboard")))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


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
# 7. Run applicatie
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
