/* StudyVault - Interactive Client Logic */

let deleteTargetId = null;
let searchTimeout = null;

// Initialize on page DOM load
document.addEventListener('DOMContentLoaded', () => {
  const pageType = document.getElementById('pageType')?.value;
  if (pageType === 'favorites' || pageType === 'archived' || document.getElementById('resourceGrid')) {
    loadResources();
  }
  highlightOverdueDeadlines();
});

// Helper for API responses (handles 401 Unauthorized)
function handleApiResponse(res) {
  if (res.status === 401) {
    showToast("Session expired or not logged in. Redirecting to login...", "warning");
    setTimeout(() => {
      window.location.href = '/login';
    }, 1000);
    throw new Error("Unauthorized");
  }
  return res.json();
}

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  let icon = 'fa-info-circle';
  if (type === 'success') icon = 'fa-check-circle';
  if (type === 'warning') icon = 'fa-exclamation-triangle';
  if (type === 'error') icon = 'fa-circle-xmark';

  toast.innerHTML = `
    <i class="fa-solid ${icon}"></i>
    <div class="toast-msg">${message}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Modal Handlers
function openAddResourceModal() {
  document.getElementById('modalTitle').innerText = 'Add New Study Resource';
  document.getElementById('resourceForm').reset();
  document.getElementById('resourceId').value = '';
  document.getElementById('urlDuplicateWarning').style.display = 'none';
  document.getElementById('btnSaveResource').innerText = 'Save Resource';
  document.getElementById('resourceModal').classList.add('active');
}

function closeResourceModal() {
  document.getElementById('resourceModal').classList.remove('active');
}

function openEditResourceModal(id) {
  fetch(`/api/resources/${id}`)
    .then(handleApiResponse)
    .then(data => {
      if (!data.success || !data.resource) {
        showToast(data.message || 'Resource not found', 'error');
        return;
      }
      const r = data.resource;
      document.getElementById('modalTitle').innerText = 'Edit Study Resource';
      document.getElementById('resourceId').value = r.id;
      document.getElementById('resUrl').value = r.url;
      document.getElementById('resTitle').value = r.title;
      document.getElementById('resSubject').value = r.subject;
      document.getElementById('resCategory').value = r.category || 'Other';
      document.getElementById('resTask').value = r.task || '';
      document.getElementById('resDeadline').value = r.deadline || '';
      document.getElementById('resPriority').value = r.priority || 'Medium';
      document.getElementById('resStatus').value = r.status || 'Not Started';
      document.getElementById('resTags').value = r.tags || '';
      document.getElementById('resDescription').value = r.description || '';
      document.getElementById('urlDuplicateWarning').style.display = 'none';
      document.getElementById('btnSaveResource').innerText = 'Update Resource';

      document.getElementById('resourceModal').classList.add('active');
    })
    .catch(err => {
      if (err.message !== "Unauthorized") {
        showToast('Error loading resource details: ' + err, 'error');
      }
    });
}

// Automatic URL Title Fetching
function fetchWebpageTitle() {
  const urlInput = document.getElementById('resUrl');
  const titleInput = document.getElementById('resTitle');
  const btnAuto = document.getElementById('btnAutoTitle');

  const url = urlInput.value.trim();
  if (!url) {
    showToast('Please enter a URL first!', 'warning');
    return;
  }

  const originalText = btnAuto.innerHTML;
  btnAuto.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Fetching...`;
  btnAuto.disabled = true;

  fetch('/api/fetch-title', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: url })
  })
    .then(handleApiResponse)
    .then(data => {
      btnAuto.innerHTML = originalText;
      btnAuto.disabled = false;

      if (data.success && data.title) {
        titleInput.value = data.title;
        showToast('Webpage title fetched automatically!', 'success');
      } else {
        showToast(data.message || 'Could not fetch title automatically. Please enter title manually.', 'warning');
      }
      if (data.url) urlInput.value = data.url;
    })
    .catch(err => {
      btnAuto.innerHTML = originalText;
      btnAuto.disabled = false;
      if (err.message !== "Unauthorized") {
        showToast('Website unreachable. Enter title manually.', 'warning');
      }
    });
}

function handleUrlBlur() {
  const urlInput = document.getElementById('resUrl');
  const url = urlInput.value.trim();
  const resId = document.getElementById('resourceId').value;
  const warning = document.getElementById('urlDuplicateWarning');

  if (!url) {
    warning.style.display = 'none';
    return;
  }

  let checkUrl = `/api/check-url?url=${encodeURIComponent(url)}`;
  if (resId) checkUrl += `&exclude_id=${resId}`;

  fetch(checkUrl)
    .then(handleApiResponse)
    .then(data => {
      if (data.exists) {
        warning.innerText = 'This resource URL has already been saved in your vault.';
        warning.style.display = 'block';
      } else {
        warning.style.display = 'none';
      }
    })
    .catch(() => {});
}

// Form Submission (Add or Edit)
function handleFormSubmit(event) {
  event.preventDefault();

  const id = document.getElementById('resourceId').value;
  const payload = {
    title: document.getElementById('resTitle').value.trim(),
    url: document.getElementById('resUrl').value.trim(),
    subject: document.getElementById('resSubject').value.trim(),
    category: document.getElementById('resCategory').value,
    task: document.getElementById('resTask').value.trim(),
    deadline: document.getElementById('resDeadline').value,
    priority: document.getElementById('resPriority').value,
    status: document.getElementById('resStatus').value,
    tags: document.getElementById('resTags').value.trim(),
    description: document.getElementById('resDescription').value.trim()
  };

  const method = id ? 'PUT' : 'POST';
  const endpoint = id ? `/api/resources/${id}` : '/api/resources';

  fetch(endpoint, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(res => {
      if (res.status === 401) {
        window.location.href = '/login';
        throw new Error("Unauthorized");
      }
      return res.json().then(data => ({ status: res.status, body: data }));
    })
    .then(({ status, body }) => {
      if (body.success) {
        showToast(body.message, 'success');
        closeResourceModal();
        if (document.getElementById('resourceGrid')) {
          loadResources();
        } else {
          window.location.reload();
        }
      } else if (body.duplicate) {
        showToast(body.message, 'warning');
        document.getElementById('urlDuplicateWarning').innerText = body.message;
        document.getElementById('urlDuplicateWarning').style.display = 'block';
      } else {
        showToast(body.message || 'Error saving resource.', 'error');
      }
    })
    .catch(err => {
      if (err.message !== "Unauthorized") {
        showToast('Network error while saving: ' + err, 'error');
      }
    });
}

// Load Resources with search & combinable filters
function loadResources() {
  const grid = document.getElementById('resourceGrid');
  if (!grid) return;

  const pageType = document.getElementById('pageType')?.value;
  const search = document.getElementById('searchInput')?.value || '';
  const subject = document.getElementById('filterSubject')?.value || '';
  const category = document.getElementById('filterCategory')?.value || '';
  const status = document.getElementById('filterStatus')?.value || '';
  const priority = document.getElementById('filterPriority')?.value || '';

  let query = `/api/resources?`;
  if (pageType === 'archived') {
    query += `archived=1&`;
  } else if (pageType === 'favorites') {
    query += `archived=0&favorite=1&`;
  } else {
    query += `archived=0&`;
  }

  if (search) query += `q=${encodeURIComponent(search)}&`;
  if (subject) query += `subject=${encodeURIComponent(subject)}&`;
  if (category) query += `category=${encodeURIComponent(category)}&`;
  if (status) query += `status=${encodeURIComponent(status)}&`;
  if (priority) query += `priority=${encodeURIComponent(priority)}&`;

  fetch(query)
    .then(handleApiResponse)
    .then(data => {
      if (!data.success) {
        grid.innerHTML = `<div class="empty-state"><h4>Error loading resources</h4><p>${data.error}</p></div>`;
        return;
      }

      updateSubjectDropdown(data.resources);

      if (!data.resources || data.resources.length === 0) {
        grid.innerHTML = `
          <div class="empty-state">
            <i class="fa-solid fa-folder-open empty-icon"></i>
            <h4>No study resources found</h4>
            <p>Try adjusting your filters or search keywords, or add a new study resource!</p>
          </div>
        `;
        return;
      }

      grid.innerHTML = data.resources.map(r => renderResourceCard(r, pageType)).join('');
      highlightOverdueDeadlines();
    })
    .catch(err => {
      if (err.message !== "Unauthorized") {
        grid.innerHTML = `<div class="empty-state"><h4>Error connecting to server</h4><p>${err}</p></div>`;
      }
    });
}

// Render individual resource card
function renderResourceCard(r, pageType) {
  const isFavorite = r.favorite === 1;
  const isArchived = r.archived === 1;
  
  const statusClass = r.status.toLowerCase().replace(/\s+/g, '-');
  const priorityClass = r.priority.toLowerCase();

  const tagPills = r.tags ? r.tags.split(',').map(t => `<span class="tag-pill">#${t.trim()}</span>`).join(' ') : '';

  let deadlineDisplay = '';
  if (r.deadline) {
    deadlineDisplay = `<div class="card-deadline"><i class="fa-solid fa-calendar-day"></i> Due: <span class="due-date" data-date="${r.deadline}">${r.deadline}</span></div>`;
  }

  let taskBlock = '';
  if (r.task) {
    taskBlock = `
      <div class="card-task-box">
        <div class="card-task-title"><i class="fa-solid fa-list-check"></i> Associated Action</div>
        <div class="card-task-text">${r.task}</div>
      </div>
    `;
  }

  let favoriteBtn = `
    <button class="btn-fav ${isFavorite ? 'active' : ''}" onclick="toggleFavorite(${r.id})" title="${isFavorite ? 'Remove from favorites' : 'Mark as favorite'}">
      <i class="fa-${isFavorite ? 'solid' : 'regular'} fa-star"></i>
    </button>
  `;

  let actionButtons = '';
  if (isArchived) {
    actionButtons = `
      <button class="btn-icon" onclick="toggleArchive(${r.id})" title="Restore Resource"><i class="fa-solid fa-rotate-left"></i></button>
      <button class="btn-icon danger" onclick="openDeleteModal(${r.id})" title="Delete Permanently"><i class="fa-solid fa-trash-can"></i></button>
    `;
  } else {
    actionButtons = `
      <button class="btn-icon" onclick="openEditResourceModal(${r.id})" title="Edit"><i class="fa-solid fa-pen-to-square"></i></button>
      <button class="btn-icon" onclick="toggleArchive(${r.id})" title="Archive Resource"><i class="fa-solid fa-box-archive"></i></button>
      <button class="btn-icon danger" onclick="openDeleteModal(${r.id})" title="Delete"><i class="fa-solid fa-trash-can"></i></button>
    `;
  }

  return `
    <div class="resource-card" id="card-${r.id}">
      <div class="card-header">
        <div class="card-badges">
          <span class="badge badge-subject">${r.subject}</span>
          <span class="badge badge-category">${r.category || 'Other'}</span>
          <span class="badge badge-priority-${priorityClass}">${r.priority}</span>
        </div>
        ${!isArchived ? favoriteBtn : ''}
      </div>

      <div>
        <h3 class="card-title">${r.title}</h3>
        ${r.description ? `<p class="card-desc" style="margin-top: 6px;">${r.description}</p>` : ''}
      </div>

      ${taskBlock}

      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
        ${deadlineDisplay}
        <select class="status-dropdown badge-status-${statusClass}" onchange="updateResourceStatus(${r.id}, this.value)">
          <option value="Not Started" ${r.status === 'Not Started' ? 'selected' : ''}>Not Started</option>
          <option value="In Progress" ${r.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
          <option value="Completed" ${r.status === 'Completed' ? 'selected' : ''}>Completed</option>
        </select>
      </div>

      ${tagPills ? `<div class="tags-list">${tagPills}</div>` : ''}

      <div class="card-actions">
        <a href="${r.url}" target="_blank" rel="noopener noreferrer" class="btn-open-link">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> Open Resource
        </a>
        <div class="btn-action-group">
          ${actionButtons}
        </div>
      </div>
    </div>
  `;
}

// Dynamically populate Subject filter dropdown from active dataset
function updateSubjectDropdown(resources) {
  const select = document.getElementById('filterSubject');
  if (!select) return;

  const currentVal = select.value;
  const subjects = new Set();

  resources.forEach(r => {
    if (r.subject) subjects.add(r.subject);
  });

  let html = `<option value="">All Subjects</option>`;
  Array.from(subjects).sort().forEach(s => {
    html += `<option value="${s}" ${currentVal === s ? 'selected' : ''}>${s}</option>`;
  });

  select.innerHTML = html;
}

// Quick Actions
function toggleFavorite(id) {
  fetch(`/api/resources/${id}/toggle-favorite`, { method: 'POST' })
    .then(handleApiResponse)
    .then(data => {
      if (data.success) {
        showToast(data.message, 'success');
        loadResources();
      } else {
        showToast(data.message, 'error');
      }
    })
    .catch(() => {});
}

function toggleArchive(id) {
  fetch(`/api/resources/${id}/toggle-archive`, { method: 'POST' })
    .then(handleApiResponse)
    .then(data => {
      if (data.success) {
        showToast(data.message, 'success');
        loadResources();
      } else {
        showToast(data.message, 'error');
      }
    })
    .catch(() => {});
}

function updateResourceStatus(id, newStatus) {
  fetch(`/api/resources/${id}/update-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus })
  })
    .then(handleApiResponse)
    .then(data => {
      if (data.success) {
        showToast(data.message, 'success');
        loadResources();
      } else {
        showToast(data.message, 'error');
      }
    })
    .catch(() => {});
}

// Delete Modal Handlers
function openDeleteModal(id) {
  deleteTargetId = id;
  document.getElementById('deleteModal').classList.add('active');
}

function closeDeleteModal() {
  deleteTargetId = null;
  document.getElementById('deleteModal').classList.remove('active');
}

function confirmDeleteResource() {
  if (!deleteTargetId) return;

  fetch(`/api/resources/${deleteTargetId}`, { method: 'DELETE' })
    .then(handleApiResponse)
    .then(data => {
      closeDeleteModal();
      if (data.success) {
        showToast(data.message, 'success');
        loadResources();
      } else {
        showToast(data.message, 'error');
      }
    })
    .catch(err => {
      closeDeleteModal();
      if (err.message !== "Unauthorized") {
        showToast('Error deleting resource: ' + err, 'error');
      }
    });
}

// Debounced Search Input
function debounceSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    loadResources();
  }, 250);
}

function resetFilters() {
  if (document.getElementById('searchInput')) document.getElementById('searchInput').value = '';
  if (document.getElementById('filterSubject')) document.getElementById('filterSubject').value = '';
  if (document.getElementById('filterCategory')) document.getElementById('filterCategory').value = '';
  if (document.getElementById('filterStatus')) document.getElementById('filterStatus').value = '';
  if (document.getElementById('filterPriority')) document.getElementById('filterPriority').value = '';
  loadResources();
}

// Overdue Deadline Highlight
function highlightOverdueDeadlines() {
  const todayStr = new Date().toISOString().split('T')[0];
  const dueElements = document.querySelectorAll('.due-date');

  dueElements.forEach(el => {
    const deadline = el.getAttribute('data-date');
    if (deadline && deadline < todayStr) {
      el.classList.add('overdue-text');
      el.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Overdue (${deadline})`;
      const card = el.closest('.deadline-card');
      if (card) card.classList.add('overdue');
    }
  });
}

// Reseed Demo Data
function reseedDemoData() {
  if (!confirm("Are you sure you want to reset all accounts and re-seed sample study resources?")) return;

  fetch('/api/seed', { method: 'POST' })
    .then(handleApiResponse)
    .then(data => {
      if (data.success) {
        showToast(data.message, 'success');
        setTimeout(() => window.location.href = '/login', 1000);
      } else {
        showToast(data.message, 'error');
      }
    })
    .catch(() => {});
}
