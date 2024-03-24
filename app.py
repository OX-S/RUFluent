from datetime import datetime

from flask import Flask, render_template, request, redirect, session, jsonify, flash
import firebase_admin
from firebase_admin import credentials, auth, firestore

app = Flask(__name__)
app.secret_key = 'your_secret_key'

cred = credentials.Certificate(
    'rufluent-firebase-adminsdk-c5p1c-40e5294999.json')
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
        user = auth.get_user_by_email(email)
        session['user_uid'] = user.uid
        return redirect('/language_select')
    except:
        return redirect('/login')


@app.route('/signuprequest', methods=['POST'])
def signuprequest():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    languages = request.form.getlist('language[]')
    proficiency = request.form.getlist('proficiency[]')

    try:
        user = auth.create_user(
            email=email,
            email_verified=False,
            password=password,
            display_name=username
        )
        uid = user.uid
    except auth.EmailAlreadyExistsError:
        flash('The email address is already in use. Please try another email or log in.', 'error')
        return redirect('/signup')
    except Exception as e:
        print("Error creating user:", e)
        flash('An error occurred during registration. Please try again.', 'error')
        return redirect('/signup')

    # Save user's information to Firestore and link with UID
    db = firestore.client()
    user_ref = db.collection('users').document(uid)
    user_ref.set({
        'username': username,
        'email': email,
        'languages': {languages[i]: proficiency[i] for i in range(len(languages))}
    })

    session['user_uid'] = uid

    return redirect('/language_select')


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


@app.route('/language_select')
def language_select():
    user_uid = session.get('user_uid')
    if user_uid:
        db = firestore.client()

        user_ref = db.collection('users').document(user_uid)
        user = user_ref.get().to_dict()
        languages = user.get('languages')
        return render_template('language_select.html', email=user.get('email'), languages=languages)

    else:
        return redirect('/')


@app.route('/save-language', methods=['POST'])
def save_language():
    language = request.json.get('language')
    session['selected_language'] = language
    return '', 200


@app.route('/menu')
def menu():
    selected_language = session.get('selected_language')
    return render_template('menu.html', selected_language=selected_language)


@app.route('/global-chat')
def global_chat():
    user_uid = session.get('user_uid')
    if not user_uid:
        return redirect('/')

    selected_language = session.get('selected_language')
    db = firestore.client()

    messages_ref = db.collection(selected_language).order_by('timestamp', direction='DESCENDING').limit(10)
    messages = []
    for message in messages_ref.stream():
        message_data = message.to_dict()
        user_doc = db.collection('users').document(message_data['user']).get()
        if user_doc.exists:
            username = user_doc.to_dict()['username']
            messages.append({'username': username, 'message': message_data['text'], 'user_id': message_data['user']})
            print(messages)

    messages.reverse()
    return render_template('global_chat.html', messages=messages, user_uid=user_uid)


@app.route('/send-message', methods=['POST'])
def send_message():
    message = request.json.get('message')
    if message:

        db = firestore.client()
        selected_language = session.get('selected_language')

        timestamp = datetime.now()

        db.collection(selected_language).add({
            'user': session.get('user_uid'),
            'text': message,
            'timestamp': timestamp
        })
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400


@app.route('/get-messages')
def get_messages():
    def generate():
        db = firestore.client()
        selected_language = session.get('selected_language')
        messages_ref = db.collection(selected_language).order_by('timestamp', direction='desc').limit(10)
        for message in messages_ref.stream():
            yield jsonify(message.to_dict())

    return app.response_class(generate(), mimetype='application/json')


@app.route('/fetch-messages', methods=['GET'])
def fetch_messages():
    # Ensure this code is executed within a Flask request context
    user_uid = session.get('user_uid')
    if not user_uid:
        return jsonify(error='User not authenticated'), 401

    db = firestore.client()
    selected_language = session.get('selected_language')
    messages_ref = db.collection(selected_language).order_by('timestamp', direction='ASCENDING').limit(10)

    messages = []
    for message in messages_ref.stream():
        message_data = message.to_dict()
        user_doc = db.collection('users').document(message_data['user']).get()
        if user_doc.exists:
            username = user_doc.to_dict().get('username')
            if username:
                message_data['username'] = username
            messages.append(message_data)
        else:
            username = 'Deleted User'
            message_data['username'] = username
            messages.append(message_data)

    return jsonify(messages), 200


@app.route('/swipe', methods=['GET'])
def swipe():
    db = firestore.client()
    selected_language = session.get('selected_language')
    users_ref = db.collection('users')

    user_profiles = []

    for user in users_ref.stream():
        user_data = user.to_dict()
        if user_data.get('languages', {}).get(selected_language):
            print(user.id, session.get('user_uid'))
            if user.id != session.get('user_uid'):
                user_profiles.append(user_data)

    print(user_profiles)
    # Convert user profiles to JSON
    user_profiles_json = {
        'users': []
    }

    for user in user_profiles:
        user_profiles_json['users'].append({
            'username': user.get('username'),
            'languages': user.get('languages'),
            'bio': user.get('bio', "null")
        })

    user_profiles_json = user_profiles_json if user_profiles else None

    return render_template('swipe.html', user_profiles=user_profiles_json, selected_language=selected_language)


if __name__ == '__main__':
    app.run(debug=True, port=8000)

