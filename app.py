import os
import logging
import re
import subprocess
import requests
import json
import random
import threading
import time
import io
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Import YouTube API functionality
from youtube_api import (
    search_videos, get_video_details, get_trending_videos, 
    get_video_stream_url, get_channel_videos, get_video_info_from_yt_dlp,
    get_channel_info, format_view_count
)

@app.route('/')
def index():
    """Home/Discover page showing trending videos for Turkey"""
    try:
        # Default to TR (Turkey) for trending videos
        country_code = request.args.get('country', 'TR')
        trending_videos = get_trending_videos(country_code=country_code)
        return render_template('index.html', videos=trending_videos, country=country_code)
    except Exception as e:
        logging.error(f"Error loading trending videos: {e}")
        return render_template('index.html', videos=[], error="Failed to load trending videos", country='TR')

@app.route('/search')
def search():
    """Search for videos based on query"""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))

    # Default to TR (Turkey) for search results
    country_code = request.args.get('country', 'TR')

    # Check if query is a YouTube URL or video ID
    youtube_regex = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(youtube_regex, query)

    if match:
        # Extract video ID and redirect to watch page
        video_id = match.group(1)
        return redirect(url_for('watch', v=video_id))

    # If it's an 11-character video ID directly
    elif len(query.strip()) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', query.strip()):
        return redirect(url_for('watch', v=query.strip()))

    try:
        # Only load a small initial batch for immediate display with country-specific results
        initial_results = search_videos(query, max_results=10, country_code=country_code)
        return render_template('search.html', videos=initial_results, query=query, country=country_code)
    except Exception as e:
        logging.error(f"Search error: {e}")
        return render_template('search.html', videos=[], query=query, error="Search failed", country=country_code)

@app.route('/subscriptions')
def subscriptions():
    """Subscriptions page showing videos from subscribed channels"""
    return render_template('subscriptions.html')

@app.route('/watch')
def watch():
    """Video player page"""
    video_id = request.args.get('v', '')
    if not video_id:
        return redirect(url_for('index'))

    try:
        video_details = get_video_details(video_id)
        return render_template('player.html', video=video_details)
    except Exception as e:
        logging.error(f"Error loading video {video_id}: {e}")
        return render_template('player.html', video=None, error="Failed to load video")

@app.route('/api/stream')
def get_stream():
    """API endpoint to get video stream URL"""
    video_id = request.args.get('v', '')
    quality = request.args.get('quality', '720')
    mode = request.args.get('mode', 'normal')  # 'normal' or 'experimental'

    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400

    try:
        if mode == 'experimental' and quality == 'best':
            # Use direct yt-dlp commands to get the best audio and video separately
            # Get best video without audio
            video_cmd = ["yt-dlp", "-f", "bestvideo", "-g", f"https://www.youtube.com/watch?v={video_id}"]
            video_result = subprocess.run(video_cmd, capture_output=True, text=True)
            
            if video_result.returncode != 0:
                logging.error(f"yt-dlp error fetching best video: {video_result.stderr}")
                # Fallback to normal mode
                stream_url = get_video_stream_url(video_id, "720")
                return jsonify({'url': stream_url, 'mode': 'normal'})
            
            video_url = video_result.stdout.strip()
            
            # Get best audio
            audio_cmd = ["yt-dlp", "-f", "bestaudio", "-g", f"https://www.youtube.com/watch?v={video_id}"]
            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
            
            if audio_result.returncode != 0:
                logging.error(f"yt-dlp error fetching best audio: {audio_result.stderr}")
                # Fallback to normal mode
                stream_url = get_video_stream_url(video_id, "720")
                return jsonify({'url': stream_url, 'mode': 'normal'})
            
            audio_url = audio_result.stdout.strip()
            
            # Log the selected formats
            logging.info(f"Selected best video and audio for {video_id}")
            
            # Return separate URLs for video and audio
            return jsonify({
                'video_url': video_url, 
                'audio_url': audio_url,
                'mode': 'experimental'
            })
        else:
            # Normal mode - get combined stream
            stream_url = get_video_stream_url(video_id, quality)
            return jsonify({'url': stream_url, 'mode': 'normal'})
    except Exception as e:
        logging.error(f"Error getting stream URL for {video_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def api_search():
    """API endpoint to search videos"""
    query = request.args.get('q', '')
    max_results = request.args.get('max_results', 10, type=int)
    skip = request.args.get('skip', 0, type=int)

    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    try:
        # Get a larger batch of results and paginate them here
        total_results = max_results + skip
        all_results = search_videos(query, total_results)
        
        # Apply pagination - only return the segment requested
        paginated_results = all_results[skip:skip + max_results] if skip < len(all_results) else []
        
        return jsonify({
            'videos': paginated_results,
            'total_available': len(all_results),
            'query': query
        })
    except Exception as e:
        logging.error(f"API search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/channel/<path:channel_id>')
def channel_page(channel_id):
    """Channel page showing channel info and videos"""
    # Remove leading @ if present
    if channel_id.startswith('@'):
        channel_id = channel_id[1:]
        
    try:
        channel_info = get_channel_info(channel_id)
        
        # Only load a small initial batch of videos for the first page render
        initial_videos = get_channel_videos(channel_id, max_results=10)
        
        # Initial stats based on available videos
        # Complete stats will be updated via JS as more videos load
        total_views = sum(int(video.get('raw_view_count', 0)) for video in initial_videos)
        video_count = len(initial_videos)
        avg_views = round(total_views / video_count) if video_count > 0 else 0
        
        channel = {
            'id': channel_id,
            'name': channel_info.get('name', 'Unknown Channel'),
            'description': channel_info.get('description', ''),
            'total_views': format_view_count(total_views),
            'video_count': video_count,
            'avg_views': format_view_count(avg_views)
        }
        
        return render_template('channel.html', channel=channel, videos=initial_videos)
    except Exception as e:
        logging.error(f"Error loading channel {channel_id}: {e}")
        return render_template('channel.html', channel=None, videos=[], error="Failed to load channel")

@app.route('/api/channel')
def channel_videos():
    """API endpoint to get videos from a specific channel"""
    channel_id = request.args.get('id', '')
    max_results = request.args.get('max_results', 10, type=int)
    skip = request.args.get('skip', 0, type=int)

    if not channel_id:
        return jsonify({'error': 'No channel ID provided'}), 400

    try:
        # Get a batch of videos with pagination
        results = get_channel_videos(channel_id, max_results, skip)
        
        # If we're loading more videos and need to update channel stats
        if skip > 0 and request.args.get('update_stats', 'false').lower() == 'true':
            # Get all videos loaded so far for accurate stats
            all_loaded_videos = get_channel_videos(channel_id, skip + max_results)
            
            # Calculate updated stats
            total_views = sum(int(video.get('raw_view_count', 0)) for video in all_loaded_videos)
            video_count = len(all_loaded_videos)
            avg_views = round(total_views / video_count) if video_count > 0 else 0
            
            channel_stats = {
                'total_views': format_view_count(total_views),
                'video_count': video_count,
                'avg_views': format_view_count(avg_views)
            }
            
            return jsonify({
                'videos': results, 
                'channel_id': channel_id,
                'channel_stats': channel_stats
            })
            
        return jsonify({
            'videos': results, 
            'channel_id': channel_id
        })
    except Exception as e:
        logging.error(f"Error fetching channel videos for {channel_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download')
def download_video():
    """API endpoint to get download link for a video"""
    video_id = request.args.get('v', '')
    quality = request.args.get('quality', '720')

    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400

    try:
        stream_url = get_video_stream_url(video_id, quality)
        return jsonify({'url': stream_url})
    except Exception as e:
        logging.error(f"Error getting download URL for {video_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/description')
def get_video_description():
    """API endpoint to get video description"""
    video_id = request.args.get('v', '')

    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400

    try:
        video_details = get_video_details(video_id)
        description = video_details.get('description', '')
        return jsonify({'description': description})
    except Exception as e:
        logging.error(f"Error getting description for {video_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error="Server error encountered"), 500

@app.route('/music')
def music():
    """Music page showing a list of songs from AnonMusic API"""
    try:
        return render_template('music.html')
    except Exception as e:
        logging.error(f"Error loading music page: {e}")
        return render_template('index.html', error="Müzik sayfası yüklenirken hata oluştu"), 500

@app.route('/music/<music_id>')
def music_detail(music_id):
    """Music detail page showing a specific song with its player"""
    try:
        # Şarkı bilgisini API'den al
        response = requests.get('https://anonmusic.glitch.me/api/s/all')
        
        if response.status_code != 200:
            logging.error(f"Error fetching music data: {response.status_code}")
            return render_template('index.html', error="Müzik bilgisi alınamadı"), 500
            
        music_list = response.json()
        music = next((m for m in music_list if m['id'] == music_id), None)
        
        if not music:
            return render_template('index.html', error="Şarkı bulunamadı"), 404
            
        # Formatlı şarkı oynatma sayısı
        plays_formatted = format_number_for_display(music.get('plays', 0))
        
        # Kapak resmi ve ses dosyası URL'lerini oluştur
        cover_url = f"https://anonmusic.glitch.me{music['imagePath']}"
        audio_url = f"https://anonmusic.glitch.me{music['audioPath']}"
        
        return render_template('music_detail.html', 
                              music=music, 
                              cover_url=cover_url, 
                              audio_url=audio_url,
                              plays_formatted=plays_formatted)
    except Exception as e:
        logging.error(f"Error loading music detail page: {e}")
        return render_template('index.html', error="Müzik detay sayfası yüklenirken hata oluştu"), 500

@app.route('/api/music')
def get_music_list():
    """API endpoint to get music list from AnonMusic API"""
    try:
        # Sunucu tarafında API çağrısı yap
        response = requests.get('https://anonmusic.glitch.me/api/s/all')
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            logging.error(f"Error fetching music data: {response.status_code}")
            return jsonify({"error": f"API returned status code {response.status_code}"}), response.status_code
    except Exception as e:
        logging.error(f"Error getting music list: {e}")
        return jsonify({"error": str(e)}), 500

def format_number_for_display(num):
    """Format a number for display (e.g., 1000 -> 1K, 1000000 -> 1M)"""
    if num < 1000:
        return str(num)
    elif num < 1000000:
        return f"{num/1000:.1f}K".replace('.0K', 'K')
    else:
        return f"{num/1000000:.1f}M".replace('.0M', 'M')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
from datetime import datetime, timedelta

# Create temp directory for cards
TEMP_CARDS_DIR = 'static/temp_cards'
os.makedirs(TEMP_CARDS_DIR, exist_ok=True)

def cleanup_old_cards():
    """Remove cards older than 5 minutes"""
    while True:
        now = datetime.now()
        for filename in os.listdir(TEMP_CARDS_DIR):
            filepath = os.path.join(TEMP_CARDS_DIR, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(filepath))
            if now - file_time > timedelta(minutes=5):
                try:
                    os.remove(filepath)
                except:
                    pass
        time.sleep(60)  # Check every minute

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_cards, daemon=True)
cleanup_thread.start()

@app.route('/api/videocard')
def generate_video_card():
    video_id = request.args.get('v', '')
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400

    try:
        # Check if card already exists and is fresh
        card_path = os.path.join(TEMP_CARDS_DIR, f'{video_id}.png')
        if os.path.exists(card_path):
            file_time = datetime.fromtimestamp(os.path.getctime(card_path))
            if datetime.now() - file_time < timedelta(minutes=5):
                return send_file(card_path, mimetype='image/png')

        video_info = get_video_details(video_id)
        
        # Create image with dark background
        width = 1280
        height = 720
        img = Image.new('RGB', (width, height), '#0d0d0d')
        draw = ImageDraw.Draw(img)
        
        # Load and resize thumbnail
        thumbnail_response = requests.get(video_info['thumbnail'])
        thumbnail = Image.open(io.BytesIO(thumbnail_response.content))
        thumbnail = thumbnail.resize((800, 450))
        
        # Add neon glow effect to thumbnail
        from PIL import ImageFilter
        glow = Image.new('RGB', (width, height), '#0d0d0d')
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.rectangle([220, 50, 1060, 500], fill='#9d4edd', outline='#ff8500', width=3)
        glow = glow.filter(ImageFilter.GaussianBlur(20))
        img.paste(glow, (0, 0), None)
        
        # Calculate positions
        thumb_x = (width - thumbnail.width) // 2
        thumb_y = 50
        
        # Load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            normal_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            stats_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            stats_font = ImageFont.load_default()
            
        # Draw thumbnail with border
        draw.rectangle([thumb_x-3, thumb_y-3, thumb_x+thumbnail.width+3, thumb_y+thumbnail.height+3], 
                      outline='#ff8500', width=3)
        img.paste(thumbnail, (thumb_x, thumb_y))
        
        # Draw title with neon effect
        y_offset = thumb_y + thumbnail.height + 30
        draw.text((width//2, y_offset), video_info['title'], 
                 font=title_font, fill='#ffffff', anchor="mm", stroke_width=1)
        
        # Draw channel name
        y_offset += 50
        draw.text((width//2, y_offset), f"by {video_info['channel']}", 
                 font=normal_font, fill='#9d4edd', anchor="mm")
        
        # Draw stats with icons
        y_offset += 50
        stats_text = f"👁️ {video_info.get('view_count', '0')} views  •  📅 {video_info.get('published_at', '')}"
        draw.text((width//2, y_offset), stats_text, 
                 font=stats_font, fill='#ff8500', anchor="mm")
        
        # Draw "Watch on NeonTube" with glow
        y_offset += 50
        draw.text((width//2, y_offset), "Watch on NeonTube!", 
                 font=title_font, fill='#ff8500', anchor="mm", stroke_width=2)
        
        # Save to file
        img.save(card_path, 'PNG')
        
        return send_file(card_path, mimetype='image/png')
    except Exception as e:
        logging.error(f"Error generating video card: {e}")
        return jsonify({'error': str(e)}), 500
