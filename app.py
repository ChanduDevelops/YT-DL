# app.py - Complete Single Flask Application for YouTube Downloader
# Install dependencies: pip install flask yt-dlp

from flask import Flask, render_template_string, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import re
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# HTML Template with embedded CSS and JavaScript
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1.0, viewport-fit=cover"
    />
    <title>YouTube Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Small custom CSS to fix edge cases on mobile (safe to keep) -->
    <style>
      /* Ensure long URLs or titles break and don't overflow */
      .break-any { word-break: break-word; overflow-wrap: break-word; }

      /* Tweak the spinner size on small screens */
      .loader {
        border-bottom-color: rgba(220, 38, 38, 1);
        width: 48px;
        height: 48px;
      }

      /* Slightly reduce card padding on very small screens */
      @media (max-width: 380px) {
        .card-pad { padding: 0.75rem; }
        .page-pad { padding-left: 0.75rem; padding-right: 0.75rem; }
      }
    </style>
  </head>

  <body class="bg-gradient-to-br from-red-50 to-purple-50 min-h-screen">
    <div class="mx-auto page-pad py-6 max-w-3xl">
      <div class="bg-white rounded-2xl shadow-lg p-6 md:p-8">
        <!-- Header -->
        <div class="text-center mb-6">
          <h1 class="text-2xl md:text-4xl font-bold text-gray-800 mb-1">
            YouTube Downloader
          </h1>
          <p class="text-sm md:text-base text-gray-600">
            Download videos, shorts, audio, and thumbnails
          </p>
        </div>

        <!-- URL Input (stack on mobile) -->
        <div class="mb-6">
          <div class="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              id="videoUrl"
              placeholder="Paste YouTube URL or Shorts URL here..."
              class="flex-1 px-3 py-3 border-2 border-gray-300 rounded-lg focus:border-red-500 focus:outline-none break-any"
              aria-label="YouTube URL"
            />
            <button
              id="submitBtn"
              class="w-full sm:w-auto px-5 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold transition-colors disabled:opacity-60"
            >
              Submit
            </button>
          </div>
          <p class="mt-2 text-xs text-gray-500 break-any">
            Supports: youtube.com/watch?v=..., youtu.be/..., youtube.com/shorts/...
          </p>
        </div>

        <!-- Feedback -->
        <div id="feedback" class="hidden mb-4 p-3 rounded text-sm"></div>

        <!-- Loading -->
        <div id="loading" class="hidden text-center py-6">
          <div class="inline-block animate-spin rounded-full loader border-4 border-gray-200"></div>
          <p class="mt-3 text-gray-600 text-sm">Loading video information...</p>
        </div>

        <!-- Download Sections -->
        <div id="downloadSections" class="hidden space-y-4">
          <!-- Video Section -->
          <div class="mb-0 bg-gray-50 rounded-xl card-pad">
            <div class="flex items-center gap-2 mb-3">
              <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <h2 class="text-lg md:text-2xl font-semibold text-gray-800">Download Video</h2>
            </div>

            <div id="videoFormats" class="grid gap-3"></div>
          </div>

          <!-- Audio Section -->
          <div class="bg-gray-50 rounded-xl card-pad">
            <div class="flex items-center gap-2 mb-3">
              <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
              <h2 class="text-lg md:text-2xl font-semibold text-gray-800">Download Audio</h2>
            </div>

            <div id="audioFormats" class="grid gap-3"></div>
          </div>

          <!-- Thumbnail Section -->
          <div class="bg-gray-50 rounded-xl card-pad">
            <div class="flex items-center gap-2 mb-3">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <h2 class="text-lg md:text-2xl font-semibold text-gray-800">Download Thumbnail</h2>
            </div>

            <div id="thumbnails" class="grid gap-3"></div>
          </div>
        </div>
      </div>
    </div>

    <script>
      let currentVideoData = null;

      const elements = {
        videoUrl: document.getElementById('videoUrl'),
        submitBtn: document.getElementById('submitBtn'),
        feedback: document.getElementById('feedback'),
        loading: document.getElementById('loading'),
        downloadSections: document.getElementById('downloadSections'),
        videoFormats: document.getElementById('videoFormats'),
        audioFormats: document.getElementById('audioFormats'),
        thumbnails: document.getElementById('thumbnails')
      };

      function showFeedback(message, type = 'info') {
        elements.feedback.className = `mb-4 p-3 rounded text-sm ${type === 'error' ? 'bg-red-50 border-l-4 border-red-500 text-red-700' :
          type === 'success' ? 'bg-green-50 border-l-4 border-green-500 text-green-700' :
          'bg-blue-50 border-l-4 border-blue-500 text-blue-700'}`;
        elements.feedback.textContent = message;
        elements.feedback.classList.remove('hidden');
      }

      function hideFeedback() {
        elements.feedback.classList.add('hidden');
      }

      async function fetchVideoInfo() {
        const url = elements.videoUrl.value.trim();

        if (!url) {
          showFeedback('Please enter a YouTube URL', 'error');
          return;
        }

        hideFeedback();
        elements.loading.classList.remove('hidden');
        elements.downloadSections.classList.add('hidden');
        elements.submitBtn.disabled = true;

        try {
          const response = await fetch('/api/video-info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to fetch video info');
          }

          currentVideoData = await response.json();
          displayVideoData();
          showFeedback('Video loaded! Select quality and download.', 'success');
        } catch (error) {
          showFeedback(error.message, 'error');
        } finally {
          elements.loading.classList.add('hidden');
          elements.submitBtn.disabled = false;
        }
      }

      function formatCardInner(label, subtitle, btnClass, onClickAttr) {
        /* helper to create responsive card markup:
           - stacked on narrow screens
           - button full-width on narrow screens
           - shows subtitle (filesize / bitrate) with line wrap */
        return `
          <div class="flex flex-col sm:flex-row sm:items-center justify-between bg-white p-3 rounded-lg shadow-sm">
            <div class="text-left break-any mb-3 sm:mb-0">
              <div class="font-semibold text-gray-700">${label}</div>
              ${subtitle ? `<div class="text-xs text-gray-500 mt-1">${subtitle}</div>` : ''}
            </div>
            <div class="sm:ml-4">
              <button ${onClickAttr} class="${btnClass} w-full sm:w-auto px-4 py-2 rounded-lg font-medium">
                Download
              </button>
            </div>
          </div>
        `;
      }

      function displayVideoData() {
        // VIDEO FORMATS
        elements.videoFormats.innerHTML = currentVideoData.video_formats.map(format => {
          const label = `${format.quality} · ${format.ext.toUpperCase()}`;
          const size = format.filesize ? (Math.round(format.filesize / (1024*1024)) + ' MB') : '';
          const subtitle = size ? `${size}` : '';
          const onclick = `onclick="downloadVideo('${format.format_id}')"`;
          return formatCardInner(label, subtitle, 'bg-red-600 text-white hover:bg-red-700', onclick);
        }).join('');

        // AUDIO FORMATS
        elements.audioFormats.innerHTML = currentVideoData.audio_formats.map(format => {
          const label = `${format.quality} · ${format.ext.toUpperCase()}`;
          const onclick = `onclick="downloadAudio('${format.format_id}')"`;
          return formatCardInner(label, '', 'bg-purple-600 text-white hover:bg-purple-700', onclick);
        }).join('');

        // THUMBNAILS — show small preview + download button
        elements.thumbnails.innerHTML = currentVideoData.thumbnails.map((thumb, index) => {
          const label = `${thumb.quality}`;
          const onclick = `onclick="downloadThumbnail('${encodeURIComponent(thumb.url)}', '${index}')"`;
          // include a tiny preview to help mobile users choose
          return `
            <div class="flex items-center justify-between bg-white p-3 rounded-lg shadow-sm">
              <div class="flex items-center gap-3">
                <img src="${thumb.url}" alt="thumb" class="w-16 h-9 object-cover rounded-sm hidden sm:block" />
                <div class="break-any">
                  <div class="font-semibold text-gray-700">${label}</div>
                </div>
              </div>
              <div>
                <button ${onclick} class="bg-green-600 text-white hover:bg-green-700 w-full sm:w-auto px-4 py-2 rounded-lg font-medium">
                  Download
                </button>
              </div>
            </div>
          `;
        }).join('');

        elements.downloadSections.classList.remove('hidden');
      }

      function downloadVideo(formatId) {
        showFeedback('Download started: Video', 'success');
        const url = elements.videoUrl.value.trim();
        window.location.href = `/api/download/video?url=${encodeURIComponent(url)}&format_id=${formatId}`;
      }

      function downloadAudio(formatId) {
        showFeedback('Download started: Audio', 'success');
        const url = elements.videoUrl.value.trim();
        window.location.href = `/api/download/audio?url=${encodeURIComponent(url)}&format_id=${formatId}`;
      }

      function downloadThumbnail(thumbnailUrl, index) {
        showFeedback('Download started: Thumbnail', 'success');
        const filename = `thumbnail_${currentVideoData.video_id}_${index}.jpg`;
        window.location.href = `/api/download/thumbnail?url=${thumbnailUrl}&filename=${encodeURIComponent(filename)}`;
      }

      elements.submitBtn.addEventListener('click', fetchVideoInfo);
      elements.videoUrl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchVideoInfo();
      });
    </script>
  </body>
</html>
'''


def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    # Handle shorts URLs
    shorts_match = re.search(r'shorts/([a-zA-Z0-9_-]+)', url)
    if shorts_match:
        return shorts_match.group(1)

    # Handle regular URLs
    patterns = [
                r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
                r'(?:embed\/)([0-9A-Za-z_-]{11})',
                r'^([0-9A-Za-z_-]{11})$'
                ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None

@app.route('/')
def index():
    """Serve the main page"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/video-info', methods=['POST'])
def video_info():
    """Get video information and available formats"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        standard_url = f'https://www.youtube.com/watch?v={video_id}'

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'cookiefile': 'youtube_cookies.txt'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(standard_url, download=False)

        # --- FIX STARTS HERE ---
        
        # Extract video formats
        video_formats = []
        seen_qualities = set()

        for fmt in info.get('formats', []):
            # Only process if it has both audio and video
            if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                quality = fmt.get('format_note', fmt.get('height', 'unknown'))
                
                # INDENTATION FIX: These lines must be INSIDE the if block
                if quality not in seen_qualities:
                    video_formats.append({
                        'format_id': fmt['format_id'],
                        'quality': f"{quality}p" if isinstance(quality, int) else quality,
                        'ext': fmt.get('ext', 'mp4'),
                        'filesize': fmt.get('filesize', 0)
                    })
                    seen_qualities.add(quality)

        # Sort video formats
        quality_order = {'2160p': 0, '1440p': 1, '1080p': 2, '720p': 3, '480p': 4, '360p': 5, '240p': 6, '144p': 7}
        video_formats.sort(key=lambda x: quality_order.get(x['quality'], 999))

        # Extract audio formats
        audio_formats = []
        seen_bitrates = set()

        for fmt in info.get('formats', []):
            # Only process if it is audio only
            if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                bitrate = fmt.get('abr', 0)
                
                # INDENTATION FIX: Apply same fix to audio to prevent 'bitrate' error
                if bitrate and bitrate not in seen_bitrates:
                    audio_formats.append({
                        'format_id': fmt['format_id'],
                        'quality': f"{int(bitrate)}kbps",
                        'ext': fmt.get('ext', 'mp3')
                    })
                    seen_bitrates.add(bitrate)

        # Sort audio formats
        audio_formats.sort(key=lambda x: int(x['quality'].replace('kbps', '')), reverse=True)

        # --- FIX ENDS HERE ---

        # Extract thumbnails
        thumbnails = []
        for thumb in info.get('thumbnails', [])[-4:]: 
            width = thumb.get('width', 0)
            quality = 'Max Resolution' if width >= 1920 else \
                     'High Quality' if width >= 1280 else \
                     'Medium Quality' if width >= 640 else 'Default'
            thumbnails.append({
                'url': thumb['url'],
                'quality': f"{quality} ({width}x{thumb.get('height', 0)})",
                'width': width
            })

        thumbnails.sort(key=lambda x: x['width'], reverse=True)

        return jsonify({
            'title': info.get('title', 'Unknown'),
            'video_id': video_id,
            'video_formats': video_formats,
            'audio_formats': audio_formats,
            'thumbnails': thumbnails
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/download/video')
def download_video():
    """Download video in specified format"""
    try:
        url = request.args.get('url', '').strip()
        format_id = request.args.get('format_id')

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        standard_url = f'https://www.youtube.com/watch?v={video_id}'

        # Create temporary file
        temp_dir = tempfile.gettempdir()
        output_template = os.path.join(temp_dir, f'{video_id}.%(ext)s')

        ydl_opts = {
        'format': format_id,
        'outtmpl': output_template,
        'quiet': True,
        'cookiefile': 'youtube_cookies.txt'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(standard_url, download=True)
            filename = ydl.prepare_filename(info)

        return send_file(
        filename,
        as_attachment=True,
        download_name=f"{info['title']}.{info['ext']}"
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/audio')
def download_audio():
    """Download audio in specified format"""
    try:
        url = request.args.get('url', '').strip()
        format_id = request.args.get('format_id')

        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        standard_url = f'https://www.youtube.com/watch?v={video_id}'

        # Create temporary file
        temp_dir = tempfile.gettempdir()
        output_template = os.path.join(temp_dir, f'{video_id}_audio.%(ext)s')

        ydl_opts = {
        'format': format_id,
        'outtmpl': output_template,
        'quiet': True,
        'cookiefile': 'youtube_cookies.txt'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(standard_url, download=True)
            filename = ydl.prepare_filename(info)

        return send_file(
        filename,
        as_attachment=True,
        download_name=f"{info['title']}_audio.{info['ext']}"
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/thumbnail')
def download_thumbnail():
    """Download thumbnail image"""
    try:
        import requests

        thumbnail_url = request.args.get('url')
        filename = request.args.get('filename', 'thumbnail.jpg')

        response = requests.get(thumbnail_url)

        temp_file = os.path.join(tempfile.gettempdir(), filename)
        with open(temp_file, 'wb') as f:
            f.write(response.content)

        return send_file(
        temp_file,
        as_attachment=True,
        download_name=filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 YouTube Downloader starting...")
    print("📱 Open your browser to: http://localhost:5000")
    print("✨ Supports regular videos and YouTube Shorts!")
    app.run(debug=True, host='0.0.0.0', port=5000)