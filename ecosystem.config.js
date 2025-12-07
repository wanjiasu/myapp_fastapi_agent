module.exports = {
  apps : [{
    name        : "tele_agent_eval",
    script      : "uvicorn",
    args        : "fastapi_app:app --host 0.0.0.0 --port 8004",
    interpreter : "env/bin/python",
  }]
}