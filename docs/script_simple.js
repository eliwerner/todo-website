// ========================================
// TODO APP - FRONTEND WITH USER AUTHENTICATION
// ========================================

let todos = [];
let currentFilter = 'all'; // can be 'all', 'active', or 'completed'
let sessionToken = localStorage.getItem('sessionToken') || null;

const todoForm = document.getElementById('todo-form');
const todoInput = document.getElementById('todo-input');
const todoList = document.getElementById('todo-list');
const tasksCount = document.getElementById('tasks-count');
const clearCompletedBtn = document.getElementById('clear-completed');
const filterBtns = document.querySelectorAll('.filter-btn');
const emptyState = document.getElementById('empty-state');

// =============================
// AUTH UI ELEMENTS
// =============================
// Add login/register form dynamically
const authContainer = document.createElement('div');
authContainer.id = 'auth-container';
authContainer.innerHTML = `
  <form id="login-form" class="auth-form">
    <h2>Login</h2>
    <input type="text" id="login-username" placeholder="Username" required />
    <input type="password" id="login-password" placeholder="Password" required />
    <button type="submit">Login</button>
    <p>or <a href="#" id="show-register">Register</a></p>
    <div id="login-status"></div>
  </form>
  <form id="register-form" class="auth-form" style="display:none;">
    <h2>Register</h2>
    <input type="text" id="register-username" placeholder="Username" required />
    <input type="password" id="register-password" placeholder="Password" required />
    <button type="submit">Register</button>
    <p>or <a href="#" id="show-login">Login</a></p>
    <div id="register-status"></div>
  </form>
`;
document.body.prepend(authContainer);

const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegister = document.getElementById('show-register');
const showLogin = document.getElementById('show-login');
const loginStatus = document.getElementById('login-status');
const registerStatus = document.getElementById('register-status');

showRegister.addEventListener('click', (e) => {
  e.preventDefault();
  loginForm.style.display = 'none';
  registerForm.style.display = 'block';
});
showLogin.addEventListener('click', (e) => {
  e.preventDefault();
  registerForm.style.display = 'none';
  loginForm.style.display = 'block';
});

// =============================
// AUTH FUNCTIONS
// =============================
async function registerUser(username, password) {
  const response = await fetch('https://todo-website-lohn.onrender.com/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  return response.json();
}

async function loginUser(username, password) {
  const response = await fetch('https://todo-website-lohn.onrender.com/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  return response.json();
}

function showAppUI() {
  authContainer.style.display = 'none';
  document.querySelector('.container').style.display = 'block';
}

function showAuthUI() {
  authContainer.style.display = '';
  document.querySelector('.container').style.display = 'none';
}

// =============================
// AUTH EVENT LISTENERS
// =============================
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  loginStatus.textContent = 'Logging in...';
  const result = await loginUser(username, password);
  if (result.token) {
    sessionToken = result.token;
    localStorage.setItem('sessionToken', sessionToken);
    loginStatus.textContent = '';
    showAppUI();
    await loadTodosAndRender();
  } else {
    loginStatus.textContent = result.error || 'Login failed.';
  }
});

registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('register-username').value.trim();
  const password = document.getElementById('register-password').value;
  registerStatus.textContent = 'Registering...';
  const result = await registerUser(username, password);
  if (result.message) {
    registerStatus.textContent = 'Registration successful! You can now log in.';
    setTimeout(() => {
      registerForm.style.display = 'none';
      loginForm.style.display = 'block';
      registerStatus.textContent = '';
    }, 1500);
  } else {
    registerStatus.textContent = result.error || 'Registration failed.';
  }
});

// =============================
// BACKEND FETCH FUNCTIONS (with token)
// =============================
function getAuthHeaders() {
  return sessionToken ? { 'Authorization': sessionToken } : {};
}

async function fetchTodosFromBackend() {
  const response = await fetch('https://todo-website-lohn.onrender.com/todos', {
    headers: getAuthHeaders()
  });
  if (response.status === 401) {
    showAuthUI();
    return [];
  }
  const data = await response.json();
  return data;
}

async function addTodoToBackend(text) {
  const response = await fetch('https://todo-website-lohn.onrender.com/todos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ text: text, completed: false })
  });
  return response.json();
}

async function deleteTodoFromBackend(id) {
  await fetch(`https://todo-website-lohn.onrender.com/todos/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
}

async function toggleTodoInBackend(id, completed) {
  await fetch(`https://todo-website-lohn.onrender.com/todos/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ completed: completed })
  });
}

async function clearCompletedInBackend() {
  await fetch('https://todo-website-lohn.onrender.com/todos/clear_completed', {
    method: 'POST',
    headers: getAuthHeaders()
  });
}

// =============================
// LOAD TODOS FROM BACKEND ON PAGE LOAD (after login)
// =============================
async function loadTodosAndRender() {
  todos = await fetchTodosFromBackend();
  render();
}

window.addEventListener('DOMContentLoaded', async () => {
  if (sessionToken) {
    showAppUI();
    await loadTodosAndRender();
  } else {
    showAuthUI();
  }

  // Add focus/blur animation for input (UI polish)
  todoInput.addEventListener('focus', () => {
    todoInput.parentElement.style.boxShadow = '0 5px 20px rgba(102, 126, 234, 0.3)';
  });
  todoInput.addEventListener('blur', () => {
    todoInput.parentElement.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
  });

  // Loading animation
  document.body.classList.add('loading');
  setTimeout(() => {
    document.body.classList.remove('loading');
  }, 500);
});

// =============================
// ADD TODO (uses backend)
// =============================
const addTodo = async (event) => {
  event.preventDefault();
  const text = todoInput.value.trim();
  if (!text) return;

  const newTodo = await addTodoToBackend(text);
  todos.unshift(newTodo);
  todoInput.value = '';
  render();

  const addBtn = document.getElementById('add-btn');
  addBtn.classList.add('success');
  setTimeout(() => addBtn.classList.remove('success'), 300);
};

todoForm.addEventListener('submit', addTodo);

todoInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    addTodo(e);
  }
});

// =============================
// TOGGLE, DELETE, CLEAR COMPLETED (NOW USE BACKEND)
// =============================
const toggleTodo = async (id) => {
  const todo = todos.find(t => t.id === id);
  if (!todo) return;
  const newCompleted = !todo.completed;
  await toggleTodoInBackend(id, newCompleted);
  todo.completed = newCompleted;
  render();
};

const deleteTodo = async (id) => {
  await deleteTodoFromBackend(id);
  todos = todos.filter(todo => todo.id !== id);
  render();
};

const clearCompleted = async () => {
  await clearCompletedInBackend();
  todos = todos.filter(todo => !todo.completed);
  render();
};

clearCompletedBtn.addEventListener('click', clearCompleted);

// =============================
// FILTERING
// =============================
filterBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    render();
  });
});

const getFilteredTodos = () => {
  if (currentFilter === 'active') {
    return todos.filter(todo => !todo.completed);
  } else if (currentFilter === 'completed') {
    return todos.filter(todo => todo.completed);
  }
  return todos;
};

// =============================
// RENDER FUNCTION
// =============================
const render = () => {
  const filtered = getFilteredTodos();
  todoList.innerHTML = '';
  if (filtered.length === 0) {
    emptyState.classList.add('show');
  } else {
    emptyState.classList.remove('show');
    filtered.forEach(todo => {
      const li = document.createElement('li');
      li.className = 'todo-item' + (todo.completed ? ' completed' : '');
      li.setAttribute('data-id', todo.id);

      const checkbox = document.createElement('div');
      checkbox.className = 'todo-checkbox' + (todo.completed ? ' checked' : '');
      checkbox.addEventListener('click', () => toggleTodo(todo.id));
      li.appendChild(checkbox);

      const span = document.createElement('span');
      span.className = 'todo-text';
      span.textContent = todo.text;
      li.appendChild(span);

      const delBtn = document.createElement('button');
      delBtn.className = 'todo-delete';
      delBtn.innerHTML = '<i class="fas fa-trash"></i>';
      delBtn.addEventListener('click', () => deleteTodo(todo.id));
      li.appendChild(delBtn);

      todoList.appendChild(li);
    });
  }
  updateStats();
};

// =============================
// UPDATE STATS
// =============================
const updateStats = () => {
  const total = todos.length;
  const completed = todos.filter(todo => todo.completed).length;
  const active = total - completed;
  let statsText = '';
  if (total === 0) {
    statsText = '0 tasks';
  } else if (currentFilter === 'all') {
    statsText = `${active} of ${total} tasks remaining`;
  } else if (currentFilter === 'active') {
    statsText = `${active} active tasks`;
  } else {
    statsText = `${completed} completed tasks`;
  }
  tasksCount.textContent = statsText;
  clearCompletedBtn.style.display = completed > 0 ? 'inline' : 'none';
};

// =============================
// KEYBOARD SHORTCUTS
// =============================
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    addTodo(e);
  }
  if (e.key === 'Escape') {
    todoInput.value = '';
    todoInput.blur();
  }
});

// =============================
// ESCAPE HTML (for security, not used here but good to have)
// =============================
const escapeHtml = (text) => {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}; 