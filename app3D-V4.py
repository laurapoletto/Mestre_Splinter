import customtkinter as ctk
import psycopg2
from PIL import Image
import os
from tkinter import messagebox, simpledialog

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
class BancoDeDados:
    def __init__(self):
        self.online = False
        self.config = {
            "dbname": "postgres",
            "user": "postgres.viashgzgutyvchzsexll",
            "password": "L4y&R1#poeTC", 
            "host": "aws-1-sa-east-1.pooler.supabase.com",
            "port": "6543",
            "sslmode": "require"
        }
        
        try:
            self.criar_tabelas()
            self.online = True
        except Exception as e:
            self.online = False
            print(f"ERRO DE CONEXÃO: {e}")

    def conectar(self):
        return psycopg2.connect(**self.config)

    def criar_tabelas(self):
        conn = self.conectar()
        cursor = conn.cursor()
        # Adicionei a coluna 'localizacao' para saber se está no Estoque, H2D ou X1C
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS filamentos (
                id SERIAL PRIMARY KEY,
                marca TEXT NOT NULL,
                material TEXT NOT NULL,
                cor TEXT NOT NULL,
                peso_inicial REAL NOT NULL,
                preco REAL,
                localizacao TEXT DEFAULT 'ESTOQUE' 
            )
        """)
        # Garante que a coluna exista caso a tabela já tenha sido criada antes
        try:
            cursor.execute("ALTER TABLE filamentos ADD COLUMN IF NOT EXISTS localizacao TEXT DEFAULT 'ESTOQUE'")
        except: pass
        
        conn.commit()
        conn.close()

    def buscar_valores_unicos(self, coluna):
        if not self.online: return []
        try:
            conn = self.conectar()
            cursor = conn.cursor()
            cursor.execute(f"SELECT DISTINCT {coluna} FROM filamentos WHERE {coluna} IS NOT NULL")
            items = [row[0] for row in cursor.fetchall()]
            conn.close()
            return items
        except: return []

    def adicionar_filamento(self, marca, material, cor, peso, preco):
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO filamentos (marca, material, cor, peso_inicial, preco, localizacao)
            VALUES (%s, %s, %s, %s, %s, 'ESTOQUE')
        """, (marca, material, cor, peso, preco))
        conn.commit()
        conn.close()

    def buscar_todos_filamentos(self):
        # Busca apenas o que está no ESTOQUE GERAL
        if not self.online: return []
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM filamentos WHERE localizacao = 'ESTOQUE' ORDER BY id DESC")
        items = cursor.fetchall()
        conn.close()
        return items

    def buscar_filamentos_por_local(self, local):
        # Busca filamentos que estão em uma impressora específica (H2D ou X1C)
        if not self.online: return []
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM filamentos WHERE localizacao = %s ORDER BY id DESC", (local,))
        items = cursor.fetchall()
        conn.close()
        return items

    def remover_filamento(self, id_item):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM filamentos WHERE id = %s", (id_item,))
        conn.commit()
        conn.close()

    def atualizar_filamento(self, id_item, marca, material, cor, peso):
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE filamentos 
            SET marca = %s, material = %s, cor = %s, peso_inicial = %s 
            WHERE id = %s
        """, (marca, material, cor, peso, id_item))
        conn.commit()
        conn.close()

    def mover_filamento(self, id_item, nova_localizacao):
        # Move do Estoque para Impressora ou vice-versa
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("UPDATE filamentos SET localizacao = %s WHERE id = %s", (nova_localizacao, id_item))
        conn.commit()
        conn.close()

# --- INTERFACE GRÁFICA ---
class App3D(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = BancoDeDados()
        self.title("3D Control - Sistema de Gestão")
        self.geometry("1150x750")
        ctk.set_appearance_mode("dark")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.botoes_menu = {}
        self.criar_menu_lateral()
        self.show_inicio()

    def carregar_imagem_proporcional(self, filename, max_width, max_height):
        try:
            # ATENÇÃO: Verifique se o caminho da pasta está correto no seu PC
            pasta_assets = "c:/Users/LIP/Documents/Projeto_Estoque_3D/assets/"
            caminho_completo = os.path.join(pasta_assets, filename)
            pil_image = Image.open(caminho_completo)
            largura_orig, altura_orig = pil_image.size
            ratio = min(max_width/largura_orig, max_height/altura_orig)
            return ctk.CTkImage(pil_image, size=(int(largura_orig*ratio), int(altura_orig*ratio)))
        except: return None

    def criar_menu_lateral(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        img_certi = self.carregar_imagem_proporcional("Certi_Logo.png", 180, 80)
        if img_certi: ctk.CTkLabel(self.sidebar, image=img_certi, text="").grid(row=0, column=0, pady=(30, 10))

        img_ctma = self.carregar_imagem_proporcional("CTMA_LOGO2.png", 150, 100)
        if img_ctma: ctk.CTkLabel(self.sidebar, image=img_ctma, text="").grid(row=1, column=0, pady=(0, 30))

        btn_estilo = {"fg_color": "#333333", "hover_color": "#444444", "anchor": "w", "height": 40, "font": ("Roboto", 14)}

        self.botoes_menu["inicio"] = ctk.CTkButton(self.sidebar, text="🏠   Início", command=self.show_inicio, **btn_estilo)
        self.botoes_menu["inicio"].grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.botoes_menu["estoque"] = ctk.CTkButton(self.sidebar, text="📦   Filamentos", command=self.show_estoque, **btn_estilo)
        self.botoes_menu["estoque"].grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.botoes_menu["impressoras"] = ctk.CTkButton(self.sidebar, text="🖨️Impressoras", command=self.show_impressoras, **btn_estilo)
        self.botoes_menu["impressoras"].grid(row=4, column=0, padx=20, pady=5, sticky="ew")

    def atualizar_destaque_menu(self, aba_ativa):
        for nome_aba, botao in self.botoes_menu.items():
            if nome_aba == aba_ativa:
                botao.configure(fg_color="#4A4A4A", border_width=1, border_color="#666666")
            else:
                botao.configure(fg_color="#333333", border_width=0)

    # --- TELAS ---
    def show_inicio(self):
        self.atualizar_destaque_menu("inicio")
        self.limpar_area_principal()
        welcome_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        welcome_frame.pack(expand=True)
        ctk.CTkLabel(welcome_frame, text="Bem-vindo ao 3D Control", font=("Roboto", 32, "bold")).pack(pady=10)
        ctk.CTkLabel(welcome_frame, text="Gestão Centralizada de Laboratório", font=("Arial", 16)).pack(pady=20)

    def show_estoque(self):
        self.atualizar_destaque_menu("estoque")
        if not self.db.online:
            self.show_offline_mode()
            return
            
        self.limpar_area_principal()
        ctk.CTkLabel(self.main_frame, text="Estoque Geral", font=("Roboto", 28, "bold")).pack(anchor="w", pady=(0, 20))

        # Formulário
        form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        form_frame.pack(fill="x", pady=10)
        LARGURA_PADRAO, RAIO_CANTO = 180, 10

        self.combo_marca = ctk.CTkOptionMenu(form_frame, width=LARGURA_PADRAO, corner_radius=RAIO_CANTO,
                                            values=sorted(list(set(["DynaLabs", "National3D"] + self.db.buscar_valores_unicos("marca")))) + ["+ Adicionar Novo"],
                                            command=lambda v: self.lidar_com_novo_valor(v, self.combo_marca, "Marca"))
        self.combo_marca.pack(side="left", padx=5)
        self.combo_marca.set("Marca")

        self.combo_material = ctk.CTkOptionMenu(form_frame, width=LARGURA_PADRAO, corner_radius=RAIO_CANTO,
                                               values=["PLA", "PETG", "ABS", "TPU", "+ Adicionar Novo"],
                                               command=lambda v: self.lidar_com_novo_valor(v, self.combo_material, "Material"))
        self.combo_material.pack(side="left", padx=5)
        self.combo_material.set("Material")

        self.combo_cor = ctk.CTkOptionMenu(form_frame, width=LARGURA_PADRAO, corner_radius=RAIO_CANTO,
                                          values=sorted(list(set(["Preto", "Branco"] + self.db.buscar_valores_unicos("cor")))) + ["+ Adicionar Novo"],
                                          command=lambda v: self.lidar_com_novo_valor(v, self.combo_cor, "Cor"))
        self.combo_cor.pack(side="left", padx=5)
        self.combo_cor.set("Cor")

        self.entry_peso = ctk.CTkEntry(form_frame, placeholder_text="Peso (g)", width=100, corner_radius=RAIO_CANTO)
        self.entry_peso.pack(side="left", padx=5)

        ctk.CTkButton(form_frame, text="+ Adicionar", command=self.salvar_filamento, 
                      fg_color="#2ecc71", hover_color="#27ae60", width=120, corner_radius=RAIO_CANTO).pack(side="left", padx=10)

        # Tabela
        self.lista_frame = ctk.CTkScrollableFrame(self.main_frame, height=450, corner_radius=RAIO_CANTO)
        self.lista_frame.pack(fill="both", expand=True, pady=20)
        self.carregar_lista_estoque()

    # --- TELA DAS IMPRESSORAS (ATUALIZADA) ---
    def show_impressoras(self):
        self.atualizar_destaque_menu("impressoras")
        self.limpar_area_principal()
        
        ctk.CTkLabel(self.main_frame, text="Selecione a Impressora", font=("Roboto", 28, "bold")).pack(anchor="w", pady=(0, 30))

        # Frame Container para os dois "Quadradões"
        grid_impressoras = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        grid_impressoras.pack(fill="both", expand=True)

        # Criação dos Cards (Função auxiliar abaixo)
        # Substitua "h2d_placeholder.png" e "x1_placeholder.png" pelos nomes reais das suas imagens na pasta assets
        self.criar_card_impressora(grid_impressoras, "H2D", "H2D.webp", "H2D", 0)
        self.criar_card_impressora(grid_impressoras, "X1 Carbon", "x1-carbon.webp", "X1C", 1)

    def criar_card_impressora(self, parent, nome_exibicao, nome_imagem, codigo_interno, coluna):
        # Card clicável
        card = ctk.CTkFrame(parent, corner_radius=15, fg_color="#2b2b2b", border_width=2, border_color="#333333")
        card.grid(row=0, column=coluna, padx=20, pady=10, sticky="nsew")
        parent.grid_columnconfigure(coluna, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # Imagem (Placeholder se não encontrar)
        img = self.carregar_imagem_proporcional(nome_imagem, 300, 300)
        
        # Area da Imagem
        img_label = ctk.CTkLabel(card, text="" if img else "\n[Imagem da Impressora]\n(Coloque na pasta assets)", 
                                 image=img, font=("Arial", 14))
        img_label.pack(expand=True, pady=20)
        
        # Nome da Impressora
        ctk.CTkLabel(card, text=nome_exibicao, font=("Roboto", 24, "bold")).pack(pady=(0, 20))

        # Bind de clique (Funciona ao clicar no Frame ou no Label/Imagem)
        cmd = lambda e: self.show_detalhes_impressora(codigo_interno, nome_exibicao)
        card.bind("<Button-1>", cmd)
        img_label.bind("<Button-1>", cmd)
        
        # Efeito visual de hover
        def on_enter(e): card.configure(border_color="#2ecc71", fg_color="#333333")
        def on_leave(e): card.configure(border_color="#333333", fg_color="#2b2b2b")
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def show_detalhes_impressora(self, codigo_interno, nome_exibicao):
        self.limpar_area_principal()
        
        # Header
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkButton(header, text="⬅ Voltar", width=80, fg_color="#444444", 
                      command=self.show_impressoras).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(header, text=f"Gerenciamento: {nome_exibicao}", font=("Roboto", 26, "bold")).pack(side="left")

        # --- ÁREA DE ESPECIFICAÇÕES TÉCNICAS (EM LISTA) ---
        specs_frame = ctk.CTkFrame(self.main_frame, fg_color="#242424", corner_radius=10)
        specs_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(specs_frame, text="ESPECIFICAÇÕES TÉCNICAS:", font=("Roboto", 12, "bold"), text_color="#3498db").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Dicionário de specs para facilitar a manutenção
        if codigo_interno == "H2D":
            specs = [
                "Tecnologia: FDM (Fused Deposition Modeling)",
                "Volume de Impressão: 300 x 300 x 400 mm",
                "Temperatura Máxima do Bico: 500°C (Suporta PEEK, PEI, PPSU)",
                "Câmara Aquecida Ativa: Até 120°C",
                "Nivelamento: Automático de alta precisão",
                "Placa de Impressão: Aço flexível aquecida até 160°C"
            ]
        else: # X1 Carbon
            specs = [
                "Volume de Impressão: 256 x 256 x 256 mm",
                "Velocidade Máxima: 500 mm/s",
                "Aceleração: 20,000 mm/s²",
                "Bico: 0.4 mm Hardened Steel (até 300°C)",
                "Sensor: Lidar com resolução de mícrons",
                "Câmera: Integrada 1080p para monitoramento e Timelapse"
            ]

        for s in specs:
            ctk.CTkLabel(specs_frame, text=s, font=("Roboto", 13), text_color="#dddddd").pack(anchor="w", padx=25, pady=1)

        # --- ÁREA DO AMS (MAX 4 FILAMENTOS) ---
        aba_ams = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        aba_ams.pack(fill="both", expand=True, pady=20)

        ctk.CTkLabel(aba_ams, text=f"Slots do AMS ({nome_exibicao})", font=("Roboto", 20, "bold")).pack(anchor="w")
        
        # Botão para alocar
        self.btn_alocar = ctk.CTkButton(aba_ams, text="+ Alocar no AMS (Máx 4)", fg_color="#2ecc71", 
                                        command=lambda: self.abrir_selecao_estoque(codigo_interno))
        self.btn_alocar.pack(anchor="w", pady=10)

        self.frame_alocados = ctk.CTkScrollableFrame(aba_ams, height=250, corner_radius=10)
        self.frame_alocados.pack(fill="both", expand=True)
        
        self.carregar_filamentos_alocados(codigo_interno)

    def carregar_filamentos_alocados(self, codigo_interno):
        for w in self.frame_alocados.winfo_children(): w.destroy()
        
        itens = self.db.buscar_filamentos_por_local(codigo_interno)
        qtd_alocada = len(itens)

        # Desabilita o botão se o AMS estiver cheio
        if qtd_alocada >= 4:
            self.btn_alocar.configure(state="disabled", fg_color="#7f8c8d", text="AMS Cheio (4/4)")
        else:
            self.btn_alocar.configure(state="normal", fg_color="#2ecc71", text=f"+ Alocar no AMS ({qtd_alocada}/4)")

        if not itens:
            ctk.CTkLabel(self.frame_alocados, text="AMS vazio. Insira até 4 filamentos.", text_color="gray").pack(pady=20)
            return

        for i, item in enumerate(itens):
            id_bd, marca, material, cor, peso, _, _ = item
            
            row = ctk.CTkFrame(self.frame_alocados, fg_color="#2b2b2b", corner_radius=5)
            row.pack(fill="x", pady=2, padx=5)
            
            # Layout do Slot
            ctk.CTkLabel(row, text=f"SLOT {i+1}", font=("Roboto", 11, "bold"), text_color="#3498db", width=60).pack(side="left", padx=10)
            
            texto = f"{marca} {material} - {cor} ({peso}g)"
            ctk.CTkLabel(row, text=texto, font=("Roboto", 14), anchor="w").pack(side="left", padx=5, pady=10)
            
            ctk.CTkButton(row, text="Remover", width=80, fg_color="#c0392b", hover_color="#a93226",
                          command=lambda id_f=id_bd: [self.db.mover_filamento(id_f, 'ESTOQUE'), 
                                                      self.carregar_filamentos_alocados(codigo_interno)]
                          ).pack(side="right", padx=10)

    def abrir_selecao_estoque(self, codigo_destino):
        # Janela Pop-up para escolher o filamento
        win = ctk.CTkToplevel(self)
        win.title("Selecionar do Estoque")
        win.geometry("400x500")
        win.attributes("-topmost", True)
        
        ctk.CTkLabel(win, text="Selecione um filamento do Estoque:", font=("Roboto", 16, "bold")).pack(pady=10)
        
        lista_scroll = ctk.CTkScrollableFrame(win)
        lista_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Lista apenas os que estão no ESTOQUE
        estoque = self.db.buscar_todos_filamentos()
        
        if not estoque:
            ctk.CTkLabel(lista_scroll, text="Estoque vazio!").pack(pady=20)

        for item in estoque:
            id_bd, marca, material, cor, peso, _, _ = item
            
            btn = ctk.CTkButton(lista_scroll, text=f"ID {id_bd}: {marca} {material} {cor}", 
                                fg_color="#333333", hover_color="#444444", anchor="w",
                                command=lambda i=id_bd: [self.db.mover_filamento(i, codigo_destino), 
                                                         self.carregar_filamentos_alocados(codigo_destino), 
                                                         win.destroy()])
            btn.pack(fill="x", pady=2)


    # --- FUNÇÕES AUXILIARES (Tabela Estoque, Editar, etc) ---
    def carregar_lista_estoque(self):
        for widget in self.lista_frame.winfo_children(): widget.destroy()

        h_frame = ctk.CTkFrame(self.lista_frame, fg_color="#1f1f1f", corner_radius=0)
        h_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        cols = [("ID", 50), ("Marca", 150), ("Material", 120), ("Cor", 120), ("Quantidade", 150)]
        for i, (txt, larg) in enumerate(cols):
            ctk.CTkLabel(h_frame, text=txt, font=("Roboto", 12, "bold"), width=larg, anchor="w").grid(row=0, column=i, padx=10, pady=5)

        for idx, item in enumerate(self.db.buscar_todos_filamentos()):
            id_bd, marca, material, cor, peso, _, _ = item
            
            row = ctk.CTkFrame(self.lista_frame, fg_color="#2b2b2b", corner_radius=5, cursor="hand2")
            row.pack(fill="x", pady=2, padx=5)
            
            def on_enter(e, r=row): r.configure(fg_color="#383838")
            def on_leave(e, r=row): r.configure(fg_color="#2b2b2b")
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)

            dados = [id_bd, marca, material, cor, f"{peso}g"]
            for i, valor in enumerate(dados):
                lbl = ctk.CTkLabel(row, text=valor, width=cols[i][1], anchor="w")
                lbl.grid(row=0, column=i, padx=10, pady=8)
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)

            btn_opcoes = ctk.CTkButton(row, text="⋮", width=30, height=25, fg_color="transparent", 
                                       hover_color="#444444", font=("Roboto", 18, "bold"),
                                       command=lambda i=id_bd: self.abrir_menu_opcoes(i))
            btn_opcoes.grid(row=0, column=5, padx=10, sticky="e")
            row.grid_columnconfigure(5, weight=1)

    def abrir_menu_opcoes(self, id_item):
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        menu.configure(fg_color="#1a1a1a")
        
        largura_menu, altura_menu = 140, 130
        mouse_x, mouse_y = self.winfo_pointerx(), self.winfo_pointery()
        
        pos_x = mouse_x - largura_menu if mouse_x + largura_menu > self.winfo_screenwidth() else mouse_x
        menu.geometry(f"{largura_menu}x{altura_menu}+{pos_x}+{mouse_y}")
        menu.bind("<FocusOut>", lambda e: menu.destroy())

        btn_estilo_pop = {"fg_color": "transparent", "hover_color": "#333333", "anchor": "w", "height": 35, "font": ("Roboto", 13)}

        ctk.CTkButton(menu, text="✏️   Editar", command=lambda: [menu.destroy(), self.janela_editar_filamento(id_item)], **btn_estilo_pop).pack(fill="x", padx=5, pady=2)
        ctk.CTkButton(menu, text="🗑️   Excluir", text_color="#ff5555", command=lambda: [self.db.remover_filamento(id_item), self.carregar_lista_estoque(), menu.destroy()], **btn_estilo_pop).pack(fill="x", padx=5, pady=2)
        # O botão Mover agora pode chamar a função real se quiser, ou deixar pro futuro
        ctk.CTkButton(menu, text="📦   Mover", command=lambda: [print("Use a tela de Impressoras para alocar"), menu.destroy()], **btn_estilo_pop).pack(fill="x", padx=5, pady=2)
        
        menu.after(10, lambda: menu.focus_set())

    def janela_editar_filamento(self, id_item):
        dados_atuais = None
        # Busca em todos (independente de onde esteja) para editar
        conn = self.db.conectar()
        cur = conn.cursor()
        cur.execute("SELECT * FROM filamentos WHERE id = %s", (id_item,))
        dados_atuais = cur.fetchone()
        conn.close()
        
        if not dados_atuais: return

        edit_win = ctk.CTkToplevel(self)
        edit_win.title(f"Editar ID {id_item}")
        edit_win.geometry("400x450")
        edit_win.attributes("-topmost", True)
        edit_win.grab_set()

        ctk.CTkLabel(edit_win, text=f"Editando Registro #{id_item}", font=("Roboto", 18, "bold")).pack(pady=20)

        entry_marca = ctk.CTkEntry(edit_win, width=250)
        entry_marca.pack(pady=10)
        entry_marca.insert(0, dados_atuais[1])

        entry_material = ctk.CTkEntry(edit_win, width=250)
        entry_material.pack(pady=10)
        entry_material.insert(0, dados_atuais[2])

        entry_cor = ctk.CTkEntry(edit_win, width=250)
        entry_cor.pack(pady=10)
        entry_cor.insert(0, dados_atuais[3])

        entry_peso = ctk.CTkEntry(edit_win, width=250)
        entry_peso.pack(pady=10)
        entry_peso.insert(0, str(dados_atuais[4]))

        def salvar():
            try:
                self.db.atualizar_filamento(id_item, entry_marca.get(), entry_material.get(), entry_cor.get(), float(entry_peso.get()))
                edit_win.destroy()
                self.carregar_lista_estoque()
                messagebox.showinfo("Sucesso", "Atualizado!")
            except: messagebox.showerror("Erro", "Verifique o peso!")

        ctk.CTkButton(edit_win, text="Salvar Alterações", fg_color="#2ecc71", command=salvar).pack(pady=30)

    def lidar_com_novo_valor(self, escolha, combo, titulo):
        if escolha == "+ Adicionar Novo":
            novo = simpledialog.askstring("Novo", f"Novo(a) {titulo}:")
            if novo:
                vals = list(combo.cget("values"))
                if novo not in vals: vals.insert(0, novo)
                combo.configure(values=vals)
                combo.set(novo)

    def salvar_filamento(self):
        try:
            m, mat, c, p = self.combo_marca.get(), self.combo_material.get(), self.combo_cor.get(), self.entry_peso.get()
            self.db.adicionar_filamento(m, mat, c, float(p), 0.0)
            self.show_estoque()
        except: messagebox.showwarning("Erro", "Preencha os campos!")

    def show_offline_mode(self):
        self.limpar_area_principal()
        ctk.CTkLabel(self.main_frame, text="⚠️ SEM CONEXÃO", font=("Arial", 30), text_color="orange").pack(pady=50)

    def limpar_area_principal(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()

if __name__ == "__main__":
    app = App3D()
    app.mainloop()