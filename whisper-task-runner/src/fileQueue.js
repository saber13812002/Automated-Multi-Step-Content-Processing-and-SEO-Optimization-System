const fs = require('fs-extra');
const path = require('path');
const config = require('./config');

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
 * Check if file has a lock file
 * @param {string} filePath - Path to video file
 * @returns {boolean} - True if lock exists
 */
function hasLockFile(filePath) {
  const lockPath = filePath + config.lockExtension;
  return fs.existsSync(lockPath);
}

/**
 * Create a lock file for a video file
 * @param {string} filePath - Path to video file
 * @returns {Promise<void>}
 */
async function createLockFile(filePath) {
  const lockPath = filePath + config.lockExtension;
  await fs.writeFile(lockPath, JSON.stringify({
    machineId: config.machineId,
    lockedAt: new Date().toISOString(),
  }), 'utf8');
}

/**
 * Remove lock file for a video file
 * @param {string} filePath - Path to video file
 * @returns {Promise<void>}
 */
async function removeLockFile(filePath) {
  const lockPath = filePath + config.lockExtension;
  if (await fs.pathExists(lockPath)) {
    await fs.remove(lockPath);
  }
}

/**
 * Scan input directory for video files that need processing
 * @returns {Promise<Array<string>>} - Array of file paths ready for processing
 */
async function scanInputDirectory() {
  const files = [];
  
  if (!(await fs.pathExists(config.inputDir))) {
    return files;
  }
  
  const entries = await fs.readdir(config.inputDir, { withFileTypes: true });
  
  for (const entry of entries) {
    if (entry.isFile()) {
      const filePath = path.join(config.inputDir, entry.name);
      const ext = path.extname(filePath).toLowerCase();
      
      if (VIDEO_EXTENSIONS.includes(ext)) {
        // Skip if SRT already exists
        if (hasSrtFile(filePath)) {
          continue;
        }
        
        // Skip if locked
        if (hasLockFile(filePath)) {
          continue;
        }
        
        files.push(filePath);
      }
    }
  }
  
  return files;
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

module.exports = {
  scanInputDirectory,
  hasSrtFile,
  hasLockFile,
  createLockFile,
  removeLockFile,
  getOutputPath,
};

