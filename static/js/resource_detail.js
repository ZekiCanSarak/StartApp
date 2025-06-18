// Handle resource content tabs
document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            const tabId = button.dataset.tab;
            document.getElementById(tabId).classList.add('active');
        });
    });
});

// Handle code copy functionality
document.addEventListener('DOMContentLoaded', function() {
    const codeBlocks = document.querySelectorAll('.code-block');
    
    codeBlocks.forEach(block => {
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
        block.appendChild(copyButton);

        copyButton.addEventListener('click', async () => {
            const code = block.querySelector('code').textContent;
            try {
                await navigator.clipboard.writeText(code);
                copyButton.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            } catch (err) {
                console.error('Failed to copy text:', err);
                copyButton.innerHTML = '<i class="fas fa-times"></i>';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            }
        });
    });
});

// Handle resource completion tracking
function markResourceComplete(resourceId) {
    fetch('/mark_resource_complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `resource_id=${resourceId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const button = document.querySelector('.complete-button');
            button.classList.add('completed');
            button.innerHTML = '<i class="fas fa-check"></i> Completed';
            
            // Update progress bar if it exists
            const progressBar = document.querySelector('.progress-bar');
            if (progressBar && data.progress) {
                progressBar.style.width = `${data.progress}%`;
                progressBar.setAttribute('aria-valuenow', data.progress);
                progressBar.textContent = `${data.progress}%`;
            }
        } else {
            alert(data.error || 'Failed to mark resource as complete');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to mark resource as complete');
    });
}

// Handle resource feedback
const feedbackForm = document.getElementById('feedback-form');
if (feedbackForm) {
    feedbackForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch('/submit_resource_feedback', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                const successMessage = document.createElement('div');
                successMessage.className = 'alert alert-success';
                successMessage.textContent = 'Thank you for your feedback!';
                feedbackForm.parentNode.insertBefore(successMessage, feedbackForm);
                
                // Clear form
                feedbackForm.reset();
                
                // Remove success message after 3 seconds
                setTimeout(() => {
                    successMessage.remove();
                }, 3000);
            } else {
                alert(data.error || 'Failed to submit feedback');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to submit feedback');
        });
    });
}

// Handle resource rating
function rateResource(resourceId, rating) {
    fetch('/rate_resource', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `resource_id=${resourceId}&rating=${rating}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update rating stars
            const stars = document.querySelectorAll('.rating-star');
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.classList.add('active');
                } else {
                    star.classList.remove('active');
                }
            });
            
            // Update average rating if displayed
            if (data.average_rating) {
                const avgRating = document.querySelector('.average-rating');
                if (avgRating) {
                    avgRating.textContent = data.average_rating.toFixed(1);
                }
            }
        } else {
            alert(data.error || 'Failed to submit rating');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to submit rating');
    });
}

// Handle bookmark functionality
function toggleBookmark(resourceId) {
    fetch('/toggle_bookmark', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `resource_id=${resourceId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const bookmarkButton = document.querySelector('.bookmark-button');
            if (data.bookmarked) {
                bookmarkButton.innerHTML = '<i class="fas fa-bookmark"></i>';
                bookmarkButton.classList.add('active');
            } else {
                bookmarkButton.innerHTML = '<i class="far fa-bookmark"></i>';
                bookmarkButton.classList.remove('active');
            }
        } else {
            alert(data.error || 'Failed to toggle bookmark');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to toggle bookmark');
    });
} 