document.addEventListener('DOMContentLoaded', () => {
    const POLL_INTERVAL_MS = 1500;
    const MAX_POLL_FAILURES = 15;
    const WIFI_API_ENDPOINT = '/api/wifi'

    const form = document.querySelector('form');
    const submitButton = document.querySelector('.submit-button');

    const statusMessage = document.createElement('p');
    statusMessage.className = 'status-message';
    statusMessage.setAttribute('role', 'status');
    statusMessage.setAttribute('aria-live', 'polite');

    form.appendChild(statusMessage);

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const ssid = document.getElementById('ssid').value.trim();
        const password = document.getElementById('password').value;

        if (!ssid || !password) {
            showStatus('Please fill in all fields', 'error');
            return;
        }

        setLoading(true);
        showStatus('Connecting to Wi-Fi...', 'info');

        try {
            const response = await fetch(`${WIFI_API_ENDPOINT}/connect`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ssid, password})
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            await pollStatus()
        } catch (error) {
            console.error('Connection request failed:', error);
            showStatus('Unable to reach the device. Please try again', 'error');
        } finally {
            setLoading(false);
        }
    });

    /**
     * Polls the device API until the Wi-Fi connection success,
     * fails or the hit the maximum number of request failures
     *
     * @returns {Promise<void>}
     */
    async function pollStatus() {
        let failures = 0;

        while (true) {
            try {
                const response = await fetch(`${WIFI_API_ENDPOINT}/status`);
                const { status } = await response.json();
                failures = 0;

                if (status === 'connected') {
                    showStatus('Connected. The device will restart and join your network', 'success');
                    return
                }

                if (status === 'failed') {
                    showStatus('Could not connect. Check the name and password', 'error');
                    return
                }
            } catch (e) {
                failures++;

                if (failures > MAX_POLL_FAILURES) {
                    showStatus('Lost contact with the device. If the plant sensor network is gone, setup succeeded', 'info')
                    return
                }
            }

            await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
        }
    }

    /**
     * Updates the submit button loading state
     *
     * @param loading The loading state
     */
    function setLoading(loading) {
        submitButton.disabled = loading;
        submitButton.textContent = loading ? 'Connecting...' : 'Connect to Wi-Fi';
    }

    /**
     * Displays a status message with the appropriate CSS class
     *
     * @param message The message to display
     * @param type The message severity (e.g. info, error, success)
     */
    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;
    }
});