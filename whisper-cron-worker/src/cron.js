const cron = require('node-cron');
const config = require('./config');
const whisperJob = require('./whisperJob');
const notifier = require('./notifier');

let cronTask = null;

/**
 * Execute the cron job
 */
async function executeJob() {
  if (!config.cronEnabled) {
    console.log('⏸️ Cron is disabled, skipping job execution');
    return;
  }
  
  try {
    const report = await whisperJob.runJob();
    await notifier.sendReport(report);
  } catch (error) {
    console.error('❌ Error executing cron job:', error);
    
    // Send error report
    await notifier.sendReport({
      startTime: new Date().toISOString(),
      endTime: new Date().toISOString(),
      error: error.message,
      successful: 0,
      failed: 0,
      processed: [],
      totalDuration: 0,
    });
  }
}

/**
 * Start the cron job
 */
function start() {
  if (cronTask) {
    console.log('⚠️ Cron job already running');
    return;
  }
  
  if (!config.cronEnabled) {
    console.log('⏸️ Cron is disabled, not starting scheduler');
    return;
  }
  
  console.log(`🕐 Starting cron job with schedule: ${config.cronSchedule}`);
  
  cronTask = cron.schedule(config.cronSchedule, async () => {
    console.log('⏰ Cron job triggered');
    await executeJob();
  }, {
    scheduled: true,
    timezone: 'Asia/Tehran',
  });
  
  console.log('✅ Cron job started');
  
  // Run immediately if enabled
  if (config.cronEnabled) {
    console.log('🚀 Running initial job...');
    executeJob();
  }
}

/**
 * Stop the cron job
 */
function stop() {
  if (cronTask) {
    cronTask.stop();
    cronTask = null;
    console.log('⏹️ Cron job stopped');
  }
}

/**
 * Restart the cron job
 */
function restart() {
  stop();
  start();
}

module.exports = {
  start,
  stop,
  restart,
  executeJob,
};

