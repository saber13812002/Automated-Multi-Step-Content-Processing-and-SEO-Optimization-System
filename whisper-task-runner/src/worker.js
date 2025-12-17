const config = require('./config');
const db = require('./db');
const fileQueue = require('./fileQueue');
const whisperProcessor = require('./whisperProcessor');

let isRunning = false;
let shouldStop = false;

/**
 * Process a single file
 * @param {string} filePath - Path to video file
 * @param {number} taskId - Optional task ID from database
 * @returns {Promise<boolean>} - True if successful
 */
async function processFile(filePath, taskId = null) {
  const outputPath = fileQueue.getOutputPath(filePath);
  
  try {
    // Create lock file
    await fileQueue.createLockFile(filePath);
    
    // Process with Whisper
    await whisperProcessor.processWithWhisper(filePath, outputPath);
    
    // Update database if task exists
    if (taskId) {
      await db.completeTask(taskId, outputPath);
    }
    
    // Remove lock file
    await fileQueue.removeLockFile(filePath);
    
    console.log(`✅ Successfully processed: ${filePath}`);
    return true;
  } catch (error) {
    console.error(`❌ Error processing ${filePath}:`, error.message);
    
    // Update database if task exists
    if (taskId) {
      await db.failTask(taskId, error.message);
    }
    
    // Remove lock file on error
    await fileQueue.removeLockFile(filePath).catch(() => {});
    
    return false;
  }
}

/**
 * Main worker loop
 */
async function workerLoop() {
  if (isRunning) {
    return;
  }
  
  isRunning = true;
  console.log('Worker loop started');
  
  while (!shouldStop) {
    try {
      // Check if we're within active time window
      if (!config.isWithinActiveWindow()) {
        const msUntilNext = config.getMsUntilNextActiveWindow();
        console.log(`⏸️ Outside active window. Waiting ${Math.round(msUntilNext / 1000 / 60)} minutes until next window...`);
        
        // Wait until next active window or stop signal
        await new Promise((resolve) => {
          const timeout = setTimeout(resolve, msUntilNext);
          const checkInterval = setInterval(() => {
            if (shouldStop) {
              clearTimeout(timeout);
              clearInterval(checkInterval);
              resolve();
            }
          }, 1000);
        });
        
        if (shouldStop) break;
        continue;
      }
      
      // Scan input directory for files
      const files = await fileQueue.scanInputDirectory();
      
      // If no files in directory, check database
      if (files.length === 0) {
        console.log('📁 No files in input directory, checking database...');
        const dbTasks = await db.getPendingTasks(config.batchSize);
        
        if (dbTasks.length === 0) {
          console.log('✅ No tasks available. Worker will stop.');
          shouldStop = true;
          break;
        }
        
        // Process database tasks
        for (const task of dbTasks) {
          if (shouldStop) break;
          
          const taskFilePath = task.input_path;
          if (await require('fs-extra').pathExists(taskFilePath)) {
            await processFile(taskFilePath, task.id);
          } else {
            console.warn(`⚠️ File not found: ${taskFilePath}`);
            await db.failTask(task.id, 'File not found');
          }
        }
      } else {
        // Process files from directory (in batches)
        const batch = files.slice(0, config.batchSize);
        
        for (const filePath of batch) {
          if (shouldStop) break;
          await processFile(filePath);
        }
      }
      
      // Small delay between iterations
      await new Promise((resolve) => setTimeout(resolve, 1000));
      
    } catch (error) {
      console.error('❌ Error in worker loop:', error);
      await new Promise((resolve) => setTimeout(resolve, 5000)); // Wait before retry
    }
  }
  
  isRunning = false;
  console.log('Worker loop stopped');
  
  // Graceful shutdown
  if (shouldStop) {
    console.log('Shutting down gracefully...');
    process.exit(0);
  }
}

/**
 * Start the worker
 */
function start() {
  console.log('Starting worker...');
  db.initPool();
  workerLoop();
}

/**
 * Stop the worker
 */
function stop() {
  console.log('Stopping worker...');
  shouldStop = true;
}

// Handle graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down...');
  stop();
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down...');
  stop();
});

module.exports = {
  start,
  stop,
  isRunning: () => isRunning,
};

