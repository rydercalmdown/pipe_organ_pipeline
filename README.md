# Organ MIDI Pipeline
A Python pipeline that converts audio files to MIDI format optimized for organ music, using Demucs for audio separation and BasicPitch for transcription.

## Features

- **Audio Separation**: Uses Demucs to separate vocals and instrumental parts
- **MIDI Transcription**: Converts audio to MIDI using BasicPitch
- **Organ Optimization**: Maps tracks to organ channels (Great, Swell, Pedal)
- **UV Package Management**: Uses UV for fast dependency management

## Setup

1. Install UV (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install dependencies:
   ```bash
   make install
   # or
   uv sync
   ```

3. Add your audio file to the `originals/` directory:
   ```bash
   cp /path/to/your/audio.mp3 originals/your_song.mp3
   ```

## Usage

Run the pipeline:
```bash
# Using default file (originals/mrbrightside.mp3)
make run

# Or specify a different file
uv run python pipeline.py originals/your_song.mp3
```

This will:
1. Separate the audio file into 4 stems using Demucs (drums, bass, vocals, other)
2. Save separated audio files to `stems/<song_name>/` directory
3. Transcribe each stem to MIDI using BasicPitch
4. Save individual MIDI files to `midi_files/<song_name>/` directory
5. Merge the MIDI files with organ channel mapping
6. Output final `midi_files/<song_name>/combined.mid`

## Output Files

After running the pipeline, you'll get:

### Final Output
- `midi_files/<song_name>/combined.mid` - Final merged MIDI file optimized for organ

### Intermediate Files
- `stems/<song_name>/<song_name>_drums.wav` - Separated drums audio
- `stems/<song_name>/<song_name>_bass.wav` - Separated bass audio
- `stems/<song_name>/<song_name>_vocals.wav` - Separated vocals audio
- `stems/<song_name>/<song_name>_other.wav` - Separated other instruments audio
- `midi_files/<song_name>/drums.mid` - MIDI transcription of drums
- `midi_files/<song_name>/bass.mid` - MIDI transcription of bass
- `midi_files/<song_name>/vocals.mid` - MIDI transcription of vocals
- `midi_files/<song_name>/other.mid` - MIDI transcription of other instruments

### MIDI Channel Mapping
The generated MIDI file will have:
- **Channel 0 (Pedal)**: Drums - Bass drum sounds
- **Channel 1 (Pedal)**: Bass - Acoustic bass sounds
- **Channel 2 (Swell)**: Vocals - Piano sounds in melody range
- **Channel 3 (Great)**: Other - Piano sounds for accompaniment

## Dependencies

- demucs==4.0.0
- basic-pitch==0.3.0
- torch
- torchaudio
- mido
- pretty_midi
