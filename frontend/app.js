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

function rotulo(chave) {
    return chave.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function renderTabela(container, linhas, acoes) {
    container.innerHTML = "";
    if (!linhas || linhas.length === 0) {
        container.innerHTML = '<p class="empty">Nenhum resultado encontrado.</p>';
        return;
    }

    const colunas = Object.keys(linhas[0]);
    const tabela = document.createElement("table");

    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    colunas.forEach((c) => {
        const th = document.createElement("th");
        th.textContent = rotulo(c);
        trh.appendChild(th);
    });
    if (acoes) trh.appendChild(document.createElement("th"));
    thead.appendChild(trh);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");
    linhas.forEach((linha) => {
        const tr = document.createElement("tr");
        colunas.forEach((c) => {
            const td = document.createElement("td");
            const valor = linha[c];
            td.textContent = valor === null || valor === undefined ? "—" : valor;
            tr.appendChild(td);
        });
        if (acoes) {
            const td = document.createElement("td");
            acoes.forEach((acao) => {
                const b = document.createElement("button");
                b.className = "btn mini";
                b.textContent = acao.rotulo;
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

// ======================================================================
// Navegação por abas
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
}

// ======================================================================
// Atendimentos
// ======================================================================

document
    .getElementById("form-criar-atendimento")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const dados = dadosDoForm(e.target);
        const corpo = {
            data_hora: dados.data_hora,
            duracao_minutos: Number(dados.duracao_minutos),
            id_paciente: Number(dados.id_paciente),
            id_residente: Number(dados.id_residente),
            id_preceptor: Number(dados.id_preceptor),
        };
        try {
            const r = await api("POST", "/atendimentos", corpo);
            toast(`Atendimento #${r.id_atendimento} cadastrado com sucesso.`);
            e.target.reset();
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

document
    .getElementById("form-listar-atendimentos")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const { id_paciente } = dadosDoForm(e.target);
        const container = document.getElementById("resultado-atendimentos");
        try {
            const linhas = await api("GET", `/atendimentos?id_paciente=${id_paciente}`);
            renderTabela(container, linhas, [
                {
                    rotulo: "Ver procedimentos",
                    aoClicar: (linha) => verProcedimentos(linha.id_atendimento),
                },
            ]);
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

// ======================================================================
// Procedimentos realizados
// ======================================================================

function verProcedimentos(idAtendimento) {
    ativarAba("procedimentos");
    const form = document.getElementById("form-listar-procedimentos");
    form.id_atendimento.value = idAtendimento;
    form.requestSubmit();
}

document
    .getElementById("form-listar-procedimentos")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const { id_atendimento } = dadosDoForm(e.target);
        const container = document.getElementById("resultado-procedimentos");
        try {
            const linhas = await api(
                "GET",
                `/atendimentos/${id_atendimento}/procedimentos`
            );
            renderTabela(container, linhas);
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

document
    .getElementById("form-remover-procedimento")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const { id_atendimento, id_procedimento } = dadosDoForm(e.target);
        try {
            await api(
                "DELETE",
                `/atendimentos/${id_atendimento}/procedimentos/${id_procedimento}`
            );
            toast("Procedimento removido com sucesso.");
            e.target.reset();
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

// ======================================================================
// Pacientes
// ======================================================================

document
    .getElementById("form-atualizar-paciente")
    .addEventListener("submit", async (e) => {
        e.preventDefault();
        const dados = dadosDoForm(e.target);
        const corpo = {};
        if (dados.endereco.trim()) corpo.endereco = dados.endereco.trim();
        if (dados.num_convenio.trim()) corpo.num_convenio = dados.num_convenio.trim();

        if (Object.keys(corpo).length === 0) {
            toast("Preencha ao menos endereço ou convênio.", "erro");
            return;
        }
        try {
            await api("PATCH", `/pacientes/${dados.id_paciente}`, corpo);
            toast(`Paciente #${dados.id_paciente} atualizado com sucesso.`);
        } catch (erro) {
            toast(erro.message, "erro");
        }
    });

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
