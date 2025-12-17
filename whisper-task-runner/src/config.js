require('dotenv').config();

const config = {
  // Server
  apiPort: parseInt(process.env.API_PORT || '3000', 10),
  nodeEnv: process.env.NODE_ENV || 'production',
  
  // Time window for GPU usage
  activeStartHour: parseInt(process.env.ACTIVE_START_HOUR || '23', 10),
  activeEndHour: parseInt(process.env.ACTIVE_END_HOUR || '5', 10),
  timezone: process.env.TIMEZONE || 'Asia/Tehran',
  
  // File paths
  inputDir: process.env.INPUT_DIR || '/media/input',
  outputDir: process.env.OUTPUT_DIR || '/media/output',
  lockExtension: process.env.LOCK_EXTENSION || '.lock',
  batchSize: parseInt(process.env.BATCH_SIZE || '2', 10),
  
  // Machine identification
  machineId: process.env.MACHINE_ID || 'worker-1',
  
  // MySQL configuration
  mysql: {
    host: process.env.MYSQL_HOST || 'mysql',
    port: parseInt(process.env.MYSQL_PORT || '3306', 10),
    user: process.env.MYSQL_USER || 'whisper',
    password: process.env.MYSQL_PASSWORD || 'whisper123',
    database: process.env.MYSQL_DATABASE || 'whisper_tasks',
  },
  
  // Task timeout
  taskTimeoutMinutes: parseInt(process.env.TASK_TIMEOUT_MINUTES || '120', 10),
  
  // Whisper model settings
  whisperModel: process.env.WHISPER_MODEL || 'large',
  whisperLanguage: process.env.WHISPER_LANGUAGE || 'ar',
};

/**
 * Check if current time is within the active window for GPU usage
 * @param {Date} now - Current date/time (defaults to now)
 * @returns {boolean} - True if within active window
 */
function isWithinActiveWindow(now = new Date()) {
  const hour = now.getHours();
  const startHour = config.activeStartHour;
  const endHour = config.activeEndHour;
  
  // Handle case where window crosses midnight (e.g., 23:00 to 05:00)
  if (startHour > endHour) {
    return hour >= startHour || hour < endHour;
  } else {
    return hour >= startHour && hour < endHour;
  }
}

/**
 * Get milliseconds until next active window starts
 * @param {Date} now - Current date/time
 * @returns {number} - Milliseconds until next active window
 */
function getMsUntilNextActiveWindow(now = new Date()) {
  const currentHour = now.getHours();
  const startHour = config.activeStartHour;
  
  let nextStart = new Date(now);
  nextStart.setHours(startHour, 0, 0, 0);
  
  // If we're past the start hour today, move to tomorrow
  if (currentHour >= startHour) {
    nextStart.setDate(nextStart.getDate() + 1);
  }
  
  return nextStart.getTime() - now.getTime();
}

module.exports = {
  ...config,
  isWithinActiveWindow,
  getMsUntilNextActiveWindow,
};

