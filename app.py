from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', engineio_logger=True)

rooms = {}  # {room: {'data': {'trials': [], 'current_trial': 0, 'max_trials': 10}, 'clients': {sid: role}}}

@app.route('/')
def index():
    role = request.args.get('role')
    room = request.args.get('room', 'test')
    if role not in ['transmitter', 'receiver']:
        return "Invalid role. Use ?role=transmitter or ?role=receiver", 400
    if room not in rooms:
        rooms[room] = {'data': {'trials': [], 'current_trial': 0, 'max_trials': 10}, 'clients': {}}
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
        rooms[room] = {'data': {'trials': [], 'current_trial': 0, 'max_trials': 10}, 'clients': {}}
    
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
    
    # Start trials if we have at least one pair
    if len(transmitters) >= 1 and len(receivers) >= 1 and rooms[room]['data']['current_trial'] == 0:
        start_next_trial(room, transmitters[0], receivers[0])

@socketio.on('submit_result')
def handle_result(data):
    room = data['room']
    trial = data['trial']
    transmitter_symbol = data.get('transmitter_symbol')  # Sent by transmitter
    receiver_symbol = data.get('receiver_symbol')       # Sent by receiver
    sid = request.sid
    role = rooms[room]['clients'][sid]
    
    # Store result
    trial_data = next((t for t in rooms[room]['data']['trials'] if t['trial'] == trial), None)
    if not trial_data:
        trial_data = {'trial': trial, 'transmitter_symbol': None, 'receiver_symbol': None}
        rooms[room]['data']['trials'].append(trial_data)
    
    if role == 'transmitter':
        trial_data['transmitter_symbol'] = transmitter_symbol
    elif role == 'receiver':
        trial_data['receiver_symbol'] = receiver_symbol
    
    # If both results are in, move to next trial
    if trial_data['transmitter_symbol'] is not None and trial_data['receiver_symbol'] is not None:
        print(f"Server: Trial {trial} complete: T={trial_data['transmitter_symbol']}, "
              f"R={trial_data['receiver_symbol']}, Correct={trial_data['transmitter_symbol'] == trial_data['receiver_symbol']}")
        start_next_trial(room, rooms[room]['clients'].keys()[0], rooms[room]['clients'].keys()[1])

def start_next_trial(room, t_sid, r_sid):
    current = rooms[room]['data']['current_trial']
    max_trials = rooms[room]['data']['max_trials']
    if current < max_trials:
        trial = current + 1
        rooms[room]['data']['current_trial'] = trial
        print(f"Server: Starting trial {trial} for pair {t_sid} (T) and {r_sid} (R)")
        emit('start_trial', {'trial': trial, 'pair': [t_sid, r_sid]}, room=room)
    else:
        print(f"Server: All {max_trials} trials complete for room {room}")
        emit('trials_complete', {'results': rooms[room]['data']['trials']}, room=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
