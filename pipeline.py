import subprocess
import os
import sys
import tempfile
import mido
import pretty_midi
from basic_pitch.inference import predict_and_save

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
        import shutil
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

def main():
    # Get input file from command line argument or use default
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "originals/mrbrightside.mp3"
    
    if not os.path.exists(input_file):
        print(f"Missing input file: {input_file}")
        print(f"Usage: python pipeline.py <input_file>")
        print(f"Default: originals/mrbrightside.mp3")
        sys.exit(1)

    # Create output directories based on original filename
    track_name = os.path.splitext(os.path.basename(input_file))[0]
    stems_dir = os.path.join("stems", track_name)
    midi_dir = os.path.join("midi_files", track_name)
    os.makedirs(stems_dir, exist_ok=True)
    os.makedirs(midi_dir, exist_ok=True)

    # Use existing stems if they exist, otherwise separate
    existing_stems = {
        "drums": os.path.join(stems_dir, f"{track_name}_drums.wav"),
        "bass": os.path.join(stems_dir, f"{track_name}_bass.wav"),
        "vocals": os.path.join(stems_dir, f"{track_name}_vocals.wav"),
        "other": os.path.join(stems_dir, f"{track_name}_other.wav")
    }
    
    # Check if stems already exist
    stems_exist = all(os.path.exists(path) for path in existing_stems.values())
    
    if stems_exist:
        print(f"[INFO] Using existing stems:")
        for stem_name, stem_path in existing_stems.items():
            print(f"  - {stem_name.title()}: {stem_path}")
        stems = existing_stems
    else:
        print(f"[INFO] Separating audio into 4 stems...")
        stems = separate_stems(input_file, stems_dir)
        
        # Copy stems to our output directory for easy access
        import shutil
        stem_outputs = {}
        for stem_name, stem_path in stems.items():
            output_path = os.path.join(stems_dir, f"{track_name}_{stem_name}.wav")
            shutil.copy2(stem_path, output_path)
            stem_outputs[stem_name] = output_path
        
        print(f"[INFO] Saved separated stems:")
        for stem_name, output_path in stem_outputs.items():
            print(f"  - {stem_name.title()}: {output_path}")

    # Transcribe each stem → MIDI
    midi_files = {}
    for stem_name, stem_path in stems.items():
        midi_path = os.path.join(midi_dir, f"{stem_name}.mid")
        transcribe_to_midi(stem_path, midi_path)
        midi_files[stem_name] = midi_path
    
    print(f"[INFO] Saved individual MIDI files:")
    for stem_name, midi_path in midi_files.items():
        print(f"  - {stem_name.title()} MIDI: {midi_path}")

        # Merge to final
        final_output = os.path.join(midi_dir, "combined.mid")
        merge_midis(midi_files, final_output)

if __name__ == "__main__":
    main()
