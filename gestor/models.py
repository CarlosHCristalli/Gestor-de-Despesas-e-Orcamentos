#gestor/models.py
#Criar uma classe e validar com if/raise
from enum import Enum
from datetime import datetime

class TipoMovimento(str, Enum):
    DESPESA = "despesa"
    RECEITA = "receita"

def _is_iso_datetime(value):
    """Valida strings no formato ISO 8601 (aceita 'YYYY-MM-DD' ou 'YYYY-MM-DDTHH:MM[:SS]')."""
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False
       
class Movimento:

    """
    Representa um movimento financeiro (despesa/receita).

    Campos:
      - id: int (gerado pelo storage)
      - tipo: TipoMovimento
      - data_iso: str no formato ISO 8601. NOTA: será, por omissão, a data/hora atual
                  no momento do comando (definido na CLI/serviço).
      - valor: float (> 0)
      - categoria: str (obrigatório)
      - descricao: str (opcional)
      - metodo_pagamento: str (opcional, ex.: 'MBWay', 'cartao', 'dinheiro', ...)
      - tags: lista de strings (opcional)
    """

    def __init__(self, id_, tipo, valor, categoria, descricao="", metodo_pagamento="",data_iso=None):
        self.id = int(id_)
        self.tipo = ( tipo if isinstance(tipo, TipoMovimento) else TipoMovimento(str(tipo)))
        self.valor = float(valor)
        self.categoria = str(categoria).strip()
        self.descricao = str(descricao or "")
        self.metodo_pagamento = str(metodo_pagamento or "").strip()
        self.data_iso = data_iso or ""
    
    def validar(self):
        if not isinstance(self.tipo, TipoMovimento):
            raise ValueError("Tipo de movimento inválido.")
        if self.valor <= 0:
            raise ValueError("O valor deve ser maior que zero.")
        if not self.categoria:
            raise ValueError("A categoria é obrigatória.")        
        
    def to_dict(self):
        #Converte a tarefa em um dicionario para guardar no JSON
        return {
            "id": self.id,
            "tipo": self.tipo.value,
            "data": self.data_iso,
            "valor": self.valor,
            "categoria": self.categoria,
            "descricao": self.descricao,
            "metodo": self.metodo_pagamento
        }

    def from_dict(d):
        #Cria a tarefa a partir do diconario (Quando carregarmos o ficheiro JSON)
        return Movimento(
            id_=int(d["id"]),
            tipo=TipoMovimento(d.get("tipo", "despesa")),
            valor=float(d.get("valor", 0.0)),
            categoria=d.get("categoria", "").strip(),
            descricao=d.get("descricao", ""),
            metodo_pagamento=d.get("metodo", ""),
            data_iso=d.get("data", "")
        )
    
class Orcamento:
    """
    Orçamento por categoria e período.   
    """
    def __init__(self,id_,categoria,limite,periodo="mensal"):
        self.id = int(id_)
        self.categoria = str(categoria).strip()
        self.limite = float(limite)
        self.periodo = str(periodo or "mensal").strip().lower()
    
    def validar(self):
        if not self.categoria:
            raise ValueError("A categoria do orçamento é obrigatória.")
        if self.limite <= 0:
            raise ValueError("O limite do orçamento deve ser maior que zero.")
        if self.periodo not in ("mensal","semanal"):
            raise ValueError("Período inválido. Suportado: 'mensal' ou 'semanal.")
        
    def to_dict(self):
        return {
            "id": self.id,
            "categoria": self.categoria,
            "limite": self.limite,
            "periodo": self.periodo,
        }
    
    def from_dict(d):
        return Orcamento(
            id_=int(d["id"]),
            categoria=d.get("categoria", "").strip(),
            limite=float(d.get("limite", 0.0)),
            periodo=d.get("periodo", "mensal"),
        )