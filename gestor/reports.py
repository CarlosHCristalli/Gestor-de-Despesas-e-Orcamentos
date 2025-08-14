# gestor/reports.py
# Relatórios: totais-por-cat, cashflow-semanal, top-categorias, alertas + export CSV/JSON

import os
import json
import csv
from datetime import datetime
from collections import defaultdict
from .storage import Storage

class Reports:
    def __init__(self,storage:Storage):
        self.storage = storage
        self.base_dir = storage.base_dir
        self.rel_dir = os.path.join(self.base_dir, "relatorios")
        os.makedirs(self.rel_dir, exist_ok=True)

    @staticmethod
    def _parse_dt(iso_str):
         # aceita 'YYYY-MM-DD' ou 'YYYY-MM-DDTHH:MM[:SS]'
        return datetime.fromisoformat(iso_str.replace("Z", ""))
    
    @staticmethod
    def _yyyymm(iso_str):
        return Reports._parse_dt(iso_str).strftime("%Y-%m")
    
    @staticmethod
    def _isoweek_key(iso_str):
        dt = Reports._parse_dt(iso_str)
        iso_year, iso_week, _ = dt.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    
    def _filtro_periodo(self, movs, inicio=None, fim=None):
        if not inicio and not fim:
            return movs
        out = []
        dt_inicio = self._parse_dt(inicio) if inicio else None
        dt_fim = self._parse_dt(fim) if fim else None
        for m in movs:
            dt = self._parse_dt(m["data"])
            if dt_inicio and dt < dt_inicio:
                continue
            if dt_fim and dt > dt_fim:
                continue
            out.append(m)
        return out
    
    def _load_movs(self, inicio=None, fim=None):
        movs = self.storage.carregar_movimentos()
        return self._filtro_periodo(movs,inicio,fim)
    
    def _load_orcs(self):
        return self.storage.carregar_orcamentos() if hasattr(self.storage, "carregar_orcamentos") else []

    # ------------- Relatórios -------------
    def totais_por_cat(self, inicio=None, fim=None):
        """
        Soma por categoria separando despesa/receita e calcula saldo.
        Retorna lista de dicts: {categoria, despesa, receita, saldo}
        """
        movs = self._load_movs(inicio, fim)
        soma_rec = defaultdict(float)
        soma_des = defaultdict(float)
        for m in movs:
            if m["tipo"] == "receita":
                soma_rec[m["categoria"]] += float(m["valor"])
            elif m["tipo"] == "despesa":
                soma_des[m["categoria"]] += float(m["valor"])
        cats = sorted(set(list(soma_rec.keys()) + list(soma_des.keys())))
        res = []
        for c in cats:
            receita = round(soma_rec[c], 2)
            despesa = round(soma_des[c], 2)
            saldo   = round(receita - despesa, 2)
            res.append({"categoria": c, "despesa": despesa, "receita": receita, "saldo": saldo})
        res.sort(key=lambda x: (-abs(x["saldo"]), x["categoria"]))
        return res
    
    def cashflow_semanal(self, inicio=None, fim=None):
        """
        Agrega por semana ISO (YYYY-Www): receita, despesa e saldo.
        Retorna lista de dicts: {semana, receita, despesa, saldo}
        """
        movs = self._load_movs(inicio,fim)
        rec = defaultdict(float)
        des = defaultdict(float)
        for m in movs:
            wk = self._isoweek_key(m['data'])
            if m["tipo"] == "receita":
                rec[wk] += float(m["valor"])
            elif m["tipo"] == "despesa":
                des[wk] += float(m["valor"])
        semanas = sorted(set(list(rec.keys()) + list(des.keys())))
        res = []
        for s in semanas:
            receita = round(rec[s], 2)
            despesa = round(des[s], 2)
            saldo   = round(receita - despesa, 2)
            res.append({"semana": s, "receita": receita, "despesa": despesa, "saldo": saldo})
        res.sort(key=lambda x: x['semana'])
        return res
    
    def top_categorias(self, n=5, tipo='despesa', inicio=None, fim=None):
        """
        Top N categorias por soma (por tipo: despesa/receita).
        Retorna lista de dicts: {categoria, total}
        """
        movs = self._load_movs(inicio,fim)
        soma = defaultdict(float)
        for m in movs:
             if m['tipo'] == tipo:
                 soma[m['categoria']] += float(m['valor'])
        pares = [{'categoria': c, 'total': round(v,2)} for c, v in soma.items()]
        pares.sort(key=lambda x: x['total'], reverse=True)
        return pares[: max(0,int(n))]
    
    def alertas(self, inicio=None, fim=None):
        """
        Verifica excessos face a orçamentos 'mensal' e 'semanal'.
        Produz entradas como:
        {categoria, periodo, referencia, limite, gasto, excesso}
        """
        movs = self._load_movs(inicio, fim)
        orcs = self._load_orcs()
        if not orcs:
            return []
        
        gastos_mensal  = defaultdict(lambda: defaultdict(float))
        gastos_semanal = defaultdict(lambda: defaultdict(float))

        for m in movs:
            if m['tipo'] != 'despesa':
                continue
            cat = m['categoria']
            gastos_mensal[cat][self._yyyymm(m['data'])] += float(m['valor'])
            gastos_semanal[cat][self._isoweek_key(m["data"])] += float(m["valor"])

        res = []
        for o in orcs:
            cat = o['categoria']
            limite = float(o['limite'])
            periodo = o.get('periodo','mensal')
            if periodo == 'mensal':
                for ref, valor in (gastos_mensal.get(cat) or {}).items():
                    if valor > limite:
                        res.append({
                            "categoria": cat,
                            "periodo": "mensal",
                            "referencia": ref,
                            "limite": round(limite, 2),
                            "gasto": round(valor, 2),
                            "excesso": round(valor - limite, 2),
                        })
            elif periodo == 'semanal':
                for ref, valor in (gastos_semanal.get(cat) or {}).items():
                    if valor > limite:
                        res.append({
                            "categoria": cat,
                            "periodo": "semanal",
                            "referencia": ref,
                            "limite": round(limite, 2),
                            "gasto": round(valor, 2),
                            "excesso": round(valor - limite, 2),
                        })
        res.sort(key=lambda x: x["excesso"], reverse=True)
        return res
    
    def exportar(self, dados, tipo_rel, formato='json', nome=None):
        """
        Escreve ficheiro no diretório 'relatorios'.
        - formato: 'json' ou 'csv'
        - nome: opcional; se None gera automaticamente.
        Retorna o caminho do ficheiro criado.
        """
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        ext = 'json' if formato == 'json' else 'csv'
        fname = nome or f"{tipo_rel}_{ts}.{ext}"
        path = os.path.join(self.rel_dir,fname)

        if formato == 'json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        else: #csv
            rows = dados if isinstance(dados,list) else [dados]
            headers = set()
            for r in rows:
                headers.update(r.keys())
            headers = list(headers)
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for r in rows:
                    writer.writerow(r)
        return path