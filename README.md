# 🎯 Strava Segment Hunter 🚵

![KOMs Won](./badges/koms-won.svg) ![Top Tens](./badges/top-tens.svg)

A CLI utility to identify easily winnable Strava cycling segments based on
attempt count and leader performance data.

Vibe-coded with Claude Code.

```console
$ python strava_hunter.py --cookie '<VALUE>' --location '38.63967708152421, -90.28551754879541' --radius 15
🗺️  Searching around (38.63967708152421, -90.28551754879541) with radius 15.0km
📍 Found 9 tiles to search
  Fetching segments from tiles...
Found 113 segments to analyze
  Fetching segment details...           ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Analyzing segments for winnability... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╸

🎯 Found 11 winnable segments!
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🏁 Segment                             ┃ 📏 Distance ┃ 👥 Attempts ┃ 🥇 Leader                  ┃ 🕐 Time ┃   💗 HR ┃ ⚡ Power ┃ 🔗 URL                                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 6 Revs on Ze Roundabout                │       1405m │          40 │ Andy Atchison              │    0:24 │         │          │ https://www.strava.com/segments/19578962 │
│ Delmar 170                             │        831m │         139 │ Robin Zünd                 │    1:04 │ 119 bpm │    ⚡94W │ https://www.strava.com/segments/5642798  │
│ Ruth Loop                              │        564m │         175 │ Jon Okenfuss               │    1:57 │ 173 bpm │   ⚡246W │ https://www.strava.com/segments/13847924 │
│ loopy to Midland                       │       1310m │          32 │ Chris Hulse                │    1:59 │         │   ⚡182W │ https://www.strava.com/segments/38743879 │
│ Eager Rd - Brentwood to Hanley w/ loop │       1232m │          26 │ Ben Rothacker              │    1:57 │         │   ⚡237W │ https://www.strava.com/segments/14022312 │
│ Over the Creek and up the Hill         │       1320m │         103 │ Evan Wykes                 │    2:13 │         │   ⚡281W │ https://www.strava.com/segments/34489938 │
│ SLOP/SLAAP Hill                        │       1038m │         193 │ Micah Goulet               │    1:45 │         │     412W │ https://www.strava.com/segments/1862655  │
│ Sulphur Hill                           │        557m │         130 │ Evan Wykes                 │    1:04 │         │   ⚡450W │ https://www.strava.com/segments/32543027 │
│ Meramec - Spring to Broadway           │       1785m │         171 │ The Derek  Loudermilk Show │    3:08 │         │   ⚡241W │ https://www.strava.com/segments/9241959  │
│ Oak Hill - Arsenal to Chippewa         │       1530m │         186 │ Matt F.                    │    2:20 │ 154 bpm │   ⚡267W │ https://www.strava.com/segments/9258750  │
│ Crittenden Chug                        │        574m │          57 │ Hugo Gonzalez              │    1:07 │ 160 bpm │          │ https://www.strava.com/segments/7537772  │
└────────────────────────────────────────┴─────────────┴─────────────┴────────────────────────────┴─────────┴─────────┴──────────┴──────────────────────────────────────────┘
```

## 🚨 Important Disclaimer

This tool is for educational and personal use only. Users are responsible for:
- Respecting Strava's Terms of Service
- Not overwhelming their servers with excessive requests
- Using appropriate rate limiting (built-in 1-second delays)
- Ensuring their usage complies with applicable laws and regulations

The authors are not responsible for any misuse of this tool or resulting account restrictions.

## Features

- **Location-based search**: Enter lat/long coordinates (easy to copy from Google Maps)
- **Configurable search radius**: Search within 5-50km of your location
- Filter by distance range (meters)
- Filter by leader's heart rate and/or power data
- Filter by number of attempts on segment
- Export results to JSON

## Installation

Requirements: Python 3.10+

```console
pip install -r requirements.txt
```

## Usage

```console
python strava_hunter.py --cookie '<YOUR_STRAVA_COOKIE>' --location '<LAT,LON>' [options]
```

### Getting Your Location

1. Go to Google Maps
2. Right-click on your desired location
3. Copy the coordinates (they'll be in the format 'lat, lon' like '38.63683, -90.28304').
4. Use them with the `--location` parameter

### Getting Your Cookie

1. Open your browser and go to strava.com
2. Log in to your account
3. Open Developer Tools (F12)
4. Go to 'Network' tab
5. Find a request to 'graphql.strava.com' and click on it
6. Copy the entire cookie string in the Request Headers. It should start with `_strava4_session=`.

### Required Arguments

- `--cookie`: Your Strava authentication cookie string
- `--location`: Comma-separated lat,lon coordinates (e.g., '38.63683928705081, -90.28304510572536')

### Optional Arguments

- `--min-distance`: Minimum segment distance in meters (default: 500)
- `--max-distance`: Maximum segment distance in meters (default: 2000)
- `--max-heart-rate`: Maximum leader heart rate (bpm)
- `--max-power`: Maximum leader power (watts)
- `--min-attempts`: Minimum number of attempts (default: 1)
- `--max-attempts`: Maximum number of attempts (default: 50)
- `--radius`: Search radius in kilometers (default: 10)
- `--region-id`: Strava region/area ID (default: 34576447 - should be good at least in the US)
- `--output`: Output file for results (JSON format)

### Examples

Find segments around St. Louis under 1km with fewer than 20 attempts:
```console
python strava_hunter.py --cookie '<YOUR_COOKIE>' --location '38.63683928705081, -90.28304510572536' --max-distance 1000 --max-attempts 20
```

Find segments where leader had HR < 160 and power < 250W within 5km:
```console
python strava_hunter.py --cookie '<YOUR_COOKIE>' --location '38.63683928705081, -90.28304510572536' --radius 5 --max-heart-rate 160 --max-power 250
```

Search larger area and save results:
```console
python strava_hunter.py --cookie '<YOUR_COOKIE>' --location '38.63683928705081, -90.28304510572536' --radius 15 --output results.json
```

## Output

The tool will display found segments with:
- Segment name and distance
- Number of attempts
- Leader information (name, time)
- Leader's heart rate and power (if available)
- Direct link to segment

Results can be saved to JSON format using the `--output` option.
