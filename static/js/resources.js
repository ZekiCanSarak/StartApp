// Handle resource filtering
document.addEventListener('DOMContentLoaded', function() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const resourceCards = document.querySelectorAll('.resource-card');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            button.classList.add('active');
            
            const category = button.dataset.category;
            
            resourceCards.forEach(card => {
                if (category === 'all' || card.dataset.category === category) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
});

// Handle resource search
const searchInput = document.getElementById('resource-search');
if (searchInput) {
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const resourceCards = document.querySelectorAll('.resource-card');
        
        resourceCards.forEach(card => {
            const title = card.querySelector('.resource-title').textContent.toLowerCase();
            const description = card.querySelector('.resource-description').textContent.toLowerCase();
            
            if (title.includes(searchTerm) || description.includes(searchTerm)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });
}

// Handle resource submission form
const resourceForm = document.getElementById('resource-form');
if (resourceForm) {
    resourceForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch('/submit_resource', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload(); // Refresh to show new resource
            } else {
                alert(data.error || 'Failed to submit resource');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to submit resource');
        });
    });
}

// Handle resource voting
function voteResource(resourceId, voteType) {
    fetch('/vote_resource', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `resource_id=${resourceId}&vote_type=${voteType}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update vote counts
            const upvoteCount = document.querySelector(`#upvote-count-${resourceId}`);
            const downvoteCount = document.querySelector(`#downvote-count-${resourceId}`);
            
            if (upvoteCount) upvoteCount.textContent = data.upvotes;
            if (downvoteCount) downvoteCount.textContent = data.downvotes;
            
            // Update button states
            const upvoteBtn = document.querySelector(`#upvote-btn-${resourceId}`);
            const downvoteBtn = document.querySelector(`#downvote-btn-${resourceId}`);
            
            if (voteType === 'upvote') {
                upvoteBtn.classList.toggle('active');
                downvoteBtn.classList.remove('active');
            } else {
                downvoteBtn.classList.toggle('active');
                upvoteBtn.classList.remove('active');
            }
        } else {
            alert(data.error || 'Failed to vote');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to vote');
    });
}

// Handle resource deletion
function deleteResource(resourceId) {
    if (confirm('Are you sure you want to delete this resource?')) {
        fetch('/delete_resource', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `resource_id=${resourceId}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove the resource card from the DOM
                const resourceCard = document.querySelector(`#resource-${resourceId}`);
                if (resourceCard) {
                    resourceCard.remove();
                }
            } else {
                alert(data.error || 'Failed to delete resource');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to delete resource');
        });
    }
}

// Modal Functions
function showResourceModal() {
    document.getElementById('resourceModal').style.display = 'flex';
}

function hideResourceModal() {
    document.getElementById('resourceModal').style.display = 'none';
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const resourceModal = document.getElementById('resourceModal');
    if (e.target === resourceModal) {
        hideResourceModal();
    }
});

// Flash Messages
document.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });
}); 