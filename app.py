import os
from datetime import datetime, date
from urllib.parse import urlparse, urlunparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # Em produção no Render, as variáveis vêm pelo ambiente.
    # Localmente, python-dotenv carrega o .env quando instalado.
    pass

from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text


def normalize_database_url(url: str | None) -> str:
    """
    Local sem DATABASE_URL usa SQLite.
    No Render, converte postgres/postgresql para pg8000, driver 100% Python,
    evitando erro de pg_config/psycopg2 no Windows e no deploy.
    """
    if not url:
        return "sqlite:///demandas.db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+pg8000://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+pg8000://", 1)
    return url


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(os.getenv("DATABASE_URL"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Usuários cadastrados diretamente no Python.
# Observação: para produção pública, o ideal é migrar senhas para variáveis de ambiente
# ou para uma tabela de usuários com hash de senha. Para uso interno/teste, este formato funciona.
USUARIOS = {
    "admin": "123456",
    "gerber": "nicolas1616",
    "elvis.santos@olos.com.br": "olos@2026",
    "nubia.gomes@olos.com.br": "olos@2026",
    "eduardo.molina@olos.com.br": "olos@2026",
    "michele.silva@olos.com.br": "olos@2026",
    "marcelo.rizzetto@olos.com.br": "olos@2026",
    "hayane.silva@olos.com.br": "olos@2026",
    

    # Usuários restritos por cliente
    "sky": "sky123",
    "negocie_online": "negocie@2026",
    "talentos": "talentos123",
    "sky_talentos": "multi123",
    "link": "link123",
}

USUARIOS_RESTRITOS_CLIENTE = {
    "sky": ["SKY"],
    "negocie_online": ["NEGOCIE ONLINE", "NEGOCIE_ONLINE"],
    "talentos": ["TALENTOS"],
    "sky_talentos": ["SKY", "TALENTOS"],
    "link": ["LINK", "LINK SOLUCOES", "LINK SOLUÇÕES"],
}

USUARIOS_ADMIN = {
    "admin",
    "gerber",
    "elvis.santos@olos.com.br",
    "nubia.gomes@olos.com.br",
    "eduardo.molina@olos.com.br",
    "michele.silva@olos.com.br",
    "hayane.silva@olos.com.br",
    "marcelo.rizzetto@olos.com.br"
}

db = SQLAlchemy(app)

STATUS_OPTIONS = ["Implantado", "POC", "Homolog cliente", "Fila OSP", "Em Mapeamento"]
ANALISTAS = ["Elvis", "Duda", "Molina", "Pedro", "Michele", "Sheila", "Hayane"]
VALIDACAO_OPTIONS = ["S/CPF", "C/CPF"]

CHECKPOINT_DEFAULTS = {
    "tipo_agente_virtual": "Locator",
    "organizacao": "Olos",
    "plano_tabulacao": "Plano Olos",
    "horario_inicio": "08:00",
    "horario_fim": "20:40",
    "recursos_midia": "MediaResource_ADA",
    "lcr_rota": "AGIL_LOC",
    "rota_portal_voz": "SIPADA",
    "canais": "150",
    "url_aplicacao": "http://olosgtlspobot01:3200/GrupoTalentos-LocatorStudio/start",
    "dnis_portal_voz": "ada-locator-semcpf-history",
    "tempo_maximo_chamada": "120",
    "campanha_receptiva": "Receptivo Locator",
    "calculo_demanda": "Balanceado",
    "portal_voz": "KAMAILIO_Locator",
    "plano_tarifacao_telecom": "Plano Olos",
    "plano_tarifacao_agentes_digitais": "Plano Olos",
    "gestor_negocio": "Cadastrado",
}

CHECKPOINT_FIELDS = [
    "tipo_agente_virtual", "organizacao", "plano_tabulacao", "horario_inicio", "horario_fim",
    "recursos_midia", "lcr_rota", "rota_portal_voz", "canais", "url_aplicacao",
    "dnis_portal_voz", "tempo_maximo_chamada", "campanha_receptiva", "calculo_demanda",
    "portal_voz", "plano_tarifacao_telecom", "plano_tarifacao_agentes_digitais", "gestor_negocio",
]

CHECKPOINT_SELECT_OPTIONS = {
    "tipo_agente_virtual": ["Locator", "Sem informação no Painel"],
    "rota_portal_voz": ["SIPADA", "Sem informação"],
    "calculo_demanda": ["Balanceado", "Apenas Ativo", "Pelo Receptivo"],
    "portal_voz": ["KAMAILIO_Locator", "Sem informação"],
    "gestor_negocio": ["Cadastrado", "Pendente"],
}



class Demanda(db.Model):
    __tablename__ = "demandas"

    id = db.Column(db.Integer, primary_key=True)
    acompanhamento = db.Column(db.String(120), nullable=True)
    cliente = db.Column(db.String(180), nullable=False)
    validacao_dados_locator = db.Column(db.String(20), nullable=True)
    carteira = db.Column(db.String(220), nullable=True)
    status_etapa_atual = db.Column(db.String(80), nullable=False, default="Em Mapeamento")
    inicio_poc = db.Column(db.Date, nullable=True)
    final_poc = db.Column(db.Date, nullable=True)
    wrike = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def dias_poc(self):
        if self.inicio_poc and self.final_poc:
            return max((self.final_poc - self.inicio_poc).days, 0)
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "acompanhamento": self.acompanhamento or "",
            "cliente": self.cliente or "",
            "validacao_dados_locator": self.validacao_dados_locator or "",
            "carteira": self.carteira or "",
            "status_etapa_atual": self.status_etapa_atual or "Em Mapeamento",
            "dias_poc": self.dias_poc,
            "inicio_poc": self.inicio_poc.isoformat() if self.inicio_poc else "",
            "final_poc": self.final_poc.isoformat() if self.final_poc else "",
            "inicio_poc_br": format_date_br(self.inicio_poc),
            "final_poc_br": format_date_br(self.final_poc),
            "wrike": self.wrike or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class Checkpoint(db.Model):
    __tablename__ = "checkpoints"

    id = db.Column(db.Integer, primary_key=True)
    demanda_id = db.Column(db.Integer, db.ForeignKey("demandas.id"), nullable=False, unique=True, index=True)
    tipo_agente_virtual = db.Column(db.String(80), nullable=True)
    organizacao = db.Column(db.String(160), nullable=True)
    plano_tabulacao = db.Column(db.String(180), nullable=True)
    horario_inicio = db.Column(db.String(8), nullable=True)
    horario_fim = db.Column(db.String(8), nullable=True)
    recursos_midia = db.Column(db.String(180), nullable=True)
    lcr_rota = db.Column(db.String(120), nullable=True)
    rota_portal_voz = db.Column(db.String(120), nullable=True)
    canais = db.Column(db.String(40), nullable=True)
    url_aplicacao = db.Column(db.Text, nullable=True)
    dnis_portal_voz = db.Column(db.String(220), nullable=True)
    tempo_maximo_chamada = db.Column(db.String(40), nullable=True)
    campanha_receptiva = db.Column(db.String(180), nullable=True)
    calculo_demanda = db.Column(db.String(80), nullable=True)
    portal_voz = db.Column(db.String(120), nullable=True)
    plano_tarifacao_telecom = db.Column(db.String(180), nullable=True)
    plano_tarifacao_agentes_digitais = db.Column(db.String(180), nullable=True)
    gestor_negocio = db.Column(db.String(80), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    demanda = db.relationship("Demanda", backref=db.backref("checkpoint", uselist=False, cascade="all, delete-orphan"), single_parent=True)

    @property
    def filled_count(self):
        return sum(1 for field in CHECKPOINT_FIELDS if clean_text(getattr(self, field, None)))

    @property
    def total_count(self):
        return len(CHECKPOINT_FIELDS)

    @property
    def pending_count(self):
        return self.total_count - self.filled_count

    @property
    def completion_percent(self):
        if self.total_count == 0:
            return 0
        return round((self.filled_count / self.total_count) * 100, 1)

    def to_dict(self):
        payload = {field: getattr(self, field, "") or "" for field in CHECKPOINT_FIELDS}
        payload.update({
            "id": self.id,
            "demanda_id": self.demanda_id,
            "observacoes": self.observacoes or "",
            "filled_count": self.filled_count,
            "pending_count": self.pending_count,
            "total_count": self.total_count,
            "completion_percent": self.completion_percent,
            "status_geral": "Completo" if self.pending_count == 0 else "Parcial",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        })
        return payload


def parse_date(value):
    if not value or str(value).strip().lower() in {"sem previsão", "sem previsao"}:
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def format_date_br(value):
    if not value:
        return "Sem previsão"
    return value.strftime("%d/%m/%Y")


def clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalize_key(value):
    return (value or "").strip().upper()


def user_is_admin():
    return bool(session.get("is_admin"))


def clientes_permitidos_usuario():
    return session.get("clientes_permitidos") or []


def apply_access_filter(query):
    """Filtra demandas para usuários restritos por cliente."""
    if user_is_admin():
        return query

    clientes = clientes_permitidos_usuario()
    if not clientes:
        # Sem permissão explícita, não retorna demandas.
        return query.filter(False)

    filtros = []
    for cliente in clientes:
        termo = f"%{cliente.lower()}%"
        filtros.append(func.lower(Demanda.cliente).like(termo))
        filtros.append(func.lower(Demanda.carteira).like(termo))

    return query.filter(db.or_(*filtros))


def can_access_demanda(demanda: "Demanda") -> bool:
    if user_is_admin():
        return True

    clientes = [normalize_key(c) for c in clientes_permitidos_usuario()]
    cliente_demanda = normalize_key(demanda.cliente)
    carteira_demanda = normalize_key(demanda.carteira)

    return any(c in cliente_demanda or c in carteira_demanda for c in clientes)


def get_demanda_authorized_or_404(demanda_id: int) -> "Demanda":
    demanda = Demanda.query.get_or_404(demanda_id)
    if not can_access_demanda(demanda):
        return None
    return demanda


def seed_data():
    if Demanda.query.count() > 0:
        return

    rows = [
        ("Elvis", "Talentos", "S/CPF", "VIA VAREJO RECOVERY", "Implantado", "17/04/2026", "30/04/2026", ""),
        ("Duda", "NovaQuest", "C/CPF", "MERCADO PAGO", "Implantado", "01/04/2026", "13/04/2026", ""),
        ("Molina", "Ferreira e Chagas P1", "", "ATIVOS BB", "Implantado", "17/04/2026", "20/05/2026", ""),
        ("Molina", "NW Advogados", "", "SANTANDER", "Implantado", "29/05/2026", "29/05/2026", ""),
        ("Molina", "Millennium", "", "RETURN", "POC", "09/06/2026", "24/06/2026", ""),
        ("Pedro", "Creditas", "S/CPF", "CREDITAS", "POC", "03/06/2026", "18/06/2026", ""),
        ("Michele", "Renac", "S/CPF", "RENNER CARTAO", "POC", "08/06/2026", "23/06/2026", ""),
        ("Sheila", "Link Solucoes", "C/CPF", "SIMPLIC FASE 2", "POC", "03/06/2026", "19/06/2026", ""),
        ("Elvis", "Talentos", "S/CPF", "CRUZEIRO DO SUL", "Implantado", "02/06/2026", "02/06/2026", ""),
        ("Elvis", "Talentos", "S/CPF", "IPANEMA", "Implantado", "02/06/2026", "02/06/2026", ""),
        ("Elvis", "Setra", "C/CPF", "BULLA", "POC", "08/06/2026", "23/06/2026", ""),
        ("Michele", "Aranha e Ferreira", "C/CPF", "TOYOTA", "POC", "08/06/2026", "20/06/2026", ""),
        ("Elvis", "Syscob", "C/CPF", "BEMOL", "POC", "09/06/2026", "24/06/2026", ""),
        ("Duda", "Rede Brasil", "C/CPF", "BRADESCO", "Homolog cliente", "17/06/2026", "02/07/2026", ""),
        ("Michele", "Perez de Rezende", "C/CPF", "BRADESCO", "Homolog cliente", "18/06/2026", "03/07/2026", ""),
        ("Sheila", "TRC Taborda", "", "RENNER CARTÃO", "Fila OSP", "18/06/2026", "", ""),
        ("Hayane", "VGX", "", "CLARO", "Fila OSP", "22/06/2026", "07/07/2026", ""),
        ("Elvis", "Talentos", "", "CLARO", "Fila OSP", "22/06/2026", "", ""),
        ("Michele", "Schulze", "", "BANCO PAN", "Fila OSP", "19/06/2026", "04/07/2026", ""),
        ("Pedro", "Elo Contact Center", "", "UNIMED", "Fila OSP", "19/06/2026", "04/07/2026", ""),
        ("Molina", "Ferreira e Chagas P1", "", "TIM", "Fila OSP", "22/06/2026", "07/07/2026", ""),
        ("Molina", "Ferreira e Chagas P3", "", "ATIVOS", "Fila OSP", "24/06/2026", "09/07/2026", ""),
        ("Michele", "Precisão Global", "", "", "Fila OSP", "29/06/2026", "14/07/2026", ""),
        ("Sheila", "Dunice & Marcon", "", "DIVZERO", "Fila OSP", "26/06/2026", "11/07/2026", ""),
        ("", "Arauz Solucz", "", "", "Em Mapeamento", "03/07/2026", "18/07/2026", ""),
        ("Pedro", "MB Finance", "", "", "Em Mapeamento", "03/07/2026", "18/07/2026", ""),
        ("", "EmDia (Liderança)", "", "SANTANDER LAB | ESCOB", "Em Mapeamento", "", "", ""),
        ("", "EmDia (Liderança)", "", "ESCOB", "Em Mapeamento", "", "", ""),
        ("", "Full Time", "S/CPF", "NEON", "Em Mapeamento", "", "", ""),
        ("", "Full Time", "", "VERISURE", "Em Mapeamento", "", "", ""),
    ]

    for row in rows:
        demanda = Demanda(
            acompanhamento=clean_text(row[0]),
            cliente=row[1],
            validacao_dados_locator=clean_text(row[2]),
            carteira=clean_text(row[3]),
            status_etapa_atual=row[4],
            inicio_poc=parse_date(row[5]),
            final_poc=parse_date(row[6]),
            wrike=clean_text(row[7]),
        )
        db.session.add(demanda)
    db.session.commit()


def init_db():
    db.create_all()
    seed_data()


@app.before_request
def ensure_db_ready_and_auth():
    if not getattr(app, "_db_ready", False):
        init_db()
        app._db_ready = True

    public_endpoints = {"login", "health", "static"}
    endpoint = request.endpoint or ""
    if endpoint in public_endpoints or endpoint.startswith("static"):
        return None

    if session.get("logged_in"):
        return None

    if request.path.startswith("/api/") or request.path == "/db-status":
        return jsonify({"error": "login_required"}), 401

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""

        if username in USUARIOS and USUARIOS[username] == password:
            session.clear()
            session["logged_in"] = True
            session["user"] = username
            session["is_admin"] = username in USUARIOS_ADMIN
            session["clientes_permitidos"] = USUARIOS_RESTRITOS_CLIENTE.get(username, [])
            return redirect(url_for("index"))

        error = "Usuário ou senha inválidos."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    return render_template(
        "index.html",
        status_options=STATUS_OPTIONS,
        analistas=ANALISTAS,
        validacao_options=VALIDACAO_OPTIONS,
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "painel-demandas"})


@app.route("/db-status")
def db_status():
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    parsed = urlparse(db_uri)
    safe_netloc = parsed.hostname or "local"
    safe_uri = urlunparse((parsed.scheme, safe_netloc, parsed.path, "", "", ""))
    try:
        db.session.execute(text("SELECT 1"))
        total = Demanda.query.count()
        return jsonify({
            "database": safe_uri,
            "total_demandas": total,
            "status": "conectado",
        })
    except Exception as exc:
        return jsonify({
            "database": safe_uri,
            "status": "erro",
            "error": str(exc),
        }), 500


@app.route("/api/meta")
def api_meta():
    return jsonify({
        "status_options": STATUS_OPTIONS,
        "analistas": ANALISTAS,
        "validacao_options": VALIDACAO_OPTIONS,
        "usuario": session.get("user", ""),
        "is_admin": user_is_admin(),
        "clientes_permitidos": clientes_permitidos_usuario(),
    })


@app.route("/api/demandas", methods=["GET"])
def list_demandas():
    search = (request.args.get("search") or "").strip().lower()
    status = (request.args.get("status") or "").strip()
    analista = (request.args.get("analista") or "").strip()

    query = apply_access_filter(Demanda.query)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                func.lower(Demanda.cliente).like(like),
                func.lower(Demanda.carteira).like(like),
                func.lower(Demanda.acompanhamento).like(like),
            )
        )
    if status:
        query = query.filter(Demanda.status_etapa_atual == status)
    if analista:
        query = query.filter(Demanda.acompanhamento == analista)

    demandas = query.order_by(Demanda.id.asc()).all()

    status_counts = {status_name: 0 for status_name in STATUS_OPTIONS}
    all_rows_for_counts = apply_access_filter(Demanda.query).all()
    for item in all_rows_for_counts:
        status_counts[item.status_etapa_atual] = status_counts.get(item.status_etapa_atual, 0) + 1

    return jsonify({
        "items": [d.to_dict() for d in demandas],
        "cards": {
            "Total": apply_access_filter(Demanda.query).count(),
            **status_counts,
        },
    })


@app.route("/api/demandas", methods=["POST"])
def create_demanda():
    data = request.get_json(force=True) or {}
    demanda = Demanda()
    apply_payload(demanda, data, creating=True)
    db.session.add(demanda)
    db.session.commit()
    return jsonify(demanda.to_dict()), 201


@app.route("/api/demandas/<int:demanda_id>", methods=["PUT"])
def update_demanda(demanda_id):
    demanda = get_demanda_authorized_or_404(demanda_id)
    if demanda is None:
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(force=True) or {}
    apply_payload(demanda, data, creating=False)
    db.session.commit()
    return jsonify(demanda.to_dict())


@app.route("/api/demandas/<int:demanda_id>", methods=["DELETE"])
def delete_demanda(demanda_id):
    demanda = get_demanda_authorized_or_404(demanda_id)
    if demanda is None:
        return jsonify({"error": "forbidden"}), 403
    checkpoint = Checkpoint.query.filter_by(demanda_id=demanda_id).first()
    if checkpoint:
        db.session.delete(checkpoint)
    db.session.delete(demanda)
    db.session.commit()
    return jsonify({"deleted": True})



def get_or_create_checkpoint(demanda_id: int) -> Checkpoint:
    demanda = get_demanda_authorized_or_404(demanda_id)
    if demanda is None:
        return None
    checkpoint = Checkpoint.query.filter_by(demanda_id=demanda.id).first()
    if checkpoint:
        return checkpoint
    checkpoint = Checkpoint(demanda_id=demanda.id, **CHECKPOINT_DEFAULTS)
    # Ajuste leve para o DNIS conforme a validação da demanda, quando existir.
    if demanda.validacao_dados_locator == "C/CPF":
        checkpoint.dnis_portal_voz = "ada-locator-comcpf-history"
    db.session.add(checkpoint)
    db.session.commit()
    return checkpoint


@app.route("/api/checkpoint/meta")
def checkpoint_meta():
    return jsonify({
        "defaults": CHECKPOINT_DEFAULTS,
        "fields": CHECKPOINT_FIELDS,
        "select_options": CHECKPOINT_SELECT_OPTIONS,
    })


@app.route("/api/demandas/<int:demanda_id>/checkpoint", methods=["GET"])
def get_checkpoint(demanda_id):
    demanda = get_demanda_authorized_or_404(demanda_id)
    if demanda is None:
        return jsonify({"error": "forbidden"}), 403
    checkpoint = get_or_create_checkpoint(demanda.id)
    return jsonify({
        "demanda": demanda.to_dict(),
        "checkpoint": checkpoint.to_dict(),
    })


@app.route("/api/demandas/<int:demanda_id>/checkpoint", methods=["PUT"])
def update_checkpoint(demanda_id):
    Checkpoint.query.filter_by(demanda_id=demanda_id).first()
    checkpoint = get_or_create_checkpoint(demanda_id)
    if checkpoint is None:
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(force=True) or {}
    for field in CHECKPOINT_FIELDS:
        if field in data:
            setattr(checkpoint, field, clean_text(data.get(field)))
    checkpoint.observacoes = clean_text(data.get("observacoes"))
    db.session.commit()
    demanda = get_demanda_authorized_or_404(demanda_id)
    if demanda is None:
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "demanda": demanda.to_dict(),
        "checkpoint": checkpoint.to_dict(),
    })


@app.route("/api/demandas/<int:demanda_id>/checkpoint/reset", methods=["POST"])
def reset_checkpoint(demanda_id):
    checkpoint = get_or_create_checkpoint(demanda_id)
    if checkpoint is None:
        return jsonify({"error": "forbidden"}), 403
    for field, value in CHECKPOINT_DEFAULTS.items():
        setattr(checkpoint, field, value)
    demanda = get_demanda_authorized_or_404(demanda_id)
    if demanda is None:
        return jsonify({"error": "forbidden"}), 403
    if demanda.validacao_dados_locator == "C/CPF":
        checkpoint.dnis_portal_voz = "ada-locator-comcpf-history"
    checkpoint.observacoes = None
    db.session.commit()
    return jsonify({"demanda": demanda.to_dict(), "checkpoint": checkpoint.to_dict()})


def checkpoint_stats_for_demanda(demanda_id: int):
    checkpoint = Checkpoint.query.filter_by(demanda_id=demanda_id).first()
    total = len(CHECKPOINT_FIELDS)
    if not checkpoint:
        return {"filled": 0, "pending": total, "total": total, "percent": 0.0}
    return {
        "filled": checkpoint.filled_count,
        "pending": checkpoint.pending_count,
        "total": checkpoint.total_count,
        "percent": checkpoint.completion_percent,
    }


def prazo_bucket(demanda: Demanda, today: date):
    if not demanda.final_poc:
        return "Sem previsão"
    if demanda.status_etapa_atual == "Implantado":
        return "No prazo"
    diff = (demanda.final_poc - today).days
    if diff < 0:
        return "Vencidas"
    if diff <= 3:
        return "Vence em até 3 dias"
    return "No prazo"


def farol_for(demanda: Demanda, checkpoint_stats: dict, today: date):
    if not demanda.final_poc:
        return "Vermelho"
    if demanda.status_etapa_atual != "Implantado" and demanda.final_poc < today:
        return "Vermelho"
    percent = checkpoint_stats.get("percent", 0) or 0
    if percent >= 100:
        return "Verde"
    if percent >= 70:
        return "Amarelo"
    return "Laranja"


@app.route("/api/indicadores")
def api_indicadores():
    demandas = apply_access_filter(Demanda.query).order_by(Demanda.id.asc()).all()
    today = date.today()

    status_counts = {name: 0 for name in STATUS_OPTIONS}
    analista_map = {}
    prazo_counts = {"No prazo": 0, "Vence em até 3 dias": 0, "Vencidas": 0, "Sem previsão": 0}
    pending_fields = {field: 0 for field in CHECKPOINT_FIELDS}
    farol_rows = []
    completion_values = []
    pendentes_config = 0
    implantacao_status = {"POC", "Homolog cliente", "Fila OSP"}

    field_labels = {
        "tipo_agente_virtual": "Tipo de Agente Virtual",
        "organizacao": "Organização",
        "plano_tabulacao": "Plano de Tabulação",
        "horario_inicio": "Horário Início",
        "horario_fim": "Horário Fim",
        "recursos_midia": "Recursos de Mídia",
        "lcr_rota": "LCR ROTA",
        "rota_portal_voz": "Rota Portal de Voz",
        "canais": "Canais",
        "url_aplicacao": "URL da Aplicação",
        "dnis_portal_voz": "DNIS Portal de Voz",
        "tempo_maximo_chamada": "Tempo Máximo Chamada",
        "campanha_receptiva": "Campanha Receptiva",
        "calculo_demanda": "Cálculo de Demanda",
        "portal_voz": "Portal de Voz",
        "plano_tarifacao_telecom": "Plano Tarifação Telecom",
        "plano_tarifacao_agentes_digitais": "Plano Tarifação Agentes Digitais",
        "gestor_negocio": "Gestor de Negócio",
    }

    for demanda in demandas:
        status_counts[demanda.status_etapa_atual] = status_counts.get(demanda.status_etapa_atual, 0) + 1
        analista = demanda.acompanhamento or "Sem responsável"
        analista_map.setdefault(analista, {"analista": analista, "total": 0, "poc": 0, "fila_osp": 0, "pendentes_checkpoint": 0})
        analista_map[analista]["total"] += 1
        if demanda.status_etapa_atual == "POC":
            analista_map[analista]["poc"] += 1
        if demanda.status_etapa_atual == "Fila OSP":
            analista_map[analista]["fila_osp"] += 1

        checkpoint = Checkpoint.query.filter_by(demanda_id=demanda.id).first()
        stats = checkpoint_stats_for_demanda(demanda.id)
        completion_values.append(stats["percent"])
        if stats["pending"] > 0:
            pendentes_config += 1
            analista_map[analista]["pendentes_checkpoint"] += 1

        if checkpoint:
            for field in CHECKPOINT_FIELDS:
                if not clean_text(getattr(checkpoint, field, None)):
                    pending_fields[field] += 1
        else:
            for field in CHECKPOINT_FIELDS:
                pending_fields[field] += 1

        prazo = prazo_bucket(demanda, today)
        prazo_counts[prazo] += 1
        farol = farol_for(demanda, stats, today)
        farol_rows.append({
            "id": demanda.id,
            "cliente": demanda.cliente,
            "carteira": demanda.carteira or "Sem carteira",
            "status": demanda.status_etapa_atual,
            "checkpoint_percent": stats["percent"],
            "pendentes": stats["pending"],
            "final_poc": format_date_br(demanda.final_poc),
            "farol": farol,
        })

    ranking_pendencias = [
        {"campo": field_labels.get(field, field), "qtde": qtde}
        for field, qtde in sorted(pending_fields.items(), key=lambda item: item[1], reverse=True)
        if qtde > 0
    ][:10]

    analistas = sorted(analista_map.values(), key=lambda item: item["total"], reverse=True)
    media_checkpoint = round(sum(completion_values) / len(completion_values), 1) if completion_values else 0
    farol_order = {"Vermelho": 0, "Laranja": 1, "Amarelo": 2, "Verde": 3}
    farol_rows.sort(key=lambda item: (farol_order.get(item["farol"], 9), item["checkpoint_percent"], item["id"]))

    return jsonify({
        "cards": {
            "total_demandas": len(demandas),
            "em_implantacao_poc": sum(status_counts.get(s, 0) for s in implantacao_status),
            "implantadas": status_counts.get("Implantado", 0),
            "pendentes_configuracao": pendentes_config,
            "conclusao_media_checkpoint": media_checkpoint,
            "demandas_vencidas": prazo_counts["Vencidas"],
        },
        "status_counts": status_counts,
        "analistas": analistas,
        "ranking_pendencias": ranking_pendencias,
        "farol_clientes": farol_rows[:20],
        "prazo_counts": prazo_counts,
    })


def apply_payload(demanda: Demanda, data: dict, creating: bool):
    cliente = clean_text(data.get("cliente"))
    if creating and not cliente:
        raise ValueError("Cliente é obrigatório")

    if cliente is not None:
        demanda.cliente = cliente
    demanda.acompanhamento = clean_text(data.get("acompanhamento"))
    demanda.validacao_dados_locator = clean_text(data.get("validacao_dados_locator"))
    demanda.carteira = clean_text(data.get("carteira"))
    demanda.status_etapa_atual = clean_text(data.get("status_etapa_atual")) or "Em Mapeamento"
    demanda.inicio_poc = parse_date(data.get("inicio_poc"))
    demanda.final_poc = parse_date(data.get("final_poc"))
    demanda.wrike = clean_text(data.get("wrike"))


@app.errorhandler(ValueError)
def handle_value_error(error):
    return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
