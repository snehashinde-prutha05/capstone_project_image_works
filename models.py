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
    

    def __repr__(self):
        return f"<History {self.tool_name} #{self.id}>"
    

