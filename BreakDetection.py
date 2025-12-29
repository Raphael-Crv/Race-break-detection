import xml.etree.ElementTree as ET
import math
from datetime import datetime, timedelta

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two geographic points using the Haversine formula.
    Returns the distance in meters.
    """
    # Earth's radius in meters
    R = 6371000.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def extract_gpx_points(gpx_file):
    """
    Extract all points (latitude, longitude, timestamp) from a GPX file.
    """
    tree = ET.parse(gpx_file)
    root = tree.getroot()
    
    # Handle GPX namespaces
    namespace = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    points = []
    
    # Extract trackpoints with timestamps
    for trkpt in root.findall('.//gpx:trkpt', namespace):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        
        # Extract timestamp if available
        time_elem = trkpt.find('gpx:time', namespace)
        timestamp = None
        if time_elem is not None and time_elem.text:
            try:
                timestamp = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00'))
            except:
                timestamp = None
        
        if timestamp:  # Only keep points with timestamps
            points.append((lat, lon, timestamp))
    
    return points

def calculate_max_distance_window(points, start_index, duration_seconds):
    """
    Calculate the maximum distance between any two points within a time window
    starting from a given index.
    Returns the maximum distance in meters.
    """
    start_point = points[start_index]
    start_time = start_point[2]
    end_time = start_time + timedelta(seconds=duration_seconds)
    
    # Get all points within the time window
    window_points = [start_point]
    for i in range(start_index + 1, len(points)):
        if points[i][2] <= end_time:
            window_points.append(points[i])
        else:
            break
    
    # Calculate maximum distance between any two points in the window
    max_distance = 0
    for i, (lat1, lon1, _) in enumerate(window_points):
        for lat2, lon2, _ in window_points[i+1:]:
            distance = haversine(lat1, lon1, lat2, lon2)
            if distance > max_distance:
                max_distance = distance
    
    return max_distance

def calculate_average_pace_last_points(points, index, nb_points=10):
    """
    Calculate the average pace over the last N points before the given index.
    Returns pace in min/km. Returns None if not enough data.
    """
    if index < nb_points:
        # Not enough points, use all available points
        start_index = 0
    else:
        start_index = index - nb_points
    
    if start_index >= index:
        return None
    
    # Calculate total distance and time
    total_distance = 0
    total_time = 0
    
    for i in range(start_index, index):
        lat1, lon1, ts1 = points[i]
        lat2, lon2, ts2 = points[i + 1]
        
        total_distance += haversine(lat1, lon1, lat2, lon2)
        total_time += (ts2 - ts1).total_seconds()
    
    if total_distance == 0 or total_time == 0:
        return None
    
    # Calculate pace in min/km
    pace = (total_time / total_distance) * 1000 / 60
    return pace

def calculate_point_density_last_seconds(points, index, duration_seconds=30):
    """
    Calculate point density (points per second) over the last N seconds before the given index.
    Returns points per second. Returns None if not enough data.
    """
    if index == 0:
        return None
    
    current_time = points[index][2]
    start_time = current_time - timedelta(seconds=duration_seconds)
    
    # Count points in the time window
    nb_window_points = 0
    for i in range(index, -1, -1):
        if points[i][2] >= start_time:
            nb_window_points += 1
        else:
            break
    
    if nb_window_points < 2:
        return None
    
    # Calculate actual time span
    actual_time = (points[index][2] - points[index - nb_window_points + 1][2]).total_seconds()
    
    if actual_time == 0:
        return None
    
    # Return points per second
    density = nb_window_points / actual_time
    return density

def detect_pauses(gpx_file, threshold_start=30, threshold_end=30, time_window=45, 
                  pace_threshold=15, nb_points_pace=10, 
                  density_threshold=1.0, density_window=30, time_window_end=30,
                  pace_threshold_end=20, nb_points_pace_end=7):
    """
    Detect pauses in a GPX track.
    
    Parameters:
    - threshold_start: distance threshold in meters to start a pause (presently 30m)
    - threshold_end: distance threshold in meters to end a pause (presently 30m)
    - time_window: time window in seconds to check for START of pause (presently 45s)
    - pace_threshold: maximum pace in min/km before pause detection (presently 15 min/km)
    - nb_points_pace: number of points to calculate average speed for START (presently 10)
    - density_threshold: maximum point density in points/sec to detect pause START (presently 1.0)
    - density_window: time window in seconds for density calculation to START pause (presently 30s)
    - time_window_end: time window in seconds to check distance for END of pause (presently 30s)
    - pace_threshold_end: minimum pace in min/km to end pause (presently 20 min/km - must be faster)
    - nb_points_pace_end: number of points to calculate average speed for END (presently 7)
    
    Pause ends when BOTH conditions are met:
    - distance increases above threshold_end over time_window_end
    - pace becomes faster than pace_threshold_end over nb_points_pace_end points
    
    Returns a list of pauses with start time, end time, duration, and distance during pause.
    """
    points = extract_gpx_points(gpx_file)
    
    if len(points) < 2:
        print("Error: Not enough points with timestamps in the GPX file.")
        return [], points
    
    print(f"Analyzing {len(points)} points for breaks...")
    print(f"Break starts when:")
    print(f"  - Max distance over {time_window}s < {threshold_start}m")
    print(f"  - Average pace over last {nb_points_pace} points > {pace_threshold} min/km (slower)")
    print(f"  - Point density over last {density_window}s < {density_threshold} points/sec")
    print(f"Break ends when BOTH:")
    print(f"  - Max distance over {time_window_end}s > {threshold_end}m")
    print(f"  - AND average pace over last {nb_points_pace_end} points < {pace_threshold_end} min/km (faster)\n")
    
    # Store the start time of the activity (first point)
    activity_start_time = points[0][2]
    
    # Pre-calculate cumulative distance at each point
    cumulative_distances = [0]
    for i in range(len(points) - 1):
        lat1, lon1, _ = points[i]
        lat2, lon2, _ = points[i+1]
        cumulative_distances.append(cumulative_distances[-1] + haversine(lat1, lon1, lat2, lon2))
    
    pauses = []
    in_pause = False
    pause_start = None
    pause_start_index = None
    pause_start_distance = None
    i = 0
    
    while i < len(points):
        current_point = points[i]
        
        if not in_pause:
            # Check if we should start a pause
            max_distance = calculate_max_distance_window(points, i, time_window)
            avg_pace = calculate_average_pace_last_points(points, i, nb_points_pace)
            point_density = calculate_point_density_last_seconds(points, i, density_window)
            
            # Three criteria to start pause:
            # 1. Max distance over time window is below threshold
            distance_criterion = max_distance < threshold_start
            
            # 2. Average pace is slower than threshold (or None if not enough data)
            pace_criterion = (avg_pace is None) or (avg_pace > pace_threshold)
            
            # 3. Point density is below threshold (or None if not enough data)
            density_criterion = (point_density is None) or (point_density < density_threshold)
            
            # We start pause when ALL THREE criteria are met
            if distance_criterion and pace_criterion and density_criterion:
                in_pause = True
                pause_start = current_point
                pause_start_index = i
                pause_start_distance = cumulative_distances[i]
                
                print(f"⏸️  Break detected: {current_point[2]}")
                print(f"   At distance: {pause_start_distance:.2f}m ({pause_start_distance/1000:.3f}km)")
                print(f"   Max distance over {time_window}s: {max_distance:.2f}m")
                if avg_pace is not None:
                    print(f"   Average pace: {avg_pace:.2f} min/km (slower than {pace_threshold} min/km)")
                else:
                    print(f"   Average pace: Not enough data (assumed slower than {pace_threshold} min/km)")
                if point_density is not None:
                    print(f"   Point density: {point_density:.3f} points/sec (lower than {density_threshold} points/sec)")
                else:
                    print(f"   Point density: Not enough data (assumed lower than {density_threshold} points/sec)")
        
        else:
            # Check if we should end the pause - TWO criteria must BOTH be met
            max_distance = calculate_max_distance_window(points, i, time_window_end)
            avg_pace = calculate_average_pace_last_points(points, i, nb_points_pace_end)
            
            # Criterion 1: Max distance over time window exceeds threshold
            distance_criterion = max_distance > threshold_end
            
            # Criterion 2: Average pace is faster than threshold (excluding None case)
            pace_criterion = (avg_pace is not None) and (avg_pace < pace_threshold_end)
            
            # We end pause when BOTH criteria are met
            if distance_criterion and pace_criterion:
                pause_end = current_point
                pause_end_index = i
                pause_end_distance = cumulative_distances[i]
                duration = (pause_end[2] - pause_start[2]).total_seconds()
                
                # Calculate distance traveled during pause
                distance_during_pause = 0
                for j in range(pause_start_index, pause_end_index):
                    lat1, lon1, _ = points[j]
                    lat2, lon2, _ = points[j+1]
                    distance_during_pause += haversine(lat1, lon1, lat2, lon2)
                
                # Calculate time from start of activity
                time_from_start = (pause_start[2] - activity_start_time).total_seconds()
                
                pause_info = {
                    'start': pause_start[2],
                    'end': pause_end[2],
                    'duration_seconds': duration,
                    'time_from_start_seconds': time_from_start,
                    'start_coords': (pause_start[0], pause_start[1]),
                    'end_coords': (pause_end[0], pause_end[1]),
                    'distance_meters': distance_during_pause,
                    'start_index': pause_start_index,
                    'end_index': pause_end_index,
                    'distance_start_km': pause_start_distance / 1000,
                    'distance_end_km': pause_end_distance / 1000,
                    'nb_points': pause_end_index - pause_start_index + 1
                }
                pauses.append(pause_info)
                
                print(f"▶️  Break ended: {pause_end[2]}")
                print(f"   At distance: {pause_end_distance:.2f}m ({pause_end_distance/1000:.3f}km)")
                print(f"   Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)")
                print(f"   Distance during break: {distance_during_pause:.2f}m")
                print(f"   Max distance over {time_window_end}s: {max_distance:.2f}m (> {threshold_end}m)")
                print(f"   Average pace: {avg_pace:.2f} min/km (< {pace_threshold_end} min/km = running)\n")
                
                in_pause = False
                pause_start = None
                pause_start_index = None
                pause_start_distance = None
        
        i += 1
    
    # Handle case where track ends during a pause
    if in_pause:
        pause_end = points[-1]
        pause_end_index = len(points) - 1
        pause_end_distance = cumulative_distances[pause_end_index]
        duration = (pause_end[2] - pause_start[2]).total_seconds()
        
        # Calculate distance traveled during pause
        distance_during_pause = 0
        for j in range(pause_start_index, pause_end_index):
            lat1, lon1, _ = points[j]
            lat2, lon2, _ = points[j+1]
            distance_during_pause += haversine(lat1, lon1, lat2, lon2)
        
        # Calculate time from start of activity
        time_from_start = (pause_start[2] - activity_start_time).total_seconds()
        
        pause_info = {
            'start': pause_start[2],
            'end': pause_end[2],
            'duration_seconds': duration,
            'time_from_start_seconds': time_from_start,
            'start_coords': (pause_start[0], pause_start[1]),
            'end_coords': (pause_end[0], pause_end[1]),
            'distance_meters': distance_during_pause,
            'start_index': pause_start_index,
            'end_index': pause_end_index,
            'distance_start_km': pause_start_distance / 1000,
            'distance_end_km': pause_end_distance / 1000,
            'nb_points': pause_end_index - pause_start_index + 1
        }
        pauses.append(pause_info)
        
        print(f"▶️  Break ended at end of track: {pause_end[2]}")
        print(f"   At distance: {pause_end_distance:.2f}m ({pause_end_distance/1000:.3f}km)")
        print(f"   Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)")
        print(f"   Distance during break: {distance_during_pause:.2f}m\n")
    
    return pauses, points

def calculate_total_distance(gpx_file):
    """
    Calculate the total distance of the GPS track.
    Returns distance in meters.
    """
    points = extract_gpx_points(gpx_file)
    
    if len(points) < 2:
        return 0
    
    total_distance = 0
    for i in range(len(points) - 1):
        lat1, lon1, _ = points[i]
        lat2, lon2, _ = points[i+1]
        total_distance += haversine(lat1, lon1, lat2, lon2)
    
    return total_distance

def calculate_average_pace_during_pause(points, start_index, end_index):
    """
    Calculate the average pace during a pause from instantaneous speeds.
    Calculates speed for each segment, then averages them.
    Returns pace in min/km format.
    """
    if not points or start_index >= end_index:
        return None
    
    # Calculate instantaneous pace for each segment
    instantaneous_paces = []
    
    for i in range(start_index, end_index):
        lat1, lon1, ts1 = points[i]
        lat2, lon2, ts2 = points[i+1]
        
        # Calculate distance for this segment
        distance_meters = haversine(lat1, lon1, lat2, lon2)
        
        # Calculate time for this segment
        duration_seconds = (ts2 - ts1).total_seconds()
        
        # Avoid division by zero
        if distance_meters > 0 and duration_seconds > 0:
            # Calculate instantaneous pace (min/km) for this segment
            pace_segment = (duration_seconds / distance_meters) * 1000 / 60
            instantaneous_paces.append(pace_segment)
    
    # Return the average of all instantaneous paces
    if len(instantaneous_paces) == 0:
        return None
    
    average_pace = sum(instantaneous_paces) / len(instantaneous_paces)
    return average_pace

def format_pace(pace_min_per_km):
    """
    Format pace from decimal minutes to MM:SS format.
    """
    minutes = int(pace_min_per_km)
    seconds = int((pace_min_per_km - minutes) * 60)
    return f"{minutes}:{seconds:02d}"

def format_time(seconds):
    """
    Format time from seconds to HH:MM:SS or MM:SS format.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

# Usage
if __name__ == "__main__":
    gpx_file = r"C:\OuiRace\Fichiers gpx\30secRun1minBreak30secBreak.gpx"
    
    try:
        # Calculate total GPS distance
        total_gps_distance = calculate_total_distance(gpx_file)
        
        # Detect pauses and get points
        pauses, points = detect_pauses(
            gpx_file, 
            threshold_start=30,        # Distance threshold to START pause: < 30m over 45s
            threshold_end=30,          # Distance threshold to END pause: > 30m over 30s
            time_window=45,            # Time window for START: 45 seconds
            pace_threshold=15,         # Pace threshold to START: > 15 min/km (slower)
            nb_points_pace=10,         # Number of points for START pace check: 10 points
            density_threshold=1.0,     # Density threshold to START: < 1.0 points/sec
            density_window=30,         # Time window for START density: 30 seconds
            time_window_end=30,        # Time window for END: 30 seconds (shorter to avoid anticipating)
            pace_threshold_end=20,     # Pace threshold to END: < 20 min/km (faster than 20 = running)
            nb_points_pace_end=7       # Number of points for END pace check: 7 points
        )
        
        print("\n" + "="*60)
        print("=== BREAK SUMMARY ===")
        print("="*60)
        
        if pauses:
            print(f"Total breaks detected: {len(pauses)}\n")
            
            total_pause_time = sum(p['duration_seconds'] for p in pauses)
            total_pause_distance = sum(p['distance_meters'] for p in pauses)
            
            for i, pause in enumerate(pauses, 1):
                print(f"Break #{i}:")
                print(f"  Position in race: from {pause['distance_start_km']:.3f}km to {pause['distance_end_km']:.3f}km")
                print(f"  Time from start: {format_time(pause['time_from_start_seconds'])}")
                print(f"  Start: {pause['start']}")
                print(f"  End: {pause['end']}")
                print(f"  Duration: {pause['duration_seconds']:.0f}s ({pause['duration_seconds']/60:.1f} min)")
                print(f"  Distance during break: {pause['distance_meters']:.2f}m ({pause['distance_meters']/1000:.3f} km)")
                print(f"  Location: {pause['start_coords'][0]:.6f}, {pause['start_coords'][1]:.6f}")
                
                # Calculate point density (seconds per point)
                nb_points = pause['nb_points']
                if nb_points > 1:
                    point_density = pause['duration_seconds'] / (nb_points - 1)
                    print(f"  Point density: 1 point every {point_density:.2f} seconds ({nb_points} points total)")
                
                # Calculate and display average pace during pause from GPX data
                avg_pace = calculate_average_pace_during_pause(points, pause['start_index'], pause['end_index'])
                if avg_pace:
                    print(f"  Average pace during break (from GPX): {format_pace(avg_pace)} min/km")
                
                print()
            
            print(f"Total break time: {total_pause_time:.0f}s ({total_pause_time/60:.1f} min)")
            print(f"Total distance during breaks: {total_pause_distance:.2f}m ({total_pause_distance/1000:.3f} km)")
        else:
            print("No breaks detected in this track.")
            total_pause_distance = 0
        
        # Display distance comparison
        print("\n" + "="*60)
        print("=== DISTANCE COMPARISON ===")
        print("="*60)
        print(f"Total GPS distance: {total_gps_distance:.2f}m ({total_gps_distance/1000:.3f} km)")
        print(f"Distance during breaks: {total_pause_distance:.2f}m ({total_pause_distance/1000:.3f} km)")
        print(f"Distance without breaks: {total_gps_distance - total_pause_distance:.2f}m ({(total_gps_distance - total_pause_distance)/1000:.3f} km)")
        
        if total_gps_distance > 0:
            pause_percentage = (total_pause_distance / total_gps_distance) * 100
            print(f"Percentage of distance during breaks: {pause_percentage:.2f}%")
    
    except FileNotFoundError:
        print(f"Error: File '{gpx_file}' not found.")
    except ET.ParseError:
        print(f"Error: File '{gpx_file}' is not a valid GPX file.")
    except Exception as e:
        print(f"Unexpected error: {e}")