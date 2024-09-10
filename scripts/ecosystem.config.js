module.exports = {
  apps: [
    {
      name: '🏰 Watchtower',
      script: './scripts/start_watchtower.sh',
      cwd: '/home/maos/Mugsy/dev/Operator',
      wait_ready: true,
      listen_timeout: 10000,
      kill_timeout: 3000
    },
    {
      name: '☎️ Operator',
      script: './scripts/start_operator.sh',
      cwd: '/home/maos/Mugsy/dev/Operator',
      wait_ready: true,
      listen_timeout: 10000,
      kill_timeout: 3000,
      depends_on: ['watchtower']
    }
  ]
};