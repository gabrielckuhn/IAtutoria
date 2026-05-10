"""
db.py — Camada de acesso ao Supabase (estado compartilhado entre tutor e projetor)
Usa apenas requests, sem SDK externo.
"""

import json
import time
import requests
import streamlit as st

# ── Credenciais via st.secrets ───────────────────────────────────────────────
def _url():
    return st.secrets["SUPABASE_URL"].rstrip("/")

def _headers():
    return {
        "apikey":        st.secrets["SUPABASE_KEY"],
        "Authorization": f"Bearer {st.secrets['SUPABASE_KEY']}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }

TABELA = "sessao"
ID_FIXO = 1  # sempre usamos a linha com id=1 (upsert)

# ── Escrever estado ──────────────────────────────────────────────────────────
def salvar_estado(caso_data: dict, revelados: list, ultimo_revelado):
    payload = {
        "id":              ID_FIXO,
        "caso_data":       json.dumps(caso_data,      ensure_ascii=False),
        "revelados":       json.dumps(revelados,       ensure_ascii=False),
        "ultimo_revelado": json.dumps(ultimo_revelado, ensure_ascii=False),
        "timestamp":       time.time(),
    }
    r = requests.post(
        f"{_url()}/rest/v1/{TABELA}",
        headers={**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=payload,
        timeout=8,
    )
    r.raise_for_status()

# ── Ler estado ───────────────────────────────────────────────────────────────
def carregar_estado() -> dict | None:
    r = requests.get(
        f"{_url()}/rest/v1/{TABELA}?id=eq.{ID_FIXO}&select=*",
        headers=_headers(),
        timeout=8,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    row = rows[0]
    return {
        "caso_data":       json.loads(row["caso_data"]       or "{}"),
        "revelados":       json.loads(row["revelados"]       or "[]"),
        "ultimo_revelado": json.loads(row["ultimo_revelado"] or "null"),
        "timestamp":       row.get("timestamp", 0.0),
    }
