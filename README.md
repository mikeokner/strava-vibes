# Strava Segment Hunter

A CLI utility to identify easily winnable Strava cycling segments based on attempt count and leader performance data.

## Features

- **Location-based search**: Enter lat/long coordinates (easy to copy from Google Maps)
- **Automatic tile calculation**: Converts coordinates to map tiles automatically
- **Configurable search radius**: Search within 5-50km of your location
- Filter by distance range (meters)
- Filter by leader's heart rate and/or power data
- Filter by number of attempts on segment
- Rate-limited requests to avoid account issues
- Export results to JSON

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python strava_hunter.py --cookie "YOUR_STRAVA_COOKIE" --location "LAT,LON" [options]
```

### Required Arguments

- `--cookie`: Your Strava authentication cookie string
- `--location`: Comma-separated lat,lon coordinates (e.g., "44.95103069303635,-93.0927614972472")

### Optional Arguments

- `--min-distance`: Minimum segment distance in meters (default: 500)
- `--max-distance`: Maximum segment distance in meters (default: 2000)
- `--max-heart-rate`: Maximum leader heart rate (bpm)
- `--max-power`: Maximum leader power (watts)
- `--min-attempts`: Minimum number of attempts (default: 1)
- `--max-attempts`: Maximum number of attempts (default: 50)
- `--radius`: Search radius in kilometers (default: 10)
- `--region-id`: Strava region/area ID (default: 34576447)
- `--output`: Output file for results (JSON format)

### Examples

Find segments around Minneapolis under 1km with fewer than 20 attempts:
```bash
python strava_hunter.py --cookie "YOUR_COOKIE" --location "44.95103069303635,-93.0927614972472" --max-distance 1000 --max-attempts 20
```

Find segments where leader had HR < 160 and power < 250W within 5km:
```bash
python strava_hunter.py --cookie "YOUR_COOKIE" --location "37.7749,-122.4194" --radius 5 --max-heart-rate 160 --max-power 250
```

Search larger area and save results:
```bash
python strava_hunter.py --cookie "YOUR_COOKIE" --location "40.7128,-74.0060" --radius 15 --output results.json
```

## Getting Your Location

1. Go to Google Maps
2. Right-click on your desired location
3. Copy the coordinates (they'll be in the format "lat, lon")
4. Use them with the `--location` parameter

## Getting Your Cookie

1. Open your browser and go to strava.com
2. Log in to your account
3. Open Developer Tools (F12)
4. Go to Application/Storage tab
5. Find the Cookie section
6. Copy the entire cookie string

## Rate Limiting

The tool includes a 1-second delay between requests to avoid overwhelming Strava's servers and prevent account flagging.

## Output

The tool will display found segments with:
- Segment name and distance
- Number of attempts
- Leader information (name, time)
- Leader's heart rate and power (if available)
- Direct link to segment

Results can be saved to JSON format using the `--output` option.