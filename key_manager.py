import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
from datetime import datetime, timedelta

class LiteLLMKeyManager:
    def __init__(self, root):
        self.root = root
        self.root.title("LiteLLM Key Manager")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variáveis
        self.server_url = tk.StringVar(value="https://litellm-server-458225897211.us-central1.run.app")
        self.master_key = tk.StringVar()
        self.key_name = tk.StringVar()
        self.team_id = tk.StringVar()
        self.max_budget = tk.DoubleVar(value=50.0)
        self.expires_days = tk.StringVar(value="30d")
        
        # Modelos disponíveis
        self.available_models = [
            "gpt-3.5-turbo", 
            "gpt-4", 
            "claude-3-opus", 
            "claude-3-sonnet", 
            "gemini-pro", 
            "grok-1"
        ]
        
        # Checkbuttons para os modelos
        self.model_vars = {}
        for model in self.available_models:
            self.model_vars[model] = tk.BooleanVar(value=False)
        
        self.create_widgets()
        
    def create_widgets(self):
        # Frame principal com notebook para abas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Aba de Conexão
        connection_frame = ttk.Frame(notebook)
        notebook.add(connection_frame, text="Conexão")
        
        # Aba de Gerenciamento de Chaves
        keys_frame = ttk.Frame(notebook)
        notebook.add(keys_frame, text="Gerenciar Chaves")
        
        # Aba de Listagem de Chaves
        list_keys_frame = ttk.Frame(notebook)
        notebook.add(list_keys_frame, text="Listar Chaves")
        
        # Configurar a aba de Conexão
        self.setup_connection_tab(connection_frame)
        
        # Configurar a aba de Gerenciamento de Chaves
        self.setup_keys_tab(keys_frame)
        
        # Configurar a aba de Listagem de Chaves
        self.setup_list_keys_tab(list_keys_frame)
        
        # Barra de status
        self.status_var = tk.StringVar(value="Pronto")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_connection_tab(self, parent):
        # Frame de configuração do servidor
        server_frame = ttk.LabelFrame(parent, text="Configuração do Servidor")
        server_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        # URL do Servidor
        ttk.Label(server_frame, text="URL do Servidor:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(server_frame, textvariable=self.server_url, width=50).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Chave Mestra
        ttk.Label(server_frame, text="Chave Mestra:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(server_frame, textvariable=self.master_key, width=50, show="*").grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Botão para testar conexão
        ttk.Button(server_frame, text="Testar Conexão", command=self.test_connection).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Instruções de uso
        instructions_frame = ttk.LabelFrame(parent, text="Instruções")
        instructions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        instructions = scrolledtext.ScrolledText(instructions_frame, wrap=tk.WORD, width=70, height=15)
        instructions.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        instructions.insert(tk.END, """
1. Iniciando o LiteLLM Server:
   - Clone o repositório: git clone https://github.com/BerriAI/litellm.git
   - Navegue até o diretório: cd litellm
   - Crie o arquivo config.yaml na pasta raiz
   - Configure as variáveis de ambiente com suas chaves de API
   - Inicie o servidor com:
     python -m litellm.proxy.proxy_server --config /path/to/config.yaml --port 8000 --api_key sua_chave_mestra

2. Conectando ao servidor:
   - Configure a URL do servidor (padrão: http://localhost:8000)
   - Digite a chave mestra definida ao iniciar o servidor
   - Clique em "Testar Conexão" para verificar

3. Gerenciando chaves:
   - Crie novas chaves com parâmetros específicos na aba "Gerenciar Chaves"
   - Visualize chaves existentes na aba "Listar Chaves"
   - Delete chaves quando necessário
        """)
        instructions.config(state=tk.DISABLED)
    
    def setup_keys_tab(self, parent):
        # Frame para criar novas chaves
        create_frame = ttk.LabelFrame(parent, text="Criar Nova Chave")
        create_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Formulário em grid para criar chaves
        ttk.Label(create_frame, text="Nome da Chave:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(create_frame, textvariable=self.key_name, width=40).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(create_frame, text="ID da Equipe (opcional):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(create_frame, textvariable=self.team_id, width=40).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(create_frame, text="Orçamento Máximo ($):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(create_frame, from_=0, to=1000, textvariable=self.max_budget, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(create_frame, text="Expirar em (ex: 30d, 24h, 60m):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Função de validação para permitir números e sufixos de tempo (d, h, m, s)
        def validate_duration(input):
            if input == "":
                return True
            # Aceita dígitos seguidos opcionalmente por d, h, m ou s
            import re
            return bool(re.match(r'^[0-9]+[dhms]?$', input))
                
        vcmd = (self.root.register(validate_duration), '%P')
        ttk.Entry(create_frame, textvariable=self.expires_days, width=10, 
                 validate="key", validatecommand=vcmd).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Frame para os modelos
        models_frame = ttk.LabelFrame(create_frame, text="Modelos Permitidos")
        models_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=10)
        
        # Checkbuttons para modelos
        for i, model in enumerate(self.available_models):
            row, col = divmod(i, 3)
            ttk.Checkbutton(models_frame, text=model, variable=self.model_vars[model]).grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
        
        # Botão para criar chave
        ttk.Button(create_frame, text="Criar Chave", command=self.create_key).grid(row=5, column=0, columnspan=2, pady=10)
        
        # Área para mostrar a chave criada
        ttk.Label(create_frame, text="Chave Gerada:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.key_result = scrolledtext.ScrolledText(create_frame, wrap=tk.WORD, width=70, height=10)
        self.key_result.grid(row=7, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)
        
    def setup_list_keys_tab(self, parent):
        # Frame para listar chaves
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Botão para atualizar lista
        ttk.Button(list_frame, text="Atualizar Lista de Chaves", command=self.list_keys).pack(pady=10)
        
        # Treeview para mostrar as chaves
        columns = ('key', 'name', 'team_id', 'models', 'budget', 'spend', 'expires')
        self.keys_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Configurar cabeçalhos
        self.keys_tree.heading('key', text='Nome')
        self.keys_tree.heading('name', text='Chave')
        self.keys_tree.heading('team_id', text='Equipe')
        self.keys_tree.heading('models', text='Modelos')
        self.keys_tree.heading('budget', text='Orçamento')
        self.keys_tree.heading('spend', text='Gasto')
        self.keys_tree.heading('expires', text='Expira em')
        
        # Configurar colunas
        self.keys_tree.column('key', width=150, anchor='w')
        self.keys_tree.column('name', width=100, anchor='w')
        self.keys_tree.column('team_id', width=80, anchor='w')
        self.keys_tree.column('models', width=200, anchor='w')
        self.keys_tree.column('budget', width=80, anchor='e')
        self.keys_tree.column('spend', width=80, anchor='e')
        self.keys_tree.column('expires', width=100, anchor='w')
        
        # Adicionar scrollbar
        keys_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.keys_tree.yview)
        self.keys_tree.configure(yscroll=keys_scroll.set)
        
        # Empacotar elementos
        self.keys_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        keys_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botão para revogar chave selecionada
        ttk.Button(list_frame, text="Revogar Chave Selecionada", command=self.revoke_key).pack(pady=10)
        
    def test_connection(self):
        """Testa a conexão com o servidor LiteLLM"""
        try:
            url = f"{self.server_url.get()}/health"
            headers = {"Authorization": f"Bearer {self.master_key.get()}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                messagebox.showinfo("Conexão", "Conexão com o servidor bem-sucedida!")
                self.status_var.set("Conexão com o servidor estabelecida")
            else:
                messagebox.showerror("Erro", f"Erro ao conectar: Status {response.status_code}")
                self.status_var.set(f"Erro de conexão: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao conectar ao servidor: {str(e)}")
            self.status_var.set(f"Erro de conexão: {str(e)}")
    
    def create_key(self):
        """Cria uma nova chave de API"""
        if not self.validate_form():
            return
            
        try:
            # Preparar dados
            selected_models = [model for model, var in self.model_vars.items() if var.get()]

            # Formatar a duração corretamente
            duration_str = None
            expires_value = self.expires_days.get()
            
            if expires_value:
                # Verifica se já tem um sufixo (d, h, m, s)
                import re
                if re.match(r'^[0-9]+[dhms]$', expires_value):
                    # Já está no formato correto como "10d", "24h", etc.
                    duration_str = expires_value
                else:
                    # Se for apenas um número, assumir que são dias e adicionar "d"
                    try:
                        days = int(expires_value)
                        if days > 0:
                            duration_str = f"{days}d"
                    except ValueError:
                        messagebox.showerror("Erro", "Formato de duração inválido. Use números seguidos por d (dias), h (horas), m (minutos) ou s (segundos).")
                        return

            print(f"Valor original da duração: {expires_value}")
            print(f"Duração formatada: {duration_str}")

            # Criar o payload básico
            payload = {}
            
            # Adicionar campos apenas se tiverem valores
            if self.key_name.get():
                payload["key_name"] = self.key_name.get()
                # Adicionar também como key_alias para garantir compatibilidade
                payload["key_alias"] = self.key_name.get()
                
            if selected_models:
                payload["models"] = selected_models
                
            if self.max_budget.get() > 0:
                payload["max_budget"] = self.max_budget.get()
                
            # Adicionar duration apenas se tiver valor - GARANTIR QUE É STRING
            if duration_str:
                # Usar aspas duplas extras para garantir que seja tratado como string
                payload["duration"] = duration_str
                
            # Adicionar team_id se foi fornecido
            if self.team_id.get():
                payload["team_id"] = self.team_id.get()
            
            # Debug: mostrar payload antes de enviar
            print("Payload a ser enviado:", json.dumps(payload, indent=2))
            print("Tipo de duration:", type(payload.get("duration", None)).__name__)

            # Enviar solicitação
            url = f"{self.server_url.get()}/key/generate"
            headers = {"Authorization": f"Bearer {self.master_key.get()}", "Content-Type": "application/json"}

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                self.key_result.delete(1.0, tk.END)
                self.key_result.insert(tk.END, json.dumps(result, indent=2))
                self.status_var.set("Chave criada com sucesso")
            else:
                error_msg = f"Erro ao criar chave: {response.status_code}\n{response.text}"
                print("Erro completo:", error_msg)
                messagebox.showerror("Erro", error_msg)
                self.status_var.set(f"Erro ao criar chave: {response.status_code}")
        except Exception as e:
            error_msg = f"Erro ao criar chave: {str(e)}"
            print("Exceção:", error_msg)
            messagebox.showerror("Erro", error_msg)
            self.status_var.set(error_msg)
    
    def list_keys(self):
        """Lista todas as chaves existentes"""
        try:
            url = f"{self.server_url.get()}/key/list"
            headers = {"Authorization": f"Bearer {self.master_key.get()}"}
            
            print("Listando chaves...")
            print(f"URL: {url}")
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Processando a resposta
                print(f"Status code: {response.status_code}")
                data = response.json()
                print(f"Resposta do servidor: {json.dumps(data, indent=2)}")
                
                # A resposta tem um formato específico com um campo "keys" que contém um array
                # O array pode conter strings (IDs das chaves) ou objetos (detalhes das chaves)
                keys = []
                
                # Verificar o formato da resposta
                if isinstance(data, dict) and "keys" in data:
                    # Formato oficial com campo "keys"
                    keys = data["keys"]
                else:
                    print(f"Erro: Formato de resposta inesperado: {data}")
                    keys = []
                
                print(f"Chaves encontradas: {keys}")
                
                # Limpar treeview existente
                for item in self.keys_tree.get_children():
                    self.keys_tree.delete(item)
                
                # Preencher com novos dados
                for key_info in keys:
                    # Obter detalhes da chave
                    key_details = self.get_key_details(key_info)
                    
                    if key_details:
                        # Obter valores específicos - sem condicionais
                        key_id = key_details["info"].get("token", "")
                        if not key_id:
                            key_id = key_details["info"].get("api_key", key_details["info"].get("key", ""))

                        key_name = key_details["info"].get("key_name", "")
                        key_alias = key_details["info"].get("key_alias", "")
                        
                        # Team ID
                        team_id = key_details["info"].get("team_id", "")
                        
                        # Modelos permitidos
                        models_data = key_details["info"].get("models", [])
                        
                        # Formatar modelos para exibição
                        if isinstance(models_data, list):
                            models = ", ".join(models_data)
                        else:
                            models = "Todos"
                        
                        # Orçamento máximo
                        max_budget = key_details["info"].get("max_budget")
                        max_budget_str = f"${max_budget}" if max_budget else "$∞"
                        
                        # Gastos
                        spend = key_details["info"].get("spend", 0)
                        spend_str = f"${float(spend):.2f}"
                        
                        # Expiração
                        expires = key_details["info"].get("expires", "")
                        if expires:
                            try:
                                if isinstance(expires, str):
                                    if "Z" in expires:
                                        expires = expires.replace("Z", "+00:00")
                                    exp_date = datetime.fromisoformat(expires)
                                    expires = exp_date.strftime("%d/%m/%Y")
                            except:
                                expires = str(expires)
                        else:
                            expires = "Não expira"
                    else:
                        print(f"Erro ao obter detalhes da chave: {key_info}")
                        continue
                    
                    # Garantir que o ID da chave tem o prefixo sk_ para exibição
                    if isinstance(key_id, str) and not key_id.startswith("sk_") and key_id:
                        key_id = f"sk_{key_id}"
                    
                    # Registrar os dados para depuração
                    print(f"Exibindo chave: ID={key_id}, key_name={key_name}, key_alias={key_alias}, Team={team_id}, " 
                          f"Modelos={models}, Budget={max_budget_str}, Spend={spend_str}, Expires={expires}")
                    
                    # Usar key_alias na coluna Nome e key_name na coluna Chave
                    self.keys_tree.insert('', tk.END, values=(key_alias, key_name, team_id, models, max_budget_str, spend_str, expires))
                
                self.status_var.set(f"{len(keys)} chaves listadas")
            else:
                messagebox.showerror("Erro", f"Erro ao listar chaves: {response.status_code}\n{response.text}")
                self.status_var.set(f"Erro ao listar chaves: {response.status_code}")
        except Exception as e:
            error_msg = f"Erro ao listar chaves: {str(e)}"
            print(error_msg)
            messagebox.showerror("Erro", error_msg)
            self.status_var.set(error_msg)
    
    def revoke_key(self):
        """Revoga a chave selecionada"""
        selected = self.keys_tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma chave para revogar")
            return
            
        # Obter o valor de key_name da segunda coluna (índice 1)
        key_name = self.keys_tree.item(selected[0], 'values')[1]
        
        # Se o key_name começa com sk_, remover esse prefixo para a API
        api_key_id = key_name
        if key_name.startswith("sk_"):
            api_key_id = key_name[3:]  # Remover o prefixo sk_
            
        print(f"Tentando revogar chave: {key_name} (API ID: {api_key_id})")
        
        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja revogar a chave {key_name}?"):
            try:
                # Tentar diferentes formatos de URL para revogar a chave
                endpoints_to_try = [
                    # Formato 1: POST /key/delete com token no payload
                    {"method": "POST", "url": f"{self.server_url.get()}/key/delete", 
                     "data": {"token": api_key_id}},
                     
                    # Formato 2: POST /key/delete com key no payload
                    {"method": "POST", "url": f"{self.server_url.get()}/key/delete", 
                     "data": {"key": api_key_id}},
                    
                    # Formato 3: DELETE /key/delete/{key_id}
                    {"method": "DELETE", "url": f"{self.server_url.get()}/key/delete/{api_key_id}"},
                     
                    # Formato 4: DELETE /key/{key_id}
                    {"method": "DELETE", "url": f"{self.server_url.get()}/key/{api_key_id}"},
                    
                    # Tentar também com o prefixo sk_
                    {"method": "POST", "url": f"{self.server_url.get()}/key/delete", 
                     "data": {"token": key_name}},
                    {"method": "DELETE", "url": f"{self.server_url.get()}/key/delete/{key_name}"}
                ]
                
                headers = {"Authorization": f"Bearer {self.master_key.get()}", "Content-Type": "application/json"}
                success = False
                
                # Tentar todos os endpoints até um funcionar
                for attempt in endpoints_to_try:
                    try:
                        print(f"Tentando revogar: {attempt['method']} {attempt['url']} {attempt.get('data', {})}")
                        
                        if attempt["method"] == "DELETE":
                            response = requests.delete(attempt["url"], headers=headers)
                        else:  # POST
                            response = requests.post(attempt["url"], headers=headers, json=attempt.get("data", {}))
                        
                        print(f"Resposta: HTTP {response.status_code}")
                        try:
                            print(f"Conteúdo da resposta: {response.text}")
                        except:
                            pass
                        
                        # Códigos de sucesso: 200 OK, 201 Created, 202 Accepted, 204 No Content
                        if response.status_code in [200, 201, 202, 204]:
                            print("Revogação bem-sucedida")
                            success = True
                            break
                    except Exception as e:
                        print(f"Erro ao tentar endpoint {attempt['url']}: {str(e)}")
                        continue
                
                if success:
                    self.keys_tree.delete(selected[0])
                    messagebox.showinfo("Sucesso", "Chave revogada com sucesso")
                    self.status_var.set("Chave revogada com sucesso")
                    # Atualizar a lista de chaves
                    self.list_keys()
                else:
                    messagebox.showerror("Erro", "Não foi possível revogar a chave. Tente novamente mais tarde.")
                    self.status_var.set("Erro ao revogar chave")
            except Exception as e:
                error_msg = f"Erro ao revogar chave: {str(e)}"
                print(error_msg)
                messagebox.showerror("Erro", error_msg)
                self.status_var.set(error_msg)
    
    def validate_form(self):
        """Valida o formulário de criação de chave"""
        if not self.key_name.get():
            messagebox.showwarning("Aviso", "O nome da chave é obrigatório")
            return False
            
        if not self.master_key.get():
            messagebox.showwarning("Aviso", "A chave mestra é necessária para criar novas chaves")
            return False
            
        return True

    def get_key_details(self, key_id):
        """Obtém detalhes de uma chave específica pelo ID"""
        try:
            url = f"{self.server_url.get()}/key/info?key={key_id}"
            headers = {"Authorization": f"Bearer {self.master_key.get()}", "Content-Type": "application/json"}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Detalhes obtidos com sucesso: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"Erro ao obter detalhes da chave: Status {response.status_code}, Text: {response.text}")
                return {"key": key_id, "key_name": "Erro (Não encontrado)", "team_id": "", "models": [], "max_budget": 0, "spend": 0}
        except Exception as e:
            print(f"Exceção ao obter detalhes da chave {key_id}: {str(e)}")
            return {"key": key_id, "key_name": f"Erro: {str(e)}", "team_id": "", "models": [], "max_budget": 0, "spend": 0}

if __name__ == "__main__":
    root = tk.Tk()
    app = LiteLLMKeyManager(root)
    root.mainloop()
