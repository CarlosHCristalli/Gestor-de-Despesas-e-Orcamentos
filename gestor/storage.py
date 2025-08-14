#gestor/storage.py
#Responsavel por ler e guardar a lista de tarefas num ficheiro JSON.

#Importa as funcionalidades do sistema operativo para permitir a utilizacao de pastas ficheiros e variaves de ambiente 
import os
#Permite trabalhar com dados em formato JSON
import json

class Storage:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.movimentos_path = os.path.join(self.base_dir,"movimentos.json")
        self.orcamentos_path = os.path.join(self.base_dir, "orcamentos.json")

    def carregar_movimentos(self):
        #Devolver uma lista de dicionarios. Se o ficheiro nao existir, deve devolver uma lista vazia
        if not os.path.exists(self.movimentos_path):
            return []
        with open(self.movimentos_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def guardar_movimentos(self,movimentos_lista):
        #receber a lista de dicionarios e gravar em JSON
        with open(self.movimentos_path,'w',encoding='utf-8') as f:
            json.dump(movimentos_lista,f,ensure_ascii=False,indent=2)
    def proximo_id(self):
        #Calcular o proximo id com base no maior id ja existente
        movimentos = self.carregar_movimentos()
        max_id=0
        for movimento in movimentos :
            if int(movimento.get('id',0))>max_id:
                max_id = int(movimento['id'])
        return max_id + 1      

    def carregar_orcamentos(self):
        if not os.path.exists(self.orcamentos_path):
             return []
        with open(self.orcamentos_path, "r", encoding="utf-8") as f:
            return json.load(f)
        
    def guardar_orcamentos(self, orcamento_lista):
        with open(self.orcamentos_path, "w", encoding="utf-8") as f:
            json.dump(orcamento_lista, f, ensure_ascii=False, indent=2)

    def proximo_id_orcamento(self):
        orcs = self.carregar_orcamentos()
        max_id = 0
        for o in orcs:
            if int(o.get("id",0)) > max_id:
                max_id = int(o["id"])
        return max_id + 1