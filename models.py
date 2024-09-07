from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

# Users table
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    country_updated = db.Column(db.Integer, default=0)
    referral_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    referred_users = db.relationship('User', remote_side=[id], backref='referrer')
    attendance = db.relationship('Attendance', backref='user', lazy=True)
    signins = db.relationship('Signin', backref='user', lazy=True)
    ranks = db.relationship('Rank', backref='user', lazy=True)
    completed_activities = db.relationship('UserCompletedActivity', backref='user', lazy=True)
    completed_national_activities = db.relationship('UserCompletedActivityNational', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


# Attendance table
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Attendance {self.date} {self.time}>'


# Referrals table
class Referral(db.Model):
    __tablename__ = 'referrals'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<Referral referrer_id={self.referrer_id}, referred_id={self.referred_id}>'


# Signins table
class Signin(db.Model):
    __tablename__ = 'signins'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    signins = db.Column(db.Integer, default=10)

    def __repr__(self):
        return f'<Signin user_id={self.user_id} signins={self.signins}>'


# Ranks table
class Rank(db.Model):
    __tablename__ = 'ranks'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    rank = db.Column(db.String(50))
    signins = db.Column(db.Integer)
    global_signins = db.Column(db.Integer, default=0)
    global_rank = db.Column(db.String(50))
    bonus_claimed = db.Column(db.Boolean, default=False)
    bonus_amount = db.Column(db.Float, default=0)

    def __repr__(self):
        return f'<Rank user_id={self.user_id} rank={self.rank}>'


# Activities table
class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Activity {self.title}>'


# National Activities table
class NationalActivity(db.Model):
    __tablename__ = 'nationalactivities'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<NationalActivity {self.title}>'


# UserCompletedActivities table
class UserCompletedActivity(db.Model):
    __tablename__ = 'usercompletedactivities'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), primary_key=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserCompletedActivity user_id={self.user_id} activity_id={self.activity_id}>'


# UserCompletedActivitiesNational table
class UserCompletedActivityNational(db.Model):
    __tablename__ = 'usercompletedactivitiesnational'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    nationalactivities_id = db.Column(db.Integer, db.ForeignKey('nationalactivities.id'), primary_key=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserCompletedActivityNational user_id={self.user_id} nationalactivities_id={self.nationalactivities_id}>'
