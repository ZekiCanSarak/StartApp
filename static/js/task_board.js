// Check if user is admin
const isAdmin = document.body.dataset.isAdmin === 'true';

// Initialize Sortable for each task list
document.querySelectorAll('.task-cards').forEach(taskList => {
    new Sortable(taskList, {
        group: 'tasks',
        animation: 150,
        ghostClass: 'task-card-ghost',
        dragClass: 'task-card-drag',
        handle: '.task-card',
        draggable: '.task-card',
        onStart: function(evt) {
            evt.item.classList.add('being-dragged');
        },
        onEnd: function(evt) {
            evt.item.classList.remove('being-dragged');
            const taskId = evt.item.dataset.taskId;
            const newListId = evt.to.closest('.task-list').dataset.listId;
            const newPosition = Array.from(evt.to.children).indexOf(evt.item);
            
            // Update task position in database
            fetch('/update_task_position', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    task_id: taskId,
                    list_id: newListId,
                    position: newPosition
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    alert(data.error || 'Failed to update task position');
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                location.reload();
            });
        }
    });
});

// Only show create task button for admins
if (!isAdmin) {
    const createTaskBtn = document.querySelector('.create-task-btn');
    if (createTaskBtn) {
        createTaskBtn.style.display = 'none';
    }
}

// Modal Functions
function showCreateTaskModal() {
    // Get the first list's ID from the page
    const firstList = document.querySelector('.task-list');
    if (firstList) {
        const listId = firstList.dataset.listId;
        document.getElementById('list_id').value = listId;
    }
    document.getElementById('createTaskModal').style.display = 'flex';
}

function hideCreateTaskModal() {
    document.getElementById('createTaskModal').style.display = 'none';
    document.getElementById('createTaskForm').reset();
}

function showEditTaskModal(taskId) {
    // Fetch task details
    fetch(`/get_task/${taskId}`)
        .then(response => response.json())
        .then(task => {
            document.getElementById('edit_task_id').value = task.id;
            document.getElementById('edit-task-title').value = task.title;
            document.getElementById('edit-task-description').value = task.description;
            document.getElementById('edit-task-assignee').value = task.assigned_to || '';
            document.getElementById('edit-task-priority').value = task.priority || '';
            document.getElementById('edit-task-due-date').value = task.due_date || '';
            document.getElementById('editTaskModal').style.display = 'flex';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to load task details');
        });
}

function hideEditTaskModal() {
    document.getElementById('editTaskModal').style.display = 'none';
    document.getElementById('editTaskForm').reset();
}

// Close modals when clicking outside
document.addEventListener('click', (e) => {
    const createModal = document.getElementById('createTaskModal');
    const editModal = document.getElementById('editTaskModal');
    
    if (e.target === createModal) {
        hideCreateTaskModal();
    }
    if (e.target === editModal) {
        hideEditTaskModal();
    }
});

// Create Task Form Submission
document.getElementById('createTaskForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const listId = document.getElementById('list_id').value;
    
    if (!listId) {
        alert('Error: No list selected to add task to');
        return;
    }
    
    // Ensure list_id is included in form data
    formData.set('list_id', listId);
    
    fetch('/create_task', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload(); // Refresh to show new task
        } else {
            alert(data.error || 'Failed to create task');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to create task');
    });
});

// Edit Task Form Submission
document.getElementById('editTaskForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const taskId = formData.get('task_id');
    
    fetch(`/update_task/${taskId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload(); // Refresh to show updated task
        } else {
            alert(data.error || 'Failed to update task');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to update task');
    });
});

// Delete Task
function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }
    
    fetch(`/delete_task/${taskId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload(); // Refresh to remove deleted task
        } else {
            alert(data.error || 'Failed to delete task');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to delete task');
    });
}

// Task Filtering
function filterTasks() {
    const assigneeFilter = document.getElementById('assigneeFilter').value;
    const priorityFilter = document.getElementById('priorityFilter').value;
    
    document.querySelectorAll('.task-list').forEach(list => {
        let visibleCount = 0;
        const cards = list.querySelectorAll('.task-card');
        
        cards.forEach(card => {
            const assignee = card.dataset.assignee;
            const priority = card.dataset.priority;
            
            let show = true;
            
            if (assigneeFilter && assignee !== assigneeFilter) {
                show = false;
            }
            
            if (priorityFilter && priority !== priorityFilter) {
                show = false;
            }
            
            card.style.display = show ? 'block' : 'none';
            if (show) visibleCount++;
        });
        
        // Update the task count for this list
        const countElement = list.querySelector('.task-count');
        if (countElement) {
            countElement.textContent = visibleCount;
            // Add visual feedback for filtered state
            if (assigneeFilter || priorityFilter) {
                countElement.classList.add('filtered');
                countElement.setAttribute('title', `Showing ${visibleCount} of ${cards.length} tasks`);
            } else {
                countElement.classList.remove('filtered');
                countElement.removeAttribute('title');
            }
        }
    });
}

// Update Task Counts
function updateTaskCounts() {
    document.querySelectorAll('.task-list').forEach(list => {
        const visibleTasks = list.querySelectorAll('.task-card[style="display: block"], .task-card:not([style*="display"])').length;
        list.querySelector('.task-count').textContent = visibleTasks;
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