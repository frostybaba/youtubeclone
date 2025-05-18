import subprocess
import json
import logging
import re
import urllib.parse
import requests
from typing import List, Dict, Any, Optional

def run_yt_dlp_command(command: List[str], timeout: int = 30) -> str:
    """Execute a yt-dlp command and return the output with timeout"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logging.error(f"yt-dlp command timed out after {timeout} seconds")
        raise Exception(f"Command timed out after {timeout} seconds")
    except subprocess.CalledProcessError as e:
        logging.error(f"yt-dlp command error: {e}")
        logging.error(f"stderr: {e.stderr}")
        raise Exception("Failed to execute yt-dlp command")

def get_video_stream_url(video_id: str, quality: str = "720") -> str:
    """Get direct stream URL for a YouTube video using yt-dlp"""
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    command = ["yt-dlp", "-f", f"best[height<={quality}]", "-g", youtube_url]

    try:
        return run_yt_dlp_command(command)
    except Exception as e:
        logging.error(f"Error getting stream URL for {video_id}: {e}")
        raise Exception(f"Failed to get video stream URL: {str(e)}")

def extract_video_info(video: Dict[str, Any]) -> Dict[str, Any]:
    """Format video information into a standard structure"""
    return {
        'id': video.get('id', {}).get('videoId', video.get('id', '')),
        'title': video.get('snippet', {}).get('title', 'Untitled Video'),
        'description': video.get('snippet', {}).get('description', ''),
        'channel': video.get('snippet', {}).get('channelTitle', 'Unknown Channel'),
        'channel_id': video.get('snippet', {}).get('channelId', ''),
        'published_at': video.get('snippet', {}).get('publishedAt', ''),
        'thumbnail': video.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', '') or 
                     video.get('snippet', {}).get('thumbnails', {}).get('medium', {}).get('url', '') or
                     video.get('snippet', {}).get('thumbnails', {}).get('default', {}).get('url', '')
    }

def get_video_info_from_yt_dlp(video_id: str) -> Dict[str, Any]:
    """Get detailed video information using yt-dlp"""
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    command = ["yt-dlp", "--dump-json", "--no-playlist", youtube_url]

    try:
        output = run_yt_dlp_command(command)
        video_info = json.loads(output)

        # Format the duration safely
        duration_seconds = video_info.get('duration', 0)
        formatted_duration = "00:00"
        try:
            if duration_seconds:
                formatted_duration = format_duration(int(duration_seconds))
        except Exception as e:
            logging.error(f"Error formatting duration: {e}")

        # Format the date (YYYYMMDD to readable format)
        upload_date = video_info.get('upload_date', '')
        formatted_date = upload_date
        try:
            if upload_date and isinstance(upload_date, str) and len(upload_date) == 8:
                from datetime import datetime
                date_obj = datetime.strptime(upload_date, '%Y%m%d')
                formatted_date = date_obj.strftime('%B %d, %Y')
        except Exception as e:
            logging.error(f"Error formatting date {upload_date}: {e}")

        # Format view count safely
        view_count = video_info.get('view_count', 0)
        formatted_view_count = "0"
        try:
            if view_count:
                formatted_view_count = format_view_count(int(view_count))
        except Exception as e:
            logging.error(f"Error formatting view count: {e}")
            formatted_view_count = str(view_count)

        # Get the best thumbnail safely
        thumbnail = video_info.get('thumbnail', '')
        try:
            thumbnails = video_info.get('thumbnails', [])
            if thumbnails and isinstance(thumbnails, list):
                # Find larger thumbnails first
                for t in reversed(thumbnails):
                    if isinstance(t, dict) and 'url' in t:
                        thumbnail = t['url']
                        break
        except Exception as e:
            logging.error(f"Error getting thumbnail: {e}")

        # Format likes count safely
        likes = "0"
        try:
            like_count = video_info.get('like_count', 0)
            if like_count:
                likes = format_view_count(int(like_count))
        except Exception as e:
            logging.error(f"Error formatting likes: {e}")

        return {
            'id': video_id,
            'title': video_info.get('title', 'Untitled Video'),
            'description': video_info.get('description', ''),
            'channel': video_info.get('uploader', 'Unknown Channel'),
            'channel_id': video_info.get('channel_id', ''),
            'published_at': formatted_date,
            'duration': formatted_duration,
            'duration_seconds': duration_seconds,
            'view_count': formatted_view_count,
            'raw_view_count': view_count,
            'thumbnail': thumbnail,
            'likes': likes,
            'categories': video_info.get('categories', [])
        }
    except Exception as e:
        logging.error(f"Error getting video info for {video_id}: {e}")
        raise Exception(f"Failed to get video information: {str(e)}")

def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS format"""
    if not seconds:
        return "00:00"

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def format_view_count(count: int) -> str:
    """Format large numbers to human-readable form (e.g., 1.5M, 4.3K)"""
    if not count:
        return "0"

    try:    
        if count >= 1000000:
            return f"{count/1000000:.1f}M"
        elif count >= 1000:
            return f"{count/1000:.1f}K"
        else:
            return str(count)
    except Exception as e:
        logging.error(f"Error formatting view count {count}: {e}")
        return str(count)

def search_videos(query: str, max_results: int = 20, country_code: str = "TR") -> List[Dict[str, Any]]:
    """Search for videos using yt-dlp with country-specific results
    
    Args:
        query: The search query
        max_results: Maximum number of results to return
        country_code: ISO country code (e.g., 'TR' for Turkey, 'US' for United States)
    """
    search_query = urllib.parse.quote(query)
    
    # Add country code parameter to search query for region-specific results
    region_param = f"&region={country_code}"
    command = ["yt-dlp", "--flat-playlist", "--dump-json", "--extractor-args", 
               f"youtube:lang=tr,region={country_code}", 
               f"ytsearch{max_results}:{search_query}"]

    try:
        output = run_yt_dlp_command(command, timeout=10)
        videos = []

        # Process each line as a separate JSON object
        for line in output.splitlines():
            if line.strip():
                try:
                    video_info = json.loads(line)

                    # Format duration safely
                    duration = None
                    try:
                        if video_info.get('duration'):
                            duration = format_duration(int(video_info.get('duration')))
                    except Exception as e:
                        logging.error(f"Error formatting duration: {e}")

                    # Format view count safely
                    view_count = None
                    try:
                        if video_info.get('view_count'):
                            view_count = format_view_count(int(video_info.get('view_count')))
                    except Exception as e:
                        logging.error(f"Error formatting view count: {e}")

                    # Format date safely
                    published_at = video_info.get('upload_date', '')
                    try:
                        if published_at and isinstance(published_at, str) and len(published_at) == 8:
                            from datetime import datetime
                            date_obj = datetime.strptime(published_at, '%Y%m%d')
                            published_at = date_obj.strftime('%B %d, %Y')
                    except Exception as e:
                        logging.error(f"Error formatting date: {e}")

                    # Ensure thumbnail exists
                    thumbnail = video_info.get('thumbnail', '')
                    if not thumbnail:
                        thumbnail = f"https://i.ytimg.com/vi/{video_info.get('id', '')}/hqdefault.jpg"

                    videos.append({
                        'id': video_info.get('id', ''),
                        'title': video_info.get('title', 'Untitled Video'),
                        'channel': video_info.get('uploader', 'Unknown Channel'),
                        'channel_id': video_info.get('channel_id', ''),
                        'thumbnail': thumbnail,
                        'duration': duration,
                        'view_count': view_count,
                        'published_at': published_at,
                        'country': country_code
                    })
                except Exception as e:
                    logging.error(f"Error processing video info: {e}")
                    continue

        # If no results found with country-specific search, fall back to global search
        if not videos:
            logging.warning(f"No search results found for '{query}' in {country_code}, falling back to global search")
            fallback_command = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch{max_results}:{search_query}"]
            output = run_yt_dlp_command(fallback_command, timeout=10)
            
            # Process fallback videos (similar to above)
            for line in output.splitlines():
                if line.strip():
                    try:
                        video_info = json.loads(line)
                        # Same processing as above (simplified here)
                        videos.append({
                            'id': video_info.get('id', ''),
                            'title': video_info.get('title', 'Untitled Video'),
                            'channel': video_info.get('uploader', 'Unknown Channel'),
                            'channel_id': video_info.get('channel_id', ''),
                            'thumbnail': video_info.get('thumbnail', '') or f"https://i.ytimg.com/vi/{video_info.get('id', '')}/hqdefault.jpg",
                            'duration': format_duration(int(video_info.get('duration', 0))) if video_info.get('duration') else None,
                            'view_count': format_view_count(int(video_info.get('view_count', 0))) if video_info.get('view_count') else None,
                            'published_at': video_info.get('upload_date', ''),
                            'country': 'GLOBAL'
                        })
                    except Exception as e:
                        logging.error(f"Error processing fallback search result: {e}")
                        continue

        return videos
    except Exception as e:
        logging.error(f"Error searching videos for '{query}' in {country_code}: {e}")
        # Try global search as fallback
        try:
            fallback_command = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch{max_results}:{search_query}"]
            output = run_yt_dlp_command(fallback_command, timeout=10)
            videos = []
            
            for line in output.splitlines():
                if line.strip():
                    try:
                        video_info = json.loads(line)
                        videos.append({
                            'id': video_info.get('id', ''),
                            'title': video_info.get('title', 'Untitled Video'),
                            'channel': video_info.get('uploader', 'Unknown Channel'),
                            'channel_id': video_info.get('channel_id', ''),
                            'thumbnail': video_info.get('thumbnail', '') or f"https://i.ytimg.com/vi/{video_info.get('id', '')}/hqdefault.jpg",
                            'duration': format_duration(int(video_info.get('duration', 0))) if video_info.get('duration') else None,
                            'view_count': format_view_count(int(video_info.get('view_count', 0))) if video_info.get('view_count') else None,
                            'published_at': video_info.get('upload_date', ''),
                            'country': 'GLOBAL'
                        })
                    except:
                        continue
            return videos
        except Exception as e2:
            logging.error(f"Global search fallback also failed: {e2}")
            raise Exception(f"Failed to search videos: {str(e)}")

def get_trending_videos(max_results: int = 20, country_code: str = "TR") -> List[Dict[str, Any]]:
    """Get trending videos for specific country using yt-dlp
    
    Args:
        max_results: Maximum number of videos to return
        country_code: ISO country code (e.g., 'TR' for Turkey, 'US' for United States)
    """
    # Use country-specific trending URL
    trending_url = f"https://www.youtube.com/feed/trending?gl={country_code}"
    command = ["yt-dlp", "--flat-playlist", "--dump-json", "--extractor-args", "youtube:skip=dash,hls", "-I", f"1:{max_results}", trending_url]

    try:
        output = run_yt_dlp_command(command, timeout=10)  # Increased timeout for trending
        videos = []

        # Process each line as a separate JSON object
        for line in output.splitlines():
            if line.strip():
                try:
                    video_info = json.loads(line)

                    # Format duration safely
                    duration = None
                    try:
                        if video_info.get('duration'):
                            duration = format_duration(int(video_info.get('duration')))
                    except Exception as e:
                        logging.error(f"Error formatting duration: {e}")

                    # Format view count safely
                    view_count = None
                    try:
                        if video_info.get('view_count'):
                            view_count = format_view_count(int(video_info.get('view_count')))
                    except Exception as e:
                        logging.error(f"Error formatting view count: {e}")

                    # Format date safely
                    published_at = video_info.get('upload_date', '')
                    try:
                        if published_at and isinstance(published_at, str) and len(published_at) == 8:
                            from datetime import datetime
                            date_obj = datetime.strptime(published_at, '%Y%m%d')
                            published_at = date_obj.strftime('%B %d, %Y')
                    except Exception as e:
                        logging.error(f"Error formatting date: {e}")

                    # Ensure thumbnail exists
                    thumbnail = video_info.get('thumbnail', '')
                    if not thumbnail:
                        thumbnail = f"https://i.ytimg.com/vi/{video_info.get('id', '')}/hqdefault.jpg"

                    videos.append({
                        'id': video_info.get('id', ''),
                        'title': video_info.get('title', 'Untitled Video'),
                        'channel': video_info.get('uploader', 'Unknown Channel'),
                        'channel_id': video_info.get('channel_id', ''),
                        'thumbnail': thumbnail,
                        'duration': duration,
                        'view_count': view_count,
                        'published_at': published_at,
                        'country': country_code
                    })
                except Exception as e:
                    logging.error(f"Error processing trending video info: {e}")
                    continue
                    
        # If no results from country-specific trending, fall back to general trending
        if not videos:
            logging.warning(f"No trending videos found for country {country_code}, falling back to general trending")
            fallback_command = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearchdate{max_results}:YouTube trending"]
            output = run_yt_dlp_command(fallback_command, timeout=10)
            
            # Process fallback videos similar to above
            for line in output.splitlines():
                if line.strip():
                    try:
                        video_info = json.loads(line)
                        
                        # Same processing as above (simplified here for brevity)
                        duration = format_duration(int(video_info.get('duration', 0))) if video_info.get('duration') else None
                        view_count = format_view_count(int(video_info.get('view_count', 0))) if video_info.get('view_count') else None
                        
                        # Format date
                        published_at = video_info.get('upload_date', '')
                        if published_at and len(published_at) == 8:
                            from datetime import datetime
                            try:
                                date_obj = datetime.strptime(published_at, '%Y%m%d')
                                published_at = date_obj.strftime('%B %d, %Y')
                            except:
                                pass
                                
                        # Ensure thumbnail
                        thumbnail = video_info.get('thumbnail', '') or f"https://i.ytimg.com/vi/{video_info.get('id', '')}/hqdefault.jpg"
                        
                        videos.append({
                            'id': video_info.get('id', ''),
                            'title': video_info.get('title', 'Untitled Video'),
                            'channel': video_info.get('uploader', 'Unknown Channel'),
                            'channel_id': video_info.get('channel_id', ''),
                            'thumbnail': thumbnail,
                            'duration': duration,
                            'view_count': view_count,
                            'published_at': published_at,
                            'country': 'GLOBAL'
                        })
                    except Exception as e:
                        logging.error(f"Error processing fallback trending video: {e}")
                        continue

        return videos
    except Exception as e:
        logging.error(f"Error getting trending videos for {country_code}: {e}")
        # Try fallback if country-specific trending fails
        try:
            fallback_command = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearchdate{max_results}:YouTube trending"]
            output = run_yt_dlp_command(fallback_command, timeout=10)
            # Process results (shortened here)
            videos = []
            for line in output.splitlines():
                if line.strip():
                    try:
                        video_info = json.loads(line)
                        videos.append({
                            'id': video_info.get('id', ''),
                            'title': video_info.get('title', 'Untitled Video'),
                            'channel': video_info.get('uploader', 'Unknown Channel'),
                            'channel_id': video_info.get('channel_id', ''),
                            'thumbnail': video_info.get('thumbnail', '') or f"https://i.ytimg.com/vi/{video_info.get('id', '')}/hqdefault.jpg",
                            'duration': format_duration(int(video_info.get('duration', 0))) if video_info.get('duration') else None,
                            'view_count': format_view_count(int(video_info.get('view_count', 0))) if video_info.get('view_count') else None,
                            'published_at': video_info.get('upload_date', ''),
                            'country': 'GLOBAL'
                        })
                    except:
                        continue
            return videos
        except Exception as e2:
            logging.error(f"Error with fallback trending: {e2}")
            raise Exception(f"Failed to get trending videos: {str(e)}")

def get_video_details(video_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific video"""
    try:
        return get_video_info_from_yt_dlp(video_id)
    except Exception as e:
        logging.error(f"Error getting video details for {video_id}: {e}")
        raise Exception(f"Failed to get video details: {str(e)}")

def get_channel_info(channel_id: str) -> Dict[str, Any]:
    """Get channel information using yt-dlp with a fast timeout and fallback"""
    # Basic info fallback function to avoid breaking the page
    def get_basic_channel_info():
        """Return basic channel info without making network requests"""
        logging.warning(f"Using basic channel info for {channel_id}")
        channel_name = channel_id
        if channel_id.startswith('@'):
            channel_name = channel_id[1:]  # Remove @ symbol for display
        return {
            'name': f"Channel: {channel_name}",
            'description': 'Channel information is currently unavailable',
            'channel_id': channel_id,
            'subscriber_count': 'N/A',
            'channel_url': f'https://www.youtube.com/{channel_id}'
        }
    
    # Try with username format with a short timeout
    try:
        channel_url = f"https://www.youtube.com/{('@' + channel_id) if not channel_id.startswith('@') else channel_id}"
        command = ["yt-dlp", "--dump-single-json", "--extractor-args", "youtube:skip=dash,hls", channel_url]
        
        # Use a short timeout of 3 seconds to avoid hanging
        output = run_yt_dlp_command(command, timeout=3)
        channel_info = json.loads(output)
        
        return {
            'name': channel_info.get('channel', channel_info.get('uploader', 'Unknown Channel')),
            'description': channel_info.get('description', ''),
            'channel_id': channel_info.get('channel_id', channel_id),
            'subscriber_count': channel_info.get('subscriber_count', '0'),
            'channel_url': channel_info.get('channel_url', channel_url)
        }
    except Exception as e:
        logging.error(f"Error getting channel info for {channel_id}: {e}")
        
        # Try alternative method with channel ID format
        try:
            alt_url = f"https://www.youtube.com/channel/{channel_id}"
            command = ["yt-dlp", "--dump-single-json", "--extractor-args", "youtube:skip=dash,hls", alt_url]
            
            # Even shorter timeout for the fallback
            output = run_yt_dlp_command(command, timeout=2)
            channel_info = json.loads(output)
            
            return {
                'name': channel_info.get('channel', channel_info.get('uploader', 'Unknown Channel')),
                'description': channel_info.get('description', ''),
                'channel_id': channel_info.get('channel_id', channel_id),
                'subscriber_count': channel_info.get('subscriber_count', '0'),
                'channel_url': channel_info.get('channel_url', alt_url)
            }
        except Exception as e2:
            logging.error(f"Error in alternative method for {channel_id}: {e2}")
            # Return basic information to avoid breaking the page
            return get_basic_channel_info()

def get_channel_videos(channel_id: str, max_results: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
    """Get videos from a specific channel using yt-dlp with pagination
    
    Args:
        channel_id: The YouTube channel ID to fetch videos from
        max_results: Maximum number of videos to return
        skip: Number of videos to skip (for pagination)
    """
    from datetime import datetime
    
    # Try different channel URL formats
    urls_to_try = [
        f"https://www.youtube.com/@{channel_id}/videos",
        f"https://www.youtube.com/channel/{channel_id}/videos"
    ]
    
    videos = []
    
    for url in urls_to_try:
        try:
            # If skip is 0, we're just getting the first page
            # Otherwise, we need to fetch (skip + max_results) videos and then slice
            fetch_count = skip + max_results
            
            command = ["yt-dlp", "--flat-playlist", "--dump-json", "--extractor-args", "youtube:skip=dash,hls", "-I", f"1:{fetch_count}", url]
            output = run_yt_dlp_command(command)
            
            # Process each video
            all_videos = []
            for line in output.splitlines():
                if not line.strip():
                    continue
                
                try:
                    video_info = json.loads(line)
                    
                    # Get duration
                    duration = None
                    if video_info.get('duration'):
                        try:
                            duration = format_duration(int(video_info.get('duration')))
                        except:
                            pass
                    
                    # Get view count
                    view_count = None
                    raw_view_count = "0"
                    if video_info.get('view_count'):
                        try:
                            view_count = format_view_count(int(video_info.get('view_count')))
                            raw_view_count = str(video_info.get('view_count'))
                        except:
                            pass
                    
                    # Format date
                    published_at = video_info.get('upload_date', '')
                    if published_at and len(published_at) == 8:
                        try:
                            date_obj = datetime.strptime(published_at, '%Y%m%d')
                            published_at = date_obj.strftime('%B %d, %Y')
                        except:
                            pass
                    
                    # Get thumbnail
                    thumbnail = video_info.get('thumbnail', '')
                    if not thumbnail:
                        thumbnail = f"https://i.ytimg.com/vi/{video_info.get('id', '')}/hqdefault.jpg"
                    
                    all_videos.append({
                        'id': video_info.get('id', ''),
                        'title': video_info.get('title', 'Untitled Video'),
                        'channel': video_info.get('uploader', 'Unknown Channel'),
                        'channel_id': video_info.get('channel_id', ''),
                        'thumbnail': thumbnail,
                        'duration': duration,
                        'view_count': view_count,
                        'raw_view_count': raw_view_count,
                        'published_at': published_at
                    })
                except Exception as e:
                    logging.error(f"Error processing video: {e}")
                    continue
            
            # Apply pagination - if skip is 0, we take the first batch
            # If skip is provided, we slice only the required videos
            if skip > 0:
                # We add all to videos list (not overwriting it) in case we tried multiple URLs
                videos.extend(all_videos[skip:skip + max_results])
            else:
                # For first page, just take the requested number
                videos.extend(all_videos[:max_results])
            
            # If we got videos, no need to try other URLs
            if videos:
                return videos
                
        except Exception as e:
            logging.error(f"Error with URL {url}: {e}")
            continue
    
    # If we reach here, fall back to search
    logging.info(f"Channel {channel_id} not found, falling back to search")
    return search_videos(channel_id, max_results)