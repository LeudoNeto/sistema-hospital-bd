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
    id_escala: "ID",
    id_unidade: "ID",
    dia_semana: "Dia",
    mes_referencia: "Mês",
    ano_referencia: "Ano",
    capacidade_leitos: "Leitos",
    data_hora_inicio: "Início",
    atendimentos_medidos: "Atendimentos medidos",
    tempo_medio_espera_minutos: "Espera média (min)",
    menor_espera_minutos: "Menor espera (min)",
    maior_espera_minutos: "Maior espera (min)",
    tempo_estimado_minutos: "Estimado (min)",
    media_observada_minutos: "Observado (min)",
    desvio_minutos: "Desvio (min)",
    desvio_percentual: "Desvio (%)",
    realizacoes: "Realizações",
    id_internacao: "ID",
    mes: "Mês",
    situacao: "Situação",
    data_hora_entrada: "Entrada",
    data_hora_saida: "Saída",
    dias_internado: "Dias internado",
    tipo_unidade: "Tipo",
    titulacao_preceptor: "Titulação",
    supervisao_ativa: "Supervisão ativa",
    duracao_media_minutos: "Duração média (min)",
    duracao_minima_minutos: "Duração mín. (min)",
    duracao_maxima_minutos: "Duração máx. (min)",
    total_procedimentos: "Procedimentos",
    procedimentos_mais_comuns: "Mais comuns",
};

// Campos de ATENDIMENTO guardados no JSON da auditoria. id_atendimento fica
// de fora: já é coluna própria da tabela da trilha.
const CAMPOS_AUDITORIA = {
    data_hora: "data/hora",
    duracao_minutos: "duração",
    id_paciente: "paciente",
    id_residente: "residente",
    id_preceptor: "preceptor",
    id_unidade: "unidade",
};

// Domínios de ESCALA, na ordem cronológica (espelham os CHECK do schema).
const DIAS_SEMANA = [
    "segunda",
    "terça",
    "quarta",
    "quinta",
    "sexta",
    "sábado",
    "domingo",
];
const TURNOS = ["manhã", "tarde", "noite"];

function rotulo(chave) {
    if (ROTULOS[chave]) return ROTULOS[chave];
    return chave.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function formatarValor(valor) {
    if (valor === null || valor === undefined) return "—";
    if (typeof valor === "boolean") return valor ? "Sim" : "Não";
    // ISO da API ("...T10:00") e o formato do JSON da auditoria ("... 10:00").
    if (typeof valor === "string" && /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(valor)) {
        const [data, hora] = valor.split(/[T ]/);
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
    const [pacientes, profissionais, procedimentos, unidades] = await Promise.all([
        api("GET", "/pacientes"),
        api("GET", "/profissionais"),
        api("GET", "/procedimentos"),
        api("GET", "/unidades"),
    ]);
    return {
        pacientes,
        residentes: profissionais.filter((p) => p.papel === "Residente"),
        preceptores: profissionais.filter((p) => p.papel === "Preceptor"),
        procedimentos,
        unidades,
    };
}

// Preenche um <select> com valores que são o próprio texto (dias, turnos).
function preencherSelectSimples(select, valores) {
    select.innerHTML = "";
    valores.forEach((v) => select.appendChild(opcaoSelect(v, v)));
}

/** Monta a query string ignorando os campos em branco. */
function queryString(parametros) {
    const busca = new URLSearchParams();
    Object.entries(parametros).forEach(([chave, valor]) => {
        if (valor !== "" && valor !== null && valor !== undefined) {
            busca.append(chave, valor);
        }
    });
    const texto = busca.toString();
    return texto ? `?${texto}` : "";
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
        renderTabela(
            container,
            linhas,
            (linha) => [
                {
                    rotulo: "Ver procedimentos",
                    aoClicar: () => verProcedimentos(linha.id_atendimento),
                },
                {
                    rotulo: "Editar",
                    aoClicar: () => abrirModalEditarAtendimento(linha),
                },
                {
                    rotulo: "Excluir",
                    classe: "perigo",
                    titulo: "Remove o atendimento e seus procedimentos realizados",
                    aoClicar: () => excluirAtendimento(linha),
                },
            ],
            // Ids que o formulário de edição usa, mas que a tabela não mostra
            // (as colunas de nome já cobrem a leitura).
            ["id_residente", "id_preceptor", "id_unidade"]
        );
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
    // Unidade é opcional: sem ela o atendimento não entra no relatório de espera.
    preencherSelect(form.id_unidade, opcoes.unidades, (u) => u.id_unidade, (u) => u.nome, "Não informada");

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
        if (form.id_unidade.value) corpo.id_unidade = Number(form.id_unidade.value);

        // As duas rotas recebem o mesmo corpo e respondem os mesmos status: a
        // diferença é onde a transação e as validações acontecem.
        const viaProcedure = form.motor.value === "procedure";
        const caminho = viaProcedure ? "/atendimentos/completo" : "/atendimentos";
        try {
            const r = await api("POST", caminho, corpo);
            toast(
                `Atendimento #${r.id_atendimento} cadastrado via ` +
                    `${viaProcedure ? "stored procedure" : "ORM"}.`
            );
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
        const inicio = linha.querySelector('[name="data_hora_inicio"]').value;
        if (inicio) proc.data_hora_inicio = inicio;
        return proc;
    });
}

// --- Modal: Editar atendimento (gera a trilha de UPDATE) ---
async function abrirModalEditarAtendimento(atendimento) {
    let opcoes;
    try {
        opcoes = await carregarOpcoes();
    } catch (erro) {
        toast(erro.message, "erro");
        return;
    }

    const form = clonarTemplate("tpl-editar-atendimento");
    preencherSelect(form.id_residente, opcoes.residentes, (p) => p.id_pessoa, (p) => p.nome);
    preencherSelect(form.id_preceptor, opcoes.preceptores, (p) => p.id_pessoa, (p) => p.nome);
    preencherSelect(form.id_unidade, opcoes.unidades, (u) => u.id_unidade, (u) => u.nome, "Não informada");

    // O input datetime-local aceita "AAAA-MM-DDTHH:MM" — o ISO da API vem com
    // segundos, que precisam ser cortados.
    form.data_hora.value = (atendimento.data_hora || "").slice(0, 16);
    form.duracao_minutos.value = atendimento.duracao_minutos;
    form.id_residente.value = atendimento.id_residente;
    form.id_preceptor.value = atendimento.id_preceptor;
    form.id_unidade.value = atendimento.id_unidade === null ? "" : atendimento.id_unidade;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        // Manda os cinco campos editáveis; a ORM só emite UPDATE para o que
        // realmente mudou, então submeter sem alterar nada não gera trilha.
        const corpo = {
            data_hora: form.data_hora.value,
            duracao_minutos: Number(form.duracao_minutos.value),
            id_residente: Number(form.id_residente.value),
            id_preceptor: Number(form.id_preceptor.value),
            id_unidade: form.id_unidade.value ? Number(form.id_unidade.value) : null,
        };
        try {
            await api("PATCH", `/atendimentos/${atendimento.id_atendimento}`, corpo);
            toast(`Atendimento #${atendimento.id_atendimento} atualizado com sucesso.`);
            fecharModal();
            carregarAtendimentos();
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

    abrirModal(`Editar atendimento #${atendimento.id_atendimento}`, form);
}

async function excluirAtendimento(atendimento) {
    const confirmado = confirm(
        `Excluir o atendimento #${atendimento.id_atendimento} ` +
            `(${atendimento.paciente}) e todos os seus procedimentos realizados?\n\n` +
            "A exclusão fica registrada no histórico de alterações."
    );
    if (!confirmado) return;

    try {
        await api("DELETE", `/atendimentos/${atendimento.id_atendimento}`);
        toast(`Atendimento #${atendimento.id_atendimento} excluído.`);
        carregarAtendimentos();
    } catch (erro) {
        toast(erro.message, "erro");
    }
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
// Auditoria (trilha gravada pelos triggers trg_audita_atendimento_*)
// ======================================================================

document
    .getElementById("btn-historico-auditoria")
    .addEventListener("click", abrirModalAuditoria);

function abrirModalAuditoria() {
    abrirModal("Histórico de alterações em atendimentos", '<p class="empty">Carregando…</p>');
    renderAuditoria();
}

async function renderAuditoria() {
    const corpo = document.getElementById("modal-corpo");
    try {
        const linhas = await api("GET", "/auditoria");
        if (linhas.length === 0) {
            corpo.innerHTML =
                '<p class="empty">Nenhuma alteração registrada ainda. ' +
                "A trilha começa a ser preenchida no primeiro atendimento gravado.</p>";
            return;
        }
        corpo.innerHTML = "";
        corpo.appendChild(tabelaAuditoria(linhas));
    } catch (erro) {
        corpo.innerHTML = `<p class="empty">${erro.message}</p>`;
    }
}

/**
 * Descreve o que mudou em cada registro da trilha:
 * UPDATE compara antes/depois e lista só os campos alterados; INSERT e DELETE
 * mostram o estado gravado/removido.
 */
function resumirAuditoria(registro) {
    const antes = registro.dados_antigos || {};
    const depois = registro.dados_novos || {};
    const campos = Object.keys(CAMPOS_AUDITORIA);

    if (registro.operacao === "UPDATE") {
        const alterados = campos.filter((c) => String(antes[c]) !== String(depois[c]));
        if (alterados.length === 0) return ["(nenhum campo auditado mudou)"];
        return alterados.map(
            (c) =>
                `${CAMPOS_AUDITORIA[c]}: ${formatarValor(antes[c])} → ` +
                `${formatarValor(depois[c])}`
        );
    }

    const estado = registro.operacao === "DELETE" ? antes : depois;
    return campos.map((c) => `${CAMPOS_AUDITORIA[c]}: ${formatarValor(estado[c])}`);
}

function tabelaAuditoria(linhas) {
    const tabela = document.createElement("table");
    tabela.innerHTML =
        "<thead><tr><th>Quando</th><th>Atendimento</th><th>Operação</th>" +
        "<th>Usuário</th><th>Alterações</th></tr></thead>";

    const tbody = document.createElement("tbody");
    linhas.forEach((registro) => {
        const tr = document.createElement("tr");

        [
            formatarValor(registro.data_hora),
            `#${registro.id_atendimento}`,
        ].forEach((texto) => {
            const td = document.createElement("td");
            td.textContent = texto;
            tr.appendChild(td);
        });

        const tdOperacao = document.createElement("td");
        const chip = document.createElement("span");
        chip.className = `chip ${registro.operacao.toLowerCase()}`;
        chip.textContent = registro.operacao;
        tdOperacao.appendChild(chip);
        tr.appendChild(tdOperacao);

        const tdUsuario = document.createElement("td");
        tdUsuario.textContent = registro.usuario;
        tr.appendChild(tdUsuario);

        const tdMudancas = document.createElement("td");
        tdMudancas.className = "col-mudancas";
        resumirAuditoria(registro).forEach((texto) => {
            const div = document.createElement("div");
            div.textContent = texto;
            tdMudancas.appendChild(div);
        });
        tr.appendChild(tdMudancas);

        tbody.appendChild(tr);
    });
    tabela.appendChild(tbody);
    return tabela;
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
// Escalas (listagem + reajuste de dia/turno via sp_reajustar_escala)
// ======================================================================

// ======================================================================
// Internações (card da view vw_pacientes_internados + CRUD da tabela)
// ======================================================================

// A aba tem duas tabelas que precisam andar juntas: registrar uma alta muda a
// listagem E o card de internados.
async function carregarInternacoes() {
    await Promise.all([carregarPacientesInternados(), carregarTodasInternacoes()]);
}

async function carregarPacientesInternados() {
    const container = document.getElementById("tabela-internados");
    const contador = document.getElementById("contador-internados");
    try {
        const linhas = await api("GET", "/internacoes/internados");
        contador.textContent =
            linhas.length === 1 ? "1 paciente" : `${linhas.length} pacientes`;
        renderTabela(container, linhas, null, ["id_internacao", "id_paciente"]);
    } catch (erro) {
        contador.textContent = "";
        toast(erro.message, "erro");
    }
}

async function carregarTodasInternacoes() {
    const container = document.getElementById("tabela-internacoes");
    try {
        const linhas = await api("GET", "/internacoes");
        renderTabela(
            container,
            linhas,
            (linha) => [
                {
                    rotulo: "Editar",
                    aoClicar: () => abrirModalInternacao(linha),
                },
                {
                    rotulo: "Excluir",
                    classe: "perigo",
                    aoClicar: () => excluirInternacao(linha.id_internacao),
                },
            ],
            ["id_paciente", "id_unidade"]
        );
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

async function excluirInternacao(idInternacao) {
    try {
        await api("DELETE", `/internacoes/${idInternacao}`);
        toast(`Internação #${idInternacao} removida com sucesso.`);
        carregarInternacoes();
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

document
    .getElementById("btn-nova-internacao")
    .addEventListener("click", () => abrirModalInternacao());

/** Converte "2026-07-28T14:00:00" (ou null) no formato do datetime-local. */
function paraDatetimeLocal(valor) {
    return valor ? valor.slice(0, 16) : "";
}

/**
 * Um só modal para inserir e editar. Sem `internacao` é cadastro (POST);
 * com `internacao` é edição (PUT), que substitui o registro inteiro.
 */
async function abrirModalInternacao(internacao) {
    let opcoes;
    try {
        opcoes = await carregarOpcoes();
    } catch (erro) {
        toast(erro.message, "erro");
        return;
    }

    const editando = internacao !== undefined;
    const form = clonarTemplate("tpl-internacao");
    preencherSelect(form.id_paciente, opcoes.pacientes, (p) => p.id_paciente, (p) => p.nome, "Selecione…");
    preencherSelect(form.id_unidade, opcoes.unidades, (u) => u.id_unidade, (u) => u.nome, "Selecione…");

    if (editando) {
        form.id_paciente.value = internacao.id_paciente;
        form.id_unidade.value = internacao.id_unidade;
        form.data_hora_entrada.value = paraDatetimeLocal(internacao.data_hora_entrada);
        form.data_hora_saida.value = paraDatetimeLocal(internacao.data_hora_saida);
        form.leito.value = internacao.leito || "";
        form.motivo.value = internacao.motivo || "";
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const corpo = {
            id_paciente: Number(form.id_paciente.value),
            id_unidade: Number(form.id_unidade.value),
            data_hora_entrada: form.data_hora_entrada.value,
            // null (e não omitido) para o PUT poder reabrir uma internação
            // encerrada — é substituição completa, ver InternacaoCreate.
            data_hora_saida: form.data_hora_saida.value || null,
            leito: form.leito.value.trim() || null,
            motivo: form.motivo.value.trim() || null,
        };
        try {
            if (editando) {
                await api("PUT", `/internacoes/${internacao.id_internacao}`, corpo);
                toast(`Internação #${internacao.id_internacao} atualizada com sucesso.`);
            } else {
                const r = await api("POST", "/internacoes", corpo);
                toast(`Internação #${r.id_internacao} cadastrada com sucesso.`);
            }
            fecharModal();
            carregarInternacoes();
        } catch (erro) {
            // Paciente já com internação em aberto chega aqui como 409.
            toast(erro.message, "erro");
        }
    });

    abrirModal(
        editando ? `Editar internação #${internacao.id_internacao}` : "Nova internação",
        form
    );
}

// ======================================================================
// Escalas
// ======================================================================

async function carregarEscalas() {
    const container = document.getElementById("tabela-escalas");
    try {
        const linhas = await api("GET", "/escalas");
        renderTabela(container, linhas, (linha) => [
            {
                rotulo: "Excluir",
                classe: "perigo",
                aoClicar: () => excluirEscala(linha.id_escala),
            },
        ]);
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

async function excluirEscala(idEscala) {
    try {
        await api("DELETE", `/escalas/${idEscala}`);
        toast(`Escala #${idEscala} removida com sucesso.`);
        carregarEscalas();
    } catch (erro) {
        toast(erro.message, "erro");
    }
}

// --- Modal: Nova escala ---
document
    .getElementById("btn-nova-escala")
    .addEventListener("click", abrirModalNovaEscala);

async function abrirModalNovaEscala() {
    let opcoes;
    try {
        opcoes = await carregarOpcoes();
    } catch (erro) {
        toast(erro.message, "erro");
        return;
    }

    const form = clonarTemplate("tpl-nova-escala");
    preencherSelect(form.id_unidade, opcoes.unidades, (u) => u.id_unidade, (u) => u.nome, "Selecione…");
    preencherSelect(form.id_residente, opcoes.residentes, (p) => p.id_pessoa, (p) => p.nome, "Selecione…");
    preencherSelect(form.id_preceptor, opcoes.preceptores, (p) => p.id_pessoa, (p) => p.nome, "Selecione…");
    preencherSelectSimples(form.dia_semana, DIAS_SEMANA);
    preencherSelectSimples(form.turno, TURNOS);

    // Mês/ano correntes como padrão — é o recorte que o painel mais usa.
    const agora = new Date();
    form.mes_referencia.value = agora.getMonth() + 1;
    form.ano_referencia.value = agora.getFullYear();

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const corpo = {
            id_unidade: Number(form.id_unidade.value),
            dia_semana: form.dia_semana.value,
            turno: form.turno.value,
            mes_referencia: Number(form.mes_referencia.value),
            ano_referencia: Number(form.ano_referencia.value),
            id_residente: Number(form.id_residente.value),
            id_preceptor: Number(form.id_preceptor.value),
        };
        try {
            const r = await api("POST", "/escalas", corpo);
            toast(`Escala #${r.id_escala} cadastrada com sucesso.`);
            fecharModal();
            carregarEscalas();
        } catch (erro) {
            // Sobreposição entre unidades (trigger) e repetição exata
            // (UNIQUE) chegam aqui como 409, com a mensagem do banco.
            toast(erro.message, "erro");
        }
    });

    abrirModal("Nova escala de plantão", form);
}

document
    .getElementById("btn-reajustar-escala")
    .addEventListener("click", abrirModalReajustarEscala);

async function abrirModalReajustarEscala() {
    let residentes;
    try {
        const profissionais = await api("GET", "/profissionais");
        residentes = profissionais.filter((p) => p.papel === "Residente");
    } catch (erro) {
        toast(erro.message, "erro");
        return;
    }

    const form = clonarTemplate("tpl-reajustar-escala");
    preencherSelect(form.id_residente, residentes, (p) => p.id_pessoa, (p) => p.nome, "Selecione…");
    form.querySelectorAll(".select-dia").forEach((s) => preencherSelectSimples(s, DIAS_SEMANA));
    form.querySelectorAll(".select-turno").forEach((s) => preencherSelectSimples(s, TURNOS));

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const corpo = {
            id_residente: Number(form.id_residente.value),
            dia_origem: form.dia_origem.value,
            turno_origem: form.turno_origem.value,
            dia_destino: form.dia_destino.value,
            turno_destino: form.turno_destino.value,
        };
        // Em branco = todos os meses (a procedure trata NULL como curinga).
        if (form.mes.value) corpo.mes = Number(form.mes.value);
        if (form.ano.value) corpo.ano = Number(form.ano.value);

        try {
            const r = await api("POST", "/escalas/reajustar", corpo);
            const plural = r.escalas_movidas === 1 ? "escala" : "escalas";
            toast(`${r.escalas_movidas} ${plural} reajustada(s) com sucesso.`);
            fecharModal();
            carregarEscalas();
        } catch (erro) {
            // Conflito, domínio inválido e "nada a mover" vêm da procedure.
            toast(erro.message, "erro");
        }
    });

    abrirModal("Reajustar dia/turno das escalas", form);
}

// ======================================================================
// Relatórios
// ======================================================================

const RELATORIOS = {
    "tempo-medio-residentes": "rel-tempo-medio",
    "ranking-residentes": "rel-ranking",
    "plantoes-por-unidade": "rel-plantoes",
    "pacientes-sem-procedimento-alto": "rel-pacientes-alto",
    "tempos-observados-procedimentos": "rel-tempos-observados",
    "residentes-sem-supervisor": "rel-sem-supervisor",
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

// sp_calcular_tempo_medio_espera — mês/ano em branco = todo o período.
document
    .getElementById("form-tempo-espera")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const { mes, ano } = dadosDoForm(e.target);
        const container = document.getElementById("rel-tempo-espera");
        try {
            const linhas = await api(
                "GET",
                `/relatorios/tempo-medio-espera${queryString({ mes, ano })}`
            );
            renderTabela(container, linhas, null, ["id_unidade"]);
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

// vw_estatisticas_atendimentos_mensal — ano/mês em branco = todo o período.
document
    .getElementById("form-estatisticas-mensais")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const { ano, mes } = dadosDoForm(e.target);
        const container = document.getElementById("rel-estatisticas-mensais");
        try {
            const linhas = await api(
                "GET",
                `/relatorios/estatisticas-mensais${queryString({ ano, mes })}`
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
    internacoes: carregarInternacoes,
    escalas: carregarEscalas,
};

popularFiltroPacientes(); // opções do filtro por paciente
carregarAtendimentos(); // aba inicial
