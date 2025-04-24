from flask import Flask, render_template, redirect, url_for, session, flash, make_response, request, g
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import io
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import calendar

# Configuração inicial do Flask
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configurações de segurança
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_secreta_temporaria')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = True  # Apenas em HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configuração para ambiente de produção
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
app.config['DEBUG'] = False

# Configuração do banco de dados
db_url = os.environ.get('DATABASE_URL', 'sqlite:///chamada.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização do SQLAlchemy
db = SQLAlchemy(app)

# Configuração para upload de arquivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Esta função pode ser adicionada para verificar os tipos de arquivos permitidos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'master', 'professor'

class Professor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    foto_perfil = db.Column(db.String(255), nullable=True)
    turmas = db.relationship('Turma', backref='professor', lazy=True)

class Turma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professor.id'), nullable=True)
    alunos = db.relationship('Aluno', backref='turma', lazy=True)
    
    @property
    def chamadas(self):
        # Retorna todas as chamadas únicas desta turma (por data)
        datas = set()
        chamadas_list = []
        for aluno in self.alunos:
            for chamada in aluno.chamadas:
                if chamada.data not in datas and chamada.turma_id == self.id:
                    datas.add(chamada.data)
                    chamadas_list.append(chamada)
        return chamadas_list

class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turma.id'), nullable=False)
    chamadas = db.relationship('Chamada', backref='aluno', lazy=True)

class Chamada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    presente = db.Column(db.Boolean, default=False)
    justificativa = db.Column(db.Text)
    conteudo_aula = db.Column(db.Text)
    turma_id = db.Column(db.Integer, db.ForeignKey('turma.id'), nullable=False)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    
    # Relação bidirecional com Turma
    turma = db.relationship('Turma', backref='todas_chamadas', lazy=True, 
                           foreign_keys=[turma_id], overlaps="chamadas")

# Rotas básicas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        if not email or not senha:
            flash('Por favor, preencha todos os campos', 'danger')
            return render_template('login.html')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        # Debug para verificar se o usuário foi encontrado
        print(f"Tentativa de login: {email}")
        print(f"Usuário encontrado: {usuario is not None}")
        
        if usuario and check_password_hash(usuario.senha, senha):
            # Login bem-sucedido
            session['user_id'] = usuario.id
            session['tipo_usuario'] = usuario.tipo
            
            # Redirecionar com base no tipo de usuário
            if usuario.tipo == 'master':
                return redirect(url_for('master_dashboard'))
            elif usuario.tipo == 'professor':
                return redirect(url_for('professor_dashboard'))
            
            # Caso seja outro tipo de usuário
            return redirect(url_for('index'))
        
        # Login mal-sucedido
        flash('Email ou senha incorretos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Rotas para usuário master
@app.route('/master/dashboard')
def master_dashboard():
    if 'user_id' not in session or session['tipo_usuario'] != 'master':
        return redirect(url_for('login'))
    
    return render_template('master/dashboard.html')

@app.route('/master/professores', methods=['GET', 'POST'])
def master_gerenciar_professores():
    if 'user_id' not in session or session.get('tipo_usuario') != 'master':
        flash('Acesso não autorizado!')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        
        # Verificar se o email já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Email já cadastrado no sistema!')
            return redirect(url_for('master_gerenciar_professores'))
        
        # Criar o usuário (para autenticação)
        senha_hash = generate_password_hash(senha)
        novo_usuario = Usuario(email=email, senha=senha_hash, tipo='professor')
        db.session.add(novo_usuario)
        db.session.flush()  # Para obter o ID do usuário antes do commit
        
        # Criar o professor associado ao usuário
        novo_professor = Professor(nome=nome, email=email)
        db.session.add(novo_professor)
        
        try:
            db.session.commit()
            flash('Professor adicionado com sucesso!')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar professor: {str(e)}')
        
        return redirect(url_for('master_gerenciar_professores'))
    
    # GET - listar professores
    professores = Professor.query.all()
    return render_template('master/professores.html', professores=professores)

@app.route('/master/excluir-professor/<int:professor_id>', methods=['POST'])
def master_excluir_professor(professor_id):
    if 'user_id' not in session or session.get('tipo_usuario') != 'master':
        flash('Acesso não autorizado!')
        return redirect(url_for('login'))
    
    professor = Professor.query.get_or_404(professor_id)
    
    # Remover o usuário associado
    usuario = Usuario.query.filter_by(email=professor.email).first()
    
    # Verificar se este professor tem turmas associadas
    turmas_associadas = Turma.query.filter_by(professor_id=professor_id).all()
    
    if turmas_associadas:
        flash('Este professor possui turmas associadas e não pode ser excluído!')
        return redirect(url_for('master_gerenciar_professores'))
    
    try:
        if usuario:
            db.session.delete(usuario)
        db.session.delete(professor)
        db.session.commit()
        flash('Professor excluído com sucesso!')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir professor: {str(e)}')
    
    return redirect(url_for('master_gerenciar_professores'))

@app.route('/master/turmas', methods=['GET', 'POST'])
def master_gerenciar_turmas():
    if 'user_id' not in session or session.get('tipo_usuario') != 'master':
        flash('Acesso não autorizado!')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        professor_id = request.form['professor_id']
        
        # Verificar se já existe uma turma com este nome
        turma_existente = Turma.query.filter_by(nome=nome).first()
        if turma_existente:
            flash('Já existe uma turma com este nome!')
            return redirect(url_for('master_gerenciar_turmas'))
        
        # Criar nova turma
        nova_turma = Turma(nome=nome, professor_id=professor_id)
        db.session.add(nova_turma)
        
        try:
            db.session.commit()
            flash('Turma adicionada com sucesso!')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar turma: {str(e)}')
        
        return redirect(url_for('master_gerenciar_turmas'))
    
    # GET - listar turmas
    turmas = Turma.query.all()
    professores = Professor.query.all()
    return render_template('master/turmas.html', turmas=turmas, professores=professores)

@app.route('/master/excluir-turma/<int:turma_id>', methods=['POST'])
def master_excluir_turma(turma_id):
    if 'user_id' not in session or session.get('tipo_usuario') != 'master':
        flash('Acesso não autorizado!')
        return redirect(url_for('login'))
    
    turma = Turma.query.get_or_404(turma_id)
    
    # Verificar se a turma tem alunos
    alunos = Aluno.query.filter_by(turma_id=turma_id).all()
    if alunos:
        flash('Esta turma possui alunos e não pode ser excluída!')
        return redirect(url_for('master_gerenciar_turmas'))
    
    try:
        db.session.delete(turma)
        db.session.commit()
        flash('Turma excluída com sucesso!')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir turma: {str(e)}')
    
    return redirect(url_for('master_gerenciar_turmas'))

@app.route('/master/turma/<int:turma_id>/alunos', methods=['GET', 'POST'])
def master_gerenciar_alunos(turma_id):
    if 'user_id' not in session or session.get('tipo_usuario') != 'master':
        flash('Acesso não autorizado!')
        return redirect(url_for('login'))
    
    turma = Turma.query.get_or_404(turma_id)
    
    if request.method == 'POST':
        nome = request.form['nome']
        
        # Criar novo aluno
        novo_aluno = Aluno(nome=nome, turma_id=turma_id)
        db.session.add(novo_aluno)
        
        try:
            db.session.commit()
            flash('Aluno adicionado com sucesso!')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar aluno: {str(e)}')
        
        return redirect(url_for('master_gerenciar_alunos', turma_id=turma_id))
    
    # GET - listar alunos
    alunos = Aluno.query.filter_by(turma_id=turma_id).all()
    return render_template('master/alunos.html', turma=turma, alunos=alunos)

@app.route('/master/excluir-aluno/<int:aluno_id>', methods=['POST'])
def master_excluir_aluno(aluno_id):
    if 'user_id' not in session or session.get('tipo_usuario') != 'master':
        flash('Acesso não autorizado!')
        return redirect(url_for('login'))
    
    aluno = Aluno.query.get_or_404(aluno_id)
    turma_id = aluno.turma_id
    
    # Excluir chamadas associadas ao aluno
    Chamada.query.filter_by(aluno_id=aluno_id).delete()
    
    try:
        db.session.delete(aluno)
        db.session.commit()
        flash('Aluno excluído com sucesso!')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir aluno: {str(e)}')
    
    return redirect(url_for('master_gerenciar_alunos', turma_id=turma_id))

@app.route('/master/relatorios')
def master_relatorios():
    if session.get('tipo_usuario') != 'master':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    return render_template('master/relatorios.html')

# Rotas para relatórios
@app.route('/master/relatorios/frequencia-turma', methods=['GET', 'POST'])
def master_relatorios_frequencia_turma():
    if session.get('tipo_usuario') != 'master':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    turmas = Turma.query.all()
    
    # Se for uma requisição POST, gerar o relatório
    if request.method == 'POST':
        turma_id = request.form.get('turma_id')
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        formato = request.form.get('formato', 'web')  # web ou pdf
        
        turma = Turma.query.get(turma_id)
        if not turma:
            flash('Turma não encontrada', 'danger')
            return redirect(url_for('master_relatorios_frequencia_turma'))
        
        # Converter strings de data para objetos datetime
        try:
            inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            fim = datetime.strptime(data_fim, '%Y-%m-%d')
        except:
            flash('Datas inválidas', 'danger')
            return redirect(url_for('master_relatorios_frequencia_turma'))
        
        # Buscar alunos da turma
        alunos = Aluno.query.filter_by(turma_id=turma_id).order_by(Aluno.nome).all()
        
        # Buscar dados de presença para o período
        dados_presenca = {}
        datas = []
        
        # Criar um dicionário para armazenar os dados de presença por aluno e data
        for aluno in alunos:
            dados_presenca[aluno.id] = {'nome': aluno.nome, 'presencas': {}}
        
        # Buscar todas as presenças no período
        presencas = Chamada.query.filter(
            Chamada.turma_id == turma_id,
            Chamada.data >= inicio,
            Chamada.data <= fim
        ).all()
        
        # Organizar as datas encontradas
        for p in presencas:
            data_str = p.data.strftime('%Y-%m-%d')
            if data_str not in datas:
                datas.append(data_str)
        
        # Ordenar datas
        datas.sort()
        
        # Preencher os dados de presença
        for p in presencas:
            data_str = p.data.strftime('%Y-%m-%d')
            if p.aluno_id in dados_presenca:
                dados_presenca[p.aluno_id]['presencas'][data_str] = 'presente' if p.presente else 'falta'
        
        # Exportar como PDF se solicitado
        if formato == 'pdf':
            return gerar_pdf_frequencia_turma(turma, alunos, datas, dados_presenca, inicio, fim)
        
        # Caso contrário, renderiza o template com os dados
        return render_template('master/relatorio_frequencia_turma_resultado.html',
                              turma=turma,
                              alunos=alunos,
                              datas=datas,
                              dados_presenca=dados_presenca,
                              data_inicio=data_inicio,
                              data_fim=data_fim)
    
    # Renderizar o formulário para selecionar turma e período
    return render_template('master/relatorio_frequencia_turma.html', turmas=turmas)

@app.route('/master/relatorios/resumo-mensal', methods=['GET', 'POST'])
def master_relatorios_resumo_mensal():
    if session.get('tipo_usuario') != 'master':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    # Se for uma requisição POST, gerar o relatório
    if request.method == 'POST':
        mes = int(request.form.get('mes', datetime.now().month))
        ano = int(request.form.get('ano', datetime.now().year))
        formato = request.form.get('formato', 'web')  # web ou pdf
        
        # Determinar o primeiro e último dia do mês
        primeiro_dia = datetime(ano, mes, 1)
        ultimo_dia = datetime(ano, mes, calendar.monthrange(ano, mes)[1])
        
        # Buscar todas as turmas
        turmas = Turma.query.all()
        
        # Preparar dados para o relatório
        dados_relatorio = []
        
        for turma in turmas:
            # Contar alunos da turma
            num_alunos = Aluno.query.filter_by(turma_id=turma.id).count()
            
            # Contar presenças, faltas e justificativas no mês
            presencas = Chamada.query.filter(
                Chamada.turma_id == turma.id,
                Chamada.data >= primeiro_dia,
                Chamada.data <= ultimo_dia
            ).all()
            
            num_presencas = sum(1 for p in presencas if p.presente)
            num_faltas = sum(1 for p in presencas if not p.presente)
            
            # Calcular taxa de presença
            total_registros = len(presencas)
            taxa_presenca = (num_presencas / total_registros * 100) if total_registros > 0 else 0
            
            dados_turma = {
                'id': turma.id,
                'nome': turma.nome,
                'professor': turma.professor.nome if turma.professor else 'Não atribuído',
                'num_alunos': num_alunos,
                'num_presencas': num_presencas,
                'num_faltas': num_faltas,
                'taxa_presenca': round(taxa_presenca, 1)
            }
            
            dados_relatorio.append(dados_turma)
        
        # Exportar como PDF se solicitado
        if formato == 'pdf':
            return gerar_pdf_resumo_mensal(dados_relatorio, mes, ano)
        
        # Renderizar o template com os dados
        nome_mes = calendar.month_name[mes]
        return render_template('master/relatorio_resumo_mensal_resultado.html',
                              dados=dados_relatorio,
                              mes=mes,
                              nome_mes=nome_mes,
                              ano=ano)
    
    # Preparar dados para o formulário
    meses = [(i, calendar.month_name[i]) for i in range(1, 13)]
    ano_atual = datetime.now().year
    anos = range(ano_atual - 2, ano_atual + 1)
    
    # Renderizar o formulário para selecionar mês e ano
    return render_template('master/relatorio_resumo_mensal.html',
                          meses=meses,
                          anos=anos,
                          mes_atual=datetime.now().month,
                          ano_atual=ano_atual)

@app.route('/master/relatorios/estatisticas-gerais')
def master_relatorios_estatisticas_gerais():
    if session.get('tipo_usuario') != 'master':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    # Contagem geral
    num_turmas = Turma.query.count()
    num_professores = Professor.query.count()
    num_alunos = Aluno.query.count()
    
    # Estatísticas de presença nos últimos 30 dias
    data_limite = datetime.now() - timedelta(days=30)
    presencas_recentes = Chamada.query.filter(Chamada.data >= data_limite).all()
    
    num_presencas = sum(1 for p in presencas_recentes if p.presente)
    num_faltas = sum(1 for p in presencas_recentes if not p.presente)
    
    total_registros = len(presencas_recentes)
    taxa_presenca = (num_presencas / total_registros * 100) if total_registros > 0 else 0
    
    # Turmas com mais faltas
    # Agrupar presenças por turma e calcular taxa de faltas
    turmas_com_faltas = {}
    for p in presencas_recentes:
        turma_id = p.turma_id
        if turma_id not in turmas_com_faltas:
            turmas_com_faltas[turma_id] = {'presenca': 0, 'falta': 0}
        
        if p.presente:
            turmas_com_faltas[turma_id]['presenca'] += 1
        else:
            turmas_com_faltas[turma_id]['falta'] += 1
    
    # Calcular taxa de faltas para cada turma
    dados_turmas = []
    for turma_id, dados in turmas_com_faltas.items():
        turma = Turma.query.get(turma_id)
        if not turma:
            continue
        
        total = dados['presenca'] + dados['falta']
        taxa_faltas = (dados['falta'] / total * 100) if total > 0 else 0
        
        dados_turmas.append({
            'id': turma.id,
            'nome': turma.nome,
            'professor': turma.professor.nome if turma.professor else 'Não atribuído',
            'taxa_faltas': round(taxa_faltas, 1)
        })
    
    # Ordenar turmas pela taxa de faltas (decrescente)
    dados_turmas = sorted(dados_turmas, key=lambda x: x['taxa_faltas'], reverse=True)
    
    # Pegar as 5 turmas com mais faltas
    turmas_mais_faltas = dados_turmas[:5]
    
    # Verificar se quer exportar como PDF
    formato = request.args.get('formato', 'web')
    if formato == 'pdf':
        return gerar_pdf_estatisticas_gerais(num_turmas, num_professores, num_alunos,
                                            taxa_presenca, num_presencas, num_faltas,
                                            turmas_mais_faltas)
    
    return render_template('master/relatorio_estatisticas_gerais.html',
                          num_turmas=num_turmas,
                          num_professores=num_professores,
                          num_alunos=num_alunos,
                          taxa_presenca=round(taxa_presenca, 1),
                          num_presencas=num_presencas,
                          num_faltas=num_faltas,
                          turmas_mais_faltas=turmas_mais_faltas)

# Função auxiliar para gerar PDF de frequência por turma
def gerar_pdf_frequencia_turma(turma, alunos, datas, dados_presenca, data_inicio, data_fim):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Título do relatório
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, height - 50, f"Relatório de Frequência - {turma.nome}")
    
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 80, f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
    pdf.drawString(50, height - 100, f"Professor: {turma.professor.nome if turma.professor else 'Não atribuído'}")
    
    # Criar dados para a tabela
    table_data = [["Nome do Aluno"] + [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in datas]]
    
    for aluno in alunos:
        row = [aluno.nome]
        for data in datas:
            status = dados_presenca[aluno.id]['presencas'].get(data, '-')
            # Converter status para representação visual
            if status == 'presente':
                status = "P"
            elif status == 'falta':
                status = "F"
            row.append(status)
        table_data.append(row)
    
    # Criar a tabela
    table = Table(table_data)
    
    # Estilo da tabela
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    # Aplicar estilo
    table.setStyle(style)
    
    # Desenhar a tabela
    table.wrapOn(pdf, width - 100, height)
    table.drawOn(pdf, 50, height - 150 - (len(alunos) * 20))
    
    # Legenda
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 50, "P = Presente | F = Falta | - = Não Registrado")
    
    # Rodapé
    pdf.setFont("Helvetica-Italic", 8)
    pdf.drawString(50, 30, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} - Sistema de Chamada IOS")
    
    pdf.save()
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=frequencia_{turma.nome.replace(" ", "_")}.pdf'
    
    return response

# Função auxiliar para gerar PDF de resumo mensal
def gerar_pdf_resumo_mensal(dados_relatorio, mes, ano):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    nome_mes = calendar.month_name[mes]
    
    # Título do relatório
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, height - 50, f"Relatório Mensal de Frequência - {nome_mes} {ano}")
    
    # Criar dados para a tabela
    table_data = [["Turma", "Professor", "Alunos", "Presenças", "Faltas", "Taxa Presença"]]
    
    for dados in dados_relatorio:
        row = [
            dados['nome'],
            dados['professor'],
            str(dados['num_alunos']),
            str(dados['num_presencas']),
            str(dados['num_faltas']),
            f"{dados['taxa_presenca']}%"
        ]
        table_data.append(row)
    
    # Criar a tabela
    table = Table(table_data)
    
    # Estilo da tabela
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    # Aplicar estilo
    table.setStyle(style)
    
    # Desenhar a tabela
    table.wrapOn(pdf, width - 100, height)
    table.drawOn(pdf, 50, height - 120 - (len(dados_relatorio) * 20))
    
    # Rodapé
    pdf.setFont("Helvetica-Italic", 8)
    pdf.drawString(50, 30, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} - Sistema de Chamada IOS")
    
    pdf.save()
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=resumo_mensal_{nome_mes}_{ano}.pdf'
    
    return response

# Função auxiliar para gerar PDF de estatísticas gerais
def gerar_pdf_estatisticas_gerais(num_turmas, num_professores, num_alunos, taxa_presenca, 
                                 num_presencas, num_faltas, turmas_mais_faltas):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Título do relatório
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, height - 50, "Estatísticas Gerais do Sistema")
    
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 80, f"Data de geração: {datetime.now().strftime('%d/%m/%Y')}")
    pdf.drawString(50, height - 100, "Período analisado: Últimos 30 dias")
    
    # Estatísticas gerais
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 140, "Números Gerais")
    
    pdf.setFont("Helvetica", 12)
    pdf.drawString(70, height - 170, f"Total de turmas: {num_turmas}")
    pdf.drawString(70, height - 190, f"Total de professores: {num_professores}")
    pdf.drawString(70, height - 210, f"Total de alunos: {num_alunos}")
    
    # Estatísticas de presença
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 250, "Estatísticas de Presença (últimos 30 dias)")
    
    pdf.setFont("Helvetica", 12)
    pdf.drawString(70, height - 280, f"Taxa média de presença: {round(taxa_presenca, 1)}%")
    pdf.drawString(70, height - 300, f"Total de presenças registradas: {num_presencas}")
    pdf.drawString(70, height - 320, f"Total de faltas registradas: {num_faltas}")
    
    # Turmas com mais faltas
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 380, "Turmas com Maior Taxa de Faltas")
    
    # Criar tabela para turmas com mais faltas
    table_data = [["Turma", "Professor", "Taxa de Faltas"]]
    
    for turma in turmas_mais_faltas:
        row = [
            turma['nome'],
            turma['professor'],
            f"{turma['taxa_faltas']}%"
        ]
        table_data.append(row)
    
    # Criar a tabela
    table = Table(table_data)
    
    # Estilo da tabela
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    # Aplicar estilo
    table.setStyle(style)
    
    # Desenhar a tabela
    table.wrapOn(pdf, width - 100, height)
    table.drawOn(pdf, 50, height - 410 - (len(turmas_mais_faltas) * 20))
    
    # Rodapé
    pdf.setFont("Helvetica-Italic", 8)
    pdf.drawString(50, 30, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} - Sistema de Chamada IOS")
    
    pdf.save()
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=estatisticas_gerais_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    usuario = Usuario.query.get(user_id)
    
    if not usuario:
        flash('Usuário não encontrado', 'danger')
        return redirect(url_for('logout'))
    
    # Verificar tipo de usuário e buscar dados específicos
    if session['tipo_usuario'] == 'professor':
        professor = Professor.query.filter_by(email=usuario.email).first()
        turmas = Turma.query.filter_by(professor_id=professor.id).all() if professor else []
        
        if not professor:
            flash('Perfil de professor não encontrado', 'warning')
            return redirect(url_for('professor_dashboard'))
        
        return render_template('perfil.html', usuario=usuario, professor=professor, turmas=turmas)
    
    elif session['tipo_usuario'] == 'master':
        admin = Professor.query.filter_by(email=usuario.email).first()
        return render_template('perfil.html', usuario=usuario, professor=admin)
    
    return redirect(url_for('index'))

@app.route('/editar-perfil', methods=['GET', 'POST'])
def editar_perfil():
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    usuario = Usuario.query.get(user_id)
    
    if request.method == 'POST':
        # Atualizar dados do usuário
        if session['tipo_usuario'] in ['professor', 'master']:
            professor = Professor.query.filter_by(email=usuario.email).first()
            
            if professor:
                # Atualizar nome do professor
                professor.nome = request.form['nome']
                
                # Verificar se a senha deve ser alterada
                senha_atual = request.form.get('senha_atual')
                nova_senha = request.form.get('nova_senha')
                confirmar_senha = request.form.get('confirmar_senha')
                
                if senha_atual and nova_senha and confirmar_senha:
                    # Verificar se a senha atual está correta
                    if check_password_hash(usuario.senha, senha_atual):
                        # Verificar se a nova senha e a confirmação são iguais
                        if nova_senha == confirmar_senha:
                            # Hash da nova senha
                            usuario.senha = generate_password_hash(nova_senha)
                            flash('Senha alterada com sucesso!', 'success')
                        else:
                            flash('A nova senha e a confirmação não coincidem', 'danger')
                            return render_template('editar_perfil.html', usuario=usuario, professor=professor)
                    else:
                        flash('Senha atual incorreta', 'danger')
                        return render_template('editar_perfil.html', usuario=usuario, professor=professor)
                
                # Upload de foto de perfil (opcional)
                if 'foto_perfil' in request.files:
                    arquivo = request.files['foto_perfil']
                    if arquivo and arquivo.filename != '':
                        # Verificar extensão do arquivo
                        extensao = arquivo.filename.rsplit('.', 1)[1].lower() if '.' in arquivo.filename else ''
                        if extensao in {'png', 'jpg', 'jpeg', 'gif'}:
                            # Salvar arquivo com nome seguro
                            nome_arquivo = f"perfil_{user_id}.{extensao}"
                            caminho_arquivo = os.path.join('static/uploads/perfil', nome_arquivo)
                            
                            # Criar diretório se não existir
                            os.makedirs('static/uploads/perfil', exist_ok=True)
                            
                            # Salvar arquivo
                            arquivo.save(caminho_arquivo)
                            
                            # Salvar caminho da foto no banco de dados
                            professor.foto_perfil = f"uploads/perfil/{nome_arquivo}"
                            flash('Foto de perfil atualizada com sucesso!', 'success')
                        else:
                            flash('Formato de arquivo não permitido. Use PNG, JPG, JPEG ou GIF.', 'warning')
                
                try:
                    db.session.commit()
                    flash('Perfil atualizado com sucesso!', 'success')
                    return redirect(url_for('perfil'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao atualizar perfil: {str(e)}', 'danger')
        
        return redirect(url_for('perfil'))
    
    # GET - Exibir formulário
    if session['tipo_usuario'] in ['professor', 'master']:
        professor = Professor.query.filter_by(email=usuario.email).first()
        return render_template('editar_perfil.html', usuario=usuario, professor=professor)
    
    return redirect(url_for('index'))

def inicializar_banco():
    with app.app_context():
        # Garantir que a tabela Presenca exista (se estiver sendo usada em algum lugar do código)
        try:
            db.create_all()
            print("Tabelas criadas com sucesso!")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            
        # Verificar se existem usuários
        if Usuario.query.count() == 0:
            try:
                # Criar usuário master
                senha_hash = generate_password_hash('admin123')
                admin = Usuario(
                    email='admin@ios.org.br',
                    senha=senha_hash,
                    tipo='master'
                )
                db.session.add(admin)
                
                # Criar registro de professor para o admin
                admin_prof = Professor(
                    nome='Administrador',
                    email='admin@ios.org.br'
                )
                db.session.add(admin_prof)
                
                # Criar professores de exemplo
                professores = [
                    {"email": "carlos@ios.org", "nome": "Carlos Silva", "senha": "professor123"},
                    {"email": "ana@ios.org", "nome": "Ana Souza", "senha": "professor123"},
                    {"email": "paulo@ios.org", "nome": "Paulo Ferreira", "senha": "professor123"}
                ]
                
                for prof in professores:
                    senha_hash = generate_password_hash(prof["senha"])
                    user = Usuario(
                        email=prof["email"],
                        senha=senha_hash,
                        tipo='professor'
                    )
                    db.session.add(user)
                    
                    professor = Professor(
                        nome=prof["nome"],
                        email=prof["email"]
                    )
                    db.session.add(professor)
                
                db.session.commit()
                print("Banco de dados inicializado com sucesso!")
                
            except Exception as e:
                db.session.rollback()
                print(f"Erro na inicialização do banco de dados: {e}")

if __name__ == '__main__':
    # Criar diretórios necessários
    os.makedirs('static/uploads/perfil', exist_ok=True)
    
    # Inicializar o banco de dados
    inicializar_banco()
    
    # Definir uma chave secreta se não existir
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.urandom(24).hex()
    
    # Verificar ambiente
    if app.config['ENV'] == 'production':
        # Configurações para produção
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        # Desenvolvimento
        app.run(debug=True)