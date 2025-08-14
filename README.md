Instrucoes para instalacao e utilizacao da nossa aplicacao

## Estrutura do projeto

## Instalacao
1. clonar o repositorio
git clone <url_do_repositorio>
cd Gestor-de-Despesas-e-Orcamentos

## Comandos principais
1. Adicionar movimento
Regista uma despesa ou receita.
A data é preenchida automaticamente com a hora atual do sistema.

Exemplo: python -m gestor.cli add-mov --tipo despesa --valor 12.50 --cat supermercado --metodo MBWay --desc "Leite e pão"

Opções:
--tipo → despesa ou receita (obrigatório)
--valor → Valor numérico (obrigatório)
--cat → Categoria (obrigatório)
--desc → Descrição (opcional)
--metodo → Método de pagamento (opcional)

2. Listar movimentos
Mostra todos os movimentos registados.

Exemplo: python -m gestor.cli list-mov


3. Adicionar orçamento
Cria ou atualiza um orçamento para uma categoria.

Exemplo: python -m gestor.cli add-orc --cat supermercado --limite 50 --periodo mensal

Opções:
--cat → categoria (obrigatório)
--limite → valor do orçamento (obrigatório)
--periodo → mensal (padrão) ou semanal

4. Listar orçamentos
Mostra todos os orçamentos registados.

Exemplo: python -m gestor.cli list-orc

5. Gerar relatórios
Tipos de relatórios disponíveis:
-totais-por-cat
-cashflow-semanal
-top-categorias
-alertas

Exemplo:
python -m gestor.cli relatorio --tipo totais-por-cat --inicio 2025-08-01 --fim 2025-08-31T23:59:59 --saida csv

Opções gerais:
--inicio / --fim → intervalo de datas
--saida → formato do ficheiro (json ou csv)

Opções específicas para top-categorias:
--top → número de categorias a listar
--mov-tipo → despesa ou receita


## Testes:

pythin -m tests.test_basico
