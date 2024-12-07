from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///investment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    balance = db.Column(db.Float, default=10000.0)  # Starting balance
    portfolio = db.relationship('Portfolio', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(4), nullable=False)  # 'buy' or 'sell'
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    portfolio = Portfolio.query.filter_by(user_id=current_user.id).all()
    portfolio_data = []
    total_value = current_user.balance

    for position in portfolio:
        stock = yf.Ticker(position.symbol)
        current_price = stock.info.get('regularMarketPrice', 0)
        position_value = current_price * position.shares
        total_value += position_value
        
        portfolio_data.append({
            'symbol': position.symbol,
            'shares': position.shares,
            'current_price': current_price,
            'position_value': position_value,
            'gain_loss': (current_price - position.purchase_price) * position.shares
        })

    return render_template('dashboard.html', 
                         portfolio=portfolio_data, 
                         balance=current_user.balance,
                         total_value=total_value)

@app.route('/api/stock/<symbol>')
@login_required
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period='1mo')
        
        return jsonify({
            'price': stock.info.get('regularMarketPrice', 0),
            'change': stock.info.get('regularMarketChangePercent', 0),
            'history': hist['Close'].tolist(),
            'dates': hist.index.strftime('%Y-%m-%d').tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/trade', methods=['POST'])
@login_required
def trade():
    data = request.json
    symbol = data.get('symbol')
    shares = int(data.get('shares'))
    action = data.get('action')  # 'buy' or 'sell'

    stock = yf.Ticker(symbol)
    current_price = stock.info.get('regularMarketPrice', 0)
    total_cost = current_price * shares

    if action == 'buy':
        if total_cost > current_user.balance:
            return jsonify({'error': 'Insufficient funds'}), 400

        current_user.balance -= total_cost
        portfolio_item = Portfolio.query.filter_by(
            user_id=current_user.id, symbol=symbol).first()

        if portfolio_item:
            portfolio_item.shares += shares
        else:
            portfolio_item = Portfolio(
                user_id=current_user.id,
                symbol=symbol,
                shares=shares,
                purchase_price=current_price
            )
            db.session.add(portfolio_item)

    elif action == 'sell':
        portfolio_item = Portfolio.query.filter_by(
            user_id=current_user.id, symbol=symbol).first()

        if not portfolio_item or portfolio_item.shares < shares:
            return jsonify({'error': 'Insufficient shares'}), 400

        current_user.balance += total_cost
        portfolio_item.shares -= shares

        if portfolio_item.shares == 0:
            db.session.delete(portfolio_item)

    transaction = Transaction(
        user_id=current_user.id,
        symbol=symbol,
        shares=shares,
        price=current_price,
        transaction_type=action
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify({
        'message': f'Successfully {action}ed {shares} shares of {symbol}',
        'new_balance': current_user.balance
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))