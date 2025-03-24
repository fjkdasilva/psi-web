from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', transports=['polling'])

rooms = {}

@app.route('/')
def index():
    role = request.args.get('role')
    room = request.args.get('room', 'test')
    if role not in ['transmitter', 'receiver']:
        return "Invalid role. Use ?role=transmitter or ?role=receiver", 400
    if room not in rooms:
        rooms[room] = {'data': {'trials': [], 'current_trial': 0}}
    return render_template('index.html', role=role, room=room)

@socketio.on('connect')
def handle_connect():
    emit('connected', {'sid': request.sid})

@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    role = data['role']
    print(f"Server: {role} joining room {room}")
    if room not in rooms:
        rooms[room] = {'data': {'trials': [], 'current_trial': 0}}
    join_room(room)
    emit('joined_room', {'message': f'{role} joined room {room}'}, room=room)
    clients_in_room = len(socketio.server.manager.rooms.get(room, {}).get('/', {}))
    print(f"Server: {clients_in_room} clients in room {room}")
    if clients_in_room == 2 and rooms[room]['data']['current_trial'] == 0:  # Changed >= to ==
        print("Server: Starting trial 1")
        emit('start_trial', {'trial': 1}, room=room)
        rooms[room]['data']['current_trial'] = 1

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
