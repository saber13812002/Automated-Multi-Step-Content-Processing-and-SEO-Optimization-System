const axios = require('axios');
const config = require('./config');

/**
 * Send report to webhook
 * @param {Object} report - Job report object
 * @returns {Promise<boolean>} - True if successful
 */
async function sendToWebhook(report) {
  if (!config.reportWebhookUrl) {
    return false;
  }
  
  try {
    await axios.post(config.reportWebhookUrl, {
      type: 'whisper_cron_report',
      ...report,
    });
    console.log('✅ Report sent to webhook');
    return true;
  } catch (error) {
    console.error('❌ Error sending report to webhook:', error.message);
    return false;
  }
}

/**
 * Send report to Telegram
 * @param {Object} report - Job report object
 * @returns {Promise<boolean>} - True if successful
 */
async function sendToTelegram(report) {
  if (!config.telegramBotToken || !config.telegramChatId) {
    return false;
  }
  
  try {
    const message = formatTelegramMessage(report);
    const url = `https://api.telegram.org/bot${config.telegramBotToken}/sendMessage`;
    
    await axios.post(url, {
      chat_id: config.telegramChatId,
      text: message,
      parse_mode: 'HTML',
    });
    
    console.log('✅ Report sent to Telegram');
    return true;
  } catch (error) {
    console.error('❌ Error sending report to Telegram:', error.message);
    return false;
  }
}

/**
 * Format report as Telegram message
 * @param {Object} report - Job report object
 * @returns {string} - Formatted message
 */
function formatTelegramMessage(report) {
  let message = '<b>🤖 Whisper Cron Job Report</b>\n\n';
  
  message += `📅 <b>Start:</b> ${new Date(report.startTime).toLocaleString()}\n`;
  message += `📅 <b>End:</b> ${new Date(report.endTime).toLocaleString()}\n`;
  message += `⏱️ <b>Duration:</b> ${report.totalDuration}s\n\n`;
  
  message += `✅ <b>Successful:</b> ${report.successful}\n`;
  message += `❌ <b>Failed:</b> ${report.failed}\n`;
  message += `📊 <b>Total:</b> ${report.processed.length}\n\n`;
  
  if (report.failed > 0) {
    message += '<b>Failed Files:</b>\n';
    report.processed
      .filter(p => !p.success)
      .forEach(p => {
        message += `❌ ${p.file}: ${p.error || 'Unknown error'}\n`;
      });
  }
  
  if (report.successful > 0) {
    message += '\n<b>Successful Files:</b>\n';
    report.processed
      .filter(p => p.success)
      .slice(0, 10) // Limit to first 10
      .forEach(p => {
        message += `✅ ${p.file} (${p.duration}s)\n`;
      });
    
    if (report.successful > 10) {
      message += `... and ${report.successful - 10} more\n`;
    }
  }
  
  return message;
}

/**
 * Send report via all configured channels
 * @param {Object} report - Job report object
 * @returns {Promise<void>}
 */
async function sendReport(report) {
  const promises = [];
  
  if (config.reportWebhookUrl) {
    promises.push(sendToWebhook(report));
  }
  
  if (config.telegramBotToken && config.telegramChatId) {
    promises.push(sendToTelegram(report));
  }
  
  if (promises.length === 0) {
    console.log('⚠️ No notification channels configured');
    return;
  }
  
  await Promise.allSettled(promises);
}

module.exports = {
  sendReport,
  sendToWebhook,
  sendToTelegram,
};

