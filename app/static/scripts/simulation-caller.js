const form = document.querySelector('#simulation-number-form');
const status = document.querySelector('#simulation-number-status');
const controls = document.querySelector('#simulation-voice-controls');
const startButton = document.querySelector('#simulation-start-call');
const endButton = document.querySelector('#simulation-end-call');
const changeNumber = document.querySelector('#simulation-change-number');
const submitButton = form.querySelector('button[type="submit"]');
const assistantId = controls.dataset.assistantId;
let callerToken;
let vapi;

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  status.textContent = 'Setting caller number…';
  try {
    const response = await fetch('/dashboard/simulation/number', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone_number: document.querySelector('#simulation-phone').value,
        csrf_token: document.querySelector('#simulation-csrf').value,
      }),
    });
    if (!response.ok) throw new Error('Enter a valid 10-digit US number and try again.');
    ({ token: callerToken } = await response.json());
    form.querySelector('input').disabled = true;
    startButton.hidden = false;
    changeNumber.hidden = false;
    status.textContent = 'Number ready. Start the voice test and allow microphone access.';
  } catch (error) {
    status.textContent = error.message;
    submitButton.disabled = false;
  }
});

startButton.addEventListener('click', async () => {
  startButton.disabled = true;
  status.textContent = 'Connecting to the voice assistant…';
  try {
    if (!vapi) {
      const { default: Vapi } = await import('https://esm.sh/@vapi-ai/web@2.7.1');
      vapi = new Vapi(controls.dataset.publicKey);
      vapi.on('call-start', () => {
        startButton.hidden = true;
        endButton.hidden = false;
        status.textContent = 'Voice test in progress. You can speak now.';
      });
      vapi.on('call-end', () => {
        endButton.hidden = true;
        startButton.hidden = false;
        startButton.disabled = false;
        status.textContent = 'Voice test ended. Start another call or change the number.';
      });
      vapi.on('error', (error) => {
        endButton.hidden = true;
        startButton.hidden = false;
        startButton.disabled = false;
        status.textContent = error.message || 'The voice test could not start.';
      });
    }
    await vapi.start(assistantId, {
      variableValues: { simulationCallerToken: callerToken },
    });
  } catch (error) {
    startButton.disabled = false;
    status.textContent = error.message || 'The voice test could not start.';
  }
});

endButton.addEventListener('click', () => vapi.stop());
changeNumber.addEventListener('click', () => {
  if (vapi) vapi.stop();
  window.location.reload();
});
