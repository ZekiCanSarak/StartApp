// Modal Functions
function showInviteModal() {
    document.getElementById('inviteModal').style.display = 'flex';
}

function hideInviteModal() {
    document.getElementById('inviteModal').style.display = 'none';
}

function showUpdateModal() {
    document.getElementById('updateModal').style.display = 'flex';
}

function hideUpdateModal() {
    document.getElementById('updateModal').style.display = 'none';
}

// Close modals when clicking outside
document.addEventListener('click', (e) => {
    const inviteModal = document.getElementById('inviteModal');
    const updateModal = document.getElementById('updateModal');
    
    if (e.target === inviteModal) {
        hideInviteModal();
    }
    if (e.target === updateModal) {
        hideUpdateModal();
    }
});

// Skill Endorsement
function endorseSkill(username, skill) {
    fetch('/endorse_skill', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `username=${encodeURIComponent(username)}&skill=${encodeURIComponent(skill)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the endorsement count in the UI
            const skillChips = document.querySelectorAll('.skill-chip');
            skillChips.forEach(chip => {
                if (chip.querySelector('span').textContent === skill) {
                    chip.querySelector('.endorsement-count').textContent = data.new_count;
                }
            });
        } else {
            alert(data.error || 'Failed to endorse skill');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to endorse skill');
    });
}

// Project Updates
document.getElementById('updateForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/post_update', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload(); // Refresh to show new update
        } else {
            alert(data.error || 'Failed to post update');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to post update');
    });
});

// GitHub Integration
if (document.querySelector('.github-section')) {
    const repoUrl = document.querySelector('.github-link').href;
    const [owner, repo] = repoUrl.split('github.com/')[1].split('/');
    
    // Fetch Issues
    fetch(`https://api.github.com/repos/${owner}/${repo}/issues?state=open`)
        .then(response => response.json())
        .then(issues => {
            const issuesList = document.getElementById('issuesList');
            issuesList.innerHTML = issues.length ? issues.map(issue => `
                <div class="github-item">
                    <a href="${issue.html_url}" target="_blank" class="github-link">
                        <span class="issue-title">${issue.title}</span>
                        <span class="issue-number">#${issue.number}</span>
                    </a>
                    <div class="issue-meta">
                        <span class="issue-author">
                            <img src="${issue.user.avatar_url}" alt="${issue.user.login}" class="avatar-small">
                            ${issue.user.login}
                        </span>
                        <span class="issue-date">${new Date(issue.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('') : '<p>No open issues</p>';
        })
        .catch(error => {
            console.error('Error fetching issues:', error);
            document.getElementById('issuesList').innerHTML = '<p>Failed to load issues</p>';
        });

    // Fetch Commits
    fetch(`https://api.github.com/repos/${owner}/${repo}/commits`)
        .then(response => response.json())
        .then(commits => {
            const commitsList = document.getElementById('commitsList');
            commitsList.innerHTML = commits.length ? commits.slice(0, 5).map(commit => `
                <div class="github-item">
                    <a href="${commit.html_url}" target="_blank" class="github-link">
                        <span class="commit-message">${commit.commit.message}</span>
                    </a>
                    <div class="commit-meta">
                        <span class="commit-author">
                            <img src="${commit.author?.avatar_url || 'https://github.com/identicons/jasonlong.png'}" 
                                 alt="${commit.commit.author.name}" class="avatar-small">
                            ${commit.commit.author.name}
                        </span>
                        <span class="commit-date">${new Date(commit.commit.author.date).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('') : '<p>No commits found</p>';
        })
        .catch(error => {
            console.error('Error fetching commits:', error);
            document.getElementById('commitsList').innerHTML = '<p>Failed to load commits</p>';
        });
}

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