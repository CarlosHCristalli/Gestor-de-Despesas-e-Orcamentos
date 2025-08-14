#finance/cli.py
#Ler comandos e argumentos no terminal e realizar os pedidos
import os, argparse
from .storage import Storage
from .service import FinanceService
from .models import TipoMovimento, Movimento
from .reports import Reports

BASE_DATA=os.path.join(os.path.dirname(os.path.dirname(__file__)),'data')

def build_service():
    return FinanceService(Storage(BASE_DATA))

# --------- comandos movimentos ---------
def cmd_add_mov(args):
    s=build_service()
    mov, alerta =s.add_movimento(
        tipo=(TipoMovimento(args.tipo) if args.tipo in ("despesa", "receita") else TipoMovimento("despesa")),
        valor=args.valor,
        categoria=args.cat,
        descricao=args.desc or "",
        metodo_pagamento=args.metodo or "",
        data_iso=None
    )
    print(f"Criado movimento #{mov.id}: {mov.tipo.value} {mov.valor:.2f} [{mov.categoria}] em {mov.data_iso}")
    if alerta:
        print(f"Orçamento EXCEDIDO em {alerta['referencia']} para '{alerta['categoria']}' "
              f"(limite {alerta['limite']:.2f}, gasto {alerta['gasto']:.2f}, excesso {alerta['excesso']:.2f})")

def cmd_list_mov(args):
    s=build_service()
    if args.inicio or args.fim or args.cat or args.tipo or args.texto:
        movimentos = s.listar_filtrado(
            inicio=args.inicio, fim=args.fim, cat=args.cat, tipo=args.tipo, texto=args.texto
        )
    else:
        movimentos = s.listar()

    if not movimentos:
        print("Sem movimentos registados.")
        return
    for m in movimentos:
        print(f"#{m.id} {m.data_iso} | {m.tipo.value.upper():7} | {m.valor:8.2f} | {m.categoria} | {m.metodo_pagamento} | {m.descricao}")

# --------- comandos orçamentos ---------
def cmd_add_orc(args):
    s = build_service()
    orc, status = s.add_orcamento(categoria=args.cat, limite=args.limite, periodo=args.periodo or "mensal")
    print(f"Orçamento {status}: #{orc.id} {orc.categoria} (periodo={orc.periodo}, limite={orc.limite:.2f})")

def cmd_list_orc(args):
    s = build_service()
    orcs = s.listar_orcamentos(periodo=args.periodo)
    if not orcs:
        print("Sem orçamentos.")
        return
    for o in orcs:
        print(f"#{o.id} {o.categoria} | período={o.periodo} | limite={o.limite:.2f}")

# --------- comandos relatorios ---------
def cmd_relatorio(args):
    s = build_service()
    r = Reports(s.storage)

    tipo = args.tipo
    inicio = args.inicio
    fim = args.fim
    saida = (args.saida or 'json').lower()
    if saida not in ('json', 'csv'):
        raise ValueError("Formato de saída inválido. Use 'json' ou 'csv'.")
    
    if tipo == "totais-por-cat":
        dados = r.totais_por_cat(inicio=inicio, fim=fim)
    elif tipo == "cashflow-semanal":
        dados = r.cashflow_semanal(inicio=inicio, fim=fim)
    elif tipo == "top-categorias":
        dados = r.top_categorias(n=args.top or 5, tipo=args.mov_tipo or "despesa", inicio=inicio, fim=fim)
    elif tipo == "alertas":
        dados = r.alertas(inicio=inicio, fim=fim)
    else:
        raise ValueError("Tipo de relatório inválido.")
    
    # imprime no ecrã (resumo/visualização rápida)
    if not dados:
        print("Relatório vazio.")
    else:
        for linha in dados:
            print(linha)

    path = r.exportar(dados, tipo_rel=tipo, formato=saida)
    print(f"\nFicheiro exportado: {path}")

# --------- MAIN ---------
def main(argv=None):
    parser = argparse.ArgumentParser(prog='finance', description='Gestor de Despesas e Orçamentos')
    sub=parser.add_subparsers(required=True)

    # add-mov
    p_add=sub.add_parser("add-mov", help="Adicionar novo movimento")
    p_add.add_argument("--tipo", choices=["despesa", "receita"], required=True)
    p_add.add_argument("--valor", type=float, required=True)
    p_add.add_argument("--cat", required=True, help="Categoria")
    p_add.add_argument("--desc", help="Descrição")
    p_add.add_argument("--metodo", help="Método de pagamento (ex.: MBWay, cartao, dinheiro)")
    p_add.set_defaults(func=cmd_add_mov)

    # list-mov
    p_list = sub.add_parser("list-mov", help="Listar todos os movimentos")
    p_list.add_argument('--inicio', help="ISO inicial (ex: 2025-08-01)")
    p_list.add_argument('--fim', help="ISO final (ex: 2025-08-31T23:59:59)")
    p_list.add_argument('--cat', help="Categoria")
    p_list.add_argument('--tipo', choices=['despesa','receita'])
    p_list.add_argument('--texto', help="Texto a procurar na descrição")
    p_list.set_defaults(func=cmd_list_mov)

     # add-orc
    p_aorc = sub.add_parser('add-orc', help="Criar/atualizar orçamento por categoria")
    p_aorc.add_argument('--cat', required=True)
    p_aorc.add_argument('--limite', type=float, required=True)
    p_aorc.add_argument('--periodo', choices=["mensal","semanal"], default="mensal")
    p_aorc.set_defaults(func=cmd_add_orc)

    # list-orc
    p_lorc = sub.add_parser('list-orc', help="Listar orçamentos")
    p_lorc.add_argument('--periodo', choices=["mensal","semanal"])
    p_lorc.set_defaults(func=cmd_list_orc)

    # --- relatorio ---
    p_rep = sub.add_parser('relatorio', help="Gerar relatórios e exportar para CSV/JSON")
    p_rep.add_argument('--tipo', required=True, choices=['totais-por-cat','cashflow-semanal','top-categorias','alertas'])
    p_rep.add_argument('--inicio', help="ISO inicial (ex: 2025-08-01)")
    p_rep.add_argument('--fim', help="ISO final (ex: 2025-08-31T23:59:59)")
    p_rep.add_argument('--saida', choices=['json','csv'], default='json')
    # específicos do top-categorias:
    p_rep.add_argument('--top', type=int, help="Top N categorias (apenas para top-categorias)")
    p_rep.add_argument('--mov-tipo', choices=['despesa','receita'], help="Tipo de movimento para top-categorias")
    p_rep.set_defaults(func=cmd_relatorio)

    args=parser.parse_args(argv)
    args.func(args)

if __name__=='__main__':
    main()