const { exec } = require('child_process');
const util = require('util');
const path = require('path');
const fs = require('fs-extra');
const config = require('./config');

const execPromise = util.promisify(exec);

/**
 * Process video file with Whisper to generate SRT subtitle
 * @param {string} inputPath - Path to input video file
 * @param {string} outputPath - Path to output SRT file
 * @returns {Promise<void>}
 */
async function processWithWhisper(inputPath, outputPath) {
  // Use whisper CLI command
  // Note: This assumes whisper is installed via pip (openai-whisper)
  // The model will be downloaded and cached in /root/.cache/whisper
  
  // Ensure output directory exists
  await fs.ensureDir(path.dirname(outputPath));
  
  const outputDir = path.dirname(outputPath);
  const command = `whisper "${inputPath}" --model ${config.whisperModel} --language ${config.whisperLanguage} --output_dir "${outputDir}" --output_format srt --device cuda`;
  
  try {
    console.log(`Processing ${inputPath} with Whisper...`);
    const { stdout, stderr } = await execPromise(command);
    
    // Whisper creates output file with same name as input but .srt extension
    const expectedOutput = path.join(
      outputDir,
      path.basename(inputPath, path.extname(inputPath)) + '.srt'
    );
    
    // If output path is different, move/rename it
    if (expectedOutput !== outputPath && await fs.pathExists(expectedOutput)) {
      await fs.move(expectedOutput, outputPath, { overwrite: true });
    }
    
    // Verify output file exists
    if (!(await fs.pathExists(outputPath))) {
      throw new Error(`Output file was not created: ${outputPath}`);
    }
    
    console.log(`Whisper processing completed: ${outputPath}`);
    if (stdout) {
      console.log(stdout);
    }
    if (stderr) {
      console.error('Whisper stderr:', stderr);
    }
  } catch (error) {
    console.error(`Error processing with Whisper: ${error.message}`);
    throw error;
  }
}

module.exports = {
  processWithWhisper,
};

