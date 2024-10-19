from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
import sqlite3
import datetime


app = Flask(__name__)
app.config['DATABASE'] = 'database.sqlite'

@app.route('/')
def home():
     return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)