from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Настройка URL базы данных
database_url = os.getenv('DATABASE_URL', 'sqlite:///site.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['AVATAR_FOLDER'] = 'static/avatars'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['AVATAR_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(45), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    avatar = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contents = db.relationship('Content', backref='creator', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

    @property
    def created_at_local(self):
        return self.created_at + timedelta(hours=3) if self.created_at else None

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Content(db.Model):
    __tablename__ = 'content'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(45), nullable=False)
    path_to_content = db.Column(db.String(255), nullable=False)
    id_creator = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Float, default=0)
    rating_cols = db.Column(db.Integer, default=0)
    time_add = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    views = db.Column(db.Integer, nullable=False, default=0)
    comments = db.relationship('Comment', backref='content', lazy=True)

    @property
    def time_add_local(self):
        return self.time_add + timedelta(hours=3)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    id_content = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'content_id', name='_user_content_uc'),)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET'])
def index():
    search_query = request.args.get('search', '')
    if search_query:
        posts = Content.query.filter(Content.name.ilike(f'%{search_query}%')).order_by(Content.time_add.desc()).all()
    else:
        posts = Content.query.order_by(Content.time_add.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        elif not user:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неверный пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        title = request.form.get('title', '').strip()
        if not file or file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        rel_path = os.path.join('uploads', filename).replace('\\', '/')
        abs_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(abs_path)
        post = Content(
            name=title if title else filename,
            path_to_content=rel_path,
            id_creator=current_user.id,
            time_add=datetime.utcnow(),
            views=0,
            rating=0,
            rating_cols=0
        )
        db.session.add(post)
        db.session.commit()
        flash('Изображение успешно загружено')
        return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = Content.query.get_or_404(post_id)
    if request.method == 'GET':
        post.views += 1
        db.session.commit()
    comments = Comment.query.filter_by(id_content=post.id).order_by(Comment.id.desc()).all()
    avg_rating = post.rating if post.rating_cols else 0
    rating_count = post.rating_cols
    return render_template('post.html', post=post, comments=comments, avg_rating=avg_rating, rating_count=rating_count)

@app.route('/post/<int:post_id>/rate', methods=['POST'])
@login_required
def rate_post(post_id):
    post = Content.query.get_or_404(post_id)
    value = int(request.form.get('rating', 0))
    if not 1 <= value <= 5:
        flash('Некорректная оценка')
        return redirect(url_for('view_post', post_id=post_id))
    rating = Rating.query.filter_by(user_id=current_user.id, content_id=post.id).first()
    if rating:
        rating.value = value
    else:
        rating = Rating(user_id=current_user.id, content_id=post.id, value=value)
        db.session.add(rating)
    db.session.commit()
    ratings = Rating.query.filter_by(content_id=post.id).all()
    post.rating_cols = len(ratings)
    post.rating = sum(r.value for r in ratings) / post.rating_cols if post.rating_cols else 0
    db.session.commit()
    flash('Спасибо за вашу оценку!')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Content.query.get_or_404(post_id)
    text = request.form.get('text', '').strip()
    if not text:
        flash('Комментарий не может быть пустым')
        return redirect(url_for('view_post', post_id=post_id))
    comment = Comment(id_user=current_user.id, id_content=post.id, text=text)
    db.session.add(comment)
    db.session.commit()
    flash('Комментарий добавлен')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/post/<int:post_id>/edit', methods=['POST'])
@login_required
def edit_post(post_id):
    post = Content.query.get_or_404(post_id)
    if not current_user.is_admin and post.id_creator != current_user.id:
        flash('Нет прав на редактирование')
        return redirect(url_for('view_post', post_id=post_id))
    new_title = request.form.get('title', '').strip()
    if new_title:
        post.name = new_title
        db.session.commit()
        flash('Название обновлено')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Content.query.get_or_404(post_id)
    if not current_user.is_admin and post.id_creator != current_user.id:
        flash('Нет прав на удаление')
        return redirect(url_for('view_post', post_id=post_id))
    try:
        abs_path = os.path.join(app.root_path, 'static', post.path_to_content)
        os.remove(abs_path)
    except Exception:
        pass
    db.session.delete(post)
    db.session.commit()
    flash('Пост удалён')
    return redirect(url_for('index'))

@app.route('/download/<int:post_id>')
def download_post(post_id):
    post = Content.query.get_or_404(post_id)
    abs_path = os.path.join(app.root_path, 'static', post.path_to_content)
    return send_file(abs_path, as_attachment=True)

@app.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Content.query.filter_by(id_creator=user.id).order_by(Content.time_add.desc()).all()
    return render_template('user_profile.html', user=user, posts=posts)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['AVATAR_FOLDER'], filename)
                file.save(filepath)
                current_user.avatar = filename
                db.session.commit()
                flash('Аватар обновлён')
        if 'username' in request.form:
            new_username = request.form['username'].strip()
            if new_username and new_username != current_user.username:
                if User.query.filter_by(username=new_username).first():
                    flash('Это имя уже занято')
                else:
                    current_user.username = new_username
                    db.session.commit()
                    flash('Имя пользователя обновлено')
    return render_template('settings.html')

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post = Content.query.get_or_404(comment.id_content)
    
    if not current_user.is_admin and post.id_creator != current_user.id:
        flash('Нет прав на удаление комментариев')
        return redirect(url_for('view_post', post_id=post.id))
        
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('view_post', post_id=post.id))

if __name__ == '__main__':
    with app.app_context():
        # Удаляем все таблицы
        db.drop_all()
        # Создаем таблицы заново
        db.create_all()
        # Создаем админа
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
    app.run(debug=True)
else:
    # Для production (Render.com)
    with app.app_context():
        # Удаляем все таблицы
        db.drop_all()
        # Создаем таблицы заново
        db.create_all()
        # Создаем админа
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit() 