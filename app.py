from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from functools import wraps
import datetime
import json

# Configuração do banco de dados
def get_db_connection():
    conn = sqlite3.connect('instance/products.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Criar tabela de categorias se não existir
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    ''')
    
    # Verificar se já existem categorias padrão
    cursor.execute("SELECT * FROM categories WHERE name = 'Geral'")
    if not cursor.fetchone():
        # Inserir categoria padrão
        cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)",
                    ('Geral', 'Categoria geral para todos os produtos'))
    
    # Criar tabela de produtos se não existir (com campo de categoria)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price REAL NOT NULL,
        image TEXT,
        stock INTEGER NOT NULL DEFAULT 0,
        category_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    ''')
    
    # Criar tabela de usuários se não existir
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    # Verificar se já existe um usuário admin
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        # Inserir usuário padrão (admin/admin)
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       ('admin', 'admin'))
    
    conn.commit()
    conn.close()

# Verificar extensões permitidas
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Decorator para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor faça login para acessar esta página', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'catalogo_secreto_123'  # Chave necessária para sessions e flash messages
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'img', 'products')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16MB para uploads
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Garantir que a pasta de uploads existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Rotas para a página pública
    @app.route('/')
    def index():
        category_id = request.args.get('category', type=int)
        
        conn = get_db_connection()
        # Obter todas as categorias para o menu
        categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
        
        # Obter os últimos produtos lançados (5 mais recentes)
        latest_products = conn.execute('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            ORDER BY p.created_at DESC LIMIT 5
        ''').fetchall()
        
        # Obter produtos filtrados por categoria (se especificada)
        if category_id:
            products = conn.execute('''
                SELECT p.*, c.name as category_name 
                FROM products p 
                JOIN categories c ON p.category_id = c.id 
                WHERE p.category_id = ? 
                ORDER BY p.name
            ''', (category_id,)).fetchall()
            current_category = conn.execute('SELECT * FROM categories WHERE id = ?', 
                                         (category_id,)).fetchone()
        else:
            products = conn.execute('''
                SELECT p.*, c.name as category_name 
                FROM products p 
                JOIN categories c ON p.category_id = c.id 
                ORDER BY p.name
            ''').fetchall()
            current_category = None
            
        conn.close()
        
        return render_template('index.html', 
                            products=products, 
                            latest_products=latest_products,
                            categories=categories,
                            current_category=current_category)

    # Rota de login do admin
    @app.route('/admin', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                            (username, password)).fetchone()
            conn.close()
            
            if user:
                session['logged_in'] = True
                session['username'] = username
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('admin_panel'))
            else:
                flash('Usuário ou senha inválidos!', 'danger')
        
        return render_template('admin/login.html')

    # Rota de logout
    @app.route('/admin/logout')
    def admin_logout():
        session.pop('logged_in', None)
        session.pop('username', None)
        flash('Você saiu com sucesso!', 'success')
        return redirect(url_for('admin_login'))

    # Painel administrativo
    @app.route('/admin/panel')
    @login_required
    def admin_panel():
        conn = get_db_connection()
        products = conn.execute('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            ORDER BY p.id DESC
        ''').fetchall()
        categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
        conn.close()
        return render_template('admin/panel.html', products=products, categories=categories)

    # Rota para adicionar produtos
    @app.route('/admin/products/add', methods=['GET', 'POST'])
    @login_required
    def add_product():
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            category_id = int(request.form.get('category_id', 1))  # Categoria padrão é 1 (Geral)
            
            # Processar upload da imagem
            image_filename = 'no-image.jpg'  # Imagem padrão
            if 'image' in request.files:
                image = request.files['image']
                if image and allowed_file(image.filename):
                    # Adicionar timestamp para evitar sobreposição de nomes
                    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    filename = f"{timestamp}_{secure_filename(image.filename)}"
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path)
                    image_filename = f"img/products/{filename}"
            
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO products (name, description, price, image, stock, category_id) VALUES (?, ?, ?, ?, ?, ?)',
                (name, description, price, image_filename, stock, category_id)
            )
            conn.commit()
            conn.close()
            
            flash('Produto adicionado com sucesso!', 'success')
            return redirect(url_for('admin_panel'))
        
        conn = get_db_connection()
        categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
        conn.close()
        
        return render_template('admin/panel.html', add_mode=True, categories=categories)

    # Rota para editar produtos
    @app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_product(id):
        conn = get_db_connection()
        product = conn.execute('''
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE p.id = ?
        ''', (id,)).fetchone()
        
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            category_id = int(request.form.get('category_id', 1))
            
            # Verificar se uma nova imagem foi enviada
            image_filename = product['image']
            if 'image' in request.files:
                image = request.files['image']
                if image and allowed_file(image.filename) and image.filename != '':
                    # Adicionar timestamp para evitar sobreposição de nomes
                    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    filename = f"{timestamp}_{secure_filename(image.filename)}"
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path)
                    image_filename = f"img/products/{filename}"
            
            conn.execute(
                'UPDATE products SET name = ?, description = ?, price = ?, image = ?, stock = ?, category_id = ? WHERE id = ?',
                (name, description, price, image_filename, stock, category_id, id)
            )
            conn.commit()
            conn.close()
            
            flash('Produto atualizado com sucesso!', 'success')
            return redirect(url_for('admin_panel'))
        
        categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
        conn.close()
        
        return render_template('admin/panel.html', edit_mode=True, product=product, categories=categories)

    # Rota para deletar produtos
    @app.route('/admin/products/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_product(id):
        conn = get_db_connection()
        
        # Obter o nome da imagem para remover se não for a padrão
        product = conn.execute('SELECT image FROM products WHERE id = ?', (id,)).fetchone()
        
        # Deletar o produto
        conn.execute('DELETE FROM products WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        # Remover a imagem do produto se não for a padrão
        if product and product['image'] != 'no-image.jpg' and os.path.exists(product['image']):
            try:
                os.remove(os.path.join('static', product['image']))
            except:
                pass  # Se falhar em remover, apenas ignore
        
        flash('Produto removido com sucesso!', 'success')
        return redirect(url_for('admin_panel'))

    # API para atualizar estoque
    @app.route('/api/update-stock', methods=['POST'])
    @login_required
    def update_stock():
        data = request.get_json()
        product_id = data.get('id')
        new_stock = data.get('stock')
        
        if product_id and new_stock is not None:
            conn = get_db_connection()
            conn.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, product_id))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
    # Gerenciamento de categorias
    @app.route('/admin/categories')
    @login_required
    def admin_categories():
        conn = get_db_connection()
        categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
        conn.close()
        return render_template('admin/categories.html', categories=categories)
    
    # Adicionar categoria
    @app.route('/admin/categories/add', methods=['POST'])
    @login_required
    def add_category():
        name = request.form['name']
        description = request.form['description']
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO categories (name, description) VALUES (?, ?)', 
                      (name, description))
            conn.commit()
            flash('Categoria adicionada com sucesso!', 'success')
        except sqlite3.IntegrityError:
            flash('Erro: Uma categoria com este nome já existe!', 'danger')
        finally:
            conn.close()
            
        return redirect(url_for('admin_categories'))
    
    # Editar categoria
    @app.route('/admin/categories/edit/<int:id>', methods=['POST'])
    @login_required
    def edit_category(id):
        name = request.form['name']
        description = request.form['description']
        
        conn = get_db_connection()
        try:
            conn.execute('UPDATE categories SET name = ?, description = ? WHERE id = ?', 
                      (name, description, id))
            conn.commit()
            flash('Categoria atualizada com sucesso!', 'success')
        except sqlite3.IntegrityError:
            flash('Erro: Uma categoria com este nome já existe!', 'danger')
        finally:
            conn.close()
            
        return redirect(url_for('admin_categories'))
    
    # Excluir categoria
    @app.route('/admin/categories/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_category(id):
        # Verificar se é a categoria padrão (id=1)
        if id == 1:
            flash('A categoria padrão não pode ser excluída!', 'danger')
            return redirect(url_for('admin_categories'))
        
        conn = get_db_connection()
        # Mover produtos desta categoria para a categoria padrão (id=1)
        conn.execute('UPDATE products SET category_id = 1 WHERE category_id = ?', (id,))
        # Excluir a categoria
        conn.execute('DELETE FROM categories WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        flash('Categoria excluída com sucesso!', 'success')
        return redirect(url_for('admin_categories'))
    
    # Inicializar o banco de dados dentro do contexto da aplicação
    with app.app_context():
        init_db()
    
    return app

# Criar a instância da aplicação
app = create_app()

# Necessário para que a função allowed_file funcione corretamente
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    app.run(debug=True)