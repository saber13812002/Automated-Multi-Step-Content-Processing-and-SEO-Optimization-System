const config = require('./config');
const server = require('./server');
const cron = require('./cron');

async function main() {
  console.log('🚀 Starting Whisper Cron Worker...');
  
  // Initialize config
  await config.init();
  
  // Start API server
  server.start();
  
  // Start cron job
  cron.start();
}

main().catch((error) => {
  console.error('❌ Fatal error:', error);
  process.exit(1);
});

