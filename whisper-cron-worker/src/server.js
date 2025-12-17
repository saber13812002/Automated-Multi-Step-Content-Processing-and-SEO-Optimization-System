const express = require('express');
const cors = require('cors');
const config = require('./config');
const cron = require('./cron');
const whisperJob = require('./whisperJob');

const app = express();

app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    cronEnabled: config.cronEnabled,
    cronSchedule: config.cronSchedule,
  });
});

// Get cron status
app.get('/api/cron/status', (req, res) => {
  res.json({
    enabled: config.cronEnabled,
    schedule: config.cronSchedule,
  });
});

// Enable cron
app.post('/api/cron/enable', async (req, res) => {
  try {
    await config.setCronEnabled(true);
    cron.restart();
    res.json({ message: 'Cron enabled', enabled: true });
  } catch (error) {
    console.error('Error enabling cron:', error);
    res.status(500).json({ error: error.message });
  }
});

// Disable cron
app.post('/api/cron/disable', async (req, res) => {
  try {
    await config.setCronEnabled(false);
    cron.stop();
    res.json({ message: 'Cron disabled', enabled: false });
  } catch (error) {
    console.error('Error disabling cron:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update cron schedule
app.post('/api/cron/schedule', async (req, res) => {
  try {
    const { schedule } = req.body;
    
    if (!schedule) {
      return res.status(400).json({ error: 'schedule is required' });
    }
    
    // Validate cron expression (basic check)
    if (!/^[\d\*\s\,\-]+$/.test(schedule.split(' ').slice(0, 5).join(' '))) {
      return res.status(400).json({ error: 'Invalid cron schedule format' });
    }
    
    // Update schedule (would need to persist this)
    config.cronSchedule = schedule;
    cron.restart();
    
    res.json({ message: 'Schedule updated', schedule });
  } catch (error) {
    console.error('Error updating schedule:', error);
    res.status(500).json({ error: error.message });
  }
});

// Run job manually
app.post('/api/job/run', async (req, res) => {
  try {
    console.log('Manual job execution triggered via API');
    const report = await whisperJob.runJob();
    await require('./notifier').sendReport(report);
    res.json({ message: 'Job completed', report });
  } catch (error) {
    console.error('Error running job:', error);
    res.status(500).json({ error: error.message });
  }
});

function start() {
  app.listen(config.apiPort, '0.0.0.0', () => {
    console.log(`🚀 API server listening on port ${config.apiPort}`);
    console.log(`📁 Input directory: ${config.inputDir}`);
    console.log(`📁 Output directory: ${config.outputDir}`);
    console.log(`⏰ Cron schedule: ${config.cronSchedule}`);
    console.log(`🔔 Cron enabled: ${config.cronEnabled}`);
  });
}

module.exports = { start, app };

