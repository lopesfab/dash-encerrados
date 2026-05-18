import os
import xmlrpc.client
import json
from datetime import datetime

# ── Configuração ────────────────────────────────────────────────
# Em produção (GitHub Actions), as credenciais vêm de variáveis
# de ambiente (Secrets). Em desenvolvimento local, usa os defaults.
URL      = os.environ.get("ODOO_URL",      "https://mmp.intelligenti.com.br")
DB       = os.environ.get("ODOO_DB",       "mmp.intelligenti.com.br")
USERNAME = os.environ.get("ODOO_USERNAME", "Intel_bot_andamento")
PASSWORD = os.environ.get("ODOO_PASSWORD", "Intel_bot_andamento")

DOMAIN = [
    "&",
    ["polo_cliente", "=", "p"],
    ["data_encerramento", ">=", "2026-01-01"],
]

FIELDS = [
    "id", "name", "processo",
    "fase_id", "situacao_id", "state",
    "estado_cliente",
    "carteira_id", "carteira_metas_id",
    "objeto_id", "estado_id",
    "projeto_id", "grupo_id",
    "motivo_encerramento_id",
    "valor_encerramento_cliente",
    "data_encerramento",
]

ESTADO_CLIENTE_LABELS = {
    "a": "Ativo",
    "e": "Encerrado",
    "m": "Migrado",
    "s": "Suspenso",
}

# ── Conexão ─────────────────────────────────────────────────────
print(f"[{datetime.now():%H:%M:%S}] Conectando ao Odoo...")
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
if not uid:
    raise Exception("Autenticacao falhou.")
print(f"[{datetime.now():%H:%M:%S}] Autenticado. UID={uid}")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

# ── Busca registros encerrados ───────────────────────────────────
print(f"[{datetime.now():%H:%M:%S}] Buscando dossies encerrados...")
records = models.execute_kw(
    DB, uid, PASSWORD,
    "dossie.dossie", "search_read",
    [DOMAIN],
    {"fields": FIELDS, "limit": 0}
)
print(f"[{datetime.now():%H:%M:%S}] {len(records)} encerrados encontrados.")

# ── Busca siglas UF via res.country.state ────────────────────────
print(f"[{datetime.now():%H:%M:%S}] Buscando siglas UF...")
estado_ids = list(set(r["estado_id"][0] for r in records if r.get("estado_id")))
uf_map = {}
if estado_ids:
    estados = models.execute_kw(DB, uid, PASSWORD,
        "res.country.state", "read",
        [estado_ids],
        {"fields": ["id", "code"]}
    )
    for e in estados:
        uf_map[e["id"]] = e.get("code", "N/A")
print(f"[{datetime.now():%H:%M:%S}] {len(uf_map)} UFs mapeadas.")

# ── Normalização ─────────────────────────────────────────────────
def m2o(val):
    return val[1] if val else None

def parse_date(val):
    if not val:
        return {"dia": "", "semana": "", "mes": "", "ano": ""}
    try:
        dt = datetime.strptime(val[:10], "%Y-%m-%d")
        jan1 = datetime(dt.year, 1, 1)
        week = ((dt - jan1).days + jan1.weekday() + 1) // 7 + 1
        return {
            "dia":    dt.strftime("%Y-%m-%d"),
            "semana": f"{dt.year}-W{week:02d}",
            "mes":    dt.strftime("%Y-%m"),
            "ano":    dt.strftime("%Y"),
        }
    except Exception:
        return {"dia": "", "semana": "", "mes": "", "ano": ""}

def to_float(val):
    try:
        return float(val) if val is not None else 0.0
    except Exception:
        return 0.0

compact = []
hier = {}
ec_debug = {}

for r in records:
    gr  = m2o(r.get("grupo_id"))          or "N/A"
    pr  = m2o(r.get("projeto_id"))        or "N/A"
    cm  = m2o(r.get("carteira_metas_id")) or "Sem carteira"
    fa  = m2o(r.get("fase_id"))           or "N/A"
    si  = m2o(r.get("situacao_id"))       or "N/A"

    ec_raw = r.get("estado_cliente") or ""
    ec = ESTADO_CLIENTE_LABELS.get(ec_raw, "N/A")
    ec_debug[ec_raw] = ec_debug.get(ec_raw, 0) + 1

    ob  = m2o(r.get("objeto_id"))         or "N/A"
    mt  = m2o(r.get("motivo_encerramento_id")) or "Sem motivo"

    valor = to_float(r.get("valor_encerramento_cliente"))

    estado_val = r.get("estado_id")
    uf = uf_map.get(estado_val[0], "N/A") if estado_val else "N/A"

    dts = parse_date(r.get("data_encerramento"))

    compact.append([
        gr, pr, cm, fa, si, ec, ob, uf,
        dts["dia"], dts["semana"], dts["mes"], dts["ano"],
        mt, valor,
    ])

    if gr not in hier:
        hier[gr] = {}
    if pr not in hier[gr]:
        hier[gr][pr] = set()
    hier[gr][pr].add(cm)

print(f"[{datetime.now():%H:%M:%S}] estado_cliente valores: {ec_debug}")

hier_out = {g: {p: sorted(list(c)) for p, c in ps.items()} for g, ps in hier.items()}

output = {
    "gerado_em":  datetime.now().strftime("%d/%m/%Y %H:%M"),
    "total":      len(compact),
    "tipo":       "encerrados",
    "hier":       hier_out,
    "rows":       compact,
}

with open("dados_encerrados.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

print(f"[{datetime.now():%H:%M:%S}] dados_encerrados.json gerado com {len(compact)} registros.")
