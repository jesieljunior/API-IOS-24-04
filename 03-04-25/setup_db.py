from app import app, db, Usuario, Professor, Turma, Aluno
from werkzeug.security import generate_password_hash

# Este script recria o banco de dados e adiciona dados iniciais
# ATENÇÃO: Este script apaga todos os dados existentes!

def setup_database():
    with app.app_context():
        # Recriar todas as tabelas
        db.drop_all()
        db.create_all()
        
        # Criar usuário Master
        senha_hash = generate_password_hash('admin123')
        usuario_master = Usuario(email='admin@ios.org', senha=senha_hash, tipo='master')
        db.session.add(usuario_master)
        
        # Criar alguns professores
        professores = [
            {'nome': 'Carlos Silva', 'email': 'carlos@ios.org'},
            {'nome': 'Ana Oliveira', 'email': 'ana@ios.org'},
            {'nome': 'Paulo Santos', 'email': 'paulo@ios.org'},
        ]
        
        for p in professores:
            # Criar usuário para professor
            senha_hash = generate_password_hash('professor123')
            usuario = Usuario(email=p['email'], senha=senha_hash, tipo='professor')
            db.session.add(usuario)
            
            # Criar professor
            professor = Professor(nome=p['nome'], email=p['email'])
            db.session.add(professor)
        
        # Commit para obter IDs dos professores
        db.session.commit()
        
        # Buscar professores para associar às turmas
        professor1 = Professor.query.filter_by(email='carlos@ios.org').first()
        professor2 = Professor.query.filter_by(email='ana@ios.org').first()
        professor3 = Professor.query.filter_by(email='paulo@ios.org').first()
        
        # Criar turmas
        turmas = [
            {'nome': 'Desenvolvimento Web 2025', 'professor_id': professor1.id},
            {'nome': 'Administração 2025', 'professor_id': professor2.id},
            {'nome': 'Design Gráfico 2025', 'professor_id': professor3.id},
        ]
        
        for t in turmas:
            turma = Turma(nome=t['nome'], professor_id=t['professor_id'])
            db.session.add(turma)
        
        # Commit para obter IDs das turmas
        db.session.commit()
        
        # Buscar turmas para adicionar alunos
        turma1 = Turma.query.filter_by(nome='Desenvolvimento Web 2025').first()
        turma2 = Turma.query.filter_by(nome='Administração 2025').first()
        turma3 = Turma.query.filter_by(nome='Design Gráfico 2025').first()
        
        # Criar alunos para turma 1
        alunos_turma1 = [
            'Maria Santos', 'João Silva', 'Pedro Oliveira', 
            'Ana Carolina', 'Lucas Ferreira'
        ]
        
        for nome in alunos_turma1:
            aluno = Aluno(nome=nome, turma_id=turma1.id)
            db.session.add(aluno)
        
        # Criar alunos para turma 2
        alunos_turma2 = [
            'Gabriela Lima', 'Rafael Costa', 'Juliana Martins', 
            'Bruno Almeida', 'Carla Sousa'
        ]
        
        for nome in alunos_turma2:
            aluno = Aluno(nome=nome, turma_id=turma2.id)
            db.session.add(aluno)
        
        # Criar alunos para turma 3
        alunos_turma3 = [
            'Mariana Rocha', 'Felipe Santos', 'Thiago Mendes', 
            'Bianca Silva', 'Mateus Oliveira'
        ]
        
        for nome in alunos_turma3:
            aluno = Aluno(nome=nome, turma_id=turma3.id)
            db.session.add(aluno)
        
        # Salvar tudo
        db.session.commit()
        
        print("Banco de dados configurado com sucesso!")
        print("Usuário master: admin@ios.org / Senha: admin123")
        print("Professores: carlos@ios.org, ana@ios.org, paulo@ios.org / Senha: professor123")

if __name__ == '__main__':
    setup_database()