const { exec } = require('child_process');
const util = require('util');
const path = require('path');
const fs = require('fs-extra');
const config = require('./config');

const execPromise = util.promisify(exec);

const VIDEO_EXTENSIONS = ['.mp4', '.m4v', '.mp3', '.m4a', '.wav', '.aac', '.flac', '.ogg', '.mkv', '.webm', '.avi'];

/**
 * Check if file has a corresponding SRT file
 * @param {string} filePath - Path to video file
 * @returns {boolean} - True if SRT exists
 */
function hasSrtFile(filePath) {
  const srtPath = path.join(path.dirname(filePath), path.basename(filePath, path.extname(filePath)) + '.srt');
  return fs.existsSync(srtPath);
}

/**
 * Get output path for a video file
 * @param {string} inputPath - Input video file path
 * @returns {string} - Output SRT file path
 */
function getOutputPath(inputPath) {
  const dir = path.dirname(inputPath);
  const basename = path.basename(inputPath, path.extname(inputPath));
  return path.join(dir, basename + '.srt');
}

/**
 * Process video file with Whisper
 * @param {string} inputPath - Path to input video file
 * @returns {Promise<{success: boolean, outputPath?: string, error?: string}>}
 */
async function processFile(inputPath) {
  const outputPath = getOutputPath(inputPath);
  const startTime = Date.now();
  
  try {
    const command = `whisper "${inputPath}" --model ${config.whisperModel} --language ${config.whisperLanguage} --output_dir "${path.dirname(outputPath)}" --output_format srt --device cuda`;
    
    console.log(`Processing ${inputPath} with Whisper...`);
    const { stdout, stderr } = await execPromise(command);
    
    // Whisper creates output file with same name as input but .srt extension
    const expectedOutput = path.join(
      path.dirname(outputPath),
      path.basename(inputPath, path.extname(inputPath)) + '.srt'
    );
    
    // If output path is different, move/rename it
    if (expectedOutput !== outputPath && await fs.pathExists(expectedOutput)) {
      await fs.move(expectedOutput, outputPath, { overwrite: true });
    }
    
    const duration = Math.round((Date.now() - startTime) / 1000);
    console.log(`✅ Successfully processed: ${inputPath} (${duration}s)`);
    
    return {
      success: true,
      outputPath,
      duration,
    };
  } catch (error) {
    const duration = Math.round((Date.now() - startTime) / 1000);
    console.error(`❌ Error processing ${inputPath}:`, error.message);
    
    return {
      success: false,
      error: error.message,
      duration,
    };
  }
}

/**
 * Run the whisper processing job
 * @returns {Promise<Object>} - Job report
 */
async function runJob() {
  console.log('🔄 Starting Whisper cron job...');
  const jobStartTime = Date.now();
  
  const report = {
    startTime: new Date().toISOString(),
    processed: [],
    successful: 0,
    failed: 0,
    totalDuration: 0,
  };
  
  try {
    // Scan input directory
    if (!(await fs.pathExists(config.inputDir))) {
      console.warn(`⚠️ Input directory does not exist: ${config.inputDir}`);
      return {
        ...report,
        error: 'Input directory does not exist',
      };
    }
    
    const entries = await fs.readdir(config.inputDir, { withFileTypes: true });
    const videoFiles = [];
    
    for (const entry of entries) {
      if (entry.isFile()) {
        const filePath = path.join(config.inputDir, entry.name);
        const ext = path.extname(filePath).toLowerCase();
        
        if (VIDEO_EXTENSIONS.includes(ext) && !hasSrtFile(filePath)) {
          videoFiles.push(filePath);
        }
      }
    }
    
    console.log(`📁 Found ${videoFiles.length} video files to process`);
    
    // Process each file
    for (const filePath of videoFiles) {
      const result = await processFile(filePath);
      report.processed.push({
        file: path.basename(filePath),
        ...result,
      });
      
      if (result.success) {
        report.successful++;
      } else {
        report.failed++;
      }
      
      report.totalDuration += result.duration || 0;
    }
    
    report.endTime = new Date().toISOString();
    report.totalDuration = Math.round((Date.now() - jobStartTime) / 1000);
    
    console.log(`✅ Job completed: ${report.successful} successful, ${report.failed} failed`);
    
    return report;
  } catch (error) {
    console.error('❌ Error in cron job:', error);
    return {
      ...report,
      error: error.message,
    };
  }
}

module.exports = {
  runJob,
};

