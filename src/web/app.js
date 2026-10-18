document.addEventListener('DOMContentLoaded', () => {
    const POLL_INTERVAL_MS = 1500;
    const MAX_POLL_FAILURES = 15;
    const API_ENDPOINT = '/api'

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
        const wifiPassword = document.getElementById('password').value;
        const plantName = document.getElementById('plant-name').value;
        const mqttServer = document.getElementById('mqtt-server').value;
        const mqttPort = document.getElementById('mqtt-port').value
        const mqttUsername = document.getElementById('mqtt-username').value
        const mqttPassword = document.getElementById('mqtt-password').value

        if (!ssid || !wifiPassword || !plantName || !mqttServer || !mqttPort) {
            showStatus('Please fill in all fields', 'error');
            return;
        }

        const payload = {
            wifi: {ssid, password: wifiPassword},
            mqtt: {server: mqttServer, port: mqttPort, username: mqttUsername, password: mqttPassword},
            sensor: {plant_name: plantName},
        }

        setLoading(true);
        showStatus('Submitting...', 'info');

        try {
            const response = await fetch(`${API_ENDPOINT}/setup`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
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
                const response = await fetch(`${API_ENDPOINT}/status`);
                const { status, reason } = await response.json();
                failures = 0;

                if (status === 'connected') {
                    showStatus('Connected. The device will restart and join your network', 'success');
                    return
                }

                if (status === 'failed') {
                    showStatus(failureMessage(reason), 'error');
                    return
                }
            } catch (e) {
                failures++;

                if (failures > MAX_POLL_FAILURES) {
                    showStatus('Lost contact with the device. This is expected after setup. ' +
                        'Reconnect to the Plant-Sensor network to check the result. ' +
                        'If the network is gone, setup succeeded', 'info')
                    return
                }
            }

            await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
        }
    }

    /**
     * Shows the result of the previous setup attempt when the page re-opens
     *
     * @returns {Promise<void>}
     */
    async function restoreStatus() {
        try {
            const response = await fetch(`${API_ENDPOINT}/status`);
            const { status, reason } = await response.json();

            if (status === 'failed') {
                showStatus(failureMessage(reason), 'error');
            } else if (status === 'connecting') {
                setLoading(true);
                showStatus('Connecting to Wi-Fi...', 'info');
                await pollStatus()
                setLoading(false);
            }
        } catch (e) {
            // Device is unreachable
        }
    }

    /**
     * Updates the submit button loading state
     *
     * @param loading The loading state
     */
    function setLoading(loading) {
        submitButton.disabled = loading;
        submitButton.textContent = loading ? 'Connecting...' : 'Save and Connect';
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

    /**
     * Builds the error message for a failed setup attempt
     *
     * @param reason The failing part reported by the device ('wifi' or 'mqtt')
     * @returns {string}
     */
    function failureMessage(reason) {
        return reason === 'mqtt'
            ? 'Wi-Fi connected, but the MQTT broker rejected the settings. Check server, port and credentials'
            : 'Could not connect to the Wi-Fi. Check the name and password';
    }

    restoreStatus();
});

