#coding:utf8
from flask import Flask
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
import os
from flask_redis import  FlaskRedis
import pymysql
app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]="mysql+pymysql://root:123456@127.0.0.1:3306/movie"
app.config["SECRET_KEY"]='1b8215959d234dbfb8a2084c7820a4cc'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=True
app.config["UP_DIR"]=os.path.join(os.path.abspath(os.path.dirname(__file__)),"static/uploads/")
app.config["FC_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/users/")
app.debug = True
db=SQLAlchemy(app)
app.config['REDIS_URL'] = 'redis://localhost:3306/0'
rd = FlaskRedis(app)
from app.home import  home as home_blueprint
from app.admin import admin as admin_blueprint

app.register_blueprint(home_blueprint)
app.register_blueprint(admin_blueprint,url_prefix="/admin")

#404
@app.errorhandler(404)
def page_not_found(error):
    return render_template("home/404.html"),404