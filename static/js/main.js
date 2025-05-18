/**
 * Main JavaScript for the YouTube Alternative App
 * Handles common functionality across the site
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize search functionality
  initSearch();
  
  // Add lazy loading for video thumbnails
  initLazyLoading();
  
  // Add smooth transitions between pages
  initPageTransitions();
  
  // Handle dark theme toggles if implemented
  initTheme();
});

/**
 * Initialize search functionality
 */
function initSearch() {
  const searchForm = document.getElementById('search-form');
  const searchInput = document.getElementById('search-input');
  
  if (searchForm && searchInput) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = searchInput.value.trim();
      
      if (query) {
        window.location.href = `/search?q=${encodeURIComponent(query)}`;
      }
    });
  }
  
  // Set the search input value from URL params if on search page
  if (window.location.pathname === '/search') {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    if (query && searchInput) {
      searchInput.value = query;
    }
  }
}

/**
 * Initialize lazy loading for images
 */
function initLazyLoading() {
  if ('IntersectionObserver' in window) {
    const lazyImages = document.querySelectorAll('.lazy-load');
    
    const imageObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target;
          const src = img.dataset.src;
          
          if (src) {
            img.src = src;
            img.classList.remove('lazy-load');
            imageObserver.unobserve(img);
          }
        }
      });
    });
    
    lazyImages.forEach((img) => imageObserver.observe(img));
  } else {
    // Fallback for browsers that don't support IntersectionObserver
    const lazyImages = document.querySelectorAll('.lazy-load');
    
    lazyImages.forEach((img) => {
      img.src = img.dataset.src;
      img.classList.remove('lazy-load');
    });
  }
}

/**
 * Initialize smooth page transitions
 */
function initPageTransitions() {
  // Add animation classes when page loads
  document.body.classList.add('animate-fade-in');
  
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.classList.add('animate-slide-up');
  }
  
  // Add click handlers to video cards for smooth navigation
  const videoCards = document.querySelectorAll('.video-card');
  videoCards.forEach((card) => {
    card.addEventListener('click', (e) => {
      if (!e.target.matches('a')) {
        const videoId = card.dataset.videoId;
        if (videoId) {
          // Apply exit animation before navigating
          document.body.classList.add('animate-fade-out');
          setTimeout(() => {
            window.location.href = `/watch?v=${videoId}`;
          }, 300);
        }
      }
    });
  });
}

/**
 * Initialize theme preferences
 */
function initTheme() {
  // This is a stub for future theme customization
  // The current implementation uses a fixed dark theme
  // with purple/red accents as specified in CSS
}

/**
 * Format large numbers (views, etc.) into human-readable form
 * @param {number} num - The number to format
 * @returns {string} - Formatted number (e.g., 1.2M, 4.5K)
 */
function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  } else {
    return num.toString();
  }
}

/**
 * Format a date string to a relative time (e.g., "2 days ago")
 * @param {string} dateString - The date string to format
 * @returns {string} - Relative time string
 */
function formatRelativeTime(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffInMs = now - date;
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
  
  if (diffInDays < 1) {
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
    if (diffInHours < 1) {
      const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
      if (diffInMinutes < 1) {
        return 'Just now';
      }
      return `${diffInMinutes} minute${diffInMinutes === 1 ? '' : 's'} ago`;
    }
    return `${diffInHours} hour${diffInHours === 1 ? '' : 's'} ago`;
  } else if (diffInDays < 30) {
    return `${diffInDays} day${diffInDays === 1 ? '' : 's'} ago`;
  } else if (diffInDays < 365) {
    const diffInMonths = Math.floor(diffInDays / 30);
    return `${diffInMonths} month${diffInMonths === 1 ? '' : 's'} ago`;
  } else {
    const diffInYears = Math.floor(diffInDays / 365);
    return `${diffInYears} year${diffInYears === 1 ? '' : 's'} ago`;
  }
}

/**
 * Format duration in seconds to a human-readable format (MM:SS or HH:MM:SS)
 * @param {number} seconds - Duration in seconds
 * @returns {string} - Formatted time string
 */
function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes < 10 ? '0' : ''}${minutes}:${secs < 10 ? '0' : ''}${secs}`;
  } else {
    return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
  }
}
