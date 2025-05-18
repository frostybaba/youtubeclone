/**
 * Custom Video Player for YouTube Alternative
 * Provides a clean, ad-free video player experience
 */

class VideoPlayer {
  constructor(videoElement, controlsWrapper) {
    this.video = videoElement;
    this.controls = controlsWrapper;
    this.videoId = null;
    this.currentQuality = '720';
    this.isLooping = false; // Add loop state
    
    // Control elements
    this.playPauseBtn = document.getElementById('play-pause-btn');
    this.muteBtn = document.getElementById('mute-btn');
    this.fullscreenBtn = document.getElementById('fullscreen-btn');
    this.loopBtn = document.getElementById('loop-btn'); // Add loop button
    this.progressContainer = document.getElementById('progress-container');
    this.progressBar = document.getElementById('progress-bar');
    this.volumeSlider = document.getElementById('volume-slider');
    this.currentTime = document.getElementById('current-time');
    this.duration = document.getElementById('duration');
    this.qualitySelector = document.getElementById('quality-selector');
    
    // Initialize
    this.init();
  }
  
  init() {
    // Get video ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    this.videoId = urlParams.get('v');
    
    if (!this.videoId) {
      console.error('No video ID found in URL');
      this.showError('Video not found', 'Please check the URL and try again');
      return;
    }
    
    // Set up event listeners
    this.setupEventListeners();
    
    // Load video
    this.loadVideo(this.videoId, this.currentQuality);
  }
  
  setupEventListeners() {
    // Play/Pause
    this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
    this.video.addEventListener('click', () => this.togglePlayPause());
    
    // Loop video
    if (this.loopBtn) {
      this.loopBtn.addEventListener('click', () => this.toggleLoop());
    }
    
    // Video events
    this.video.addEventListener('loadedmetadata', () => this.updateDuration());
    this.video.addEventListener('timeupdate', () => this.updateProgress());
    this.video.addEventListener('ended', () => this.videoEnded());
    this.video.addEventListener('waiting', () => this.showBuffering());
    this.video.addEventListener('playing', () => this.hideBuffering());
    
    // Progress bar
    this.progressContainer.addEventListener('click', (e) => this.seek(e));
    
    // Volume
    this.muteBtn.addEventListener('click', () => this.toggleMute());
    this.volumeSlider.addEventListener('input', () => this.changeVolume());
    
    // Fullscreen
    this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => this.handleKeyPress(e));
    
    // Handle quality button click to toggle menu
    const qualityBtn = document.getElementById('quality-btn');
    if (qualityBtn) {
      qualityBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Tıklamanın yayılmasını önle
        const qualitySelector = document.querySelector('.quality-selector');
        qualitySelector.classList.toggle('menu-open');
      });
    }
    
    // Handle quality change events
    const qualityOptions = document.querySelectorAll('.quality-option');
    qualityOptions.forEach(option => {
      option.addEventListener('click', (e) => {
        e.stopPropagation(); // Tıklamanın yayılmasını önle
        this.changeQuality(option.dataset.quality);
        // Menüyü açık tutmaya devam et, böylece kullanıcı farklı kalite seçeneklerini kolayca deneyebilir
      });
    });
    
    // Close quality menu when clicking elsewhere
    document.addEventListener('click', () => {
      const qualitySelector = document.querySelector('.quality-selector');
      if (qualitySelector) {
        qualitySelector.classList.remove('menu-open');
      }
    });
  }
  
  loadVideo(videoId, quality) {
    // Always show buffering indicator regardless of quality
    this.showBuffering();
    
    // Set mode based on quality
    const mode = quality === 'best' ? 'experimental' : 'normal';
    
    // Get stream URL from API
    fetch(`/api/stream?v=${videoId}&quality=${quality}&mode=${mode}`)
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to get video stream');
        }
        return response.json();
      })
      .then(data => {
        if (data.error) {
          throw new Error(data.error);
        }
        
        if (data.mode === 'experimental') {
            console.log('Using experimental mode (highest quality)');
            
            // Create audio element for experimental mode if it doesn't exist
            if (!this.audioElement) {
                this.audioElement = new Audio();
            }
            
            // Set audio properties
            this.audioElement.volume = this.video.volume;
            this.audioElement.muted = this.video.muted;
            
            // Set sources
            this.video.src = data.video_url;
            this.audioElement.src = data.audio_url;
            
            // Create precise sync between video and audio
            this.bothMediaReady = false;
            this.syncInterval = null;
            this.isWaitingForSync = false;
            
            // Reset sync flags when media sources change
            this.video.onloadstart = () => {
                this.bothMediaReady = false;
                this.videoReady = false;
            };
            
            this.audioElement.onloadstart = () => {
                this.bothMediaReady = false;
                this.audioReady = false;
            };
            
            // Initial loading of both media elements
            const waitForBothMediaReady = () => {
                return new Promise((resolve) => {
                    const checkReady = () => {
                        const videoReady = this.video.readyState >= 3; // HAVE_FUTURE_DATA
                        const audioReady = this.audioElement.readyState >= 3;
                        
                        if (videoReady && audioReady) {
                            console.log("Both media elements ready to play");
                            this.bothMediaReady = true;
                            resolve();
                        } else {
                            setTimeout(checkReady, 50);
                        }
                    };
                    
                    checkReady();
                });
            };
            
            // Setup precise sync at playback start
            this.video.oncanplay = () => {
                if (!this.bothMediaReady && !this.isWaitingForSync) {
                    this.isWaitingForSync = true;
                    
                    waitForBothMediaReady().then(() => {
                        this.isWaitingForSync = false;
                        
                        // If user has clicked play but media wasn't ready yet
                        if (!this.video.paused) {
                            // Make sure both start exactly together
                            this.audioElement.currentTime = this.video.currentTime;
                            this.audioElement.play().catch(err => {
                                console.error('Error playing audio:', err);
                            });
                        }
                        
                        // Start periodic sync check if not already running
                        if (!this.syncInterval) {
                            this.startPeriodicSync();
                        }
                    });
                }
            };
            
            // Video play handling with precise sync
            this.video.onplay = () => {
                if (this.audioElement) {
                    if (this.bothMediaReady) {
                        // Ensure perfect sync before playing
                        this.audioElement.currentTime = this.video.currentTime;
                        this.audioElement.play().catch(err => {
                            console.error('Error playing audio:', err);
                            if (this.currentQuality === 'best') {
                                console.log('Audio playback failed, falling back to normal mode');
                                this.changeQuality('720');
                            }
                        });
                    } else {
                        // Let the canplay handler deal with it when both are ready
                        console.log("Waiting for both media to be ready before sync play");
                    }
                    
                    // Start periodic sync check if not already running
                    if (!this.syncInterval) {
                        this.startPeriodicSync();
                    }
                }
            };
            
            // When video pauses, also pause audio
            this.video.onpause = () => {
                if (this.audioElement && !this.audioElement.paused) {
                    this.audioElement.pause();
                }
            };
            
            // When seeking, ensure perfect sync
            this.video.onseeking = () => {
                if (this.audioElement) {
                    console.log(`Syncing audio to video time: ${this.video.currentTime.toFixed(3)}`);
                    this.audioElement.currentTime = this.video.currentTime;
                }
            };
            
            // Periodic sync check - runs every 2 seconds
            this.startPeriodicSync = () => {
                if (this.syncInterval) {
                    clearInterval(this.syncInterval);
                }
                
                this.syncInterval = setInterval(() => {
                    if (this.audioElement && this.video && !this.video.paused) {
                        const diff = Math.abs(this.video.currentTime - this.audioElement.currentTime);
                        
                        // If out of sync by more than 0.1 seconds, resync
                        if (diff > 0.1) {
                            console.log(`Periodic sync correction: ${diff.toFixed(3)}s difference`);
                            this.audioElement.currentTime = this.video.currentTime;
                        }
                    }
                }, 2000); // Check every 2 seconds
            };
            
            // When video ends, make sure audio also stops
            this.video.onended = () => {
                if (this.audioElement) {
                    this.audioElement.pause();
                }
                this.videoEnded();
            };
            
            // Load both media elements
            this.video.load();
            this.audioElement.load();
        } else {
            // Normal mode
            if (this.audioElement) {
                this.audioElement.src = '';
            }
            this.video.src = data.url;
            this.video.load();
        }
        
        // Save current playback time and status
        const wasPlaying = !this.video.paused;
        const currentTime = this.video.currentTime;
        
        // Set listeners for when video is loaded
        this.video.onloadeddata = () => {
          this.hideBuffering();
          this.video.currentTime = currentTime;
          if (wasPlaying) {
            this.video.play().catch(err => console.error('Error playing video:', err));
          }
        };
        
        // Update active quality option
        this.updateActiveQualityOption(quality);
      })
      .catch(error => {
        console.error('Error loading video:', error);
        this.showError('Failed to load video', error.message);
      });
  }
  
  togglePlayPause() {
    if (this.video.paused) {
      // Play the video
      this.video.play().catch(err => console.error('Error playing video:', err));
      this.playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
      
      // Also play the audio if in experimental mode
      if (this.audioElement && this.audioElement.src) {
        this.audioElement.play().catch(err => console.error('Error playing audio:', err));
      }
    } else {
      // Pause the video
      this.video.pause();
      this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
      
      // Also pause the audio if in experimental mode
      if (this.audioElement && this.audioElement.src) {
        this.audioElement.pause();
      }
    }
  }
  
  updateProgress() {
    const percent = (this.video.currentTime / this.video.duration) * 100;
    this.progressBar.style.width = `${percent}%`;
    
    // Update time display
    this.currentTime.textContent = this.formatTime(this.video.currentTime);
  }
  
  updateDuration() {
    this.duration.textContent = this.formatTime(this.video.duration);
  }
  
  formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
  }
  
  seek(e) {
    const rect = this.progressContainer.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    const newTime = pos * this.video.duration;
    
    // Set video time
    this.video.currentTime = newTime;
    
    // Sync audio if in experimental mode
    if (this.audioElement && this.audioElement.src) {
      this.audioElement.currentTime = newTime;
    }
  }
  
  toggleMute() {
    // Toggle video mute state
    this.video.muted = !this.video.muted;
    
    // Also toggle audio mute state if in experimental mode
    if (this.audioElement && this.audioElement.src) {
      this.audioElement.muted = this.video.muted;
    }
    
    // Update UI
    this.muteBtn.innerHTML = this.video.muted ? 
      '<i class="fas fa-volume-mute"></i>' : 
      '<i class="fas fa-volume-up"></i>';
    this.volumeSlider.value = this.video.muted ? 0 : this.video.volume * 100;
  }
  
  changeVolume() {
    const volumeLevel = this.volumeSlider.value / 100;
    
    // Set video volume
    this.video.volume = volumeLevel;
    this.video.muted = (volumeLevel === 0);
    
    // Also set audio volume if in experimental mode
    if (this.audioElement && this.audioElement.src) {
      this.audioElement.volume = volumeLevel;
      this.audioElement.muted = (volumeLevel === 0);
    }
    
    // Update mute button icon
    this.muteBtn.innerHTML = (volumeLevel === 0) ? 
      '<i class="fas fa-volume-mute"></i>' : 
      '<i class="fas fa-volume-up"></i>';
  }
  
  toggleFullscreen() {
    const playerWrapper = document.querySelector('.video-player-wrapper');
    
    if (!document.fullscreenElement) {
      if (playerWrapper.requestFullscreen) {
        playerWrapper.requestFullscreen();
      } else if (playerWrapper.webkitRequestFullscreen) {
        playerWrapper.webkitRequestFullscreen();
      } else if (playerWrapper.msRequestFullscreen) {
        playerWrapper.msRequestFullscreen();
      }
      this.fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>';
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
      }
      this.fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
    }
  }
  
  videoEnded() {
    this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
    
    // If loop is enabled, restart the video
    if (this.isLooping) {
      this.video.currentTime = 0;
      this.video.play().catch(err => console.error('Error playing video in loop:', err));
      
      // Also restart audio if in experimental mode
      if (this.audioElement && this.audioElement.src) {
        this.audioElement.currentTime = 0;
        this.audioElement.play().catch(err => console.error('Error playing audio in loop:', err));
      }
    }
  }
  
  // Toggle loop functionality
  toggleLoop() {
    this.isLooping = !this.isLooping;
    
    // Update the loop button UI
    if (this.loopBtn) {
      if (this.isLooping) {
        this.loopBtn.classList.add('active');
        this.loopBtn.innerHTML = '<i class="fas fa-redo" style="color: var(--accent);"></i>';
      } else {
        this.loopBtn.classList.remove('active');
        this.loopBtn.innerHTML = '<i class="fas fa-redo"></i>';
      }
    }
  }
  
  showBuffering() {
    const bufferingIndicator = document.getElementById('buffering');
    if (bufferingIndicator) {
      bufferingIndicator.style.display = 'flex';
    }
  }
  
  hideBuffering() {
    const bufferingIndicator = document.getElementById('buffering');
    if (bufferingIndicator) {
      bufferingIndicator.style.display = 'none';
    }
  }
  
  changeQuality(quality) {
    if (quality === this.currentQuality) return;
    
    // Remember current playback state
    const currentTime = this.video.currentTime;
    const wasPlaying = !this.video.paused;
    
    // Update quality and reload video
    this.currentQuality = quality;
    this.loadVideo(this.videoId, quality);
    
    // Save time position to resume from
    this.video.oncanplay = () => {
      this.video.currentTime = currentTime;
      if (wasPlaying) {
        this.video.play().catch(err => console.error('Error resuming video:', err));
      }
    };
  }
  
  updateActiveQualityOption(quality) {
    const options = document.querySelectorAll('.quality-option');
    options.forEach(option => {
      if (option.dataset.quality === quality) {
        option.classList.add('active');
      } else {
        option.classList.remove('active');
      }
    });
  }
  
  handleKeyPress(e) {
    switch(e.key.toLowerCase()) {
      case ' ':
      case 'k':
        // Space or K - Play/Pause
        e.preventDefault();
        this.togglePlayPause();
        break;
      case 'f':
        // F - Fullscreen
        e.preventDefault();
        this.toggleFullscreen();
        break;
      case 'm':
        // M - Mute
        e.preventDefault();
        this.toggleMute();
        break;
      case 'arrowright':
        // Right arrow - Forward 5 seconds
        e.preventDefault();
        const forwardTime = Math.min(this.video.duration, this.video.currentTime + 5);
        this.video.currentTime = forwardTime;
        if (this.audioElement && this.audioElement.src) {
          this.audioElement.currentTime = forwardTime;
        }
        break;
      case 'arrowleft':
        // Left arrow - Backward 5 seconds
        e.preventDefault();
        const backwardTime = Math.max(0, this.video.currentTime - 5);
        this.video.currentTime = backwardTime;
        if (this.audioElement && this.audioElement.src) {
          this.audioElement.currentTime = backwardTime;
        }
        break;
      case 'arrowup':
        // Up arrow - Volume up
        e.preventDefault();
        this.volumeSlider.value = Math.min(100, parseInt(this.volumeSlider.value) + 5);
        this.changeVolume();
        break;
      case 'arrowdown':
        // Down arrow - Volume down
        e.preventDefault();
        this.volumeSlider.value = Math.max(0, parseInt(this.volumeSlider.value) - 5);
        this.changeVolume();
        break;
      case '0':
      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
      case '6':
      case '7':
      case '8':
      case '9':
        // Number keys - Jump to percentage of video
        e.preventDefault();
        const percent = parseInt(e.key) * 10;
        const jumpTime = (percent / 100) * this.video.duration;
        this.video.currentTime = jumpTime;
        if (this.audioElement && this.audioElement.src) {
          this.audioElement.currentTime = jumpTime;
        }
        break;
    }
  }
  
  showError(title, message) {
    const playerWrapper = document.querySelector('.video-player-wrapper');
    playerWrapper.innerHTML = `
      <div class="error-container">
        <div class="error-icon"><i class="fas fa-exclamation-circle"></i></div>
        <h3 class="error-message">${title}</h3>
        <p class="error-details">${message}</p>
        <a href="/" class="btn btn-accent">Back to Home</a>
      </div>
    `;
  }
}

// Initialize player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const videoElement = document.getElementById('video-player');
  const controlsWrapper = document.getElementById('custom-controls');
  
  if (videoElement && controlsWrapper) {
    const player = new VideoPlayer(videoElement, controlsWrapper);
    
    // Add mobile touch controls
    if (window.innerWidth <= 768) {
      const touchOverlay = document.createElement('div');
      touchOverlay.className = 'mobile-touch-overlay';
      
      const touchControls = document.createElement('div');
      touchControls.className = 'mobile-touch-controls';
      touchControls.innerHTML = `
        <button class="mobile-control-btn" id="mobile-prev">
          <i class="fas fa-backward"></i>
        </button>
        <button class="mobile-control-btn" id="mobile-play">
          <i class="fas fa-play"></i>
        </button>
        <button class="mobile-control-btn" id="mobile-next">
          <i class="fas fa-forward"></i>
        </button>
      `;
      
      touchOverlay.appendChild(touchControls);
      videoElement.parentElement.appendChild(touchOverlay);
      
      let touchStartX = 0;
      let touchStartTime = 0;
      let controlsVisible = false;
      let controlsTimeout;
      
      // Double tap to seek
      touchOverlay.addEventListener('touchstart', (e) => {
        const touch = e.touches[0];
        const now = Date.now();
        const timeDiff = now - touchStartTime;
        
        if (timeDiff < 300) {
          // Double tap
          const windowWidth = window.innerWidth;
          if (touch.clientX > windowWidth / 2) {
            player.video.currentTime += 10;
          } else {
            player.video.currentTime -= 10;
          }
        }
        
        touchStartX = touch.clientX;
        touchStartTime = now;
      });
      
      // Show/hide controls
      touchOverlay.addEventListener('click', () => {
        controlsVisible = !controlsVisible;
        touchControls.classList.toggle('visible');
        
        if (controlsVisible) {
          clearTimeout(controlsTimeout);
          controlsTimeout = setTimeout(() => {
            touchControls.classList.remove('visible');
            controlsVisible = false;
          }, 3000);
        }
      });
      
      // Mobile control buttons
      document.getElementById('mobile-play').addEventListener('click', (e) => {
        e.stopPropagation();
        player.togglePlayPause();
      });
      
      document.getElementById('mobile-prev').addEventListener('click', (e) => {
        e.stopPropagation();
        player.video.currentTime -= 10;
      });
      
      document.getElementById('mobile-next').addEventListener('click', (e) => {
        e.stopPropagation();
        player.video.currentTime += 10;
      });
      
      // Update play button icon
      player.video.addEventListener('play', () => {
        document.getElementById('mobile-play').innerHTML = '<i class="fas fa-pause"></i>';
      });
      
      player.video.addEventListener('pause', () => {
        document.getElementById('mobile-play').innerHTML = '<i class="fas fa-play"></i>';
      });
    }
    
    // Make player accessible globally for debugging
    window.player = player;
  }
});


  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      showNotification('Copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  }

  function setupShareAndDownload() {
    const shareBtn = document.getElementById('share-btn');
    const downloadBtn = document.getElementById('download-btn');
    const videoId = new URLSearchParams(window.location.search).get('v');

    if (shareBtn) {
      shareBtn.addEventListener('click', () => {
        const shareMenu = document.createElement('div');
        shareMenu.className = 'share-menu';
        shareMenu.innerHTML = `
          <div class="share-option" data-type="youtube">Copy YouTube URL</div>
          <div class="share-option" data-type="neontube">Copy NeonTube URL</div>
          <div class="share-option" data-type="source">Copy 720p Source URL</div>
          <div class="share-option" data-type="audio">Copy Audio URL</div>
          <div class="share-option" data-type="card">Copy Video Card</div>
        `;

        document.body.appendChild(shareMenu);

        shareMenu.addEventListener('click', async (e) => {
          const option = e.target.dataset.type;
          if (!option) return;

          try {
            switch(option) {
              case 'youtube':
                await copyToClipboard(`https://youtube.com/watch?v=${videoId}`);
                break;
              case 'neontube':
                // Tam URL'yi al (sayfanın tam adresi)
                const fullUrl = window.location.origin + window.location.pathname + window.location.search;
                await copyToClipboard(fullUrl);
                break;
              case 'source':
                const response = await fetch(`/api/stream?v=${videoId}&quality=720`);
                const data = await response.json();
                if (data.url) {
                  await copyToClipboard(data.url);
                } else if (data.error) {
                  throw new Error(data.error);
                } else {
                  throw new Error('Could not get stream URL');
                }
                break;
              case 'audio':
                const audioResponse = await fetch(`/api/stream?v=${videoId}&quality=bestaudio`);
                const audioData = await audioResponse.json();
                if (audioData.url || audioData.audio_url) {
                  await copyToClipboard(audioData.url || audioData.audio_url);
                } else if (audioData.error) {
                  throw new Error(audioData.error);
                } else {
                  throw new Error('Could not get audio URL');
                }
                break;
              case 'card':
                // Tam videocard URL'sini al
                const cardUrl = window.location.origin + `/api/videocard?v=${videoId}`;
                await copyToClipboard(cardUrl);
                break;
            }
          } catch (error) {
            console.error('Error during share operation:', error);
            showNotification('Failed to copy: ' + error.message);
          }

          shareMenu.remove();
        });

        // Close menu when clicking outside
        document.addEventListener('click', function closeMenu(e) {
          if (!shareMenu.contains(e.target) && e.target !== shareBtn) {
            shareMenu.remove();
            document.removeEventListener('click', closeMenu);
          }
        });
      });
    }

    if (downloadBtn) {
      downloadBtn.addEventListener('click', async () => {
        const response = await fetch(`/api/stream?v=${videoId}&quality=720`);
        const data = await response.json();
        window.open(data.url, '_blank');
      });
    }
  }

  setupShareAndDownload();
