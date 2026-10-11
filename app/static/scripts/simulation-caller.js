const form = document.querySelector('#simulation-number-form');
const status = document.querySelector('#simulation-number-status');
const widgetContainer = document.querySelector('#simulation-widget');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
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
    const { token } = await response.json();
    const widget = document.querySelector('#simulation-widget-template').content.firstElementChild.cloneNode(true);
    widget.setAttribute('assistant-overrides', JSON.stringify({
      variableValues: { simulationCallerToken: token },
    }));
    widgetContainer.replaceChildren(widget);
    status.textContent = 'Caller number set. Start a new voice test to use it.';
  } catch (error) {
    status.textContent = error.message;
  }
});
