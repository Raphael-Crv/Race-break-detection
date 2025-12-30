# Race Break Detection

A Python script that analyzes GPX files to automatically detect pauses/breaks during running activities using GPS data.

## Features

- **Automatic pause detection** using multiple criteria:
  - Distance traveled over time windows
  - Average pace calculation
  - GPS point density analysis
- **Detailed pause analysis** including:
  - Start/end timestamps and locations
  - Duration and distance during pauses
  - Position in the race (km markers)
  - Average pace during pauses
- **Configurable thresholds** for different activity types
- **Summary statistics** with total distance comparison

## Requirements

- Python 3.6+
- No external dependencies (uses standard library only)

## Installation

Simply download the `break_detection.py` script. No additional packages needed.

## Usage

### Basic Usage
```python
from break_detection import detect_pauses

gpx_file = "path/to/your/file.gpx"
pauses, points = detect_pauses(gpx_file)
```

### Customized Detection
```python
pauses, points = detect_pauses(
    gpx_file,
    threshold_start=30,        # Distance threshold to start pause (meters)
    threshold_end=30,          # Distance threshold to end pause (meters)
    time_window=45,            # Time window for start detection (seconds)
    pace_threshold=15,         # Pace threshold to start pause (min/km)
    pace_threshold_end=20,     # Pace threshold to end pause (min/km)
    nb_points_pace=10,         # Points for pace calculation at start
    nb_points_pace_end=7,      # Points for pace calculation at end
    density_threshold=1.0,     # Point density threshold (points/sec)
    density_window=30          # Time window for density (seconds)
)
```

## How It Works

### Pause Start Detection
A pause is detected when **ALL THREE** conditions are met:
1. Maximum distance traveled over the time window < threshold (default: 30m over 45s)
2. Average pace is slower than threshold (default: > 15 min/km)
3. GPS point density is low (default: < 1.0 points/sec)

### Pause End Detection
A pause ends when **BOTH** conditions are met:
1. Maximum distance traveled exceeds threshold (default: > 30m over 30s)
2. Average pace becomes faster (default: < 20 min/km = running)

## Research & Methodology

This algorithm was developed through extensive testing and iteration. The complete research process, including:
- Initial hypothesis and testing approach
- Parameter tuning with real GPX files
- False positive/negative analysis
- Iterative refinement of detection criteria

**📊 [View detailed research documentation](https://docs.google.com/document/d/1Mf7ShNMzFmlTMIcY1i9Uo3ZHJUqQJ0eA4o_vhFmvhak/edit?usp=sharing)**

### Key Findings from Research
- Point density is crucial to avoid false pauses (distinguishes GPS drift from actual stops)
- Speed threshold prevents false detection during normal running
- Distance-based exit detection is more reliable than pace-based
- Reactivity varies with pre-pause pace (5-30 seconds detection time)

### Testing Methodology
The algorithm was validated on:
- 7+ stationary test recordings (5-20 minutes each)
- 3 walking activities with intentional breaks
- Real running activities with known pause locations
- Edge cases (small movements, GPS drift simulation)
   

## Output Example
```
⏸️  Break detected: 2024-01-15 10:23:45
   At distance: 2453.67m (2.454km)
   Duration: 120 seconds (2.0 minutes)
   Average pace during break (from GPX): 45:23 min/km

=== BREAK SUMMARY ===
Total breaks detected: 3

Break #1:
  Position in race: from 2.454km to 2.467km
  Time from start: 15:23
  Duration: 120s (2.0 min)
  Distance during break: 13.45m (0.013 km)
  Average pace during break: 45:23 min/km

=== DISTANCE COMPARISON ===
Total GPS distance: 5234.56m (5.235 km)
Distance during breaks: 45.23m (0.045 km)
Distance without breaks: 5189.33m (5.189 km)
```

## Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threshold_start` | 30 | Max distance (m) over time window to start pause |
| `threshold_end` | 30 | Min distance (m) over time window to end pause |
| `time_window` | 45 | Time window (s) for start detection |
| `time_window_end` | 30 | Time window (s) for end detection |
| `pace_threshold` | 15 | Min pace (min/km) to trigger pause start |
| `pace_threshold_end` | 20 | Max pace (min/km) to trigger pause end |
| `nb_points_pace` | 10 | Number of points for start pace calculation |
| `nb_points_pace_end` | 7 | Number of points for end pace calculation |
| `density_threshold` | 1.0 | Max point density (points/s) for pause start |
| `density_window` | 30 | Time window (s) for density calculation |

## Use Cases

- **Training analysis**: Identify water breaks, rest periods, traffic lights
- **Race analysis**: Detect aid station stops, bathroom breaks
- **Activity cleanup**: Remove pauses for accurate pace calculations
- **GPS data processing**: Prepare data for performance analysis

## License

Free to use and modify.

## Author

Raphael-Crv
