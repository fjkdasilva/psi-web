from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', engineio_logger=True)

rooms = {}

@app.route('/')
def index():
    role = request.args.get('role')
    room = request.args.get('room', 'test')
    if role not in ['transmitter', 'receiver']:
        return "Invalid role. Use ?role=transmitter or ?role=receiver", 400
    if room not in rooms:
        rooms[room] = {'data': {'trials': [], 'current_trial': 0}}
    print(f"Server: Serving {role} in room {room}")
    return render_template('index.html', role=role, room=room)

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    print(f"Server: Client connected: {sid}")
    emit('connected', {'sid': sid})

@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    role = data['role']
    sid = request.sid
    print(f"Server: {role} ({sid}) joining room {room}")
    if room not in rooms:
        rooms[room] = {'data': {'trials': [], 'current_trial': 0}}
    join_room(room)
    emit('joined_room', {'message': f'{role} joined room {room}'}, room=room)
    # Get all rooms this client is in
    client_rooms = socketio.server.rooms(sid)
    # Count clients in the specific room
    clients_in_room = sum(1 for s in socketio.server.manager.get_participants(room, namespace='/') if s != sid) + 1
    print(f"Server: {clients_in_room} clients in room {room}: {list(socketio.server.manager.get_participants(room, namespace='/'))}")
    if clients_in_room == 2 and rooms[room]['data']['current_trial'] == 0:
        print("Server: Starting trial 1")
        emit('start_trial', {'trial': 1}, room=room)
        rooms[room]['data']['current_trial'] = 1
    else:
        print(f"Server: Not starting trial - {clients_in_room} clients, trial {rooms[room]['data']['current_trial']}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
