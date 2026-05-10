import streamlit as st
import anthropic
import json
 
# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Paciente Virtual · Tutoria Médica",
    page_icon="🩺",
    layout="wide",
)
 
# ── CSS personalizado ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
 
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
 
/* Cabeçalho do paciente */
.paciente-card {
    background: #f0f4ff;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 24px;
}
.paciente-card h2 { margin: 0 0 4px; font-size: 1.2rem; color: #1e3a8a; }
.paciente-card p  { margin: 0; color: #3b4a6b; font-size: 0.9rem; }
 
/* Cards de categoria */
.cat-oculta {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 8px;
    color: #94a3b8;
    font-size: 0.9rem;
}
.cat-revelada {
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.cat-revelada .label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #16a34a;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}
.cat-revelada .conteudo {
    font-size: 0.92rem;
    color: #1a2e1a;
    line-height: 1.6;
}
 
/* Tags de hipóteses */
.hip-tag {
    display: inline-block;
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.82rem;
    margin: 3px;
}
 
/* Rodapé da sessão */
.session-info {
    font-size: 0.78rem;
    color: #94a3b8;
    text-align: right;
    margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)
 
# ── Categorias clínicas ─────────────────────────────────────────────────────
CATEGORIAS = [
    ("queixa",       "💬 Queixa principal"),
    ("hda",          "📋 História da doença atual"),
    ("antecedentes", "🗂️ Antecedentes pessoais"),
    ("medicamentos", "💊 Medicamentos em uso"),
    ("alergias",     "⚠️ Alergias"),
    ("familiar",     "👨‍👩‍👧 Histórico familiar"),
    ("habitos",      "🏃 Hábitos de vida"),
    ("exame_fisico", "🩺 Exame físico"),
    ("exames_lab",   "🔬 Exames laboratoriais"),
    ("imagem",       "🖥️ Exames de imagem"),
    ("hipoteses_doc","💡 Hipóteses do caso (tutor)"),
    ("conduta_doc",  "📝 Conduta do caso (tutor)"),
]
 
# ── Estado da sessão ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "caso_processado": False,
        "caso_data": {},
        "revelados": set(),
        "hipoteses": [],
        "notas": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
 
init_state()
 
# ── Função: processar caso com Claude ──────────────────────────────────────
def processar_caso(texto: str, api_key: str) -> dict:
    prompt = f"""Você é um assistente médico educacional. Analise o texto da história do paciente abaixo e extraia as informações nas categorias indicadas. Responda APENAS em JSON válido, sem texto adicional, sem markdown, sem crases.
 
Categorias do JSON:
- queixa: queixa principal (1-2 frases curtas, como o paciente descreveria)
- hda: história da doença atual detalhada
- antecedentes: antecedentes pessoais e comorbidades
- medicamentos: medicamentos em uso com doses se disponíveis
- alergias: alergias conhecidas
- familiar: histórico familiar relevante
- habitos: hábitos de vida (tabagismo, etilismo, atividade física, dieta, sono)
- exame_fisico: achados do exame físico organizados por sistemas
- exames_lab: resultados de exames laboratoriais com valores de referência se disponíveis
- imagem: resultados de exames de imagem com os achados principais
- hipoteses_doc: hipóteses diagnósticas do caso (para o tutor ver)
- conduta_doc: conduta proposta no caso (para o tutor ver)
- nome_paciente: nome do paciente se mencionado, senão "Paciente não identificado"
- desc_paciente: resumo em uma frase: idade, sexo, ocupação
- emoji_paciente: emoji adequado ao perfil (ex: 👴 👩 🧒)
 
Se a categoria não tiver informação no texto, use: "Não informado neste caso."
 
Texto:
{texto}"""
 
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
 
# ═══════════════════════════════════════════════════════════════════════════
# INTERFACE
# ═══════════════════════════════════════════════════════════════════════════
 
st.title("🩺 Paciente Virtual · Tutoria Médica")
st.caption("Interface para o tutor controlar as informações do caso clínico em tempo real")
 
# ── Sidebar: configuração e entrada do caso ─────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuração")
 
    api_key = st.text_input(
        "Chave API Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Obtenha em console.anthropic.com"
    )
 
    st.divider()
    st.header("📄 História do Paciente")
 
    historia = st.text_area(
        "Cole o texto completo aqui:",
        height=280,
        placeholder="Ex: Paciente masculino, 58 anos, aposentado, tabagista há 30 anos...",
    )
 
    processar = st.button("🔄 Processar Caso", use_container_width=True, type="primary")
 
    if processar:
        if not api_key:
            st.error("Informe sua chave de API Anthropic.")
        elif not historia.strip():
            st.error("Cole o texto da história do paciente.")
        else:
            with st.spinner("A IA está organizando o caso..."):
                try:
                    dados = processar_caso(historia, api_key)
                    st.session_state.caso_data    = dados
                    st.session_state.caso_processado = True
                    st.session_state.revelados    = set()
                    st.session_state.hipoteses    = []
                    st.session_state.notas        = ""
                    st.success("Caso processado com sucesso!")
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Erro ao interpretar a resposta da IA. Tente novamente.")
                except Exception as e:
                    st.error(f"Erro: {e}")
 
    if st.session_state.caso_processado:
        st.divider()
        if st.button("🔁 Nova Sessão", use_container_width=True):
            for k in ["caso_processado","caso_data","revelados","hipoteses","notas"]:
                del st.session_state[k]
            st.rerun()
 
# ── Área principal ──────────────────────────────────────────────────────────
if not st.session_state.caso_processado:
    st.info("👈  Cole a história do paciente na barra lateral e clique em **Processar Caso** para iniciar a tutoria.")
    st.stop()
 
dados = st.session_state.caso_data
 
# Cabeçalho do paciente
emoji = dados.get("emoji_paciente", "👤")
nome  = dados.get("nome_paciente", "Paciente")
desc  = dados.get("desc_paciente", "")
 
st.markdown(f"""
<div class="paciente-card">
    <h2>{emoji} {nome}</h2>
    <p>{desc}</p>
</div>
""", unsafe_allow_html=True)
 
# ── Duas colunas: categorias | hipóteses/notas ──────────────────────────────
col_cats, col_notas = st.columns([3, 2], gap="large")
 
with col_cats:
    st.subheader("Categorias Clínicas")
 
    # Botões de controle rápido
    c1, c2 = st.columns(2)
    with c1:
        if st.button("👁️ Revelar todas", use_container_width=True):
            st.session_state.revelados = {cat[0] for cat in CATEGORIAS}
            st.rerun()
    with c2:
        if st.button("🔒 Ocultar todas", use_container_width=True):
            st.session_state.revelados = set()
            st.rerun()
 
    st.markdown("---")
 
    for cat_id, cat_label in CATEGORIAS:
        conteudo = dados.get(cat_id, "Não informado neste caso.")
        revelado = cat_id in st.session_state.revelados
 
        col_label, col_btn = st.columns([4, 1])
 
        with col_label:
            if revelado:
                st.markdown(f"""
                <div class="cat-revelada">
                    <div class="label">✅ {cat_label}</div>
                    <div class="conteudo">{conteudo}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="cat-oculta">
                    🔒 <strong>{cat_label}</strong> — oculto
                </div>
                """, unsafe_allow_html=True)
 
        with col_btn:
            if not revelado:
                if st.button("Revelar", key=f"rev_{cat_id}", use_container_width=True):
                    st.session_state.revelados.add(cat_id)
                    st.rerun()
            else:
                if st.button("Ocultar", key=f"oc_{cat_id}", use_container_width=True):
                    st.session_state.revelados.discard(cat_id)
                    st.rerun()
 
with col_notas:
    st.subheader("Registro da Sessão")
 
    # Hipóteses e condutas
    st.markdown("**💡 Hipóteses e condutas propostas pelos alunos**")
    nova_hip = st.text_input("Digitar hipótese ou conduta:", placeholder="Ex: Pneumonia bacteriana...")
    if st.button("➕ Adicionar", use_container_width=True) and nova_hip.strip():
        st.session_state.hipoteses.append(nova_hip.strip())
        st.rerun()
 
    if st.session_state.hipoteses:
        for i, h in enumerate(st.session_state.hipoteses):
            c_h, c_x = st.columns([5, 1])
            with c_h:
                st.markdown(f'<span class="hip-tag">🔹 {h}</span>', unsafe_allow_html=True)
            with c_x:
                if st.button("✕", key=f"del_hip_{i}"):
                    st.session_state.hipoteses.pop(i)
                    st.rerun()
    else:
        st.caption("Nenhuma hipótese registrada ainda.")
 
    st.divider()
 
    # Notas do tutor
    st.markdown("**📝 Observações do tutor**")
    st.session_state.notas = st.text_area(
        "Anotações sobre o desempenho e raciocínio da turma:",
        value=st.session_state.notas,
        height=180,
        label_visibility="collapsed",
        placeholder="Ex: Turma identificou corretamente a queixa respiratória, mas não perguntou sobre tabagismo na primeira rodada..."
    )
 
    st.divider()
 
    # Resumo da sessão
    revelados_n = len(st.session_state.revelados)
    total_n     = len(CATEGORIAS)
    st.markdown(f"**📊 Progresso da sessão**")
    st.progress(revelados_n / total_n, text=f"{revelados_n} de {total_n} categorias reveladas")
 
    cats_reveladas = [
        label for cid, label in CATEGORIAS if cid in st.session_state.revelados
    ]
    if cats_reveladas:
        with st.expander("Ver categorias reveladas"):
            for c in cats_reveladas:
                st.markdown(f"- {c}")
 
