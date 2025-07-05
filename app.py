import os
import datetime
import markdown
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_filename = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('home.html', posts=posts)

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    # Convert markdown to HTML
    post.content_html = markdown.markdown(post.content, extensions=['fenced_code', 'codehilite'])
    return render_template('post.html', title=post.title, post=post)

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        # Handle image upload
        image_filename = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = secure_filename(image.filename)
                image_filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        post = Post(title=title, content=content, author=current_user, image_filename=image_filename)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    
    return render_template('create_post.html', title='New Post')

@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You do not have permission to edit this post.', 'danger')
        return redirect(url_for('post', post_id=post.id))
    
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        
        # Handle image upload
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                # Delete old image if exists
                if post.image_filename:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename))
                    except:
                        pass
                
                filename = secure_filename(image.filename)
                image_filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                post.image_filename = image_filename
        
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    
    return render_template('create_post.html', title='Update Post', post=post)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(url_for('post', post_id=post.id))
    
    # Delete image if exists
    if post.image_filename:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename))
        except:
            pass
    
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    
    return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.template_filter('markdown')
def markdown_filter(text):
    return markdown.markdown(text, extensions=['fenced_code', 'codehilite'])

# Create admin user if it doesn't exist
def create_admin():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='TPO').first():
            admin = User(username='TPO')
            admin.set_password('password')  # Change this to a secure password
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Create database and admin user if they don't exist
    with app.app_context():
        db.create_all()
        create_admin()
    
    app.run(host='0.0.0.0', port=12000, debug=True)