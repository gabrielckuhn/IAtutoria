"""
app.py — Painel do Tutor · Paciente Virtual
Rode em: https://share.streamlit.io  (porta padrão)
"""

import streamlit as st
import anthropic
import json
import time
from db import salvar_estado

# ── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tutor · Paciente Virtual",
    page_icon="🩺",
    layout="wide",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

.paciente-card {
    background: #f0f4ff; border-left: 4px solid #2563eb;
    border-radius: 8px; padding: 16px 20px; margin-bottom: 20px;
}
.paciente-card h2 { margin: 0 0 4px; font-size: 1.2rem; color: #1e3a8a; }
.paciente-card p  { margin: 0; color: #3b4a6b; font-size: 0.9rem; }

.cat-oculta {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 6px;
    color: #94a3b8; font-size: 0.9rem;
}
.cat-revelada {
    background: #f0fdf4; border: 1px solid #86efac;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 6px;
}
.cat-revelada .lbl {
    font-size: 0.72rem; font-weight: 600; color: #16a34a;
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 5px;
}
.cat-revelada .txt { font-size: 0.9rem; color: #1a2e1a; line-height: 1.6; }

.hip-tag {
    display: inline-block; background: #eff6ff; color: #1d4ed8;
    border: 1px solid #bfdbfe; border-radius: 20px;
    padding: 4px 12px; font-size: 0.82rem; margin: 3px;
}
.link-box {
    background: #ecfdf5; border: 1px solid #6ee7b7; border-radius: 8px;
    padding: 10px 16px; font-size: 0.85rem; color: #065f46;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ── Categorias ───────────────────────────────────────────────────────────────
CATEGORIAS = [
    ("queixa",        "💬 Queixa principal"),
    ("hda",           "📋 História da doença atual"),
    ("antecedentes",  "🗂️ Antecedentes pessoais"),
    ("medicamentos",  "💊 Medicamentos em uso"),
    ("alergias",      "⚠️ Alergias"),
    ("familiar",      "👨‍👩‍👧 Histórico familiar"),
    ("habitos",       "🏃 Hábitos de vida"),
    ("exame_fisico",  "🩺 Exame físico"),
    ("exames_lab",    "🔬 Exames laboratoriais"),
    ("imagem",        "🖥️ Exames de imagem"),
    ("hipoteses_doc", "💡 Hipóteses do caso (tutor)"),
    ("conduta_doc",   "📝 Conduta proposta (tutor)"),
]

# ── Estado local ─────────────────────────────────────────────────────────────
for k, v in {
    "caso_processado": False,
    "caso_data": {},
    "revelados": set(),
    "ultimo_revelado": None,
    "hipoteses": [],
    "notas": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Processar caso ───────────────────────────────────────────────────────────
def processar_caso(texto: str, api_key: str) -> dict:
    prompt = f"""Você é um assistente médico educacional. Analise o texto da história do paciente e extraia as informações nas categorias abaixo. Responda APENAS em JSON válido, sem texto adicional, sem markdown, sem crases.

Categorias:
- queixa: queixa principal em 1ª pessoa, como o paciente diria (1-2 frases curtas)
- hda: história da doença atual em 1ª pessoa, detalhada
- antecedentes: antecedentes pessoais e comorbidades
- medicamentos: medicamentos em uso com doses
- alergias: alergias conhecidas
- familiar: histórico familiar relevante
- habitos: hábitos de vida (tabagismo, etilismo, atividade física, dieta, sono)
- exame_fisico: achados do exame físico por sistemas
- exames_lab: resultados laboratoriais com valores
- imagem: achados de exames de imagem
- hipoteses_doc: hipóteses diagnósticas (apenas para o tutor)
- conduta_doc: conduta proposta (apenas para o tutor)
- nome_paciente: nome completo ou "Paciente não identificado"
- desc_paciente: uma frase com idade, sexo e ocupação
- sexo: "masculino", "feminino" ou "crianca"
- prompt_avatar: descrição em inglês para gerar retrato realista do paciente. Exemplo: "elderly Brazilian man 68 years old tired expression white hospital gown neutral white background portrait photorealistic"

Se a categoria não tiver informação, use: "Não informado neste caso."

Texto:
{texto}"""

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)

# ════════════════════════════════════════════════════════════════════════════
# INTERFACE
# ════════════════════════════════════════════════════════════════════════════
st.title("🩺 Painel do Tutor · Paciente Virtual")
st.caption("Controle as informações reveladas — o projetor sincroniza automaticamente")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key = st.text_input(
        "Chave API Anthropic", type="password", placeholder="sk-ant-...",
        help="Obtenha em console.anthropic.com"
    )

    st.divider()
    st.header("📄 História do Paciente")
    historia = st.text_area(
        "Cole o texto completo:", height=260,
        placeholder="Paciente masculino, 58 anos, tabagista há 30 anos...",
    )

    if st.button("🔄 Processar Caso", use_container_width=True, type="primary"):
        if not api_key:
            st.error("Informe a chave de API Anthropic.")
        elif not historia.strip():
            st.error("Cole o texto da história do paciente.")
        else:
            with st.spinner("IA organizando o caso..."):
                try:
                    dados = processar_caso(historia, api_key)
                    st.session_state.caso_data       = dados
                    st.session_state.caso_processado = True
                    st.session_state.revelados       = set()
                    st.session_state.ultimo_revelado = None
                    st.session_state.hipoteses       = []
                    st.session_state.notas           = ""
                    salvar_estado(dados, [], None)
                    st.success("Caso processado! Projetor atualizado.")
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Erro ao interpretar resposta. Tente novamente.")
                except Exception as e:
                    st.error(f"Erro: {e}")

    if st.session_state.caso_processado:
        st.divider()
        if st.button("🔁 Nova Sessão", use_container_width=True):
            try:
                salvar_estado({}, [], None)
            except Exception:
                pass
            for k in ["caso_processado","caso_data","revelados","ultimo_revelado","hipoteses","notas"]:
                del st.session_state[k]
            st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
if not st.session_state.caso_processado:
    st.info("👈  Cole a história do paciente na barra lateral e clique em **Processar Caso**.")
    st.stop()

dados = st.session_state.caso_data
nome  = dados.get("nome_paciente", "Paciente")
desc  = dados.get("desc_paciente", "")

st.markdown(f"""
<div class="paciente-card">
    <h2>👤 {nome}</h2>
    <p>{desc}</p>
</div>
<div class="link-box">
    🖥️ Tela do projetor → abra o app <strong>projetor.py</strong> no Streamlit Cloud e projete essa aba
</div>
""", unsafe_allow_html=True)

col_cats, col_notas = st.columns([3, 2], gap="large")

# ── Categorias ───────────────────────────────────────────────────────────────
with col_cats:
    st.subheader("Categorias Clínicas")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("👁️ Revelar todas", use_container_width=True):
            st.session_state.revelados = {c[0] for c in CATEGORIAS}
            salvar_estado(dados, list(st.session_state.revelados),
                          st.session_state.ultimo_revelado)
            st.rerun()
    with c2:
        if st.button("🔒 Ocultar todas", use_container_width=True):
            st.session_state.revelados = set()
            st.session_state.ultimo_revelado = None
            salvar_estado(dados, [], None)
            st.rerun()

    st.markdown("---")

    for cat_id, cat_label in CATEGORIAS:
        conteudo = dados.get(cat_id, "Não informado neste caso.")
        revelado  = cat_id in st.session_state.revelados
        cl, cb    = st.columns([4, 1])

        with cl:
            if revelado:
                st.markdown(f"""
                <div class="cat-revelada">
                    <div class="lbl">✅ {cat_label}</div>
                    <div class="txt">{conteudo}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="cat-oculta">
                    🔒 <strong>{cat_label}</strong> — oculto
                </div>""", unsafe_allow_html=True)

        with cb:
            if not revelado:
                if st.button("Revelar", key=f"rev_{cat_id}", use_container_width=True):
                    st.session_state.revelados.add(cat_id)
                    ur = {"id": cat_id, "label": cat_label,
                          "conteudo": conteudo, "ts": time.time()}
                    st.session_state.ultimo_revelado = ur
                    salvar_estado(dados, list(st.session_state.revelados), ur)
                    st.rerun()
            else:
                if st.button("Ocultar", key=f"oc_{cat_id}", use_container_width=True):
                    st.session_state.revelados.discard(cat_id)
                    salvar_estado(dados, list(st.session_state.revelados),
                                  st.session_state.ultimo_revelado)
                    st.rerun()

# ── Notas ────────────────────────────────────────────────────────────────────
with col_notas:
    st.subheader("Registro da Sessão")

    st.markdown("**💡 Hipóteses e condutas dos alunos**")
    nova = st.text_input("Nova hipótese:", placeholder="Ex: Pneumonia bacteriana...")
    if st.button("➕ Adicionar", use_container_width=True) and nova.strip():
        st.session_state.hipoteses.append(nova.strip())
        st.rerun()

    for i, h in enumerate(st.session_state.hipoteses):
        ch, cx = st.columns([5, 1])
        with ch:
            st.markdown(f'<span class="hip-tag">🔹 {h}</span>', unsafe_allow_html=True)
        with cx:
            if st.button("✕", key=f"del_{i}"):
                st.session_state.hipoteses.pop(i)
                st.rerun()

    if not st.session_state.hipoteses:
        st.caption("Nenhuma hipótese registrada.")

    st.divider()
    st.markdown("**📝 Observações do tutor**")
    st.session_state.notas = st.text_area(
        "Notas:", value=st.session_state.notas, height=160,
        label_visibility="collapsed",
        placeholder="Desempenho da turma, dificuldades observadas...",
    )

    st.divider()
    rev_n = len(st.session_state.revelados)
    tot_n = len(CATEGORIAS)
    st.markdown("**📊 Progresso**")
    st.progress(rev_n / tot_n, text=f"{rev_n} de {tot_n} categorias reveladas")
