#finance/service.py
from .models import Movimento, TipoMovimento, Orcamento
from .storage import Storage
from datetime import datetime

def _yyyymm(date_iso):
    # extrai 'YYYY-MM' do ISO (suporta 'YYYY-MM-DD' e 'YYYY-MM-DDTHH:MM:SS')
    return datetime.fromisoformat(date_iso.replace("Z","")).strftime("%Y-%m")

def _isoweek_key(date_iso):
    dt = datetime.fromisoformat(date_iso.replace("Z",""))
    iso_year, iso_week, _ = dt.isocalendar()  # ISO: semana começa à segunda
    return f"{iso_year}-W{iso_week:02d}"

class FinanceService:
    def __init__(self,storage):
        self.storage = storage
    
    def add_movimento(self,tipo,valor,categoria,descricao="",metodo_pagamento="",data_iso=None):
        novo_id = self.storage.proximo_id()
        if data_iso is None:
            data_iso = datetime.now().isoformat(timespec="seconds")

        mov = Movimento(novo_id,tipo,valor,categoria,descricao,metodo_pagamento,data_iso)
        try:
            mov.validar()
        except ValueError as e:
            print(f"Erro ao adicionar movimento: {e}")
            return None, None

        movimentos = self.storage.carregar_movimentos()
        movimentos.append(mov.to_dict())
        self.storage.guardar_movimentos(movimentos)

        alerta = None
        if mov.tipo == TipoMovimento.DESPESA:
            alerta = self.verificar_overspend(mov)

        return mov, alerta

    def listar(self):
        #Carregar dicionarios e converter para objeto Movimento
        return [Movimento.from_dict(d) for d in self.storage.carregar_movimentos()]
    
    def listar_filtrado(self, inicio=None, fim=None, cat=None, tipo=None, texto=None):
        movs = self.listar()
        res = []
        for m in movs:
            if inicio and m.data_iso < inicio:
                continue
            if fim and m.data_iso > fim:
                continue
            if cat and m.categoria != cat:
                continue
            if tipo and m.tipo.value != tipo:
                continue
            if texto and (texto.lower() not in (m.descricao or "").lower()):
                continue
            res.append(m)
        return res
    
    def add_orcamento(self,categoria, limite, periodo="mensal"):
        novo_id = self.storage.proximo_id_orcamento()
        orc = Orcamento(novo_id,categoria,limite,periodo)
        try:
            orc.validar()
        except ValueError as e:
            print(f"Erro ao criar orçamento: {e}")
            return None, None

        orcs = self.storage.carregar_orcamentos()
        updated = False
        for o in orcs:
            if o.get("categoria") == orc.categoria and o.get("periodo") == orc.periodo:
                o["limite"] = orc.limite
                updated = True
                break

        if not updated:
            orcs.append(orc.to_dict())

        self.storage.guardar_orcamentos(orcs)
        return orc, ("atualizado" if updated else "criado")
    
    def listar_orcamentos(self, periodo=None):
        orcs = [Orcamento.from_dict(d) for d in self.storage.carregar_orcamentos()]
        if periodo:
            orcs = [o for o in orcs if o.periodo == periodo]
        return orcs
    
    def verificar_overspend(self, movimento: Movimento):
        """
        Verifica se a despesa excede o orçamento 'mensal' ou 'semanal' da categoria do movimento.
        Retorna None se não houver orçamento ou não excedeu.
        Caso exceda, retorna dict com detalhes: {categoria, periodo, limite, gasto, excesso}.
        """
        if movimento.tipo != TipoMovimento.DESPESA:
            return None
        
        orcs = [o for o in self.listar_orcamentos() if o.categoria == movimento.categoria]
        if not orcs:
            return None
        
        movs = self.listar()

        ref_mes = _yyyymm(movimento.data_iso)
        ref_sem = _isoweek_key(movimento.data_iso)

        alerta_encontrado = None

        for orc in orcs:
            if orc.periodo == "mensal":
                # soma despesas da MESMA categoria e MESMO YYYY-MM
                gasto = 0.0
                for m in movs:
                    if m.tipo == TipoMovimento.DESPESA and m.categoria == orc.categoria and _yyyymm(m.data_iso) == ref_mes:
                        gasto += m.valor
                if gasto > orc.limite:
                    alerta_encontrado = {
                        "categoria": orc.categoria,
                        "periodo": "mensal",
                        "limite": orc.limite,
                        "gasto": round(gasto, 2),
                        "excesso": round(gasto - orc.limite, 2),
                        "referencia": ref_mes,
                    }
            elif orc.periodo == "semanal":
                # soma despesas da MESMA categoria e MESMA SEMANA ISO (YYYY-Www)
                gasto = 0.0
                for m in movs:
                    if m.tipo == TipoMovimento.DESPESA and m.categoria == orc.categoria and _isoweek_key(m.data_iso) == ref_sem:
                        gasto += m.valor
                if gasto > orc.limite:
                    alerta_encontrado = {
                        "categoria": orc.categoria,
                        "periodo": "semanal",
                        "limite": orc.limite,
                        "gasto": round(gasto, 2),
                        "excesso": round(gasto - orc.limite, 2),
                        "referencia": ref_sem,  
                    }

        return alerta_encontrado