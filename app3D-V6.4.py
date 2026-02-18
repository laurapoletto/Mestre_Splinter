import customtkinter as ctk
import psycopg2
from PIL import Image
import os
from tkinter import messagebox, simpledialog
from tkinter import filedialog
import io
import datetime







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
        
        # --- Tabela de filamentos ---
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

        # --- Tabela de resinas ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resinas (
                id SERIAL PRIMARY KEY,
                marca TEXT NOT NULL,
                tipo TEXT NOT NULL,       -- ex: Standard, Tough, Dental, etc
                cor TEXT NOT NULL,
                volume_ml REAL NOT NULL,  -- resina faz mais sentido em ml
                preco REAL,
                localizacao TEXT DEFAULT 'ESTOQUE'
            )
        """)

        # --- Tabela peças ----
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pecas (
                id SERIAL PRIMARY KEY,
                titulo TEXT NOT NULL,
                data_solicitacao DATE,
                status TEXT DEFAULT 'PENDENTE',  -- 'PENDENTE' ou 'CONCLUIDO'
                
                -- DADOS DA SOLICITAÇÃO
                sol_sigla TEXT,
                sol_nome TEXT,
                centro TEXT,
                is_ctma BOOLEAN,
                dimensoes_max TEXT,   -- Novo: ex "20x20x20mm"
                complexidade INTEGER, -- Novo: 1, 2 ou 3
                obs TEXT,
                arquivo_bin BYTEA,
                arquivo_nome TEXT,

                -- DADOS DA EXECUÇÃO (Preenchidos apenas ao concluir)
                data_imp DATE,
                tempo TEXT,
                massa REAL,
                unidade_massa TEXT DEFAULT 'g',
                filamento_usado TEXT,
                impressora TEXT
            )
        """)

        
        # Atualização de colunas para quem já tem o banco criado
        colunas_novas = [
            ("unidade_massa", "TEXT DEFAULT 'g'"),
            ("sol_sigla", "TEXT"), ("sol_nome", "TEXT"), ("centro", "TEXT"),
            ("is_ctma", "BOOLEAN"), ("arquivo_bin", "BYTEA"), ("arquivo_nome", "TEXT"),
            ("status", "TEXT DEFAULT 'PENDENTE'"),
            ("dimensoes_max", "TEXT"),
            ("complexidade", "INTEGER"),
            ("data_solicitacao", "DATE")
        ]
        
        for col, tipo in colunas_novas:
            try:
                cursor.execute(f"ALTER TABLE pecas ADD COLUMN IF NOT EXISTS {col} {tipo}")
            except: pass
            
        conn.commit()
        conn.close()




    #-------------------MÉTODOS PEÇAS----------------------------------
    def criar_solicitacao(self, titulo, data_sol, sol_sigla, sol_nome, centro, is_ctma, 
                          dimensoes, complexidade, obs, arq_bin, arq_nome):
        # Cria apenas com os dados do SOLICITANTE
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pecas (titulo, data_solicitacao, status, sol_sigla, sol_nome, centro, 
                               is_ctma, dimensoes_max, complexidade, obs, arquivo_bin, arquivo_nome)
            VALUES (%s, %s, 'PENDENTE', %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (titulo, data_sol, sol_sigla, sol_nome, centro, is_ctma, dimensoes, complexidade, obs, arq_bin, arq_nome))
        conn.commit()
        conn.close()

    def concluir_peca(self, id_peca, data_imp, impressora, filamento, tempo, massa, unidade):
        # Atualiza a peça PENDENTE com os dados de EXECUÇÃO
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pecas 
            SET status = 'CONCLUIDO', data_imp = %s, impressora = %s, filamento_usado = %s, 
                tempo = %s, massa = %s, unidade_massa = %s
            WHERE id = %s
        """, (data_imp, impressora, filamento, tempo, massa, unidade, id_peca))
        conn.commit()
        conn.close()

    def buscar_pecas_por_status(self, status):
        # Busca separada para as abas
        if not self.online: return []
        conn = self.conectar()
        cursor = conn.cursor()
        # Seleciona campos relevantes para a tabela visual
        cursor.execute("""
            SELECT id, titulo, sol_sigla, centro, data_solicitacao, is_ctma, arquivo_nome, 
                   dimensoes_max, complexidade, impressora, data_imp
            FROM pecas 
            WHERE status = %s 
            ORDER BY id DESC
        """, (status,))
        items = cursor.fetchall()
        conn.close()
        return items

    def buscar_detalhes_peca(self, id_peca):
        if not self.online: return None
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, titulo, data_solicitacao, status, sol_sigla, sol_nome, centro, is_ctma,
                   dimensoes_max, complexidade, obs, arquivo_nome,
                   data_imp, tempo, massa, unidade_massa, filamento_usado, impressora
            FROM pecas WHERE id = %s
        """, (id_peca,))
        item = cursor.fetchone()
        conn.close()
        return item

    def baixar_step_peca(self, id_peca):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT arquivo_bin, arquivo_nome FROM pecas WHERE id = %s", (id_peca,))
        dados = cursor.fetchone()
        conn.close()
        return dados

    def remover_peca(self, id_peca):
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pecas WHERE id = %s", (id_peca,))
        conn.commit()
        conn.close()



    #-------------------MÉTODOS FILAMENTOS---------------------
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




    # ---------------MÉTODOS RESINAS-----------------
    def adicionar_resina(self, marca, material, cor, peso):
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        
        # REMOVIDOS: 'localizacao' e 'preco'
        # Agora só salvamos o que realmente importa
        cursor.execute("""
            INSERT INTO resinas (marca, tipo, cor, volume_ml)
            VALUES (%s, %s, %s, %s)
        """, (marca, material, cor, peso))
        
        conn.commit()
        conn.close()

    def buscar_todas_resinas(self):
        conn = self.conectar()
        cursor = conn.cursor()
        # Garante que estamos pegando ID, Marca, Material, Cor, Volume e Localização
        cursor.execute("SELECT id, marca, material, cor, volume, localizacao FROM resinas ORDER BY id DESC")
        resinas = cursor.fetchall()
        conn.close()
        return resinas

    def buscar_resinas_por_local(self, local):
        # Busca filamentos que estão em uma impressora específica (H2D ou X1C)
        if not self.online: return []
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resinas WHERE localizacao = %s ORDER BY id DESC", (local,))
        items = cursor.fetchall()
        conn.close()
        return items

    def remover_resinas(self, id_item):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resinas WHERE id = %s", (id_item,))
        conn.commit()
        conn.close()

    def atualizar_resina(self, id_item, marca, material, cor, peso):
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE resinas 
            SET marca = %s, material = %s, cor = %s, peso_inicial = %s 
            WHERE id = %s
        """, (marca, material, cor, peso, id_item))
        conn.commit()
        conn.close()

    def mover_resina(self, id_item, nova_localizacao):
        # Move do Estoque para Impressora ou vice-versa
        if not self.online: return
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("UPDATE resinas SET localizacao = %s WHERE id = %s", (nova_localizacao, id_item))
        conn.commit()
        conn.close()

























# -------------------------------------------------------------------------
# --------------- INTERFACE GRÁFICA ---------------------------------------
# -------------------------------------------------------------------------

class App3D(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = BancoDeDados()
        self.title("Mestre Splinter - Sistema de Gestão para MA")
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

        self.botoes_menu["inicio"] = ctk.CTkButton(self.sidebar, text="🏠     Início", command=self.show_inicio, **btn_estilo)
        self.botoes_menu["inicio"].grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.botoes_menu["estoque"] = ctk.CTkButton(self.sidebar, text="📦     Filamentos", command=self.show_estoque, **btn_estilo)
        self.botoes_menu["estoque"].grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.botoes_menu["resinas"] = ctk.CTkButton(self.sidebar, text="🧪     Resinas", command=self.show_resinas, **btn_estilo)
        self.botoes_menu["resinas"].grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.botoes_menu["impressoras"] = ctk.CTkButton(self.sidebar, text="🖨️Impressoras", command=self.show_impressoras, **btn_estilo)
        self.botoes_menu["impressoras"].grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        self.botoes_menu["pecas"] = ctk.CTkButton(self.sidebar, text="🧩     Peças", command=self.show_pecas, **btn_estilo)
        self.botoes_menu["pecas"].grid(row=6, column=0, padx=20, pady=5, sticky="ew")

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
        ctk.CTkLabel(welcome_frame, text="Bem-vindo ao Mestre Splinter", font=("Roboto", 32, "bold")).pack(pady=10)
        ctk.CTkLabel(welcome_frame, text="Gestão Centralizada de Laboratório", font=("Arial", 16)).pack(pady=20)
        ctk.CTkLabel(welcome_frame, text="Aqui vai ter uma introdução do CTMA ou o que quisermos", font=("Arial", 13)).pack(pady=20)

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

        pesos_padrao = ["0.5 kg", "1.0 kg", "1.5 kg", "2.0 kg", "+ Adicionar Novo"]

        self.combo_peso = ctk.CTkOptionMenu(form_frame, width=120, corner_radius=RAIO_CANTO,
                                            values=pesos_padrao,
                                            command=lambda v: self.lidar_com_novo_valor(v, self.combo_peso, "Quantidade (kg)"))
        self.combo_peso.pack(side="left", padx=5)
        self.combo_peso.set("Quantidade (kg)")

        ctk.CTkButton(form_frame, text="+ Adicionar", command=self.salvar_filamento, 
                      fg_color="#2ecc71", hover_color="#27ae60", width=120, corner_radius=RAIO_CANTO).pack(side="left", padx=10)

        # Tabela
        self.lista_frame = ctk.CTkScrollableFrame(self.main_frame, height=450, corner_radius=RAIO_CANTO)
        self.lista_frame.pack(fill="both", expand=True, pady=20)
        self.carregar_lista_estoque()

    def show_resinas(self):
        self.atualizar_destaque_menu("resinas")
        if not self.db.online:
            self.show_offline_mode()
            return
            
        self.limpar_area_principal()
        ctk.CTkLabel(self.main_frame, text="Estoque Resinas", font=("Roboto", 28, "bold")).pack(anchor="w", pady=(0, 20))

        # Formulário
        form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        form_frame.pack(fill="x", pady=10)
        LARGURA_PADRAO, RAIO_CANTO = 180, 10

        # --- CORREÇÃO 1: Referências certas nos comandos lambda ---
        
        self.combo_marca = ctk.CTkOptionMenu(form_frame, width=LARGURA_PADRAO, corner_radius=RAIO_CANTO,
                                            values=sorted(list(set(["3D Lab"] + self.db.buscar_valores_unicos("marca")))) + ["+ Adicionar Novo"],
                                            command=lambda v: self.lidar_com_novo_valor(v, self.combo_marca, "Marca"))
        self.combo_marca.pack(side="left", padx=5)
        self.combo_marca.set("Marca")

        # AQUI ESTAVA O ERRO: self.combo_material -> self.combo_tipo
        self.combo_tipo = ctk.CTkOptionMenu(form_frame, width=LARGURA_PADRAO, corner_radius=RAIO_CANTO,
                                               values=["Standard", "Tough", "+ Adicionar Novo"],
                                               command=lambda v: self.lidar_com_novo_valor(v, self.combo_tipo, "Tipo"))
        self.combo_tipo.pack(side="left", padx=5)
        self.combo_tipo.set("Tipo") # Mudei de "Material" para "Tipo" para ficar visualmente correto

        self.combo_cor = ctk.CTkOptionMenu(form_frame, width=LARGURA_PADRAO, corner_radius=RAIO_CANTO,
                                          values=sorted(list(set(["Preto", "Branco", "Cinza"] + self.db.buscar_valores_unicos("cor")))) + ["+ Adicionar Novo"],
                                          command=lambda v: self.lidar_com_novo_valor(v, self.combo_cor, "Cor"))
        self.combo_cor.pack(side="left", padx=5)
        self.combo_cor.set("Cor")

        volumes_padrao = ["1000 ml", "500 ml", "+ Adicionar Novo"]

        self.combo_volume = ctk.CTkOptionMenu(form_frame, width=120, corner_radius=RAIO_CANTO,
                                            values=volumes_padrao,
                                            command=lambda v: self.lidar_com_novo_valor(v, self.combo_volume, "Volume (ml)"))
        self.combo_volume.pack(side="left", padx=5)
        self.combo_volume.set("Volume (ml)")

        ctk.CTkButton(form_frame, text="+ Adicionar", command=self.salvar_resina, 
                      fg_color="#2ecc71", hover_color="#27ae60", width=120, corner_radius=RAIO_CANTO).pack(side="left", padx=10)

        # Tabela
        self.lista_frame = ctk.CTkScrollableFrame(self.main_frame, height=450, corner_radius=RAIO_CANTO)
        self.lista_frame.pack(fill="both", expand=True, pady=20)
        self.carregar_lista_resinas()

    def carregar_lista_resinas(self):
        # Limpa a lista visual atual
        for widget in self.lista_frame.winfo_children(): widget.destroy()

        # Cabeçalho da Tabela
        h_frame = ctk.CTkFrame(self.lista_frame, fg_color="#1f1f1f", corner_radius=0)
        h_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        # Definição das colunas visuais
        cols = [("ID", 50), ("Marca", 150), ("Tipo", 120), ("Cor", 120), ("Volume", 150)]
        
        for i, (txt, larg) in enumerate(cols):
            ctk.CTkLabel(h_frame, text=txt, font=("Roboto", 12, "bold"), width=larg, anchor="w").grid(row=0, column=i, padx=10, pady=5)

        # Preenchendo os dados
        for idx, item in enumerate(self.db.buscar_todas_resinas()):
            try:
                id_bd, marca, material, cor, peso = item
            except ValueError:
                # Fallback caso o banco tenha colunas extras
                id_bd = item[0]
                marca = item[1]
                material = item[2]
                cor = item[3]
                peso = item[4]

            # Cria a linha visual
            row = ctk.CTkFrame(self.lista_frame, fg_color="#2b2b2b", corner_radius=5)
            row.pack(fill="x", pady=2, padx=5)
            
            # Efeito de hover
            def on_enter(e, r=row): r.configure(fg_color="#383838")
            def on_leave(e, r=row): r.configure(fg_color="#2b2b2b")
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)

            dados_visuais = [id_bd, marca, material, cor, f"{peso} ml"]
            
            for i, valor in enumerate(dados_visuais):
                lbl = ctk.CTkLabel(row, text=str(valor), width=cols[i][1], anchor="w")
                lbl.grid(row=0, column=i, padx=10, pady=8)
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)
            
            # Botão de opções (três pontinhos)
            btn_opcoes = ctk.CTkButton(row, text="⋮", width=30, height=25, fg_color="transparent", 
                                       hover_color="#444444", font=("Roboto", 18, "bold"),
                                       command=lambda i=id_bd: self.abrir_menu_opcoes(i))
            
            # AQUI ESTÁ A CORREÇÃO:
            # 1. Colocamos sticky="e" (east/direita)
            btn_opcoes.grid(row=0, column=5, padx=10, sticky="e")
            
            # 2. Configuramos a coluna 5 para ter peso 1, empurrando o conteúdo para a borda
            row.grid_columnconfigure(5, weight=1)

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

            dados = [id_bd, marca, material, cor, f"{peso}kg"]
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

    # --- TELA DAS IMPRESSORAS (ATUALIZADA) ---
    def show_impressoras(self):
        self.atualizar_destaque_menu("impressoras")
        self.limpar_area_principal()
        
        ctk.CTkLabel(self.main_frame, text="Selecione a Impressora", font=("Roboto", 28, "bold")).pack(anchor="w", pady=(0, 30))

        # Frame Container para os dois "Quadradões"
        grid_impressoras = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        grid_impressoras.pack(fill="both", expand=True)

        # Criação dos Cards (Função auxiliar abaixo)
        self.criar_card_impressora(grid_impressoras, "H2D", "H2D.webp", "H2D", 0)
        self.criar_card_impressora(grid_impressoras, "X1 Carbon", "x1-carbon.webp", "X1C", 1)
        self.criar_card_impressora(grid_impressoras, "Form 4L", "form4L.webp", "4L", 2)

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

        # Funções de efeito visual
        def on_enter(e): 
            card.configure(border_color="#2ecc71", fg_color="#333333")
        def on_leave(e): 
            card.configure(border_color="#333333", fg_color="#2b2b2b")

        # Aplica o bind no CARD (o frame principal)
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        # Aplica o MESMO bind no LABEL da imagem e no LABEL do texto
        # Isso garante que o card mude de cor mesmo se o mouse estiver sobre a foto
        img_label.bind("<Enter>", on_enter)
        img_label.bind("<Leave>", on_leave)

    #--------PEÇAS------------
    def show_pecas(self):
        self.atualizar_destaque_menu("pecas")
        self.limpar_area_principal()

        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="Gestão de Solicitações", font=("Roboto", 28, "bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Nova Solicitação", command=self.abrir_nova_solicitacao, fg_color="#3498db").pack(side="right")

        self.tab_pecas = ctk.CTkTabview(self.main_frame, anchor="nw")
        self.tab_pecas.pack(fill="both", expand=True)
        
        self.tab_pecas.add("Solicitações Pendentes")
        self.tab_pecas.add("Histórico / Impressas")

        self.setup_tabela(self.tab_pecas.tab("Solicitações Pendentes"), "PENDENTE")
        self.setup_tabela(self.tab_pecas.tab("Histórico / Impressas"), "CONCLUIDO")

    def setup_tabela(self, parent, status_filtro):
        # 1. Definição das Colunas baseada no status
        if status_filtro == "PENDENTE":
            cols = [("ID", 40), ("Data Sol.", 90), ("Título", 200), ("Solicitante", 100), ("Dimensões", 120), ("Qualidade", 80)]
        else:
            # Colunas para Concluídas
            cols = [("ID", 40), ("Data Imp.", 90), ("Título", 200), ("Solicitante", 100), ("Impressora", 100), ("Tempo", 80)]

        # Cria o Header
        h_frame = ctk.CTkFrame(parent, fg_color="#1f1f1f", corner_radius=0)
        h_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        for i, (txt, larg) in enumerate(cols):
            ctk.CTkLabel(h_frame, text=txt, font=("Roboto", 12, "bold"), width=larg, anchor="w").grid(row=0, column=i, padx=10, pady=5)

        # Container com rolagem
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        items = self.db.buscar_pecas_por_status(status_filtro)
        if not items:
            ctk.CTkLabel(scroll_frame, text="Nenhum registro encontrado.", text_color="gray").pack(pady=20)
            return

        for item in items:
            # Desempacota os 11 campos retornados pelo SELECT do buscar_pecas_por_status
            # Ordem: id, titulo, sol_sigla, centro, data_sol, is_ctma, arquivo_nome, dimensoes, complexidade, impressora, data_imp
            id_bd, titulo, sol_sigla, centro, data_sol, is_ctma, arq_nome, dim, compl, imp_usada, data_imp = item

            # Prepara os dados visuais dependendo da aba
            if status_filtro == "PENDENTE":
                solicitante_txt = "CTMA" if is_ctma else sol_sigla
                qualidade_txt = "⭐" * compl if compl else "-"
                dados_visuais = [id_bd, data_sol, titulo, solicitante_txt, dim, qualidade_txt]
            else:
                # Dados para Concluídas
                solicitante_txt = "CTMA" if is_ctma else sol_sigla
                data_show = data_imp if data_imp else "-"
                dados_visuais = [id_bd, data_show, titulo, solicitante_txt, imp_usada, "-"] # O tempo não vem na query padrão, deixei "-" ou você pode ajustar a query

            # --- CRIAÇÃO DA LINHA ---
            row = ctk.CTkFrame(scroll_frame, fg_color="#2b2b2b", corner_radius=5)
            row.pack(fill="x", pady=2, padx=5)

            # --- EFEITO HOVER (AQUI ESTÁ A MÁGICA) ---
            def on_enter(e, r=row): r.configure(fg_color="#383838")
            def on_leave(e, r=row): r.configure(fg_color="#2b2b2b")
            
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)

            for i, valor in enumerate(dados_visuais):
                lbl = ctk.CTkLabel(row, text=str(valor)[:30], width=cols[i][1], anchor="w")
                lbl.grid(row=0, column=i, padx=10, pady=8)
                # IMPORTANTE: Bindar o label também, senão o hover falha ao passar o mouse em cima do texto
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)

            # Botão de Menu (3 pontinhos)
            btn_opcoes = ctk.CTkButton(row, text="⋮", width=30, height=25, fg_color="transparent", 
                                       hover_color="#444444", font=("Roboto", 18, "bold"),
                                       command=lambda e=None, i=id_bd, t=titulo, s=status_filtro: self.abrir_menu_contexto(self.winfo_pointerxy(), i, t, s)) 
            # Nota: usei self.winfo_pointerxy para simular o event se necessário, mas seu método abrir_menu_contexto original pede 'event'.
            # Ajuste do command para passar o evento corretamente é chatinho em loops. 
            # Sugiro usar bind no botão se preferir, mas lambda com event capture funciona assim:
            
            # (Melhor abordagem para o botão):
            btn_opcoes = ctk.CTkLabel(row, text="⋮", width=30, font=("Roboto", 18, "bold")) # Label fingindo ser botão fica mais facil alinhar hover
            btn_opcoes.grid(row=0, column=len(cols), padx=10, sticky="e")
            btn_opcoes.bind("<Enter>", lambda e: [on_enter(e), btn_opcoes.configure(text_color="white")])
            btn_opcoes.bind("<Leave>", lambda e: [on_leave(e), btn_opcoes.configure(text_color="gray")])
            btn_opcoes.bind("<Button-1>", lambda e, i=id_bd, t=titulo, s=status_filtro: self.abrir_menu_contexto(e, i, t, s))
            
            row.grid_columnconfigure(len(cols), weight=1)

    def abrir_menu_contexto(self, event, id_peca, titulo, status):
        # 1. Definimos as dimensões do menu aqui para usar nos cálculos
        largura_menu = 160
        altura_menu = 140
        
        # 2. Obtém as dimensões da tela do monitor
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 3. Pega a posição absoluta do clique do mouse
        x = event.x_root
        y = event.y_root
        
        # 4. LÓGICA DE CORREÇÃO:
        # Se a posição do mouse + largura do menu for maior que a tela,
        # movemos a coordenada X para a esquerda (subtraindo a largura do menu).
        if x + largura_menu > screen_width:
            x = x - largura_menu
            
        # (Opcional) O mesmo ajuste para a altura, caso clique muito embaixo
        if y + altura_menu > screen_height:
            y = y - altura_menu

        # Cria uma janela pequena sem bordas na posição AJUSTADA (x, y)
        menu = ctk.CTkToplevel(self)
        menu.geometry(f"{largura_menu}x{altura_menu}+{x}+{y}")
        menu.overrideredirect(True) # Remove a barra de título do Windows
        menu.attributes("-topmost", True)

        # Frame de fundo
        bg = ctk.CTkFrame(menu, fg_color="#222222", border_width=1, border_color="#555")
        bg.pack(fill="both", expand=True)

        def fechar_menu():
            menu.destroy()

        # --- OPÇÕES DO MENU (Mantidas do seu código original) ---
        
        # Opção 1: Concluir (Aparece apenas se estiver PENDENTE)
        if status == "PENDENTE":
            btn_ok = ctk.CTkButton(bg, text="✅ Concluir", fg_color="transparent", anchor="w", hover_color="#333", 
                                   command=lambda: [fechar_menu(), self.abrir_conclusao_peca(id_peca, titulo)])
            btn_ok.pack(fill="x", padx=2, pady=2)

        # Opção 2: Detalhes
        btn_info = ctk.CTkButton(bg, text="ℹ️ Detalhes", fg_color="transparent", anchor="w", hover_color="#333", 
                                 command=lambda: [fechar_menu(), self.ver_detalhes_peca(id_peca)])
        btn_info.pack(fill="x", padx=2, pady=2)

        # Opção 3: Excluir
        btn_del = ctk.CTkButton(bg, text="🗑️ Excluir", fg_color="transparent", anchor="w", hover_color="#333", text_color="#e74c3c", 
                                command=lambda: [fechar_menu(), self.confirmar_exclusao(id_peca)])
        btn_del.pack(fill="x", padx=2, pady=2)

        # Fecha se perder o foco (clicar fora)
        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_force()

    def abrir_nova_solicitacao(self):
        win = ctk.CTkToplevel(self)
        win.title("Nova Solicitação")
        win.geometry("550x700")
        win.attributes("-topmost", True)
        
        self.step_bytes = None
        self.step_nome = None

        ctk.CTkLabel(win, text="O que você precisa imprimir?", font=("Roboto", 16, "bold")).pack(pady=(15, 5))
        entry_titulo = ctk.CTkEntry(win, placeholder_text="Nome da Peça / Título", width=400)
        entry_titulo.pack(pady=5)

        # --- ARQUIVO ---
        def selecionar_step():
            caminho = filedialog.askopenfilename(filetypes=[("Arquivo STEP", "*.step;*.stp")])
            if caminho:
                with open(caminho, "rb") as f:
                    self.step_bytes = f.read()
                    self.step_nome = os.path.basename(caminho)
                    btn_step.configure(text=f"📎 {self.step_nome}", fg_color="#8e44ad")

        btn_step = ctk.CTkButton(win, text="Anexar Arquivo (.STEP)", command=selecionar_step, fg_color="#34495e", width=400)
        btn_step.pack(pady=5)

        # --- ESPECIFICAÇÕES (AJUSTE 2: DIMENSÕES DIVIDIDAS) ---
        frame_specs = ctk.CTkFrame(win, fg_color="transparent")
        frame_specs.pack(pady=15)

        ctk.CTkLabel(frame_specs, text="Dimensões Máximas (mm):", font=("Roboto", 12)).grid(row=0, column=0, sticky="w", padx=10)
        
        # Frame interno para os 3 campos XYZ
        frame_xyz = ctk.CTkFrame(frame_specs, fg_color="transparent")
        frame_xyz.grid(row=1, column=0, padx=10, pady=5)
        
        entry_x = ctk.CTkEntry(frame_xyz, width=50, placeholder_text="X")
        entry_x.pack(side="left", padx=2)
        ctk.CTkLabel(frame_xyz, text="x").pack(side="left")
        entry_y = ctk.CTkEntry(frame_xyz, width=50, placeholder_text="Y")
        entry_y.pack(side="left", padx=2)
        ctk.CTkLabel(frame_xyz, text="x").pack(side="left")
        entry_z = ctk.CTkEntry(frame_xyz, width=50, placeholder_text="Z")
        entry_z.pack(side="left", padx=2)

        ctk.CTkLabel(frame_specs, text="Nível de Qualidade:", font=("Roboto", 12)).grid(row=0, column=1, sticky="w", padx=10)
        seg_complexidade = ctk.CTkSegmentedButton(frame_specs, values=["1 (Baixa)", "2 (Média)", "3 (Alta)"], width=200)
        seg_complexidade.grid(row=1, column=1, padx=10, pady=5)
        seg_complexidade.set("2 (Média)")

        # --- SOLICITANTE (AJUSTE 1: CAPS LOCK NA SIGLA) ---
        ctk.CTkLabel(win, text="Quem está solicitando?", font=("Roboto", 14, "bold")).pack(pady=(20, 5))

        def toggle_solicitante():
            if check_ctma.get() == 1:
                frame_sol_campos.pack_forget()
            else:
                frame_sol_campos.pack(pady=5, after=check_ctma)

        check_ctma = ctk.CTkCheckBox(win, text="Projeto CTMA", command=toggle_solicitante, font=("Roboto", 12, "bold"))
        check_ctma.pack(pady=5)

        frame_sol_campos = ctk.CTkFrame(win, fg_color="transparent")
        frame_sol_campos.pack(pady=5)

        # Variável monitorada para forçar maiúsculas
        sigla_var = ctk.StringVar()
        def forcar_caps(*args):
            sigla_var.set(sigla_var.get().upper())
        sigla_var.trace("w", forcar_caps)

        entry_sigla = ctk.CTkEntry(frame_sol_campos, placeholder_text="SIGLA", width=70, textvariable=sigla_var)
        entry_sigla.pack(side="left", padx=5)

        entry_nome = ctk.CTkEntry(frame_sol_campos, placeholder_text="Nome Completo", width=200)
        entry_nome.pack(side="left", padx=5)
        
        combo_centro = ctk.CTkOptionMenu(frame_sol_campos, values=["CMI", "CDM", "CPC", "CEI", "CEV", "CES"], width=80)
        combo_centro.pack(side="left", padx=5)

        # --- OBS ---
        ctk.CTkLabel(win, text="Observações:", font=("Roboto", 12)).pack(anchor="w", padx=75, pady=(10,0))
        textbox_obs = ctk.CTkTextbox(win, width=400, height=80)
        textbox_obs.pack(pady=5)

        def confirmar_envio():
            if not entry_titulo.get():
                return messagebox.showwarning("Faltam dados", "Título é obrigatório!")

            # Monta a string de dimensões baseada nos 3 campos
            dim_str = f"{entry_x.get()}x{entry_y.get()}x{entry_z.get()}mm"
            if dim_str == "xxmm": dim_str = "" # Se vazio

            comp_str = seg_complexidade.get()
            comp_int = 1 if "Baixa" in comp_str else (3 if "Alta" in comp_str else 2)

            is_ctma = bool(check_ctma.get())
            
            self.db.criar_solicitacao(
                entry_titulo.get(),
                datetime.date.today(),
                "CTMA" if is_ctma else sigla_var.get(), # Pega da variavel controlada
                "" if is_ctma else entry_nome.get(),
                "-" if is_ctma else combo_centro.get(),
                is_ctma,
                dim_str,
                comp_int,
                textbox_obs.get("1.0", "end"),
                self.step_bytes,
                self.step_nome
            )
            win.destroy()
            self.show_pecas()
            messagebox.showinfo("Enviado", "Solicitação Registrada!")

        ctk.CTkButton(win, text="ENVIAR SOLICITAÇÃO", fg_color="#2ecc71", width=200, height=40, command=confirmar_envio).pack(pady=20)

    def abrir_conclusao_peca(self, id_peca, titulo):
        win = ctk.CTkToplevel(self)
        win.title(f"Concluir: {titulo}")
        win.geometry("400x450")
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="Registro de Impressão", font=("Roboto", 16, "bold")).pack(pady=20)

        ctk.CTkLabel(win, text="Impressora Utilizada:").pack()
        combo_imp = ctk.CTkOptionMenu(win, values=["X1 Carbon", "H2D", "Form 4L", "Outra"])
        combo_imp.pack(pady=5)

        ctk.CTkLabel(win, text="Material Utilizado:").pack()
        
        # --- CORREÇÃO AQUI (Carregamento seguro) ---
        lista_opcoes = []
        try:
            # Filamentos: id=0, marca=1, material=2, cor=3...
            raw_fil = self.db.buscar_todos_filamentos()
            lista_opcoes += [f"{i[1]} {i[2]} {i[3]}" for i in raw_fil] # Acessa por índice para evitar erro
            
            # Resinas: id=0, marca=1, tipo=2, cor=3...
            raw_res = self.db.buscar_todas_resinas()
            lista_opcoes += [f"{i[1]} {i[2]} {i[3]}" for i in raw_res]
        except Exception as e:
            print(f"Erro ao carregar materiais: {e}")
        
        lista_opcoes.append("Outro")
        
        combo_mat = ctk.CTkComboBox(win, values=lista_opcoes, width=250)
        combo_mat.pack(pady=5)
        # -------------------------------------------

        frame_dados = ctk.CTkFrame(win, fg_color="transparent")
        frame_dados.pack(pady=15)
        
        entry_tempo = ctk.CTkEntry(frame_dados, placeholder_text="Tempo (ex: 2h30)", width=120)
        entry_tempo.pack(side="left", padx=5)
        
        entry_massa = ctk.CTkEntry(frame_dados, placeholder_text="Qtd", width=80)
        entry_massa.pack(side="left", padx=5)
        
        seg_unidade = ctk.CTkSegmentedButton(frame_dados, values=["g", "ml"])
        seg_unidade.pack(side="left", padx=5)
        seg_unidade.set("g")

        def salvar_conclusao():
            try:
                massa = float(entry_massa.get().replace(",", ".")) if entry_massa.get() else 0.0
                self.db.concluir_peca(
                    id_peca,
                    datetime.date.today(),
                    combo_imp.get(),
                    combo_mat.get(),
                    entry_tempo.get(),
                    massa,
                    seg_unidade.get()
                )
                win.destroy()
                self.show_pecas()
                messagebox.showinfo("Sucesso", "Peça marcada como concluída!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar: {e}")

        ctk.CTkButton(win, text="CONFIRMAR IMPRESSÃO", fg_color="#27ae60", command=salvar_conclusao).pack(pady=30)

    def setup_aba_pendentes(self, parent):
        # Cabeçalho da Tabela
        cols_config = [
            ("ID", 40), ("Data Sol.", 90), ("Título", 200), ("Solicitante", 100), 
            ("Dimensões", 120), ("Qualidade", 80), ("Ações", 100)
        ]
        
        header_frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", height=35)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        for nome, largura in cols_config:
            ctk.CTkLabel(header_frame, text=nome, width=largura, font=("Roboto", 12, "bold"), anchor="w").pack(side="left", padx=5)

        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        items = self.db.buscar_pecas_por_status("PENDENTE")
        if not items: ctk.CTkLabel(scroll_frame, text="Nenhuma solicitação pendente.", text_color="gray").pack(pady=20)

        for item in items:
            # Desempacota (baseado na query do buscar_pecas_por_status)
            id_bd, titulo, sol_sigla, centro, data_sol, is_ctma, arq_nome, dim, compl, _, _ = item
            
            row = ctk.CTkFrame(scroll_frame, fg_color="#2b2b2b", height=40)
            row.pack(fill="x", pady=2, padx=5)

            def on_enter(e, r=row): r.configure(fg_color="#383838")
            def on_leave(e, r=row): r.configure(fg_color="#2b2b2b")
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)

            dados = [id_bd, titulo, sol_sigla, centro, data_sol, is_ctma, arq_nome, dim, compl]
            for i, valor in enumerate(dados):
                lbl = ctk.CTkLabel(row, text=valor, width=cols[i][1], anchor="w")
                lbl.grid(row=0, column=i, padx=10, pady=8)
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)

            texto_sol = "CTMA" if is_ctma else sol_sigla
            cor_sol = "#2ecc71" if is_ctma else "white"
            
            ctk.CTkLabel(row, text=str(id_bd), width=40, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(data_sol), width=90, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=titulo[:25], width=200, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=texto_sol, width=100, anchor="w", text_color=cor_sol, font=("Roboto",12,"bold" if is_ctma else "normal")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=dim if dim else "-", width=120, anchor="w").pack(side="left", padx=5)
            
            # Qualidade visual (Estrelas ou Número)
            str_qualidade = "⭐"*compl if compl else "-"
            ctk.CTkLabel(row, text=str_qualidade, width=80, anchor="w", text_color="#f1c40f").pack(side="left", padx=5)

            btn_opcoes = ctk.CTkButton(row, text="⋮", width=30, height=25, fg_color="transparent", 
                                       hover_color="#444444", font=("Roboto", 18, "bold"),
                                       command=lambda i=id_bd: self.abrir_menu_pecas(i))
            btn_opcoes.grid(row=0, column=5, padx=10, sticky="e")
            row.grid_columnconfigure(5, weight=1)

            # 1. Botão Check (Finalizar)
            ctk.CTkButton(btn_box, text="✅", width=35, fg_color="#27ae60", hover_color="#2ecc71",
                          command=lambda i=id_bd, t=titulo: self.abrir_conclusao_peca(i, t)).pack(side="left", padx=2)
            
            # 2. Botão Info (Detalhes)
            ctk.CTkButton(btn_box, text="ℹ️", width=35, fg_color="#34495e", 
                          command=lambda i=id_bd: self.ver_detalhes_peca(i)).pack(side="left", padx=2)
            
            # 3. Botão Excluir (Pequeno)
            ctk.CTkButton(btn_box, text="🗑️", width=35, fg_color="transparent", text_color="#e74c3c", hover_color="#333333",
                          command=lambda i=id_bd: self.confirmar_exclusao(i)).pack(side="left", padx=2)

    def setup_aba_concluidas(self, parent):
        cols_config = [
            ("ID", 40), ("Data Imp.", 90), ("Título", 200), ("Solicitante", 100), 
            ("Impressora", 100), ("Ações", 50)
        ]
        
        header_frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", height=35)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        for nome, largura in cols_config:
            ctk.CTkLabel(header_frame, text=nome, width=largura, font=("Roboto", 12, "bold"), anchor="w").pack(side="left", padx=5)

        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        items = self.db.buscar_pecas_por_status("CONCLUIDO")
        if not items: ctk.CTkLabel(scroll_frame, text="Nenhum registro histórico.", text_color="gray").pack(pady=20)

        for item in items:
            id_bd, titulo, sol_sigla, centro, data_sol, is_ctma, arq_nome, dim, compl, impressora, data_imp = item
            
            row = ctk.CTkFrame(scroll_frame, fg_color="#2b2b2b", height=40)
            row.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(row, text=str(id_bd), width=40, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(data_imp), width=90, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=titulo[:25], width=200, anchor="w").pack(side="left", padx=5)
            
            texto_sol = "CTMA" if is_ctma else sol_sigla
            cor_sol = "#2ecc71" if is_ctma else "white"
            ctk.CTkLabel(row, text=texto_sol, width=100, anchor="w", text_color=cor_sol).pack(side="left", padx=5)
            
            ctk.CTkLabel(row, text=impressora, width=100, anchor="w").pack(side="left", padx=5)

            ctk.CTkButton(row, text="ℹ️", width=35, fg_color="transparent", hover_color="#444444",
                          command=lambda i=id_bd: self.ver_detalhes_peca(i)).pack(side="right", padx=10)


    

    def confirmar_exclusao(self, id_peca):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este registro?\nEssa ação não pode ser desfeita."):
            self.db.remover_peca(id_peca)
            self.show_pecas()
            messagebox.showinfo("Sucesso", "Registro removido.")

    # Função auxiliar para baixar o arquivo vindo do botão da tabela
    def baixar_step(self, id_peca, nome_padrao):
        dados = self.db.baixar_step_peca(id_peca)
        if dados and dados[0]: # Se tem bytes
            arquivo_bin = dados[0]
            caminho = filedialog.asksaveasfilename(initialfile=nome_padrao, defaultextension=".step")
            if caminho:
                with open(caminho, "wb") as f:
                    f.write(arquivo_bin)
                messagebox.showinfo("Sucesso", "Arquivo salvo!")
        else:
            messagebox.showerror("Erro", "Arquivo não encontrado no banco.")


    
    def abrir_registro_peca(self):
        win = ctk.CTkToplevel(self)
        win.title("Registrar Peça / Solicitação")
        win.geometry("600x750")
        win.attributes("-topmost", True)
        
        self.step_bytes = None
        self.step_nome = None

        # --- SEÇÃO 1: DADOS DA PEÇA ---
        ctk.CTkLabel(win, text="Dados da Peça", font=("Roboto", 14, "bold")).pack(pady=(15, 5))
        
        entry_titulo = ctk.CTkEntry(win, placeholder_text="Título da Peça", width=400)
        entry_titulo.pack(pady=5)

        # Linha: Impressora e Filamento
        frame_tec = ctk.CTkFrame(win, fg_color="transparent")
        frame_tec.pack(pady=5)
        
        combo_impressora = ctk.CTkOptionMenu(frame_tec, values=["X1 Carbon", "H2D", "Form 4L", "Outra"], width=140)
        combo_impressora.pack(side="left", padx=5)
        
        # Carrega filamentos para o combo
        lista_fil = [f"{m} {mat}" for _, m, mat, _, _, _, _ in self.db.buscar_todos_filamentos()]
        if not lista_fil: lista_fil = ["Genérico"]
        combo_filamento = ctk.CTkComboBox(frame_tec, values=lista_fil, width=250)
        combo_filamento.pack(side="left", padx=5)

        # Linha: Tempo e Massa
        frame_medidas = ctk.CTkFrame(win, fg_color="transparent")
        frame_medidas.pack(pady=5)
        
        entry_tempo = ctk.CTkEntry(frame_medidas, placeholder_text="Tempo (ex: 2h)", width=120)
        entry_tempo.pack(side="left", padx=5)
        
        entry_massa = ctk.CTkEntry(frame_medidas, placeholder_text="Qtd Material", width=120)
        entry_massa.pack(side="left", padx=5)
        
        seg_unidade = ctk.CTkSegmentedButton(frame_medidas, values=["g", "ml"], width=80)
        seg_unidade.pack(side="left", padx=5)
        seg_unidade.set("g")

        # --- SEÇÃO 2: SOLICITANTE (REFORMULADA) ---
        ctk.CTkLabel(win, text="Solicitante", font=("Roboto", 14, "bold")).pack(pady=(20, 5))
        
        # 1. Checkbox agora fica no topo dessa seção
        # Função para esconder/mostrar campos
        def toggle_solicitante():
            if check_ctma.get() == 1:
                self.frame_campos_sol.pack_forget()
            else:
                # O segredo está aqui: dizemos para o frame voltar 
                # exatamente para depois do checkbox, mantendo a ordem original
                self.frame_campos_sol.pack(pady=5, after=check_ctma)

        check_ctma = ctk.CTkCheckBox(win, text="Destinado ao Projeto CTMA", command=toggle_solicitante, font=("Roboto", 12, "bold"))
        check_ctma.pack(pady=5)

        # 2. Frame container para os campos que vão sumir
        self.frame_campos_sol = ctk.CTkFrame(win, fg_color="transparent")
        self.frame_campos_sol.pack(pady=5)

        # 1. Crie o entry normalmente (sem a var_sigla por enquanto)
        entry_sol_sigla = ctk.CTkEntry(self.frame_campos_sol, 
                                       placeholder_text="Sigla", 
                                       width=100)
        entry_sol_sigla.pack(side="left", padx=5)

        # 2. Função interna para forçar o Caps
        def forcar_caps(event):
            conteudo = entry_sol_sigla.get()
            entry_sol_sigla.delete(0, "end")
            entry_sol_sigla.insert(0, conteudo.upper())

        # 3. Faz o bind: toda vez que soltar uma tecla, ele roda a função
        entry_sol_sigla.bind("<KeyRelease>", forcar_caps)
        
        entry_sol_nome = ctk.CTkEntry(self.frame_campos_sol, placeholder_text="Nome do Solicitante", width=200)
        entry_sol_nome.pack(side="left", padx=5)
        
        combo_centro = ctk.CTkOptionMenu(self.frame_campos_sol, values=["CMI", "CDM", "CPC", "CEI", "CEV", "CES"], width=100)
        combo_centro.pack(side="left", padx=5)
        
        # --- SEÇÃO 3: ARQUIVO E OBS ---
        ctk.CTkLabel(win, text="Arquivo e Observações", font=("Roboto", 14, "bold")).pack(pady=(20, 5))
        
        def selecionar_step():
            caminho = filedialog.askopenfilename(filetypes=[("Arquivo STEP", "*.step;*.stp")])
            if caminho:
                with open(caminho, "rb") as f:
                    self.step_bytes = f.read()
                    import os
                    self.step_nome = os.path.basename(caminho)
                    btn_step.configure(text=f"📎 {self.step_nome}", fg_color="#8e44ad")

        btn_step = ctk.CTkButton(win, text="Anexar .STEP", command=selecionar_step, fg_color="#34495e")
        btn_step.pack(pady=5)

        textbox_obs = ctk.CTkTextbox(win, width=400, height=60)
        textbox_obs.pack(pady=5)
        textbox_obs.insert("1.0", "Obs:")
        
        def salvar():
            try:
                import datetime
                if not entry_titulo.get(): return messagebox.showwarning("Erro", "Título obrigatório")
                
                massa = float(entry_massa.get()) if entry_massa.get() else 0.0
                
                # LÓGICA INTELIGENTE DO SOLICITANTE
                is_ctma_checked = bool(check_ctma.get())
                
                if is_ctma_checked:
                    # Se for CTMA, preenchemos automático
                    val_sigla = "CTMA"
                    val_nome = ""
                    val_centro = "-"
                else:
                    # Se não, pega o que o usuário digitou
                    val_sigla = entry_sol_sigla.get()
                    val_nome = entry_sol_nome.get()
                    val_centro = combo_centro.get()

                self.db.adicionar_peca(
                    entry_titulo.get(),
                    datetime.date.today(),
                    entry_tempo.get(),
                    massa,
                    seg_unidade.get(),
                    combo_filamento.get(),
                    combo_impressora.get(),
                    val_sigla,  # <--- Valor decidido acima
                    val_nome,   # <--- Valor decidido acima
                    val_centro, # <--- Valor decidido acima
                    is_ctma_checked,
                    textbox_obs.get("1.0", "end"),
                    self.step_bytes,
                    self.step_nome
                )
                win.destroy()
                self.show_pecas()
                messagebox.showinfo("Sucesso", "Registrado!")
            except Exception as e:
                messagebox.showerror("Erro", str(e))

        ctk.CTkButton(win, text="SALVAR REGISTRO", command=salvar, fg_color="#27ae60", width=200, height=40).pack(pady=10)
        
        
    def ver_detalhes_peca(self, id_peca):
        try:
            item = self.db.buscar_detalhes_peca(id_peca)
            if not item: 
                messagebox.showerror("Erro", "Peça não encontrada no banco de dados.")
                return

            # Desempacota com segurança
            (id_bd, titulo, data_sol, status, sol_sigla, sol_nome, centro, is_ctma,
             dim, compl, obs, arq_nome, data_imp, tempo, massa, un_massa, filamento, impressora) = item

            win = ctk.CTkToplevel(self)
            win.title(f"Detalhes #{id_bd}")
            win.geometry("500x650")
            win.attributes("-topmost", True)

            cor_status = "#e67e22" if status == "PENDENTE" else "#27ae60"
            ctk.CTkLabel(win, text=f"STATUS: {status}", font=("Roboto", 14, "bold"), text_color=cor_status).pack(pady=10)

            ctk.CTkLabel(win, text=titulo, font=("Roboto", 22, "bold")).pack()
            
            box_sol = ctk.CTkFrame(win, fg_color="#333333")
            box_sol.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(box_sol, text="📄 Dados da Solicitação", font=("Roboto", 12, "bold"), text_color="#aaa").pack(anchor="w", padx=10, pady=5)
            
            txt_sol = f"Solicitante: {sol_nome} ({sol_sigla})\nCentro: {centro}\nData Pedido: {data_sol}\n"
            txt_sol += f"Dimensões: {dim}\nNível de Qualidade: {compl}"
            if is_ctma: txt_sol = f"PROJETO CTMA\nData Pedido: {data_sol}\nDimensões: {dim}\nQualidade: {compl}/3"
            
            ctk.CTkLabel(box_sol, text=txt_sol, justify="left", anchor="w").pack(fill="x", padx=10, pady=(0, 10))

            if status == "CONCLUIDO":
                box_exe = ctk.CTkFrame(win, fg_color="#2c3e50")
                box_exe.pack(fill="x", padx=20, pady=10)
                ctk.CTkLabel(box_exe, text="⚙️ Dados da Execução", font=("Roboto", 12, "bold"), text_color="#aaa").pack(anchor="w", padx=10, pady=5)
                
                txt_exe = f"Impresso em: {data_imp}\nMáquina: {impressora}\nMaterial: {filamento}\nConsumo: {massa}{un_massa} ({tempo})"
                ctk.CTkLabel(box_exe, text=txt_exe, justify="left", anchor="w").pack(fill="x", padx=10, pady=(0, 10))

            ctk.CTkLabel(win, text="Observações:", font=("Roboto", 12, "bold")).pack(anchor="w", padx=25)
            t_obs = ctk.CTkTextbox(win, height=60, fg_color="#222")
            t_obs.pack(fill="x", padx=20, pady=5)
            t_obs.insert("1.0", obs if obs else "")
            t_obs.configure(state="disabled")

            if arq_nome:
                ctk.CTkButton(win, text=f"📥 Baixar {arq_nome}", command=lambda: self.baixar_step(id_bd, arq_nome)).pack(pady=20)
            else:
                ctk.CTkLabel(win, text="Sem anexo.", text_color="gray").pack(pady=10)
                
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir os detalhes.\nErro técnico: {e}")


    def show_detalhes_impressora(self, codigo_interno, nome_exibicao):
        self.limpar_area_principal()
        
        # Header
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkButton(header, text="⬅ Voltar", width=80, fg_color="#444444", 
                      command=self.show_impressoras).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(header, text=f"Gerenciamento: {nome_exibicao}", font=("Roboto", 26, "bold")).pack(side="left")

        # Define se é Resina ou Filamento baseado no código
        eh_resina = (codigo_interno == "4L") or (codigo_interno == "Form 4L")

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
        elif codigo_interno == "X1 Carbon":
            specs = [
                "Tecnologia: FDM (Fused Deposition Modeling)",
                "Volume de Impressão: 256 x 256 x 256 mm",
                "Velocidade Máxima: 500 mm/s",
                "Aceleração: 20,000 mm/s²",
                "Bico: 0.4 mm Hardened Steel (até 300°C)",
                "Sensor: Lidar com resolução de mícrons",
                "Câmera: Integrada 1080p para monitoramento e Timelapse"
            ]
        else: #Form 4L
            specs = [
                "Tecnologia: Low Force Display™ (LFD / MSLA)",
                "Volume de Impressão: 353 x 196 x 350 mm",
                "Velocidade: Até 80 mm/h",
                "Resolução XY: 46 microns (com suavização de bordas)",
                "Fonte de Luz: LPU 4 (LCD de alta potência 160mW/cm²)",
                "Sensores: 30+ sensores inteligentes (força, nível de resina, temperatura)",
                "Ecossistema: Troca automática de resina e calibração inteligente"
            ]

        for s in specs:
            ctk.CTkLabel(specs_frame, text=s, font=("Roboto", 13), text_color="#dddddd").pack(anchor="w", padx=25, pady=1)

        # --- ÁREA DE MATERIAIS (AMS ou Cartuchos) ---
        self.frame_alocados = ctk.CTkFrame(self.main_frame, fg_color="#242424", corner_radius=10)
        self.frame_alocados.pack(fill="x", pady=10)
        
        titulo_box = "Cartuchos / Tanque" if eh_resina else "AMS / Filamentos"
        ctk.CTkLabel(self.frame_alocados, text=f"MATERIAIS ALOCADOS ({titulo_box}):", 
                     font=("Roboto", 12, "bold"), text_color="#3498db").pack(anchor="w", padx=15, pady=(10, 5))

        # Chama a função que desenha os slots (Nova função abaixo)
        self.carregar_materiais_alocados(codigo_interno, eh_resina)


    def carregar_materiais_alocados(self, codigo_impressora, eh_resina):
        # Limpa slots anteriores
        for widget in self.frame_alocados.winfo_children():
            if isinstance(widget, ctk.CTkFrame): widget.destroy()

        # Define capacidade e função de busca
        if eh_resina:
            num_slots = 2
            materiais_alocados = self.db.buscar_resinas_por_local(codigo_impressora)
            funcao_remover = self.db.mover_resina
            unidade = "ml"
        else:
            num_slots = 4
            materiais_alocados = self.db.buscar_filamentos_por_local(codigo_impressora)
            funcao_remover = self.db.mover_filamento
            unidade = "g"

        # Cria os Slots (Vazios ou Ocupados)
        for i in range(num_slots):
            row = ctk.CTkFrame(self.frame_alocados, fg_color="#2b2b2b", corner_radius=5)
            row.pack(fill="x", pady=2, padx=15)
            
            lbl_slot = ctk.CTkLabel(row, text=f"SLOT {i+1}", font=("Roboto", 11, "bold"), text_color="#3498db", width=60)
            lbl_slot.pack(side="left", padx=10)

            # Verifica se tem material neste slot (lógica simples: pega sequencialmente)
            # Obs: Para um sistema real de slots fixos, você precisaria salvar o número do slot no banco.
            # Aqui vou assumir que preenche na ordem.
            if i < len(materiais_alocados):
                item = materiais_alocados[i]
                # item estrutura: (id, marca, tipo/mat, cor, peso/vol, ...)
                # Filamento e Resina tem estruturas parecidas no inicio da tupla
                id_bd = item[0]
                marca = item[1]
                mat_tipo = item[2]
                cor = item[3]
                qtd = item[4]
                
                texto = f"{marca} {mat_tipo} - {cor} ({qtd} {unidade})"
                ctk.CTkLabel(row, text=texto, font=("Roboto", 14), anchor="w").pack(side="left", padx=5, pady=10)
                
                # Botão Remover (Devolve pro Estoque)
                ctk.CTkButton(row, text="Remover", width=80, fg_color="#c0392b", hover_color="#a93226", 
                              command=lambda id_m=id_bd: [funcao_remover(id_m, 'ESTOQUE'), 
                                                          self.carregar_materiais_alocados(codigo_impressora, eh_resina)]
                             ).pack(side="right", padx=10)
            else:
                ctk.CTkLabel(row, text="[ VAZIO ]", text_color="gray", font=("Roboto", 14)).pack(side="left", padx=5)
                
                # Botão Alocar
                ctk.CTkButton(row, text="➕ Alocar", width=80, fg_color="#27ae60", hover_color="#2ecc71",
                              command=lambda: self.abrir_selecao_estoque(codigo_impressora, eh_resina)
                             ).pack(side="right", padx=10)

    def abrir_selecao_estoque(self, codigo_destino, eh_resina):
        titulo = "Selecionar Resina" if eh_resina else "Selecionar Filamento"
        
        win = ctk.CTkToplevel(self)
        win.title(titulo)
        win.geometry("450x550")
        win.attributes("-topmost", True)
        win.grab_set() 
        
        ctk.CTkLabel(win, text=f"{titulo} Disponível:", font=("Roboto", 16, "bold")).pack(pady=10)
        
        lista_scroll = ctk.CTkScrollableFrame(win)
        lista_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. Busca os dados e define variáveis de contexto
        if eh_resina:
            estoque_bruto = self.db.buscar_todas_resinas()
            unidade = "ml"
            funcao_mover = self.db.mover_resina
            # Filtro: No seu banco de resinas, a localização é o índice 5
            estoque = [r for r in estoque_bruto if r[5] in (None, 'ESTOQUE', '', 'Estoque')]
        else:
            estoque = self.db.buscar_todos_filamentos() # Já vem filtrado do banco
            unidade = "g"
            funcao_mover = self.db.mover_filamento

        if not estoque:
            ctk.CTkLabel(lista_scroll, text="Nenhum material no estoque.", text_color="gray").pack(pady=20)
            return

        # 2. O MESMO loop para ambos, garantindo o efeito visual e funcional
        for item in estoque:
            # Desempacotamento seguro (ID, Marca, Tipo, Cor, Quantidade)
            id_bd, marca, tipo, cor, qtd = item[0], item[1], item[2], item[3], item[4]
            
            item_frame = ctk.CTkFrame(lista_scroll, fg_color="#333333")
            item_frame.pack(fill="x", padx=5, pady=2)
            
            txt_exibicao = f"ID {id_bd} | {marca} {tipo} - {cor} ({qtd}{unidade})"
            
            # O botão ocupa o frame todo
            btn = ctk.CTkButton(item_frame, text=txt_exibicao, anchor="w", fg_color="transparent",
                                hover_color="#444444",
                                command=lambda i=id_bd: [
                                    funcao_mover(i, codigo_destino), 
                                    self.carregar_materiais_alocados(codigo_destino, eh_resina),
                                    win.destroy()
                                ])
            btn.pack(fill="x")


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

            dados = [id_bd, marca, material, cor, f"{peso}kg"]
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
            m = self.combo_marca.get()
            mat = self.combo_material.get()
            c = self.combo_cor.get()
            # Pega apenas o número do texto "1.0 kg" e converte para float
            p_texto = self.combo_peso.get().replace(" kg", "")
            p = float(p_texto)
            
            self.db.adicionar_filamento(m, mat, c, p, 0.0)
            self.show_estoque()
        except: 
            messagebox.showwarning("Erro", "Selecione um valor válido!")

    def salvar_resina(self):
        try:
            m = self.combo_marca.get()
            mat = self.combo_tipo.get()
            c = self.combo_cor.get()
            
            # Validação para evitar erro de conversão
            vol_texto = self.combo_volume.get()
            if "ml" not in vol_texto and not vol_texto.replace(".", "").isdigit():
                 messagebox.showwarning("Atenção", "Selecione um volume válido (ex: 1000 ml).")
                 return

            p_texto = vol_texto.replace(" ml", "").strip()
            p = float(p_texto)
            
            # CORREÇÃO AQUI: Removido o 0.0 que era o preço
            self.db.adicionar_resina(m, mat, c, p)
            
            self.show_resinas()
            messagebox.showinfo("Sucesso", "Resina adicionada!")
        except Exception as e: 
            print(e)
            messagebox.showwarning("Erro", f"Erro ao salvar: {e}")

    def show_offline_mode(self):
        self.limpar_area_principal()
        ctk.CTkLabel(self.main_frame, text="⚠️ SEM CONEXÃO", font=("Arial", 30), text_color="orange").pack(pady=50)

    def limpar_area_principal(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()

if __name__ == "__main__":
    app = App3D()
    app.mainloop()