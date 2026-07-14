// ======================================================================
// Utilitários de API e UI
// ======================================================================

async function api(metodo, caminho, corpo) {
    const opcoes = { method: metodo, headers: {} };
    if (corpo !== undefined) {
        opcoes.headers["Content-Type"] = "application/json";
        opcoes.body = JSON.stringify(corpo);
    }

    const resposta = await fetch(caminho, opcoes);

    if (resposta.status === 204) return null;

    const texto = await resposta.text();
    let dados = null;
    if (texto) {
        try { dados = JSON.parse(texto); } catch { dados = texto; }
    }

    if (!resposta.ok) {
        throw new Error(formatarErro(dados));
    }
    return dados;
}

function formatarErro(dados) {
    const detalhe = dados && dados.detail !== undefined ? dados.detail : dados;
    if (Array.isArray(detalhe)) {
        // Erros de validação do FastAPI (422)
        return detalhe
            .map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`)
            .join(" · ");
    }
    return typeof detalhe === "string" ? detalhe : "Erro na requisição.";
}

function toast(mensagem, tipo = "sucesso") {
    const div = document.createElement("div");
    div.className = `toast ${tipo}`;
    div.textContent = mensagem;
    document.getElementById("toasts").appendChild(div);
    setTimeout(() => div.remove(), 4000);
}

// Rótulos amigáveis para as colunas das tabelas.
const ROTULOS = {
    id_atendimento: "ID",
    id_procedimento: "ID",
    id_paciente: "ID",
    id_pessoa: "ID",
    is_faturado: "Faturado",
    num_convenio: "Convênio",
    grupo_sanguineo: "Grupo sanguíneo",
    tempo_medio_minutos: "Tempo médio (min)",
    tempo_real_minutos: "Tempo real (min)",
    duracao_minutos: "Duração (min)",
    data_hora: "Data/Hora",
    data_admissao: "Admissão",
    nivel_risco: "Nível de risco",
    observacao: "Observação",
    total_atendimentos: "Total de atendimentos",
    total_plantoes: "Total de plantões",
    ano_residencia: "Ano",
};

function rotulo(chave) {
    if (ROTULOS[chave]) return ROTULOS[chave];
    return chave.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function formatarValor(valor) {
    if (valor === null || valor === undefined) return "—";
    if (typeof valor === "boolean") return valor ? "Sim" : "Não";
    if (typeof valor === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(valor)) {
        const [data, hora] = valor.split("T");
        const [a, m, d] = data.split("-");
        return `${d}/${m}/${a} ${hora.slice(0, 5)}`;
    }
    if (typeof valor === "string" && /^\d{4}-\d{2}-\d{2}$/.test(valor)) {
        const [a, m, d] = valor.split("-");
        return `${d}/${m}/${a}`;
    }
    return valor;
}

/**
 * Renderiza uma tabela genérica.
 * @param acoes  array de specs OU função (linha) => [spec]. Cada spec:
 *               { rotulo, aoClicar, classe?, desabilitado?, titulo? }
 * @param colunasOcultas colunas dos dados que não devem virar coluna visível.
 */
function renderTabela(container, linhas, acoes, colunasOcultas = []) {
    container.innerHTML = "";
    if (!linhas || linhas.length === 0) {
        container.innerHTML = '<p class="empty">Nenhum resultado encontrado.</p>';
        return;
    }

    const colunas = Object.keys(linhas[0]).filter((c) => !colunasOcultas.includes(c));
    const tabela = document.createElement("table");

    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    colunas.forEach((c) => {
        const th = document.createElement("th");
        th.textContent = rotulo(c);
        trh.appendChild(th);
    });
    if (acoes) {
        const th = document.createElement("th");
        th.textContent = "Ações";
        trh.appendChild(th);
    }
    thead.appendChild(trh);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");
    linhas.forEach((linha) => {
        const tr = document.createElement("tr");
        colunas.forEach((c) => {
            const td = document.createElement("td");
            td.textContent = formatarValor(linha[c]);
            tr.appendChild(td);
        });
        if (acoes) {
            const td = document.createElement("td");
            td.className = "col-acoes";
            const specs = typeof acoes === "function" ? acoes(linha) : acoes;
            specs.forEach((acao) => {
                const b = document.createElement("button");
                b.className = `btn mini ${acao.classe || ""}`.trim();
                b.textContent = acao.rotulo;
                if (acao.desabilitado) b.disabled = true;
                if (acao.titulo) b.title = acao.titulo;
                b.onclick = () => acao.aoClicar(linha);
                td.appendChild(b);
            });
            tr.appendChild(td);
        }
        tbody.appendChild(tr);
    });
    tabela.appendChild(tbody);

    container.appendChild(tabela);
}

function dadosDoForm(form) {
    return Object.fromEntries(new FormData(form).entries());
}

function opcaoSelect(valor, texto) {
    const o = document.createElement("option");
    o.value = valor;
    o.textContent = texto;
    return o;
}

/**
 * Preenche um <select> com itens no formato "{Nome} (id {id})".
 * @param placeholder texto de uma 1ª opção com value="" (opcional).
 */
function preencherSelect(select, itens, getId, getNome, placeholder) {
    select.innerHTML = "";
    if (placeholder !== undefined) {
        select.appendChild(opcaoSelect("", placeholder));
    }
    itens.forEach((item) => {
        const id = getId(item);
        select.appendChild(opcaoSelect(id, `${getNome(item)} (id ${id})`));
    });
}

// Busca as listas de referência que alimentam os <select> do formulário.
async function carregarOpcoes() {
    const [pacientes, profissionais, procedimentos] = await Promise.all([
        api("GET", "/pacientes"),
        api("GET", "/profissionais"),
        api("GET", "/procedimentos"),
    ]);
    return {
        pacientes,
        residentes: profissionais.filter((p) => p.papel === "Residente"),
        preceptores: profissionais.filter((p) => p.papel === "Preceptor"),
        procedimentos,
    };
}

// ======================================================================
// Modal genérico
// ======================================================================

const modal = document.getElementById("modal");

function abrirModal(titulo, conteudo) {
    document.getElementById("modal-titulo").textContent = titulo;
    const corpo = document.getElementById("modal-corpo");
    corpo.innerHTML = "";
    if (typeof conteudo === "string") corpo.innerHTML = conteudo;
    else corpo.appendChild(conteudo);
    modal.hidden = false;
}

function fecharModal() {
    modal.hidden = true;
    document.getElementById("modal-corpo").innerHTML = "";
}

document.getElementById("modal-fechar").addEventListener("click", fecharModal);
modal.addEventListener("click", (e) => {
    if (e.target === modal) fecharModal();
});
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hidden) fecharModal();
});

function clonarTemplate(id) {
    return document.getElementById(id).content.firstElementChild.cloneNode(true);
}

// ======================================================================
// Navegação por abas (cada aba recarrega seus dados ao ser ativada)
// ======================================================================

document.querySelectorAll(".aba").forEach((botao) => {
    botao.addEventListener("click", () => ativarAba(botao.dataset.aba));
});

function ativarAba(nome) {
    document.querySelectorAll(".aba").forEach((b) =>
        b.classList.toggle("ativa", b.dataset.aba === nome)
    );
    document.querySelectorAll(".painel").forEach((p) =>
        p.classList.toggle("ativo", p.id === nome)
    );
    const carregar = LOADERS[nome];
    if (carregar) carregar();
}

// ======================================================================
// Atendimentos
// ======================================================================

async function popularFiltroPacientes() {
    const select = document.querySelector('#form-filtro-atendimentos [name="id_paciente"]');
    try {
        const pacientes = await api("GET", "/pacientes");
        const selecionado = select.value;
        preencherSelect(
            select,
            pacientes,
            (p) => p.id_paciente,
            (p) => p.nome,
            "Todos os pacientes"
        );
        select.value = selecionado; // preserva a seleção atual, se houver
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

async function carregarAtendimentos() {
    const filtro = document
        .querySelector('#form-filtro-atendimentos [name="id_paciente"]')
        .value.trim();
    const caminho = filtro
        ? `/atendimentos/lista?id_paciente=${encodeURIComponent(filtro)}`
        : "/atendimentos/lista";
    const container = document.getElementById("tabela-atendimentos");
    try {
        const linhas = await api("GET", caminho);
        renderTabela(container, linhas, (linha) => [
            {
                rotulo: "Ver procedimentos",
                aoClicar: () => verProcedimentos(linha.id_atendimento),
            },
        ]);
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

document
    .getElementById("form-filtro-atendimentos")
    .addEventListener("submit", (e) => {
        e.preventDefault();
        carregarAtendimentos();
    });

document.getElementById("btn-limpar-filtro").addEventListener("click", () => {
    document.querySelector('#form-filtro-atendimentos [name="id_paciente"]').value = "";
    carregarAtendimentos();
});

// --- Modal: Novo atendimento ---
document
    .getElementById("btn-novo-atendimento")
    .addEventListener("click", abrirModalNovoAtendimento);

async function abrirModalNovoAtendimento() {
    let opcoes;
    try {
        opcoes = await carregarOpcoes();
    } catch (erro) {
        toast(erro.message, "erro");
        return;
    }

    const form = clonarTemplate("tpl-novo-atendimento");
    preencherSelect(form.id_paciente, opcoes.pacientes, (p) => p.id_paciente, (p) => p.nome, "Selecione…");
    preencherSelect(form.id_residente, opcoes.residentes, (p) => p.id_pessoa, (p) => p.nome, "Selecione…");
    preencherSelect(form.id_preceptor, opcoes.preceptores, (p) => p.id_pessoa, (p) => p.nome, "Selecione…");

    const lista = form.querySelector(".lista-procedimentos");

    function adicionarLinhaProcedimento() {
        const linha = clonarTemplate("tpl-linha-procedimento");
        preencherSelect(
            linha.querySelector('[name="id_procedimento"]'),
            opcoes.procedimentos,
            (p) => p.id_procedimento,
            (p) => p.nome,
            "Selecione…"
        );
        linha.querySelector(".remover-linha").addEventListener("click", () => {
            if (lista.children.length > 1) {
                linha.remove();
            } else {
                toast("O atendimento precisa de ao menos um procedimento.", "erro");
            }
        });
        lista.appendChild(linha);
    }

    form.querySelector(".btn-add-procedimento").addEventListener(
        "click",
        adicionarLinhaProcedimento
    );
    adicionarLinhaProcedimento(); // começa com uma linha

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const corpo = {
            data_hora: form.data_hora.value,
            duracao_minutos: Number(form.duracao_minutos.value),
            id_paciente: Number(form.id_paciente.value),
            id_residente: Number(form.id_residente.value),
            id_preceptor: Number(form.id_preceptor.value),
            procedimentos: coletarProcedimentos(lista),
        };
        try {
            const r = await api("POST", "/atendimentos", corpo);
            toast(`Atendimento #${r.id_atendimento} cadastrado com sucesso.`);
            fecharModal();
            carregarAtendimentos();
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

    abrirModal("Novo atendimento", form);
}

function coletarProcedimentos(lista) {
    return [...lista.querySelectorAll(".linha-procedimento")].map((linha) => {
        const proc = {
            id_procedimento: Number(linha.querySelector('[name="id_procedimento"]').value),
            quantidade: Number(linha.querySelector('[name="quantidade"]').value),
            tempo_real_minutos: Number(linha.querySelector('[name="tempo_real_minutos"]').value),
        };
        const obs = linha.querySelector('[name="observacao"]').value.trim();
        if (obs) proc.observacao = obs;
        return proc;
    });
}

// --- Modal: Ver procedimentos de um atendimento ---
function verProcedimentos(idAtendimento) {
    abrirModal(
        `Procedimentos do atendimento #${idAtendimento}`,
        '<p class="empty">Carregando…</p>'
    );
    renderProcedimentosDoAtendimento(idAtendimento);
}

async function renderProcedimentosDoAtendimento(idAtendimento) {
    const corpo = document.getElementById("modal-corpo");
    try {
        const linhas = await api(
            "GET",
            `/atendimentos/${idAtendimento}/procedimentos-detalhados`
        );
        // MySQL retorna BOOLEAN como 1/0; converte para exibir "Sim/Não".
        const dados = linhas.map((l) => ({ ...l, is_faturado: Boolean(l.is_faturado) }));
        renderTabela(
            corpo,
            dados,
            (linha) => [
                {
                    rotulo: "Excluir",
                    classe: "perigo",
                    desabilitado: Boolean(linha.is_faturado),
                    titulo: linha.is_faturado
                        ? "Procedimento faturado — não pode ser removido"
                        : "",
                    aoClicar: () =>
                        excluirProcedimento(idAtendimento, linha.id_procedimento),
                },
            ],
            ["id_procedimento"]
        );
    } catch (erro) {
        corpo.innerHTML = `<p class="empty">${erro.message}</p>`;
    }
}

async function excluirProcedimento(idAtendimento, idProcedimento) {
    try {
        await api(
            "DELETE",
            `/atendimentos/${idAtendimento}/procedimentos/${idProcedimento}`
        );
        toast("Procedimento removido com sucesso.");
        renderProcedimentosDoAtendimento(idAtendimento); // atualiza o modal
        carregarAtendimentos();
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

// ======================================================================
// Procedimentos (listagem simples)
// ======================================================================

async function carregarProcedimentos() {
    const container = document.getElementById("tabela-procedimentos");
    try {
        const linhas = await api("GET", "/procedimentos");
        renderTabela(container, linhas);
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

// ======================================================================
// Profissionais (listagem simples)
// ======================================================================

async function carregarProfissionais() {
    const container = document.getElementById("tabela-profissionais");
    try {
        const linhas = await api("GET", "/profissionais");
        renderTabela(container, linhas);
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

// ======================================================================
// Pacientes (listagem + edição)
// ======================================================================

async function carregarPacientes() {
    const container = document.getElementById("tabela-pacientes");
    try {
        const linhas = await api("GET", "/pacientes");
        renderTabela(container, linhas, (linha) => [
            { rotulo: "Editar", aoClicar: () => abrirModalEditarPaciente(linha) },
        ]);
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

function abrirModalEditarPaciente(paciente) {
    const form = clonarTemplate("tpl-editar-paciente");
    form.endereco.value = paciente.endereco || "";
    form.num_convenio.value = paciente.num_convenio || "";

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const corpo = {};
        const endereco = form.endereco.value.trim();
        const convenio = form.num_convenio.value.trim();
        if (endereco) corpo.endereco = endereco;
        if (convenio) corpo.num_convenio = convenio;

        if (Object.keys(corpo).length === 0) {
            toast("Preencha ao menos endereço ou convênio.", "erro");
            return;
        }
        try {
            await api("PATCH", `/pacientes/${paciente.id_paciente}`, corpo);
            toast(`Paciente #${paciente.id_paciente} atualizado com sucesso.`);
            fecharModal();
            carregarPacientes();
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

    abrirModal(`Editar paciente — ${paciente.nome}`, form);
}

// ======================================================================
// Relatórios
// ======================================================================

const RELATORIOS = {
    "tempo-medio-residentes": "rel-tempo-medio",
    "ranking-residentes": "rel-ranking",
    "plantoes-por-unidade": "rel-plantoes",
    "pacientes-sem-procedimento-alto": "rel-pacientes-alto",
};

document.querySelectorAll("[data-relatorio]").forEach((botao) => {
    botao.addEventListener("click", async () => {
        const nome = botao.dataset.relatorio;
        const container = document.getElementById(RELATORIOS[nome]);
        try {
            const linhas = await api("GET", `/relatorios/${nome}`);
            renderTabela(container, linhas);
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });
});

document
    .getElementById("form-preceptores")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const { mes, ano } = dadosDoForm(e.target);
        const container = document.getElementById("rel-preceptores");
        try {
            const linhas = await api(
                "GET",
                `/relatorios/preceptores-supervisao?mes=${mes}&ano=${ano}`
            );
            renderTabela(container, linhas);
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

// ======================================================================
// Inicialização
// ======================================================================

const LOADERS = {
    atendimentos: carregarAtendimentos,
    procedimentos: carregarProcedimentos,
    profissionais: carregarProfissionais,
    pacientes: carregarPacientes,
};

popularFiltroPacientes(); // opções do filtro por paciente
carregarAtendimentos(); // aba inicial
