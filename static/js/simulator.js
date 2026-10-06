/**
 * Interactive Attack & Defense Demonstration Controller
 */

function runAttackSimulation(scenario) {
    const outputCard = document.getElementById('simulationOutputCard');
    const loadingPill = document.getElementById('simLoadingPill');
    const resultsContainer = document.getElementById('simResultsContainer');

    if (!outputCard) return;

    outputCard.style.display = 'block';
    loadingPill.style.display = 'inline-flex';
    resultsContainer.style.opacity = '0.4';

    fetch('/api/security/simulate-attack', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenario })
    })
    .then(r => r.json())
    .then(res => {
        loadingPill.style.display = 'none';
        resultsContainer.style.opacity = '1';
        displaySimulationResults(res);
    })
    .catch(err => {
        loadingPill.style.display = 'none';
        resultsContainer.style.opacity = '1';
        alert('Simulation failed: ' + err);
    });
}

function displaySimulationResults(res) {
    const risk = res.risk || {};
    const score = risk.score !== undefined ? risk.score : 0;
    const level = risk.level || 'UNKNOWN';

    document.getElementById('simScenarioName').textContent = res.scenario || 'Cybersecurity Evaluation';
    document.getElementById('simScoreValue').textContent = score + '/100';
    
    // Status badges
    const levelBadge = document.getElementById('simLevelBadge');
    levelBadge.textContent = level;
    levelBadge.className = 'badge ' + (score > 80 ? 'badge-critical' : (score > 60 ? 'badge-high' : (score > 30 ? 'badge-medium' : 'badge-low')));

    const actionBadge = document.getElementById('simActionBadge');
    actionBadge.textContent = res.status;
    actionBadge.className = 'badge ' + (res.status === 'ALLOWED' ? 'badge-allowed' : 'badge-critical');

    const responseBadge = document.getElementById('simResponseBadge');
    responseBadge.textContent = res.response_mode;
    responseBadge.className = 'badge ' + (res.response_mode.includes('DECOY') ? 'badge-decoy' : 'badge-low');

    document.getElementById('simMessage').textContent = res.message || '';

    // Factors Table
    const factorsList = document.getElementById('simFactorsList');
    factorsList.innerHTML = '';
    (risk.factors || []).forEach(f => {
        const tr = document.createElement('tr');
        const statusClass = f.status === 'PASS' || f.status === 'NORMAL' ? 'badge-low' : 'badge-critical';
        tr.innerHTML = `
            <td><strong>${f.name}</strong></td>
            <td><span class="badge ${statusClass}">+${f.score}</span></td>
            <td><span class="badge ${statusClass}">${f.status}</span></td>
            <td style="color: var(--text-muted); font-size: 0.8rem;">${f.description}</td>
        `;
        factorsList.appendChild(tr);
    });

    // Served Patient Data Preview
    const servedCard = document.getElementById('simServedCard');
    if (res.patient_served) {
        servedCard.style.display = 'block';
        document.getElementById('simPatientId').textContent = res.patient_served.id;
        document.getElementById('simPatientName').textContent = res.patient_served.name;
        document.getElementById('simPatientType').innerHTML = res.patient_served.is_decoy 
            ? '<span class="badge badge-decoy">🎭 DECOY HONEYPOT PATIENT</span>' 
            : '<span class="badge badge-low">🛡️ AUTHORIZED PATIENT</span>';
        
        const linkBtn = document.getElementById('simViewChartBtn');
        linkBtn.href = `/patient/${res.patient_served.id}`;
    } else {
        servedCard.style.display = 'none';
    }

    // Raw JSON Telemetry
    document.getElementById('simRawJson').textContent = JSON.stringify(res, null, 2);
}
