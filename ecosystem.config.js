module.exports = {
  apps : [{
    name   : "tele_agent_eval",
    script : "env/bin/python",
    args   : "-m uvicorn fastapi_app:app --host 0.0.0.0 --port 8004",
  }]
}