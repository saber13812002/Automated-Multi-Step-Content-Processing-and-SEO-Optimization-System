require('dotenv').config();
const fs = require('fs-extra');
const path = require('path');

const CONFIG_FILE = '/app/config/cron.json';

// Default config
let cronConfig = {
  enabled: process.env.CRON_ENABLED === 'true' || process.env.CRON_ENABLED === '1',
};

// Load config from file if exists
async function loadConfig() {
  try {
    if (await fs.pathExists(CONFIG_FILE)) {
      const fileContent = await fs.readFile(CONFIG_FILE, 'utf8');
      cronConfig = { ...cronConfig, ...JSON.parse(fileContent) };
    }
  } catch (error) {
    console.warn('Could not load config file, using defaults:', error.message);
  }
}

// Save config to file
async function saveConfig() {
  try {
    await fs.ensureDir(path.dirname(CONFIG_FILE));
    await fs.writeFile(CONFIG_FILE, JSON.stringify(cronConfig, null, 2), 'utf8');
  } catch (error) {
    console.error('Could not save config file:', error.message);
  }
}

const config = {
  // Server
  apiPort: parseInt(process.env.API_PORT || '3001', 10),
  nodeEnv: process.env.NODE_ENV || 'production',
  
  // Cron settings
  cronSchedule: process.env.CRON_SCHEDULE || '0 * * * *', // Every hour
  get cronEnabled() {
    return cronConfig.enabled;
  },
  setCronEnabled: async (enabled) => {
    cronConfig.enabled = enabled;
    await saveConfig();
  },
  
  // File paths
  inputDir: process.env.INPUT_DIR || '/media/input',
  outputDir: process.env.OUTPUT_DIR || '/media/output',
  
  // Whisper model settings
  whisperModel: process.env.WHISPER_MODEL || 'large',
  whisperLanguage: process.env.WHISPER_LANGUAGE || 'ar',
  
  // Notification settings
  reportWebhookUrl: process.env.REPORT_WEBHOOK_URL || '',
  telegramBotToken: process.env.TELEGRAM_BOT_TOKEN || '',
  telegramChatId: process.env.TELEGRAM_CHAT_ID || '',
  
  // Initialize
  init: loadConfig,
};

module.exports = config;

