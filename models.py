from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

# Create DB instance (no app here!)
db = SQLAlchemy()


class History(db.Model):
    __tablename__ = "history"

    id = db.Column(db.Integer, primary_key=True)
    tool_name = db.Column(db.String(100), nullable=False)
    input_text = db.Column(db.Text)
    input_image = db.Column(db.Text)
    output_text = db.Column(db.Text)
    output_image = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, server_default=func.now())
    user_id = db.Column(db.Integer , db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"<History {self.tool_name} #{self.id}>"
    
    
    
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin= db.Column(db.Boolean, default=False)



    history = db.relationship('History', backref='owner', lazy=True )

    def __repr__(self):
        return f"<USer {self.username}>"

