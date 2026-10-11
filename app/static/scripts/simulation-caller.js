const form = document.querySelector('#simulation-number-form');
const status = document.querySelector('#simulation-number-status');
const widgetContainer = document.querySelector('#simulation-widget');
const changeNumber = document.querySelector('#simulation-change-number');
const submitButton = form.querySelector('button[type="submit"]');

changeNumber.addEventListener('click', () => window.location.reload());

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  status.textContent = 'Preparing voice test…';
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
    const { token } = await response.json();
    const widget = document.querySelector('#simulation-widget-template').content.firstElementChild.cloneNode(true);
    widget.setAttribute('assistant-overrides', JSON.stringify({
      variableValues: { simulationCallerToken: token },
    }));
    widgetContainer.replaceChildren(widget);
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/@vapi-ai/client-sdk-react@0.1.1/dist/embed/widget.umd.js';
    script.onload = () => {
      status.textContent = 'Voice test ready. Click “Start voice test” and allow microphone access.';
      form.querySelector('input').disabled = true;
      changeNumber.hidden = false;
    };
    script.onerror = () => {
      status.textContent = 'The voice widget could not load. Check your connection and refresh the page.';
      submitButton.disabled = false;
    };
    document.body.append(script);
  } catch (error) {
    status.textContent = error.message;
    submitButton.disabled = false;
  }
});
