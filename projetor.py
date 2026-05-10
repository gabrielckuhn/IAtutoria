"""
projetor.py — Tela do Projetor · Paciente Virtual
Rode como app separado no Streamlit Cloud (mesmo repositório, arquivo diferente)
"""

import streamlit as st
import time
import io
import urllib.parse
from gtts import gTTS
from db import carregar_estado

# ── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Paciente Virtual · Projetor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS do projetor (tema escuro para projeção) ───────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Lato', sans-serif;
    background-color: #0f172a !important;
    color: #f1f5f9;
}
.main > div { padding-top: 0.5rem; }

.header-bar {
    background: #1e3a5f;
    border-bottom: 2px solid #2563eb;
    padding: 14px 28px;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex; align-items: center; gap: 16px;
}
.header-bar h1 { margin: 0; font-size: 1.5rem; color: #e2e8f0; font-weight: 300; }
.header-bar .sub { font-size: 0.8rem; color: #94a3b8; margin: 0; }
.badge { background: #1d4ed8; color: #fff; border-radius: 6px;
    padding: 4px 12px; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase; margin-left: auto; }

.avatar-box {
    background: #1e293b; border: 2px solid #334155;
    border-radius: 14px; padding: 14px; text-align: center;
}
.nome { font-size: 1.2rem; font-weight: 700; color: #e2e8f0; margin: 10px 0 3px; }
.desc { font-size: 0.82rem; color: #94a3b8; }

.destaque {
    background: #1e3a5f; border: 2px solid #3b82f6;
    border-radius: 12px; padding: 18px 22px; margin-bottom: 14px;
}
.destaque .lbl {
    font-size: 0.68rem; font-weight: 700; color: #93c5fd;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;
}
.destaque .txt { font-size: 1.05rem; color: #fff; line-height: 1.7; }

.info-card {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}
.info-card .lbl {
    font-size: 0.68rem; font-weight: 700; color: #60a5fa;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;
}
.info-card .txt { font-size: 0.95rem; color: #e2e8f0; line-height: 1.65; }

.aguardando {
    background: #1e293b; border: 1px dashed #334155;
    border-radius: 12px; padding: 50px 20px;
    text-align: center; color: #475569; font-size: 1rem;
}
.aguardando .ico { font-size: 2.8rem; margin-bottom: 10px; }

.prog-wrap {
    background: #1e293b; border-radius: 8px;
    padding: 10px 14px; margin-bottom: 10px; font-size: 0.78rem; color: #94a3b8;
}
.barra { background: #334155; border-radius: 4px; height: 5px; margin-top: 5px; }
.barra-fill { background: #3b82f6; height: 100%; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

CATEGORIAS_LABELS = {
    "queixa":        "💬 Queixa principal",
    "hda":           "📋 História da doença atual",
    "antecedentes":  "🗂️ Antecedentes pessoais",
    "medicamentos":  "💊 Medicamentos em uso",
    "alergias":      "⚠️ Alergias",
    "familiar":      "👨‍👩‍👧 Histórico familiar",
    "habitos":       "🏃 Hábitos de vida",
    "exame_fisico":  "🩺 Exame físico",
    "exames_lab":    "🔬 Exames laboratoriais",
    "imagem":        "🖥️ Exames de imagem",
    "hipoteses_doc": "💡 Hipóteses do caso",
    "conduta_doc":   "📝 Conduta proposta",
}

# ── Estado local do projetor ──────────────────────────────────────────────────
if "ultimo_ts_visto" not in st.session_state:
    st.session_state.ultimo_ts_visto = 0.0
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

# ── Carregar estado do Supabase ───────────────────────────────────────────────
try:
    estado = carregar_estado()
except Exception as e:
    st.error(f"Erro ao conectar ao banco: {e}")
    st.stop()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
    <div>
        <h1>🏥 Paciente Virtual</h1>
        <p class="sub">Tutoria em Raciocínio Clínico</p>
    </div>
    <span class="badge">Projetor</span>
</div>
""", unsafe_allow_html=True)

# ── Sem caso ──────────────────────────────────────────────────────────────────
if not estado or not estado.get("caso_data"):
    st.markdown("""
    <div class="aguardando">
        <div class="ico">⏳</div>
        Aguardando o tutor processar um caso clínico...
    </div>
    """, unsafe_allow_html=True)
    time.sleep(3)
    st.rerun()
    st.stop()

# ── Dados ─────────────────────────────────────────────────────────────────────
dados       = estado["caso_data"]
revelados   = set(estado.get("revelados", []))
ultimo_rev  = estado.get("ultimo_revelado")
ts_atual    = float(estado.get("timestamp", 0.0))
nome        = dados.get("nome_paciente", "Paciente")
desc        = dados.get("desc_paciente", "")
sexo        = dados.get("sexo", "masculino")
prompt_av   = dados.get("prompt_avatar", "Brazilian patient portrait photorealistic neutral background")

# ── Gerar áudio quando há novo reveal ────────────────────────────────────────
def limpar_label(label: str) -> str:
    for emoji in ["💬","📋","🗂️","💊","⚠️","👨‍👩‍👧","🏃","🩺","🔬","🖥️","💡","📝"]:
        label = label.replace(emoji, "")
    return label.strip()

if ultimo_rev and ts_atual != st.session_state.ultimo_ts_visto:
    conteudo_fala = ultimo_rev.get("conteudo", "")
    label_fala    = limpar_label(ultimo_rev.get("label", ""))
    if conteudo_fala and conteudo_fala != "Não informado neste caso.":
        try:
            texto_fala = f"{label_fala}. {conteudo_fala}"
            tts = gTTS(text=texto_fala, lang="pt", tld="com.br", slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            st.session_state.audio_bytes = buf.read()
        except Exception:
            st.session_state.audio_bytes = None
    st.session_state.ultimo_ts_visto = ts_atual

# ── Avatar URL (Pollinations.ai — gratuito, sem API key) ─────────────────────
def avatar_url(prompt: str) -> str:
    p = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{p}?width=480&height=640&nologo=true&seed=99"

# ── Layout ────────────────────────────────────────────────────────────────────
col_av, col_info = st.columns([1, 2], gap="large")

with col_av:
    st.markdown('<div class="avatar-box">', unsafe_allow_html=True)
    st.image(avatar_url(prompt_av), use_container_width=True)
    st.markdown(f"""
        <div class="nome">{nome}</div>
        <div class="desc">{desc}</div>
    </div>""", unsafe_allow_html=True)

    # Progresso
    rev_n = len(revelados)
    tot_n = len(CATEGORIAS_LABELS)
    pct   = int(rev_n / tot_n * 100) if tot_n else 0
    st.markdown(f"""
    <div class="prog-wrap">
        {rev_n} de {tot_n} informações reveladas
        <div class="barra">
            <div class="barra-fill" style="width:{pct}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Áudio automático
    if st.session_state.audio_bytes:
        st.audio(st.session_state.audio_bytes, format="audio/mp3", autoplay=True)

with col_info:
    if not revelados:
        st.markdown("""
        <div class="aguardando" style="margin-top:0">
            <div class="ico">🩺</div>
            O tutor vai revelar as informações conforme os alunos perguntam.
        </div>
        """, unsafe_allow_html=True)
    else:
        # Último revelado em destaque
        if ultimo_rev and ultimo_rev.get("id") in revelados:
            label    = CATEGORIAS_LABELS.get(ultimo_rev["id"], ultimo_rev.get("label",""))
            conteudo = ultimo_rev.get("conteudo", "")
            st.markdown(f"""
            <div class="destaque">
                <div class="lbl">🔔 Última informação · {label}</div>
                <div class="txt">{conteudo}</div>
            </div>
            """, unsafe_allow_html=True)

        # Demais revelados
        outras = [cid for cid in revelados
                  if not ultimo_rev or cid != ultimo_rev.get("id")]
        if outras:
            st.markdown("<hr style='border-color:#1e293b;margin:12px 0'>", unsafe_allow_html=True)
            for cid in outras:
                label    = CATEGORIAS_LABELS.get(cid, cid)
                conteudo = dados.get(cid, "Não informado neste caso.")
                st.markdown(f"""
                <div class="info-card">
                    <div class="lbl">{label}</div>
                    <div class="txt">{conteudo}</div>
                </div>
                """, unsafe_allow_html=True)

# ── Auto-refresh a cada 2s ────────────────────────────────────────────────────
time.sleep(2)
st.rerun()
