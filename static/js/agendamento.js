(function () {
    "use strict";

    var DIAS_ANTECEDENCIA = window.DIAS_ANTECEDENCIA || 14;
    var NOMES_DIA_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
    var NOMES_MES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

    var estado = {
        etapa: 1,
        servicos: [],
        profissional: null,
        data: null,
        hora: null,
        nome: "",
        telefone: ""
    };

    function formatarPrecoBR(valor) {
        return "R$ " + Number(valor).toFixed(2).replace(".", ",");
    }

    function pad(n) {
        return n < 10 ? "0" + n : String(n);
    }

    function formatarDataISO(dataObj) {
        return dataObj.getFullYear() + "-" + pad(dataObj.getMonth() + 1) + "-" + pad(dataObj.getDate());
    }

    function formatarDataBR(isoStr) {
        var partes = isoStr.split("-");
        return partes[2] + "/" + partes[1] + "/" + partes[0];
    }

    function mostrarErroGlobal(mensagem) {
        var el = document.getElementById("mensagem-erro-global");
        el.textContent = mensagem;
        el.style.display = "block";
    }

    function esconderErroGlobal() {
        var el = document.getElementById("mensagem-erro-global");
        el.style.display = "none";
    }

    function atualizarProgresso() {
        var el = document.getElementById("progresso");
        el.textContent = "Etapa " + estado.etapa + " de 5";
    }

    function irParaEtapa(numero) {
        for (var i = 1; i <= 5; i++) {
            var secao = document.getElementById("etapa-" + i);
            if (secao) {
                secao.style.display = (i === numero) ? "" : "none";
            }
        }
        estado.etapa = numero;
        esconderErroGlobal();
        atualizarProgresso();
        window.scrollTo(0, 0);
    }

    // ---------------------------------------------------------------------
    // Etapa 1: Serviço
    // ---------------------------------------------------------------------
    function configurarEtapa1() {
        var botoes = document.querySelectorAll('.opcao-btn[data-etapa="servico"]');

        botoes.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var id = parseInt(btn.getAttribute("data-id"), 10);
                var indice = estado.servicos.findIndex(function (servico) {
                    return servico.id === id;
                });

                if (indice >= 0) {
                    estado.servicos.splice(indice, 1);
                    btn.classList.remove("selecionado");
                } else {
                    btn.classList.add("selecionado");
                    estado.servicos.push({
                        id: id,
                        nome: btn.getAttribute("data-nome"),
                        preco: parseFloat(btn.getAttribute("data-preco"))
                    });
                }

                document.getElementById("btn-avancar-1").disabled =
                    estado.servicos.length === 0;
            });
        });

        document.getElementById("btn-avancar-1").addEventListener("click", function () {
            if (estado.servicos.length > 0) {
                irParaEtapa(2);
            }
        });
    }


    // ---------------------------------------------------------------------
    // Etapa 2: Profissional
    // ---------------------------------------------------------------------
    function configurarEtapa2() {
        var botoes = document.querySelectorAll('.opcao-btn[data-etapa="profissional"]');
        botoes.forEach(function (btn) {
            btn.addEventListener("click", function () {
                botoes.forEach(function (b) { b.classList.remove("selecionado"); });
                btn.classList.add("selecionado");
                estado.profissional = {
                    id: parseInt(btn.getAttribute("data-id"), 10),
                    nome: btn.getAttribute("data-nome")
                };
                document.getElementById("btn-avancar-2").disabled = false;
            });
        });

        document.getElementById("btn-avancar-2").addEventListener("click", function () {
            if (estado.profissional) {
                gerarGradeDeDias();
                irParaEtapa(3);
            }
        });
    }

    // ---------------------------------------------------------------------
    // Etapa 3: Data e horário
    // ---------------------------------------------------------------------
    function gerarGradeDeDias() {
        var grid = document.getElementById("dias-grid");
        grid.innerHTML = "";

        var hoje = new Date();
        hoje.setHours(0, 0, 0, 0);

        var adicionados = 0;
        var offset = 0;

        while (adicionados < DIAS_ANTECEDENCIA && offset < DIAS_ANTECEDENCIA * 2) {
            var data = new Date(hoje.getTime());
            data.setDate(hoje.getDate() + offset);
            offset++;

            if (data.getDay() === 0) {
                continue; // domingo fechado
            }

            var iso = formatarDataISO(data);
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "dia-btn";
            btn.setAttribute("data-data", iso);
            btn.innerHTML = NOMES_DIA_SEMANA[data.getDay()] + "<br>" + data.getDate() + " " + NOMES_MES[data.getMonth()];

            btn.addEventListener("click", function () {
                var todos = grid.querySelectorAll(".dia-btn");
                todos.forEach(function (b) { b.classList.remove("selecionado"); });
                this.classList.add("selecionado");
                estado.data = this.getAttribute("data-data");
                estado.hora = null;
                document.getElementById("btn-avancar-3").disabled = true;
                carregarHorarios();
            });

            grid.appendChild(btn);
            adicionados++;
        }
    }

    function carregarHorarios() {
        var container = document.getElementById("horarios-grid");
        container.innerHTML = '<p class="vazio">Carregando horários...</p>';

        var params = new URLSearchParams();
        params.set("profissional_id", estado.profissional.id);
        params.set("data", estado.data);

        estado.servicos.forEach(function (servico) {
            params.append("servico_id", servico.id);
        });

        var url = "/api/availability?" + params.toString();

        fetch(url)
            .then(function (resp) { return resp.json(); })
            .then(function (dados) {
                container.innerHTML = "";
                var horarios = dados.horarios || [];

                if (horarios.length === 0) {
                    container.innerHTML = '<p class="vazio">Nenhum horário disponível nesta data.</p>';
                    return;
                }

                horarios.forEach(function (hora) {
                    var btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "horario-btn";
                    btn.textContent = hora;
                    btn.addEventListener("click", function () {
                        var todos = container.querySelectorAll(".horario-btn");
                        todos.forEach(function (b) { b.classList.remove("selecionado"); });
                        this.classList.add("selecionado");
                        estado.hora = hora;
                        document.getElementById("btn-avancar-3").disabled = false;
                    });
                    container.appendChild(btn);
                });
            })
            .catch(function () {
                container.innerHTML = '<p class="vazio">Erro ao carregar horários. Tente novamente.</p>';
            });
    }

    function configurarEtapa3() {
        document.getElementById("btn-avancar-3").addEventListener("click", function () {
            if (estado.data && estado.hora) {
                irParaEtapa(4);
            }
        });
        document.querySelector('[data-voltar="2"]').addEventListener("click", function () {
            irParaEtapa(2);
        });
    }

    // ---------------------------------------------------------------------
    // Etapa 4: Dados do cliente
    // ---------------------------------------------------------------------
    function aplicarMascaraTelefone(valor) {
        var digitos = valor.replace(/\D/g, "").slice(0, 11);
        if (digitos.length <= 2) {
            return digitos.replace(/^(\d*)/, "($1");
        }
        if (digitos.length <= 7) {
            return digitos.replace(/^(\d{2})(\d*)/, "($1) $2");
        }
        return digitos.replace(/^(\d{2})(\d{5})(\d*)/, "($1) $2-$3");
    }

    function validarEtapa4() {
        var nome = document.getElementById("input-nome").value.trim();
        var telefone = document.getElementById("input-telefone").value.trim();
        document.getElementById("btn-avancar-4").disabled = !(nome.length > 0 && telefone.length > 0);
    }

    function configurarEtapa4() {
        var inputNome = document.getElementById("input-nome");
        var inputTelefone = document.getElementById("input-telefone");

        inputNome.addEventListener("input", validarEtapa4);
        inputTelefone.addEventListener("input", function () {
            var posicaoFinal = this.selectionStart;
            var tamanhoAntes = this.value.length;
            this.value = aplicarMascaraTelefone(this.value);
            var tamanhoDepois = this.value.length;
            this.selectionStart = this.selectionEnd = posicaoFinal + (tamanhoDepois - tamanhoAntes);
            validarEtapa4();
        });

        document.getElementById("btn-avancar-4").addEventListener("click", function () {
            estado.nome = inputNome.value.trim();
            estado.telefone = inputTelefone.value.trim();
            if (estado.nome && estado.telefone) {
                preencherResumo();
                irParaEtapa(5);
            }
        });
        document.querySelector('[data-voltar="3"]').addEventListener("click", function () {
            irParaEtapa(3);
        });
    }

    // ---------------------------------------------------------------------
    // Etapa 5: Confirmação
    // ---------------------------------------------------------------------
    function preencherResumo() {
        var nomesServicos = estado.servicos.map(function (servico) {
            return servico.nome;
        }).join(", ");

        var precoTotal = estado.servicos.reduce(function (total, servico) {
            return total + servico.preco;
        }, 0);

        document.getElementById("resumo-servico").textContent = nomesServicos;
        document.getElementById("resumo-preco").textContent = formatarPrecoBR(precoTotal);
        document.getElementById("resumo-profissional").textContent = estado.profissional.nome;
        document.getElementById("resumo-data").textContent = formatarDataBR(estado.data);
        document.getElementById("resumo-hora").textContent = estado.hora;
        document.getElementById("resumo-cliente").textContent = estado.nome;
    }

    function confirmarAgendamento() {
        var btn = document.getElementById("btn-confirmar");
        btn.disabled = true;
        esconderErroGlobal();

        var payload = {
            cliente_nome: estado.nome,
            cliente_telefone: estado.telefone,
            servico_ids: estado.servicos.map(function (servico) {
                return servico.id;
            }),
            profissional_id: estado.profissional.id,
            data: estado.data,
            hora: estado.hora
        };

        fetch("/api/appointments", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then(function (resp) {
                return resp.json().then(function (dados) {
                    return { status: resp.status, dados: dados };
                });
            })
            .then(function (resultado) {
                btn.disabled = false;
                if (resultado.status === 201) {
                    window.location.href = "/agendamento/sucesso/" + resultado.dados.agendamento_id;
                } else {
                    mostrarErroGlobal(resultado.dados.erro || "Não foi possível concluir o agendamento.");
                    if (resultado.status === 409) {
                        // horário ocupado nesse meio-tempo: força escolher outro horário
                        estado.hora = null;
                    }
                }
            })
            .catch(function () {
                btn.disabled = false;
                mostrarErroGlobal("Erro de conexão. Tente novamente.");
            });
    }

    function configurarEtapa5() {
        document.getElementById("btn-confirmar").addEventListener("click", confirmarAgendamento);
        document.querySelector('[data-voltar="4"]').addEventListener("click", function () {
            irParaEtapa(4);
        });
    }

    // ---------------------------------------------------------------------
    // Inicialização
    // ---------------------------------------------------------------------
    document.addEventListener("DOMContentLoaded", function () {
        configurarEtapa1();
        configurarEtapa2();
        configurarEtapa3();
        configurarEtapa4();
        configurarEtapa5();
        atualizarProgresso();
    });
})();
