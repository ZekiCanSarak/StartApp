// Show/Hide Project Creation Form
function showCreateProjectForm() {
    document.getElementById('createProjectForm').style.display = 'flex';
    // Clear form fields
    document.getElementById('project-title').value = '';
    document.getElementById('project-description').value = '';
    document.getElementById('github-repo').value = '';
    document.getElementById('required-skills').value = '';
    document.getElementById('weekly-commitment').value = '';
    // Uncheck all role checkboxes
    document.querySelectorAll('#needed-roles input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
    });
}

function hideCreateProjectForm() {
    document.getElementById('createProjectForm').style.display = 'none';
}

// Show/Hide Manage Project Modal
function showManageProjectModal(projectId) {
    const modal = document.getElementById('manageProjectModal');
    modal.style.display = 'flex';
    
    // Fetch project details
    fetch(`/get_project/${projectId}`)
        .then(response => response.json())
        .then(project => {
            document.getElementById('edit-project-id').value = project.id;
            document.getElementById('edit-project-title').value = project.title;
            document.getElementById('edit-project-description').value = project.description;
            document.getElementById('edit-github-repo').value = project.github_repo || '';
            document.getElementById('edit-weekly-commitment').value = project.weekly_commitment;
            
            // Load team members
            loadTeamMembers(projectId);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to load project details');
        });
}

function hideManageProjectModal() {
    document.getElementById('manageProjectModal').style.display = 'none';
}

function loadTeamMembers(projectId) {
    fetch(`/get_project_members/${projectId}`)
        .then(response => response.json())
        .then(members => {
            const membersList = document.getElementById('teamMembersList');
            membersList.innerHTML = members.map(member => `
                <div class="team-member-item">
                    <div class="team-member-info">
                        <img src="${member.avatar_url}" alt="${member.username}" class="team-member-avatar">
                        <div class="member-details">
                            <span class="team-member-name">${member.username}</span>
                            <span class="role-bubble ${member.member_role}">
                                ${formatRole(member.member_role)}
                            </span>
                            ${member.role_description ? `
                                <p class="member-role-description">${member.role_description}</p>
                            ` : ''}
                        </div>
                    </div>
                    <div class="team-member-actions">
                        ${member.can_remove ? `
                            <button onclick="removeMember(${projectId}, '${member.username}')" class="remove-member-btn">
                                <i class="fas fa-times"></i> Remove
                            </button>
                        ` : ''}
                    </div>
                </div>
            `).join('');
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to load team members');
        });
}

function formatRole(role) {
    if (!role) return 'Member';
    
    switch (role.toLowerCase()) {
        case 'admin': return 'Admin';
        case 'frontend': return 'Frontend Dev';
        case 'backend': return 'Backend Dev';
        case 'fullstack': return 'Full Stack';
        case 'ui-ux': return 'UI/UX Designer';
        case 'pm': return 'Project Manager';
        default: return role.charAt(0).toUpperCase() + role.slice(1);
    }
}

function removeMember(projectId, username) {
    if (!confirm(`Are you sure you want to remove ${username} from the project?`)) {
        return;
    }

    fetch('/remove_project_member', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            project_id: projectId,
            username: username
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadTeamMembers(projectId);
        } else {
            alert(data.error || 'Failed to remove team member');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to remove team member');
    });
}

function deleteProject() {
    const projectId = document.getElementById('edit-project-id').value;
    
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
        return;
    }

    fetch(`/delete_project/${projectId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/projects';
        } else {
            alert(data.error || 'Failed to delete project');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to delete project');
    });
}

// Close modals when clicking outside
document.addEventListener('click', (e) => {
    const createModal = document.getElementById('createProjectForm');
    const manageModal = document.getElementById('manageProjectModal');
    
    if (e.target === createModal) {
        hideCreateProjectForm();
    }
    if (e.target === manageModal) {
        hideManageProjectModal();
    }
});

// Edit Project Form Submission
document.getElementById('editProjectForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const projectId = formData.get('project_id');
    
    fetch(`/update_project/${projectId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert(data.error || 'Failed to update project');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to update project');
    });
});

// Role chips interaction
document.querySelectorAll('.role-chip').forEach(chip => {
    chip.addEventListener('click', (e) => {
        // Don't trigger if clicking the checkbox directly
        if (e.target.type !== 'checkbox') {
            const checkbox = chip.querySelector('input[type="checkbox"]');
            checkbox.checked = !checkbox.checked;
        }
    });
});

// Form Validation
document.querySelector('form').addEventListener('submit', (e) => {
    const title = document.getElementById('project-title').value.trim();
    const description = document.getElementById('project-description').value.trim();
    const githubRepo = document.getElementById('github-repo').value.trim();
    const roles = Array.from(document.querySelectorAll('input[name="roles[]"]:checked')).map(input => input.value);
    const weeklyCommitment = document.getElementById('weekly-commitment').value;
    
    if (!title) {
        e.preventDefault();
        alert('Please enter a project title');
        return;
    }

    if (!description) {
        e.preventDefault();
        alert('Please enter a project description');
        return;
    }

    if (githubRepo && !isValidGithubUrl(githubRepo)) {
        e.preventDefault();
        alert('Please enter a valid GitHub repository URL');
        return;
    }

    if (roles.length === 0) {
        e.preventDefault();
        alert('Please select at least one required role');
        return;
    }

    if (!weeklyCommitment) {
        e.preventDefault();
        alert('Please select an expected weekly commitment');
        return;
    }
});

// GitHub URL Validation
function isValidGithubUrl(url) {
    try {
        const githubUrl = new URL(url);
        return githubUrl.hostname === 'github.com' && githubUrl.pathname.split('/').length >= 3;
    } catch {
        return false;
    }
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