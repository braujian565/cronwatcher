# cronwatcher

Lightweight daemon that monitors cron job execution and sends alerts on failures.

## Installation

```bash
pip install cronwatcher
```

## Usage

Define your monitored jobs in a `cronwatcher.yaml` config file:

```yaml
jobs:
  backup:
    schedule: "0 2 * * *"
    timeout: 300
    alert:
      email: ops@example.com

  cleanup:
    schedule: "*/15 * * * *"
    timeout: 60
    alert:
      slack: "#alerts"
```

Start the daemon:

```bash
cronwatcher start --config cronwatcher.yaml
```

Wrap any existing cron command to report its status:

```bash
cronwatcher run --job backup -- /usr/local/bin/backup.sh
```

Check the status of monitored jobs:

```bash
cronwatcher status
```

## Features

- Detects missed executions, timeouts, and non-zero exit codes
- Supports email and Slack alert channels
- Minimal dependencies, runs as a lightweight background daemon
- Simple YAML-based configuration

## License

MIT © cronwatcher contributors