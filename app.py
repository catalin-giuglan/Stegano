from flask import Flask, request, render_template, url_for, flash, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from stegano import lsb
from datetime import datetime
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/img', exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar   = db.Column(db.String(200), nullable=True, default=None)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def avatar_url(self):
        """
        Returns the URL to this user's avatar image,
        or the default avatar if none uploaded.
        """
        if self.avatar:
            return url_for('static', filename=f'uploads/{self.avatar}')
        return url_for('static', filename='uploads/default_avatar.png')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(200), nullable=True)
    has_hidden_message = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    
    def __repr__(self):
        return f'<Message {self.id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Numele de utilizator există deja')
            return redirect(url_for('register'))
        
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        flash('Înregistrare reușită! Te rugăm să te loghezi.')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Nume de utilizator sau parolă invalidă')
            return redirect(url_for('login'))
        
        login_user(user)
        flash('Autentificare reușită!')
        return redirect(url_for('chat'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/chat')
@login_required
def chat():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('chat.html', users=users)

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat_with_user(user_id):
    other_user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        content = request.form.get('message')
        image = request.files.get('image')
        hidden_message = request.form.get('hidden_message')
        
        image_path = None
        has_hidden = False
        
        if image and image.filename:
            # Generate unique filename
            filename = secure_filename(image.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # If there's a hidden message, encode it
            if hidden_message and hidden_message.strip():
                secret = lsb.hide(image, hidden_message)
                secret.save(image_path)
                has_hidden = True
            else:
                image.save(image_path)
            
            # Make path relative for database
            image_path = image_path.replace('static/', '')
        
        # Create message
        message = Message(
            sender_id=current_user.id,
            receiver_id=user_id,
            content=content,
            image_path=image_path,
            has_hidden_message=has_hidden
        )
        
        db.session.add(message)
        db.session.commit()
        
        return redirect(url_for('chat_with_user', user_id=user_id))
    
    # Get messages between current user and other user
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()
    
    users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('chat_with_user.html', 
                          other_user=other_user, 
                          messages=messages, 
                          users=users)

@app.route('/get_new_messages/<int:user_id>/<int:last_message_id>', methods=['GET'])
@login_required
def get_new_messages(user_id, last_message_id):
    # Get new messages between current user and other user
    new_messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id)),
        Message.id > last_message_id
    ).order_by(Message.timestamp).all()
    
    # Convert messages to JSON
    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'image_path': msg.image_path,
            'has_hidden_message': msg.has_hidden_message,
            'sender_id': msg.sender_id,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'is_sent': msg.sender_id == current_user.id
        })
    
    return jsonify(messages_data)

@app.route('/decode_image', methods=['POST'])
@login_required
def decode_image():
    image_path = request.form.get('image_path')
    if not image_path:
        return jsonify({'error': 'No image path provided'}), 400
    
    full_path = os.path.join('static', image_path)
    
    try:
        hidden_message = lsb.reveal(full_path)
        if hidden_message:
            return jsonify({'message': hidden_message})
        return jsonify({'message': 'No hidden message found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Original steganography routes (kept for compatibility)
@app.route('/image/encode', methods=["GET", "POST"])
@login_required
def img_encode():
    # Get all users for the dropdown
    users = User.query.filter(User.id != current_user.id).all()
    
    if request.method == "POST":
        file = request.files["pic"]
        hided_message = request.form["msg"]
        send_to = request.form.get("send_to")
        
        # Generate unique filename
        filename = f"enc_image_{uuid.uuid4()}.png"
        path = os.path.join("static/img", filename)
        
        # Encode the message
        secret = lsb.hide(file, hided_message)
        secret.save(path)
        
        # If send_to is provided, send as a message
        if send_to and send_to.isdigit():
            user_id = int(send_to)
            
            # Create a message
            message = Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                content="I sent you an image with a hidden message.",
                image_path=path.replace('static/', ''),
                has_hidden_message=True
            )
            
            db.session.add(message)
            db.session.commit()
            
            flash('Image sent successfully!')
            return redirect(url_for('chat_with_user', user_id=user_id))
        
        return render_template("success.html", message="Operation was successful", image_path=path)
        
    return render_template("img_enc.html", users=users)

@app.route('/image/decode', methods=["GET", "POST"])
@login_required
def img_decode():
    if request.method == "POST":
        file = request.files["pic"]
        
        # Save temporarily to decode
        temp_path = os.path.join("static/img", "temp_decode.png")
        file.save(temp_path)
        
        try:
            msg = lsb.reveal(temp_path)
            return render_template("success.html", message=msg or "No hidden message found")
        except Exception as e:
            return render_template("success.html", message=f"Error: {str(e)}")
    return render_template("img_dec.html")

@app.route('/profile')
@login_required
def profile():
    return render_template("profile.html", user=current_user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Handle avatar upload
        file = request.files.get('avatar')
        # create user-specific folder
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], f"user_{current_user.id}")
        os.makedirs(user_folder, exist_ok=True)

        filename = secure_filename(file.filename)
        filepath = os.path.join(user_folder, filename)
        file.save(filepath)

        # store relative path under uploads/
        current_user.avatar = f"user_{current_user.id}/{filename}"
        db.session.commit()
        flash('Avatar updated!', 'success')
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=current_user)

if __name__ == '__main__':
    import sys
    port = 5000
    db_suffix = ""
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        db_suffix = sys.argv[2]
    
    # Set database URI based on suffix
    if db_suffix:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///chat{db_suffix}.db'
        
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=port, host='0.0.0.0')