'use strict'
const byId = id => document.getElementById(id)
const project = byId('project')
const question = byId('question')
const historyPane = byId('history')
const statusLine = byId('status')
let sending = false

async function request(action, values = {}) {
  const response = await fetch('/' + action, {
    method: 'POST', body: JSON.stringify(values), cache: 'no-store',
    credentials: 'omit', redirect: 'error', referrerPolicy: 'no-referrer',
  })
  if (!response.ok) throw new Error()
  return response.json()
}

async function refresh() {
  if (sending) return
  try {
    const state = await request('state')
    if (!Array.isArray(state.collections)) {
      statusLine.textContent = state.error || 'Private memory is unavailable.'
      return
    }
    const selected = project.value
    project.replaceChildren(...state.collections.map(name => new Option(name || 'Personal', name)))
    if (state.collections.includes(selected)) project.value = selected
    else { historyPane.replaceChildren(); question.value = '' }
    question.disabled = byId('send').disabled = false
    statusLine.textContent = state.error || (state.active && state.active !== 'None'
      ? 'Last answer from ' + state.active : 'Private to this desktop user and collection.')
  } catch { statusLine.textContent = 'Open the native JARVIS Control Center to use private chat.' }
}

function bubble(role, text) {
  const block = document.createElement('div')
  block.className = 'bubble ' + (role === 'You' ? 'you' : 'jarvis')
  block.dir = 'auto'
  const label = document.createElement('div')
  label.className = 'bubble-title'
  label.textContent = role
  block.append(label, document.createTextNode(text))
  historyPane.append(block)
  historyPane.scrollTop = historyPane.scrollHeight
}

byId('compose').onsubmit = async event => {
  event.preventDefault()
  const text = question.value.trim()
  if (!text || sending || question.disabled) return
  sending = true
  project.disabled = question.disabled = byId('send').disabled = true
  statusLine.textContent = 'Waiting for JARVIS…'
  bubble('You', text)
  question.value = ''
  try {
    const result = await request('ask', {project: project.value, question: text})
    if (result.answer) bubble('JARVIS · ' + result.active, result.answer)
    statusLine.textContent = result.error || ('Answered by ' + result.active)
  } catch { statusLine.textContent = 'The private connection was interrupted.' }
  finally {
    sending = project.disabled = question.disabled = byId('send').disabled = false
    question.focus()
  }
}
project.onchange = () => { historyPane.replaceChildren(); question.value = ''; question.focus() }
for (const action of ['providers', 'memory']) {
  byId(action).onclick = async () => {
    try { await request(action, {project: project.value}) }
    catch { statusLine.textContent = 'The desktop settings could not open.' }
  }
}
window.addEventListener('focus', refresh)
refresh()
