"use strict";

(() => {
  const messages = document.querySelector("#sim-messages");
  const status = document.querySelector("#sim-status");
  const startButton = document.querySelector("#sim-start");
  const resumeButton = document.querySelector("#sim-resume");
  const micButton = document.querySelector("#sim-mic");
  const form = document.querySelector("#sim-form");
  const input = document.querySelector("#sim-input");
  const sendButton = form.querySelector("button[type='submit']");
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition;
  let callId;

  function addMessage(role, text) {
    const item = document.createElement("p");
    item.className = `simulation-message ${role}`;
    item.textContent = text;
    messages.append(item);
    messages.scrollTop = messages.scrollHeight;
  }

  function speak(text) {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
    }
  }

  function assistant(text) {
    addMessage("assistant", text);
    speak(text);
  }

  async function request(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { "X-CSRF-Token": window.simulationCsrf, ...(options.headers || {}) },
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || result.error?.message || "Request failed");
    return result;
  }

  startButton.addEventListener("click", async () => {
    startButton.disabled = true;
    startButton.hidden = false;
    startButton.textContent = "Start simulation";
    resumeButton.hidden = true;
    messages.replaceChildren();
    form.hidden = true;
    input.disabled = false;
    sendButton.disabled = false;
    callId = null;
    status.textContent = "Starting simulation…";
    try {
      const result = await request("/dashboard/simulation/calls", { method: "POST" });
      callId = result.call_id;
      form.hidden = false;
      micButton.disabled = !SpeechRecognition;
      status.textContent = SpeechRecognition ? "Ready. Choose Speak or type a response." : "Speech recognition is unavailable. Type your responses.";
      assistant(result.assistant);
      input.focus();
    } catch (error) {
      status.textContent = error.message;
      startButton.disabled = false;
    }
  });

  resumeButton.addEventListener("click", () => {
    if (!callId) return;
    form.hidden = false;
    micButton.disabled = !SpeechRecognition;
    resumeButton.hidden = true;
    status.textContent = SpeechRecognition ? "Simulation resumed. Speak or type a response." : "Simulation resumed. Type your response.";
    input.focus();
  });

  request("/dashboard/simulation/current")
    .then((current) => {
      if (!current.call_id) return;
      callId = current.call_id;
      current.messages.forEach((message) => addMessage(message.role, message.message));
      startButton.hidden = true;
      resumeButton.hidden = false;
      status.textContent = "You have an unfinished simulation.";
    })
    .catch((error) => { status.textContent = error.message; });

  async function submitTurn(text) {
    if (!text.trim() || !callId || sendButton.disabled) return;
    input.value = "";
    sendButton.disabled = true;
    micButton.disabled = true;
    status.textContent = "Agent is responding…";
    try {
      const result = await request(`/dashboard/simulation/calls/${callId}/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      addMessage("user", text);
      assistant(result.assistant);
      status.textContent = result.patient_id ? "Registration saved." : "Your turn.";
      if (result.patient_id) {
        micButton.disabled = true;
        input.disabled = true;
        form.hidden = true;
        startButton.hidden = false;
        startButton.disabled = false;
        startButton.textContent = "Start a new simulation";
      } else {
        sendButton.disabled = false;
        micButton.disabled = !SpeechRecognition;
      }
    } catch (error) {
      status.textContent = error.message;
      input.value = text;
      sendButton.disabled = false;
      micButton.disabled = !SpeechRecognition;
      input.focus();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitTurn(input.value);
  });

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.onstart = () => { status.textContent = "Listening…"; micButton.textContent = "Listening…"; };
    recognition.onresult = (event) => submitTurn(event.results[0][0].transcript);
    recognition.onerror = (event) => { status.textContent = `Microphone: ${event.error}. You can type instead.`; };
    recognition.onend = () => { micButton.textContent = "Speak"; };
    micButton.addEventListener("click", () => {
      try { recognition.start(); } catch { status.textContent = "Microphone is already listening."; }
    });
  }
})();
