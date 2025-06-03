function createTokens () {
  const count = document.getElementById('tokenCount').value
  fetch('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'count=' + count
  })
    .then(res => res.json())
    .then(data => {
      alert(data.message || 'Tokens Created')
      loadTokens()
    })
}

function loadTokens () {
  fetch('/get_tokens')
    .then(res => res.json())
    .then(tokens => {
      const container = document.getElementById('tokenContainer')
      container.innerHTML = ''
      tokens.forEach(t => {
        const div = document.createElement('div')
        div.className = 'token-tile'
        div.innerHTML = `<b>Token #${t.token_number}</b><br>
                <button class="yellow" onclick="updateStatus(${t.id}, 'sm verified')">SM Verified</button>
                <button class="green" onclick="updateStatus(${t.id}, 'counselling complete')">Counselling Complete</button>
                <button class="red" onclick="updateStatus(${t.id}, 'pending')">Pending</button>
                <p>Status: ${t.status}</p>`
        container.appendChild(div)
      })
    })
}

function updateStatus (id, status) {
  fetch('/update_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `id=${id}&status=${status}`
  }).then(() => loadTokens())
}

function exportExcel () {
  window.location.href = '/export'
}

// Load existing tokens on page load
window.onload = loadTokens
