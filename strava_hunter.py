#!/usr/bin/env python3
"""
Strava Segment Hunter - Find easily winnable cycling segments
"""

import argparse
import asyncio
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
import aiohttp
import mapbox_vector_tile
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import print as rprint


@dataclass
class SegmentCriteria:
    """Criteria for filtering segments."""
    min_distance: float
    max_distance: float
    max_heart_rate: Optional[int] = None
    max_power: Optional[int] = None
    min_attempts: int = 1
    max_attempts: int = 50


@dataclass
class SegmentData:
    """Data for a single segment."""
    id: int
    name: str
    distance: float
    total_attempts: int
    leader_name: str
    leader_time: int
    leader_activity_id: int
    leader_hr: Optional[int] = None
    leader_power: Optional[int] = None
    leader_power_verified: bool = False


class StravaHunter:
    """Main class for hunting Strava segments."""
    
    def __init__(self, cookie_string: str) -> None:
        self.cookie_string = cookie_string
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 1.0  # seconds between requests
        self.console = Console()
        
    async def __aenter__(self) -> "StravaHunter":
        self.session = aiohttp.ClientSession(
            headers={
                'Cookie': self.cookie_string,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session:
            await self.session.close()
    
    def latlon_to_tile(self, lat: float, lon: float, zoom: int = 13) -> Tuple[int, int]:
        """Convert latitude/longitude to tile coordinates."""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y
    
    def get_surrounding_tiles(self, lat: float, lon: float, radius_km: float = 5,
                              zoom: int = 13) -> List[Tuple[int, int]]:
        """Get tile coordinates around a lat/lon point within a radius."""
        # Convert radius to approximate tile distance
        # At zoom 13, each tile is roughly 10km x 10km
        tile_radius = max(1, int(radius_km / 10))
        
        center_x, center_y = self.latlon_to_tile(lat, lon, zoom)
        if radius_km <= 10:
            return [(center_x, center_y)]
        tiles = []
        
        for dx in range(-tile_radius, tile_radius + 1):
            for dy in range(-tile_radius, tile_radius + 1):
                x = center_x + dx
                y = center_y + dy
                tiles.append((x, y))
        
        return tiles
    
    async def get_segments_from_tile(self, tile_x: int, tile_y: int, criteria: SegmentCriteria,
                                     zoom: int = 13, region_id: int = 34576447) -> List[int]:
        """Get segment IDs from a map tile."""
        # URL format: /tiles/segments/<region_id>/<zoom>/<tile_x>/<tile_y>
        # region_id might be user-specific or area-specific - using your example value
        url = f"https://www.strava.com/tiles/segments/{region_id}/{zoom}/{tile_x}/{tile_y}"
        params = {
            'intent': 'popular',
            'elevation_filter': 'all',
            'surface_types': '0',
            'sport_types': 'Ride',
            'distance_max': int(criteria.max_distance * 1.094),  # meters to yards
            'distance_min': int(criteria.min_distance * 1.094)
        }
        
        await asyncio.sleep(self.rate_limit_delay)
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                try:
                    # Try JSON first (in case some endpoints still return JSON)
                    data = await response.json()
                    return [segment['id'] for segment in data.get('segments', [])]
                except:
                    # Handle Mapbox Vector Tile format
                    tile_data = await response.read()
                    try:
                        decoded = mapbox_vector_tile.decode(tile_data)
                        segment_ids = []
                        
                        # Extract segment IDs from MVT layers
                        for layer_name, layer_data in decoded.items():
                            if 'features' in layer_data:
                                for feature in layer_data['features']:
                                    props = feature.get('properties', {})
                                    if 'segmentId' in props:
                                        segment_ids.append(props['segmentId'])
                                    elif 'id' in props:
                                        segment_ids.append(props['id'])
                                    elif 'segment_id' in props:
                                        segment_ids.append(props['segment_id'])
                        
                        return segment_ids
                    except Exception as e:
                        self.console.print(f"[red]Error parsing MVT tile ({tile_x}, {tile_y}): {e}[/red]")
                        return []
            else:
                self.console.print(f"[yellow]Error fetching tile ({tile_x}, {tile_y}): {response.status}[/yellow]")
                return []
    
    async def get_segment_details(self, segment_ids: List[int]) -> List[Dict]:
        """Get detailed segment information via GraphQL."""
        url = "https://graphql.strava.com/"
        
        query = """
        query Segments(
            $segmentIds: [Identifier!]!
            $leaderboardTypes: [SegmentLeaderTypeInput!]
        ) {
            segments(segmentIds: $segmentIds) {
                id
                metadata {
                    name
                    activityType
                    climbCategory
                    verifiedStatus
                }
                measurements {
                    distance
                    avgGrade
                    elevHigh
                    elevLow
                }
                totalAthletes
                totalEfforts
                athletePrEffort {
                    timing {
                        elapsedTime
                    }
                    activity {
                        id
                    }
                }
                leaderboards(leaderboardTypes: $leaderboardTypes) {
                    leaderboardEfforts {
                        athlete {
                            id
                            firstName
                            lastName
                        }
                        activity {
                            id
                        }
                        timing {
                            elapsedTime
                        }
                    }
                }
            }
        }
        """
        
        payload = {
            "query": query,
            "variables": {
                "segmentIds": segment_ids,
                "leaderboardTypes": ["Kom"]
            },
            "operationName": "Segments"
        }
        
        await asyncio.sleep(self.rate_limit_delay)
        
        async with self.session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if 'errors' in data:
                    self.console.print(f"[red]GraphQL errors: {data['errors']}[/red]")
                    return []
                return data.get('data', {}).get('segments', [])
            else:
                error_text = await response.text()
                self.console.print(f"[red]Error fetching segment details: {response.status} - {error_text[:200]}[/red]")
                return []
    
    async def get_leader_stats(self, segment_id: int) -> Tuple[Optional[int], Optional[int], bool]:
        """Scrape leader's heart rate, power data, and power verification from segment page."""
        url = f"https://www.strava.com/segments/{segment_id}"
        
        await asyncio.sleep(self.rate_limit_delay)
        
        async with self.session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find the leaderboard table and get the first row (leader)
                leaderboard_table = soup.find('table', class_='table-leaderboard')
                if leaderboard_table:
                    first_row = leaderboard_table.find('tbody').find('tr')
                    if first_row:
                        cells = first_row.find_all('td')
                        
                        hr = None
                        power = None
                        power_verified = False
                        
                        # Look for HR and power in the table cells
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            
                            # Check for heart rate (look for "bpm")
                            if 'bpm' in cell_text:
                                hr_match = re.search(r'(\d+)', cell_text)
                                if hr_match:
                                    hr = int(hr_match.group(1))
                            
                            # Check for power (look for "W" and power meter icon)
                            if 'W' in cell_text and ('power' in cell.get('class', []) or cell.find(class_=re.compile('power'))):
                                power_match = re.search(r'(\d+)', cell_text)
                                if power_match:
                                    power = int(power_match.group(1))
                                    
                                    # Check if power is verified (has power meter icon)
                                    power_icon = cell.find('span', title='Power Meter')
                                    if power_icon:
                                        power_verified = True
                        
                        return hr, power, power_verified
                
                # Fallback to regex if table parsing fails
                hr_match = re.search(r'(\d+)<abbr[^>]*title=["\']beats per minute["\']', html, re.IGNORECASE)
                power_match = re.search(r'(\d+)<abbr[^>]*title=["\']watts["\']', html, re.IGNORECASE)
                
                hr = int(hr_match.group(1)) if hr_match else None
                power = int(power_match.group(1)) if power_match else None
                
                # Check for power meter verification in fallback
                power_verified = False
                if power_match:
                    power_meter_match = re.search(r'title=["\']Power Meter["\']', html, re.IGNORECASE)
                    if power_meter_match:
                        power_verified = True
                
                return hr, power, power_verified
            else:
                self.console.print(f"[yellow]Error fetching segment page {segment_id}: {response.status}[/yellow]")
                return None, None, False
    
    async def analyze_segments(self, tiles: List[Tuple[int, int]], criteria: SegmentCriteria, region_id: int = 34576447) -> List[SegmentData]:
        """Analyze segments and return those matching criteria."""
        all_segment_ids = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Fetching segments from tiles...", total=len(tiles))
            
            # Get segment IDs from all tiles (tiles are always (x, y) tuples now)
            for tile_x, tile_y in tiles:
                segment_ids = await self.get_segments_from_tile(tile_x, tile_y, criteria, region_id=region_id)
                all_segment_ids.extend(segment_ids)
                progress.advance(task)
        
        # Remove duplicates while preserving order
        all_segment_ids = list(dict.fromkeys(all_segment_ids))
        
        if not all_segment_ids:
            self.console.print("[red]No segments found in specified tiles[/red]")
            return []
        
        self.console.print(f"[green]Found {len(all_segment_ids)} segments to analyze[/green]")
        
        # Get detailed segment information in batches to avoid overwhelming the API
        segment_details = []
        batch_size = 50  # Process segments in batches of 50
        total_batches = (len(all_segment_ids) + batch_size - 1) // batch_size
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), console=self.console) as progress:
            task = progress.add_task("Fetching segment details...          ", total=total_batches)
            
            for batch_num, i in enumerate(range(0, len(all_segment_ids), batch_size), 1):
                batch = all_segment_ids[i:i + batch_size]
                batch_details = await self.get_segment_details(batch)
                segment_details.extend(batch_details)
                progress.advance(task)
        
        winnable_segments = []
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), console=self.console) as progress:
            analysis_task = progress.add_task("Analyzing segments for winnability...", total=len(segment_details))
            
            for i, segment in enumerate(segment_details, 1):
                try:
                    # Extract segment data
                    metadata = segment.get('metadata', {})
                    measurements = segment.get('measurements', {})
                    leaderboards = segment.get('leaderboards', [])
                    
                    if not leaderboards or not leaderboards[0].get('leaderboardEfforts'):
                        continue
                    
                    leader = leaderboards[0]['leaderboardEfforts'][0]
                    
                    segment_data = SegmentData(
                        id=segment.get('id', 0),  # Get the actual segment ID from the response
                        name=metadata.get('name', ''),
                        distance=measurements.get('distance', 0),
                        total_attempts=segment.get('totalEfforts', 0),
                        leader_name=f"{leader['athlete']['firstName']} {leader['athlete']['lastName']}",
                        leader_time=leader['timing']['elapsedTime'],
                        leader_activity_id=leader['activity']['id']
                    )
                    
                    # Check if segment meets basic criteria
                    if (criteria.min_distance <= segment_data.distance <= criteria.max_distance \
                            and criteria.min_attempts <= segment_data.total_attempts <= criteria.max_attempts):
                        
                        # Always get leader's HR and power data for display
                        hr, power, power_verified = await self.get_leader_stats(segment_data.id)
                        segment_data.leader_hr = hr
                        segment_data.leader_power = power
                        segment_data.leader_power_verified = power_verified
                        
                        # Check HR/power criteria if specified
                        if criteria.max_heart_rate and (not hr or hr > criteria.max_heart_rate):
                            continue
                        if criteria.max_power and (not power or power > criteria.max_power):
                            continue
                        
                        winnable_segments.append(segment_data)
                        
                except Exception as e:
                    self.console.print(f"[red]Error processing segment: {e}[/red]")
                    continue
                
                progress.advance(analysis_task)
        
        return winnable_segments


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='Find easily winnable Strava cycling segments',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--min-distance', type=float, default=500.0, help='Minimum segment distance in meters')
    parser.add_argument('--max-distance', type=float, default=2000.0, help='Maximum segment distance in meters')
    parser.add_argument('--max-heart-rate', type=int, help='Maximum leader heart rate (bpm)')
    parser.add_argument('--max-power', type=int, help='Maximum leader power (watts)')
    parser.add_argument('--min-attempts', type=int, default=1, help='Minimum number of attempts')
    parser.add_argument('--max-attempts', type=int, default=200, help='Maximum number of attempts')
    parser.add_argument('--location', type=str, required=True, help='Comma-separated lat,lon coordinates (e.g., "44.95,-93.09")')
    parser.add_argument('--radius', type=float, default=10.0, help='Search radius in kilometers')
    parser.add_argument('--region-id', type=int, default=34576447, help='Strava region/area ID for tile requests')
    parser.add_argument('--cookie', required=True, help='Strava cookie string for authentication')
    parser.add_argument('--output', type=Path, help='Output file for results (JSON format)')
    
    args = parser.parse_args()
    
    criteria = SegmentCriteria(
        min_distance=args.min_distance,
        max_distance=args.max_distance,
        max_heart_rate=args.max_heart_rate,
        max_power=args.max_power,
        min_attempts=args.min_attempts,
        max_attempts=args.max_attempts
    )
    
    async def run_analysis():
        async with StravaHunter(args.cookie) as hunter:
            # Parse lat,lon from string and convert to tiles
            try:
                lat_str, lon_str = args.location.split(',')
                lat = float(lat_str.strip())
                lon = float(lon_str.strip())
                tiles = hunter.get_surrounding_tiles(lat, lon, args.radius)
                console = Console()
                console.print(f"[cyan]🗺️  Searching around ({lat}, {lon}) with radius {args.radius}km[/cyan]")
                console.print(f"[blue]📍 Found {len(tiles)} tiles to search[/blue]")
            except ValueError:
                Console().print("[red]❌ Error: Invalid location format. Use 'lat,lon' format.[/red]")
                return
            
            # Analyze segments in the tiles
            segments = await hunter.analyze_segments(tiles, criteria, region_id=args.region_id)
            
            console = Console()
            
            if segments:
                console.print(f"\n[green]🎯 Found {len(segments)} winnable segments![/green]")
                
                table = Table(show_header=True, header_style="bold magenta", row_styles=["", "dim"])
                table.add_column("🏁 Segment", style="cyan")
                table.add_column("📏 Distance", justify="right")
                table.add_column("👥 Attempts", justify="right")
                table.add_column("🥇 Leader", style="yellow")
                table.add_column("🕐 Time", justify="right")
                table.add_column("💗 HR", justify="right")
                table.add_column("⚡ Power", justify="right")
                table.add_column("🔗 URL", style="blue")
                
                for segment in segments:
                    # Format power with lightning bolt if verified
                    power_text = f"{'⚡' if segment.leader_power_verified else ''}{segment.leader_power}W" if segment.leader_power else ""
                    # Format heart rate
                    hr_text = f"{segment.leader_hr} bpm" if segment.leader_hr else ""
                    # Format time as minutes:seconds
                    minutes = segment.leader_time // 60
                    seconds = segment.leader_time % 60
                    time_text = f"{minutes}:{seconds:02d}"
                    # Create clickable URL
                    url = f"https://www.strava.com/segments/{segment.id}"
                    
                    table.add_row(
                        segment.name,
                        f"{segment.distance:.0f}m",
                        str(segment.total_attempts),
                        segment.leader_name,
                        time_text,
                        hr_text,
                        power_text,
                        url,
                    )
                
                console.print(table)
                
                if args.output:
                    # Convert dataclasses to dict for JSON serialization
                    segment_dicts = [{
                        'id': str(s.id),
                        'name': s.name,
                        'distance': s.distance,
                        'total_attempts': s.total_attempts,
                        'leader_name': s.leader_name,
                        'leader_time': s.leader_time,
                        'leader_hr': s.leader_hr,
                        'leader_power': s.leader_power,
                        'leader_power_verified': s.leader_power_verified,
                        'url': f"https://www.strava.com/segments/{s.id}",
                    } for s in segments]
                    
                    args.output.write_text(json.dumps(segment_dicts, indent=2, ensure_ascii=False), encoding='utf-8')
                    console.print(f"\n[green]💾 Results saved to {args.output}[/green]")
            else:
                console.print("[yellow]😞 No winnable segments found matching your criteria[/yellow]")
    
    asyncio.run(run_analysis())


if __name__ == "__main__":
    main()
