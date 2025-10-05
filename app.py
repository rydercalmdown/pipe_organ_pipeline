import os
import uuid
import threading
from flask import Flask, request, render_template, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
import subprocess
import tempfile
import mido
import pretty_midi
from basic_pitch.inference import predict_and_save
import shutil
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configuration
UPLOAD_FOLDER = '/app/data/uploads'
RESULTS_FOLDER = '/app/data/results'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Store processing status
processing_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def separate_stems(input_path: str, out_dir: str):
    """
    Use Demucs to separate audio into 4 stems: drums, bass, vocals, other.
    """
    print(f"[INFO] Running Demucs on {input_path}")
    subprocess.run([
        "demucs",
        input_path,
        "-o", out_dir
    ], check=True)

    # Demucs puts files in a subfolder
    model_dir = os.path.join(out_dir, "htdemucs")
    track_name = os.path.splitext(os.path.basename(input_path))[0]
    track_dir = os.path.join(model_dir, track_name)
    return {
        "drums": os.path.join(track_dir, "drums.wav"),
        "bass": os.path.join(track_dir, "bass.wav"),
        "vocals": os.path.join(track_dir, "vocals.wav"),
        "other": os.path.join(track_dir, "other.wav")
    }

def transcribe_to_midi(audio_path: str, midi_path: str):
    """
    Run BasicPitch to convert audio to MIDI using command line.
    """
    print(f"[INFO] Running BasicPitch on {audio_path}")
    # Use command line approach - BasicPitch expects: basic-pitch <output_dir> <audio_paths...>
    output_dir = os.path.dirname(midi_path)
    subprocess.run([
        "basic-pitch",
        "--save-midi",
        output_dir,
        audio_path
    ], check=True)
    
    # BasicPitch creates files with _basic_pitch.mid extension, rename if needed
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    generated_midi = os.path.join(output_dir, f"{base_name}_basic_pitch.mid")
    if os.path.exists(generated_midi) and generated_midi != midi_path:
        shutil.move(generated_midi, midi_path)

def merge_midis(midi_files, out_file):
    """
    Merge multiple MIDI files into a single output with organ channel mapping.
    """
    combined = pretty_midi.PrettyMIDI()

    # Organ channel mapping for 4 stems
    channel_map = {
        "drums": {"channel": 0, "name": "Pedal", "program": 0},      # Bass drum on pedal
        "bass": {"channel": 1, "name": "Pedal", "program": 32},      # Bass on pedal (acoustic bass)
        "vocals": {"channel": 2, "name": "Swell", "program": 1},     # Vocals on swell (piano)
        "other": {"channel": 3, "name": "Great", "program": 1}       # Other instruments on great (piano)
    }

    for stem_name, midi_file in midi_files.items():
        if not os.path.exists(midi_file):
            print(f"[WARNING] MIDI file not found: {midi_file}")
            continue
            
        pm = pretty_midi.PrettyMIDI(midi_file)
        config = channel_map.get(stem_name, {"channel": 0, "name": "Unknown", "program": 0})
        
        for inst in pm.instruments:
            # Create a new instrument for the combined MIDI
            new_inst = pretty_midi.Instrument(
                program=config["program"],
                is_drum=(stem_name == "drums"),
                name=f"{config['name']} - {stem_name.title()}"
            )
            
            # Copy and adjust notes
            for note in inst.notes:
                new_note = pretty_midi.Note(
                    velocity=note.velocity,
                    pitch=note.pitch,
                    start=note.start,
                    end=note.end
                )
                
                # Adjust velocities and octaves for organ
                if stem_name == "drums":
                    # Drums: lower velocity, keep in bass range
                    new_note.velocity = max(30, min(int(note.velocity * 0.7), 60))
                    new_note.pitch = max(36, min(note.pitch, 60))  # Bass drum range
                elif stem_name == "bass":
                    # Bass: medium velocity, bass range
                    new_note.velocity = max(50, min(int(note.velocity * 0.8), 80))
                    new_note.pitch = max(36, min(note.pitch, 72))  # Bass range
                elif stem_name == "vocals":
                    # Vocals: higher velocity, melody range
                    new_note.velocity = max(60, min(int(note.velocity * 0.9), 90))
                    new_note.pitch = max(60, min(note.pitch, 96))  # Melody range
                else:  # other
                    # Other: medium velocity, full range
                    new_note.velocity = max(40, min(int(note.velocity * 0.8), 85))
                
                new_inst.notes.append(new_note)
                
            combined.instruments.append(new_inst)

    combined.write(out_file)
    print(f"[INFO] Wrote merged MIDI to {out_file}")

def process_audio_file(job_id, input_file_path, original_filename):
    """
    Process the uploaded audio file in a separate thread.
    """
    try:
        processing_status[job_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Starting audio separation...',
            'started_at': datetime.now().isoformat()
        }
        
        # Create output directories
        track_name = os.path.splitext(original_filename)[0]
        job_dir = os.path.join(app.config['RESULTS_FOLDER'], job_id)
        stems_dir = os.path.join(job_dir, 'stems')
        midi_dir = os.path.join(job_dir, 'midi')
        
        os.makedirs(stems_dir, exist_ok=True)
        os.makedirs(midi_dir, exist_ok=True)
        
        # Step 1: Separate stems
        processing_status[job_id]['message'] = 'Separating audio into stems...'
        processing_status[job_id]['progress'] = 20
        
        stems = separate_stems(input_file_path, stems_dir)
        
        # Copy stems to our output directory for easy access
        stem_outputs = {}
        for stem_name, stem_path in stems.items():
            output_path = os.path.join(stems_dir, f"{track_name}_{stem_name}.wav")
            shutil.copy2(stem_path, output_path)
            stem_outputs[stem_name] = output_path
        
        # Step 2: Transcribe to MIDI
        processing_status[job_id]['message'] = 'Converting stems to MIDI...'
        processing_status[job_id]['progress'] = 50
        
        midi_files = {}
        for i, (stem_name, stem_path) in enumerate(stem_outputs.items()):
            midi_path = os.path.join(midi_dir, f"{stem_name}.mid")
            transcribe_to_midi(stem_path, midi_path)
            midi_files[stem_name] = midi_path
            
            # Update progress
            progress = 50 + (i + 1) * 30 // len(stem_outputs)
            processing_status[job_id]['progress'] = progress
            processing_status[job_id]['message'] = f'Converting {stem_name} to MIDI...'
        
        # Step 3: Merge MIDI files
        processing_status[job_id]['message'] = 'Merging MIDI files...'
        processing_status[job_id]['progress'] = 90
        
        final_output = os.path.join(midi_dir, "combined.mid")
        merge_midis(midi_files, final_output)
        
        # Clean up uploaded file
        os.remove(input_file_path)
        
        # Mark as completed
        processing_status[job_id] = {
            'status': 'completed',
            'progress': 100,
            'message': 'Processing completed successfully!',
            'completed_at': datetime.now().isoformat(),
            'results': {
                'stems': stem_outputs,
                'midi_files': midi_files,
                'combined_midi': final_output,
                'track_name': track_name
            }
        }
        
    except Exception as e:
        processing_status[job_id] = {
            'status': 'error',
            'progress': 0,
            'message': f'Error: {str(e)}',
            'error_at': datetime.now().isoformat()
        }
        # Clean up uploaded file on error
        if os.path.exists(input_file_path):
            os.remove(input_file_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
        file.save(file_path)
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_audio_file,
            args=(job_id, file_path, filename)
        )
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('processing', job_id=job_id))
    else:
        flash('Invalid file type. Please upload MP3, WAV, M4A, or FLAC files.')
        return redirect(url_for('index'))

@app.route('/processing/<job_id>')
def processing(job_id):
    return render_template('processing.html', job_id=job_id)

@app.route('/api/status/<job_id>')
def get_status(job_id):
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(processing_status[job_id])

@app.route('/results/<job_id>')
def results(job_id):
    if job_id not in processing_status:
        flash('Job not found')
        return redirect(url_for('index'))
    
    job_data = processing_status[job_id]
    if job_data['status'] != 'completed':
        flash('Job not completed yet')
        return redirect(url_for('processing', job_id=job_id))
    
    return render_template('results.html', job_id=job_id, job_data=job_data)

@app.route('/download/<job_id>/<file_type>/<filename>')
def download_file(job_id, file_type, filename):
    if job_id not in processing_status:
        return "Job not found", 404
    
    job_data = processing_status[job_id]
    if job_data['status'] != 'completed':
        return "Job not completed", 400
    
    job_dir = os.path.join(app.config['RESULTS_FOLDER'], job_id)
    
    if file_type == 'stem':
        file_path = os.path.join(job_dir, 'stems', filename)
    elif file_type == 'midi':
        file_path = os.path.join(job_dir, 'midi', filename)
    else:
        return "Invalid file type", 400
    
    if not os.path.exists(file_path):
        return "File not found", 404
    
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
