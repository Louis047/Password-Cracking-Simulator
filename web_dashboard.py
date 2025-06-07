from flask import Flask, render_template_string, jsonify
import requests
from common.config import MASTER_URL

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PCS Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status { display: flex; justify-content: space-around; }
        .metric { text-align: center; }
        .metric h3 { margin: 0; color: #333; }
        .metric p { font-size: 24px; font-weight: bold; color: #007bff; margin: 5px 0; }
        .results { max-height: 300px; overflow-y: auto; }
        .result-item { padding: 8px; border-bottom: 1px solid #eee; }
        .success { color: #28a745; }
        .header { text-align: center; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="header">🔐 Password Cracking Simulator Dashboard</h1>
        
        <div class="card">
            <h2>System Status</h2>
            <div class="status">
                <div class="metric">
                    <h3>Active Workers</h3>
                    <p>{{ status.active_workers }}</p>
                </div>
                <div class="metric">
                    <h3>Pending Tasks</h3>
                    <p>{{ status.pending_tasks }}</p>
                </div>
                <div class="metric">
                    <h3>Active Tasks</h3>
                    <p>{{ status.active_tasks }}</p>
                </div>
                <div class="metric">
                    <h3>Completed Results</h3>
                    <p>{{ status.completed_results }}</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Cracked Passwords</h2>
            <div class="results">
                {% if results %}
                    {% for task_id, password in results %}
                    <div class="result-item success">
                        <strong>Task {{ task_id }}:</strong> '{{ password }}'
                    </div>
                    {% endfor %}
                {% else %}
                    <p>No passwords cracked yet...</p>
                {% endif %}
            </div>
        </div>
        
        <div class="card">
            <p><em>Page auto-refreshes every 5 seconds</em></p>
            <p><strong>API Endpoints:</strong></p>
            <ul>
                <li><a href="/api/status">/api/status</a> - System status</li>
                <li><a href="/api/results">/api/results</a> - Cracked passwords</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    try:
        # Get status
        status_response = requests.get(f"{MASTER_URL}/status", timeout=5)
        status = status_response.json() if status_response.status_code == 200 else {}
        
        # Get results
        results_response = requests.get(f"{MASTER_URL}/results", timeout=5)
        results = results_response.json().get('results', []) if results_response.status_code == 200 else []
        
        return render_template_string(DASHBOARD_HTML, status=status, results=results)
    except Exception as e:
        return f"Error connecting to master: {e}"

@app.route('/api/status')
def api_status():
    try:
        response = requests.get(f"{MASTER_URL}/status", timeout=5)
        return response.json() if response.status_code == 200 else {"error": "Master not available"}
    except Exception as e:
        return {"error": str(e)}

@app.route('/api/results')
def api_results():
    try:
        response = requests.get(f"{MASTER_URL}/results", timeout=5)
        return response.json() if response.status_code == 200 else {"results": []}
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    print("🌐 Starting PCS Web Dashboard on http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)