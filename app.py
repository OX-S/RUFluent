import json

import requests
from flask import Flask, render_template, request, redirect, session, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize Firebase Admin SDK
cred = credentials.Certificate(
    'rufluent-firebase-adminsdk-c5p1c-40e5294999.json')  # Replace with your service account key file
firebase_admin.initialize_app(cred)


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/signup')
def signup():
    return render_template('signup.html')


@app.route('/loginrequest', methods=['POST'])
def loginrequest():
    email = request.form['email']
    password = request.form['password']

    try:
        # Sign in user with Firebase email/password authentication
        user = auth.get_user_by_email(email)
        session['user_uid'] = user.uid
        return redirect('/profile')
    except:
        return redirect('/login')


@app.route('/signuprequest', methods=['POST'])
def signuprequest():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    languages = request.form.getlist('language[]')
    proficiency = request.form.getlist('proficiency[]')

    # Register user with Firebase Authentication
    try:
        user = auth.create_user(
            email=email,
            email_verified=False,
            password=password,
            display_name=username
        )
        uid = user.uid
    except FirebaseAuthError as e:
        # Handle error if user registration fails
        print("Error creating user:", e)
        return "Error creating user"

    # Save user's information to Firestore and link with UID
    db = firestore.client()
    user_ref = db.collection('users').document(uid)
    user_ref.set({
        'username': username,
        'email': email,
        'languages': {languages[i]: proficiency[i] for i in range(len(languages))}
    })

    session['user_uid'] = uid

    return redirect('/profile')


@app.route('/profile')
def profile():
    user_uid = session.get('user_uid')
    if user_uid:
        user = auth.get_user(user_uid)
        return render_template('profile.html', email=user.email)
    else:
        return redirect('/')


@app.route('/logout')
def logout():
    session.pop('user_uid', None)
    return redirect('/')



if __name__ == '__main__':
    app.run(debug=True, port=8000)
