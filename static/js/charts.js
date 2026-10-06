/**
 * Hospital Security Analytics & Telemetry Visualizations
 * Powered by Chart.js for Hospital Security Operations Center
 */

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('chartThreatSeverity') && !document.getElementById('chartLogins') && !document.getElementById('chartThreats')) return;

    fetch('/api/security/chart-data')
        .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        })
        .then(data => {
            renderDashboardCharts(data);
        })
        .catch(err => {
            console.error('Failed to load telemetry streams:', err);
        });
});

function renderDashboardCharts(data) {
    const defaultFont = { family: 'Inter, -apple-system, sans-serif', size: 11, weight: '500' };
    const gridColor = '#f1f5f9';
    const textColor = '#475569';

    // 1. Threats by Severity (Doughnut)
    const elSeverity = document.getElementById('chartThreatSeverity') || document.getElementById('chartThreats');
    if (elSeverity && data.threats_by_severity) {
        new Chart(elSeverity, {
            type: 'doughnut',
            data: {
                labels: data.threats_by_severity.labels,
                datasets: [{
                    data: data.threats_by_severity.data,
                    backgroundColor: ['#ef4444', '#f97316', '#f59e0b', '#10b981'],
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: textColor, font: defaultFont, boxWidth: 12, padding: 14 } }
                }
            }
        });
    }

    // 2. Login Activity (Doughnut)
    const elLogins = document.getElementById('chartLoginAuth') || document.getElementById('chartLogins');
    if (elLogins && data.login_activity) {
        new Chart(elLogins, {
            type: 'doughnut',
            data: {
                labels: data.login_activity.labels,
                datasets: [{
                    data: data.login_activity.data,
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: textColor, font: defaultFont, boxWidth: 12, padding: 14 } }
                }
            }
        });
    }

    // 3. Failed Login Trend (Line)
    const elFailedTrend = document.getElementById('chartFailedTrend') || document.getElementById('chartTimeline');
    if (elFailedTrend && data.failed_trend) {
        new Chart(elFailedTrend, {
            type: 'line',
            data: {
                labels: data.failed_trend.labels,
                datasets: [{
                    label: 'Failed Access Attempts',
                    data: data.failed_trend.data,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.08)',
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: textColor, font: defaultFont }, grid: { display: false } },
                    y: { ticks: { color: textColor, font: defaultFont }, grid: { color: gridColor }, beginAtZero: true }
                },
                plugins: {
                    legend: { labels: { color: textColor, font: defaultFont, boxWidth: 12 } }
                }
            }
        });
    }

    // 4. Risk Score Distribution (Bar)
    const elRiskDist = document.getElementById('chartRiskDist');
    if (elRiskDist && data.risk_distribution) {
        new Chart(elRiskDist, {
            type: 'bar',
            data: {
                labels: data.risk_distribution.labels,
                datasets: [{
                    label: 'Evaluated Clinical Sessions',
                    data: data.risk_distribution.data,
                    backgroundColor: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
                    borderColor: '#ffffff',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: textColor, font: defaultFont }, grid: { display: false } },
                    y: { ticks: { color: textColor, font: defaultFont }, grid: { color: gridColor }, beginAtZero: true }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 5. Decoy Honeypot Activity (Bar)
    const elDecoys = document.getElementById('chartDecoyActivity') || document.getElementById('chartDecoys');
    if (elDecoys && data.decoy_activity) {
        new Chart(elDecoys, {
            type: 'bar',
            data: {
                labels: data.decoy_activity.labels,
                datasets: [{
                    label: 'Trapped Hits per Canary',
                    data: data.decoy_activity.data,
                    backgroundColor: 'rgba(124, 58, 237, 0.75)',
                    borderColor: '#7c3aed',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: textColor, font: defaultFont }, grid: { display: false } },
                    y: { ticks: { color: textColor, font: defaultFont }, grid: { color: gridColor }, beginAtZero: true }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 6. Access Attempts Overview (Doughnut)
    const elAccess = document.getElementById('chartAccessAttempts') || document.getElementById('chartAccess');
    if (elAccess && data.access_attempts) {
        new Chart(elAccess, {
            type: 'doughnut',
            data: {
                labels: data.access_attempts.labels,
                datasets: [{
                    data: data.access_attempts.data,
                    backgroundColor: ['#10b981', '#ef4444', '#7c3aed'],
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: textColor, font: defaultFont, boxWidth: 12, padding: 14 } }
                }
            }
        });
    }

    // 7. Threat Type Distribution (Bar)
    const elThreatTypes = document.getElementById('chartThreatTypes');
    if (elThreatTypes && data.threat_types) {
        new Chart(elThreatTypes, {
            type: 'bar',
            data: {
                labels: data.threat_types.labels,
                datasets: [{
                    label: 'Incidents Detected',
                    data: data.threat_types.data,
                    backgroundColor: 'rgba(2, 132, 199, 0.75)',
                    borderColor: '#0284c7',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: textColor, font: defaultFont }, grid: { display: false } },
                    y: { ticks: { color: textColor, font: defaultFont }, grid: { color: gridColor }, beginAtZero: true }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}
