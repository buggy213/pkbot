from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

QuizDBBase = declarative_base()
PkBotBase = declarative_base()
hostname = 'postgresql+psycopg2://postgres:password@' if os.name == 'nt' else 'postgresql+psycopg2://postgres@'
QuizDBEngine = create_engine(f'{hostname}/quizdb')
PkBotEngine = create_engine(f'{hostname}/pkbot')

class Bonus(QuizDBBase):
    __tablename__ = 'bonuses'

    id = Column(Integer, primary_key=True)
    number = Column(Integer)
    round = Column(String)
    category_id = Column(Integer)
    subcategory_id = Column(Integer)
    quinterest_id = Column(Integer)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'))
    leadin = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    errors_count = Column(Integer)
    formatted_leadin = Column(String)

    tournament = relationship("Tournament", back_populates='bonuses')
    bonus_parts = relationship("BonusPart", back_populates='bonus')

class BonusPart(QuizDBBase):
    __tablename__ = 'bonus_parts'

    id = Column(Integer, primary_key=True)
    bonus_id = Column(Integer, ForeignKey('bonuses.id'))
    text = Column(String)
    answer = Column(String)
    formatted_text = Column(String)
    formatted_answer = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    number = Column(Integer)
    wikipedia_url = Column(String)

    bonus = relationship("Bonus", back_populates='bonus_parts')

class Tournament(QuizDBBase):
    __tablename__ = 'tournaments'

    id = Column(Integer, primary_key=True)
    year = Column(Integer)
    name = Column(String)
    difficulty = Column(Integer)
    quality = Column(Integer)
    address = Column(String)
    type = Column(String)
    link = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    tossups = relationship("Tossup", back_populates='tournament')
    bonuses = relationship("Bonus", back_populates='tournament')

class Tossup(QuizDBBase):
    __tablename__ = 'tossups'

    id = Column(Integer, primary_key=True)
    text = Column(String)
    answer = Column(String)
    number = Column(Integer)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'))
    category_id = Column(Integer)
    subcategory_id = Column(Integer)
    round = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    quinterest_id = Column(Integer)
    formatted_text = Column(String)
    errors_count = Column(Integer)
    formatted_answer = Column(String)
    wikipedia_url = Column(String)

    tournament = relationship("Tournament", back_populates='tossups')

class TrainingData(PkBotBase):
    __tablename__ = "training_data"

    id = Column(Integer, primary_key=True)
    formatted_answer = Column(String)
    given_answer = Column(String)
    correctness = Column(Integer)

class DiscordUser(PkBotBase):
    __tablename__ = 'discord_users'

    id = Column(Integer, primary_key=True)

    pk_sessions = relationship("PkSession", back_populates='discord_user')
    tk_sessions = relationship("TkSession", back_populates='discord_user')


class PkSession(PkBotBase):
    __tablename__ = 'pk_sessions'

    id = Column(Integer, primary_key=True)
    player = Column(Integer, ForeignKey('discord_users.id'))
    bonuses_heard = Column(Integer)
    points = Column(Integer)
    settings = Column(String)

    discord_user = relationship("DiscordUser", back_populates='pk_sessions')

class TkSession(PkBotBase):
    __tablename__ = 'tk_sessions'

    id = Column(Integer, primary_key=True)
    player = Column(Integer, ForeignKey('discord_users.id'))
    tossups_heard = Column(Integer)
    points = Column(Integer)
    tens = Column(Integer)
    powers = Column(Integer)
    negs = Column(Integer)
    settings = Column(String)

    discord_user = relationship("DiscordUser", back_populates='tk_sessions')

QuizDBSession = sessionmaker()
QuizDBSession.configure(bind=QuizDBEngine)

PkBotSession = sessionmaker()
PkBotSession.configure(bind=PkBotEngine)

PkBotBase.metadata.create_all(PkBotEngine)

def get_pkbot_session():
    return PkBotSession()

def get_quizdb_session():
    return QuizDBSession()