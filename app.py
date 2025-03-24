from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', engineio_logger=True)

rooms = {}  # {room: {'data': {'trials': [], 'current_trial': 0}, 'clients': {sid: role}}}

@app.route('/')
def index():
    role = request.args.get('role')
    room = request.args.get('room', 'test')
    if role not in ['transmitter', 'receiver']:
        return "Invalid role. Use ?role=transmitter or ?role=receiver", 400
    if room not in rooms:
        rooms[room] = {'data': {'trials': [], 'current_trial': 0}, 'clients': {}}
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
        rooms[room] = {'data': {'trials': [], 'current_trial': 0}, 'clients': {}}
    
    # Add client to room with role
    join_room(room)
    rooms[room]['clients'][sid] = role
    emit('joined_room', {'message': f'{role} joined room {room}'}, room=room)
    
    # Count transmitters and receivers
    clients = rooms[room]['clients']
    transmitters = [sid for sid, r in clients.items() if r == 'transmitter']
    receivers = [sid for sid, r in clients.items() if r == 'receiver']
    print(f"Server: {len(clients)} clients in room {room}: {list(clients.keys())} "
          f"(T: {len(transmitters)}, R: {len(receivers)})")
    
    # If we have at least one unpaired transmitter and receiver, pair them and start a trial
    if transmitters and receivers and rooms[room]['data']['current_trial'] < len(transmitters):
        trial = rooms[room]['data']['current_trial'] + 1
        t_sid = transmitters[trial - 1]  # Pair with the next available transmitter
        r_sid = receivers[trial - 1]     # Pair with the next available receiver
        print(f"Server: Starting trial {trial} for pair {t_sid} (T) and {r_sid} (R)")
        emit('start_trial', {'trial': trial, 'pair': [t_sid, r_sid]}, room=room)
        rooms[room]['data']['current_trial'] = trial
    else:
        print(f"Server: Not starting trial - T: {len(transmitters)}, R: {len(receivers)}, "
              f"trial {rooms[room]['data']['current_trial']}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
